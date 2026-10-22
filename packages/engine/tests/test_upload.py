"""N8 by upload (goals/n8-upload-on-marking.yaml, ADR 0092): an educator puts a scan in on Marking, and the browser sends
it straight to the engine (`POST /read/upload`) with a short-lived token the site signs. What is tested: what the engine
takes and where it puts it, that the reading starts for the run the caller is told about, what it refuses and in what
words, and that a page with no code is kept by its page number. No network; the reading itself is stood in for, as in
`test_inbox`, except in the last test, which reads a printed paper as `test_a_scan_read_whole` does."""

import hashlib
import hmac
import io
import time
from base64 import urlsafe_b64encode

import pillow_heif
import pymupdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from engine.api import deps
from engine.api.app import app
from engine.w3_read import copies, inbox
from tests import test_copies
from tests.test_a_scan_read_whole import _printed
from tests.test_copies import stand_in_reader
from tests.test_inbox import KEY, RUN, _pdf
from tests.test_sorting import _scanned

conn, worksheet = test_copies.conn, test_copies.worksheet


def token(who="achal@school", ttl=600, key=KEY):
    """A token as the site signs one (apps/web/lib/engine.ts `uploadTicket`)."""
    body = f"{urlsafe_b64encode(who.encode()).decode().rstrip('=')}.{int((time.time() + ttl) * 1000)}"
    return f"{body}.{hmac.new(key.encode(), f'upload.{body}'.encode(), hashlib.sha256).hexdigest()}"


def _photo(colour, fmt="JPEG"):
    out = io.BytesIO()
    img = Image.new("RGB", (60, 80), colour)
    if fmt == "HEIF":
        pillow_heif.from_pillow(img).save(out, quality=80)
    else:
        img.save(out, fmt)
    return out.getvalue()


@pytest.fixture
def upload(monkeypatch, tmp_path):
    """The engine as the browser reaches it, the run and the reading stood in for: → (post, what was started)."""
    monkeypatch.setenv("ENGINE_KEY", KEY)
    monkeypatch.setattr(inbox, "INBOX", tmp_path / "inbox")
    monkeypatch.setattr(deps, "tenant_now", lambda: "tenant-1")
    started = []
    monkeypatch.setattr(
        inbox,
        "start",
        lambda tenant, path, actor, pages=None: started.append((tenant, path, actor, pages)) or RUN,
    )
    monkeypatch.setattr(
        inbox, "read", lambda run_id, path, actor, again=False: started.append(("read", run_id, path))
    )
    with TestClient(app) as c:

        def post(files, tok=None):
            return c.post(
                "/read/upload",
                files=[("file", f) for f in files],
                headers={"X-Upload-Token": token() if tok is None else tok, "Origin": "https://site.example"},
            )

        yield post, started


def test_an_uploaded_pdf_lands_in_the_inbox_and_its_reading_starts(upload, tmp_path):
    post, started = upload
    r = post([("24 sept.pdf", _pdf(16), "application/pdf")])
    assert r.status_code == 200, r.text
    assert r.json() == {"run_id": RUN, "pages": 16, "file": "24 sept.pdf"}
    saved = tmp_path / "inbox" / "24 sept.pdf"
    assert saved.read_bytes().startswith(b"%PDF") and len(pymupdf.open(saved)) == 16
    assert started == [("tenant-1", saved, "achal@school", 16), ("read", RUN, saved)]
    # the browser is on the site's own address, not the engine's: it may read the answer
    assert r.headers["access-control-allow-origin"] in ("*", "https://site.example")


def test_photos_of_one_paper_become_one_pdf_in_page_order(upload, tmp_path):
    post, started = upload
    # chosen in any order; a phone names its photos in the order they were taken
    r = post(
        [
            ("IMG_0012.HEIC", _photo("blue", "HEIF"), "image/heic"),
            ("IMG_0002.jpg", _photo("red"), "image/jpeg"),
            ("IMG_0010.png", _photo("green", "PNG"), "image/png"),
        ]
    )
    assert r.status_code == 200, r.text
    assert r.json()["pages"] == 3 and r.json()["file"] == "IMG_0002.pdf"
    with pymupdf.open(tmp_path / "inbox" / "IMG_0002.pdf") as doc:
        colours = [doc[i].get_pixmap().pixel(10, 10) for i in range(len(doc))]
    red, green, blue = colours
    assert red[0] > 200 > red[2] and green[1] > 100 > green[0] and blue[2] > 200 > blue[0], colours
    assert started[0][3] == 3


def test_a_file_not_a_pdf_or_a_photo_is_refused_in_words(upload):
    post, started = upload
    r = post([("marks.xlsx", b"PK\x03\x04 a spreadsheet", "application/vnd.ms-excel")])
    assert (
        r.status_code == 415 and r.json()["detail"] == "marks.xlsx is not a PDF or a photo (JPG, PNG or HEIC)"
    )
    # named .pdf, but not one
    r = post([("scan.pdf", b"<html>sign in</html>", "application/pdf")])
    assert r.status_code == 415 and "scan.pdf is not a PDF or a photo" in r.json()["detail"]
    # a PDF is read alone: photos are pages of one paper, a PDF is a file of its own
    r = post([("a.pdf", _pdf(2), "application/pdf"), ("b.jpg", _photo("red"), "image/jpeg")])
    assert (
        r.status_code == 400 and r.json()["detail"] == "send a PDF on its own; photos together are one paper"
    )
    assert started == [], "nothing refused is read"


def test_a_file_larger_than_a_scan_of_a_class_is_refused(upload, monkeypatch):
    post, started = upload
    monkeypatch.setattr(inbox, "MOST", 2**20)
    r = post([("big.pdf", _pdf(1) + b"0" * (3 * 2**19), "application/pdf")])
    assert (
        r.status_code == 413
        and r.json()["detail"] == "big.pdf is larger than any scan of a class (1 MB at most)"
    )
    # far larger: refused on its size alone, before the engine takes it in
    r = post([("huge.pdf", _pdf(1) + b"0" * (3 * 2**20), "application/pdf")])
    assert r.status_code == 413 and "larger than any scan of a class" in r.json()["detail"]
    assert started == []


def test_only_the_sites_own_fresh_token_may_upload(upload):
    post, started = upload
    one = [("24 sept.pdf", _pdf(1), "application/pdf")]
    assert post(one, tok="").status_code == 401
    assert post(one, tok=token(ttl=-5)).status_code == 401, "an old token"
    assert post(one, tok=token(ttl=24 * 3600)).status_code == 401, "a token that lives too long"
    assert post(one, tok=token(key="not-the-engine-key")).status_code == 401, "signed by anyone else"
    body, _, mac = token().rpartition(".")
    assert post(one, tok=f"{token(who='someone@else').rpartition('.')[0]}.{mac}").status_code == 401
    assert started == []
    # the engine's own key is not a token, and the browser is never given it
    assert post(one, tok=KEY).status_code == 401


def test_a_page_with_no_readable_code_is_kept_by_its_page_number(conn, worksheet, tmp_path, monkeypatch):
    kids, page, n, ids = _printed(conn, worksheet, tmp_path, ["71", "72"])
    stand_in_reader(conn, ids, monkeypatch)
    blank = tmp_path / "blank.pdf"
    doc = pymupdf.open()
    doc.new_page(width=595, height=842)
    doc.save(blank)
    # both children's copies, then a page whose code cannot be read
    scan = _scanned([*page[: 2 * n], blank], tmp_path / "with-a-blank.pdf")

    got = copies.read(conn, scan, "", None, "test")
    assert [(c["child_id"], c["answers"]) for c in got[:2]] == [(k, len(ids)) for k in kids], (
        "both read whole"
    )
    assert [c["no_code"] for c in got] == [[], [], [2 * n + 1]], "the page is named by its number"
    assert (got[2]["child_id"], got[2]["skipped"], got[2]["why"]) == (
        None,
        True,
        "no code could be read on the page",
    )
