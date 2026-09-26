"""A scan arrives as a Drive link and is read without anyone at a terminal (`w3_read/inbox.py`, `POST /read/file`).
No network and no database: the download and the reading are stood in for; what is tested is what the engine
accepts, where it puts the file, and that the reading is started for the run the caller is told about."""

import pymupdf
import pytest
from fastapi.testclient import TestClient

from engine.api import deps
from engine.api.app import app
from engine.w3_read import copies, inbox

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


RUN = "11111111-1111-1111-1111-111111111111"


class _Conn:
    """A connection that says when its transaction ended: `db.connect` commits on leaving its block."""

    def __init__(self, log):
        self.log = log

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.log.append("run committed")

    def execute(self, sql, params=None):
        self.log.append(sql.split(" (")[0])
        return self

    def fetchone(self):
        return {"id": RUN}


def test_the_run_is_committed_on_its_own_before_the_reading_starts(tmp_path, monkeypatch):
    """2026-09-25, the first live run: FastAPI runs a background task BEFORE the request's own transaction
    commits, so a run written on the request's connection was invisible for the whole reading ("no run")."""
    log = []
    monkeypatch.setattr(inbox.db, "connect", lambda *a, **k: _Conn(log))
    assert inbox.start("tenant-1", tmp_path / "24 sept.pdf", "achal@school") == RUN
    assert log == ["insert into flow_run", "run committed"]


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("ENGINE_KEY", KEY)
    app.dependency_overrides[deps.get_conn] = lambda: (yield None)
    app.dependency_overrides[deps.get_tenant_id] = lambda: "tenant-1"
    with TestClient(app, headers={"X-Engine-Key": KEY}) as c:
        yield c, None
    app.dependency_overrides.clear()


def test_the_route_fetches_the_file_answers_at_once_and_reads_it_after(client, tmp_path, monkeypatch):
    c, _ = client
    scan = tmp_path / "24 sept.pdf"
    scan.write_bytes(_pdf(16))
    order = []
    monkeypatch.setattr(inbox, "fetch", lambda url: scan)
    monkeypatch.setattr(
        inbox, "start", lambda tenant, path, actor: order.append(("start", tenant, actor)) or RUN
    )
    monkeypatch.setattr(
        inbox, "read", lambda run_id, path, actor, again=False: order.append(("read", run_id, path, again))
    )
    r = c.post("/read/file", json={"url": LINKS[0], "actor": "achal@school"})
    assert r.status_code == 200, r.text
    assert r.json() == {"run_id": RUN, "pages": 16}
    assert order == [("start", "tenant-1", "achal@school"), ("read", RUN, scan, False)]
    # read again with a better reader: every copy no person has worked on is read afresh
    order.clear()
    assert (
        c.post("/read/file", json={"url": LINKS[0], "actor": "achal@school", "again": True}).status_code
        == 200
    )
    assert order[-1] == ("read", RUN, scan, True)


def test_a_link_the_engine_will_not_take_is_refused_in_words(client, monkeypatch):
    c, _ = client

    def refuse(url):
        raise ValueError("that is not a Google Drive link to a file")

    monkeypatch.setattr(inbox, "fetch", refuse)
    r = c.post("/read/file", json={"url": "https://example.com/x.pdf", "actor": "achal@school"})
    assert r.status_code == 400 and r.json()["detail"] == "that is not a Google Drive link to a file"


def test_a_scans_copies_are_given_by_roll_number_never_by_name(client, monkeypatch):
    c, _ = client
    seen = []
    row = {"copy": "copy01", "section": "G3", "roll_no": "1", "code": "R31-H02", "capture_id": RUN, "answers": 12,
           "right": 9, "wrong": 2, "blank": 1, "unclear": 0, "waiting": 12}  # fmt: skip
    monkeypatch.setattr(copies, "of_scan", lambda conn, name: seen.append(name) or [row])
    r = c.get("/read/scan/24 sept.pdf/copies")
    assert r.status_code == 200 and r.json() == [row] and seen == ["24 sept.pdf"]
    assert "name" not in r.text


class _Tx:
    """A connection that keeps what was committed and throws away the rest, as `db.connect` does on a failure."""

    def __init__(self, kept):
        self.kept, self.pending = kept, []

    def __enter__(self):
        return self

    def __exit__(self, kind, *rest):
        if kind is None:
            self.commit()
        self.pending = []  # rolled back

    def execute(self, sql, params=None):
        self.pending.append((sql, params))
        return self

    def commit(self):
        self.kept += self.pending
        self.pending = []

    def rollback(self):
        self.pending = []


def test_a_reading_that_fails_says_why_on_its_run(tmp_path, monkeypatch):
    """2026-09-25: the reading died on the server's unreadable AWS credentials and its run said "running" for
    25 minutes — the error was written, then rolled back with the failure."""
    kept = []
    monkeypatch.setattr(inbox.db, "connect", lambda *a, **k: _Tx(kept))

    def broken(*a, **k):
        raise RuntimeError("Unable to parse config file: /root/.aws/credentials")

    monkeypatch.setattr(copies, "read", broken)
    with pytest.raises(RuntimeError):
        inbox.read(RUN, tmp_path / "24 sept.pdf", "achal@school")
    [(sql, params)] = kept
    assert "status = 'error'" in sql and params == (
        "RuntimeError: Unable to parse config file: /root/.aws/credentials",
        RUN,
    )
