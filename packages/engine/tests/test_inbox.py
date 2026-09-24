"""A scan arrives as a Drive link and is read without anyone at a terminal (`w3_read/inbox.py`, `POST /read/file`).
No network and no database: the download and the reading are stood in for; what is tested is what the engine
accepts, where it puts the file, and that the reading is started for the run the caller is told about."""

import pymupdf
import pytest
from fastapi.testclient import TestClient

from engine.api import deps
from engine.api.app import app
from engine.w3_read import inbox

KEY = "test-engine-key"
LINKS = [
    "https://drive.google.com/file/d/13Zsrf3B2PDzSbCVWJJaCWObhfAWGQIl6/view?usp=drive_link",
    "https://drive.google.com/open?id=13Zsrf3B2PDzSbCVWJJaCWObhfAWGQIl6",
    "https://drive.google.com/uc?export=download&id=13Zsrf3B2PDzSbCVWJJaCWObhfAWGQIl6",
]


def _pdf(pages=2):
    doc = pymupdf.open()
    for _ in range(pages):
        doc.new_page()
    return doc.tobytes()


@pytest.mark.parametrize("link", LINKS)
def test_a_drive_link_in_any_of_its_forms_names_its_file(link):
    assert inbox.drive_id(link) == "13Zsrf3B2PDzSbCVWJJaCWObhfAWGQIl6"


def test_the_file_lands_in_the_inbox_under_its_own_name_and_only_a_pdf_is_taken(tmp_path, monkeypatch):
    monkeypatch.setattr(inbox, "INBOX", tmp_path / "inbox")
    asked = []

    def download(url):
        asked.append(url)
        return _pdf(), inbox._NAME.search('attachment; filename="24 sept.pdf"')

    out = inbox.fetch(LINKS[0], download)
    assert out == tmp_path / "inbox" / "24 sept.pdf" and out.read_bytes().startswith(b"%PDF")
    assert asked == ["https://drive.google.com/uc?export=download&id=13Zsrf3B2PDzSbCVWJJaCWObhfAWGQIl6"]
    with pytest.raises(ValueError, match="not a Google Drive link"):
        inbox.fetch("https://example.com/scan.pdf", download)
    with pytest.raises(ValueError, match="not a PDF"):
        inbox.fetch(LINKS[0], lambda url: (b"<html>sign in</html>", None))


def test_a_different_file_of_the_same_name_keeps_both(tmp_path, monkeypatch):
    monkeypatch.setattr(inbox, "INBOX", tmp_path / "inbox")
    one = _pdf(1)
    first = inbox.fetch(LINKS[0], lambda url: (one, None))
    again = inbox.fetch(LINKS[0], lambda url: (one, None))
    other = inbox.fetch(LINKS[0], lambda url: (_pdf(3), None))
    assert first == again and other != first and other.parent == first.parent


class _Conn:
    def __init__(self):
        self.sql = []

    def execute(self, sql, params=None):
        self.sql.append((sql, params))
        return self

    def fetchone(self):
        return {"id": "11111111-1111-1111-1111-111111111111"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("ENGINE_KEY", KEY)
    conn = _Conn()
    app.dependency_overrides[deps.get_conn] = lambda: (yield conn)
    app.dependency_overrides[deps.get_tenant_id] = lambda: "tenant-1"
    with TestClient(app, headers={"X-Engine-Key": KEY}) as c:
        yield c, conn
    app.dependency_overrides.clear()


def test_the_route_fetches_the_file_answers_at_once_and_reads_it_after(client, tmp_path, monkeypatch):
    c, conn = client
    scan = tmp_path / "24 sept.pdf"
    scan.write_bytes(_pdf(16))
    read = []
    monkeypatch.setattr(inbox, "fetch", lambda url: scan)
    monkeypatch.setattr(inbox, "read", lambda run_id, path, actor: read.append((run_id, path, actor)))
    r = c.post("/read/file", json={"url": LINKS[0], "actor": "achal@school"})
    assert r.status_code == 200, r.text
    assert r.json() == {"run_id": "11111111-1111-1111-1111-111111111111", "pages": 16}
    assert read == [("11111111-1111-1111-1111-111111111111", scan, "achal@school")]
    assert any("insert into flow_run" in sql and params[1] == inbox.FLOW for sql, params in conn.sql)


def test_a_link_the_engine_will_not_take_is_refused_in_words(client, monkeypatch):
    c, _ = client

    def refuse(url):
        raise ValueError("that is not a Google Drive link to a file")

    monkeypatch.setattr(inbox, "fetch", refuse)
    r = c.post("/read/file", json={"url": "https://example.com/x.pdf", "actor": "achal@school"})
    assert r.status_code == 400 and r.json()["detail"] == "that is not a Google Drive link to a file"
