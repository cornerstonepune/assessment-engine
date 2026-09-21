"""`engine read again` — the corpus read afresh so every unclear answer carries the reader's guess
(goals/s4-validation-queue.yaml). The reader itself is replaced here by a stand-in, so nothing is
sent anywhere: what is tested is the driver — which papers it reads, that it reads them from the
rows the database already holds, and that it names every settled answer whose reading changed.
"""

import os

import pytest

from engine import db, legacy, reread

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def test_every_live_capture_is_read_again_from_its_own_rows(conn, monkeypatch):
    seen = []
    monkeypatch.setattr(
        legacy, "import_scan", lambda c, **kw: seen.append(kw) or {"results": [], "notes": []}
    )
    live = conn.execute(
        "select count(distinct c.id) as n from capture c join item_result r on r.capture_id = c.id"
        " where c.superseded_by is null"
    ).fetchone()["n"]
    out = reread.run(conn, commit=False)
    assert out["read"] + out["missing"] + out["failed"] == live
    assert all(kw["again"] is True and kw["pages"] for kw in seen)
    assert all(kw["child_id"] and kw["paper_code"] for kw in seen)


def test_a_settled_answer_whose_reading_changed_is_named(conn, monkeypatch):
    target = conn.execute(
        "select r.id, r.capture_id from item_result r join capture c on c.id = r.capture_id"
        " where c.superseded_by is null and r.status = 'correct' limit 1"
    ).fetchone()

    def stand_in(c, **kw):  # a reader that now reads one settled answer differently
        c.execute("update item_result set status = 'wrong' where id = %s", (target["id"],))
        return {"results": [], "notes": []}

    monkeypatch.setattr(legacy, "import_scan", stand_in)
    out = reread.run(conn, commit=False)
    assert [c["item_result"] for c in out["changed"]] == [target["id"]]
    assert out["changed"][0]["was"] == "correct" and out["changed"][0]["now"] == "wrong"


def test_one_file_that_fails_does_not_stop_the_rest(conn, monkeypatch):
    calls = []

    def flaky(c, **kw):
        calls.append(kw["path"])
        if len(calls) == 1:
            raise RuntimeError("the reader could not be reached")
        return {"results": [], "notes": []}

    monkeypatch.setattr(legacy, "import_scan", flaky)
    out = reread.run(conn, commit=False)
    assert out["failed"] == 1 and out["read"] == len(calls) - 1
