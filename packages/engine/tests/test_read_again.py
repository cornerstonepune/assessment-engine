"""`engine read again` — the corpus read afresh so every unclear answer carries the reader's guess
(goals/s4-validation-queue.yaml). The reader itself is replaced here by a stand-in, so nothing is
sent anywhere: what is tested is the driver — which papers it reads, that it reads them from the
rows the database already holds, and that it names every settled answer whose reading changed.
"""

import os

import pytest

from engine.core import db
from engine.w3_read import legacy, reread
from tests.rows import a_read_paper

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


def test_a_settled_answer_whose_reading_changed_is_named(conn, monkeypatch, tmp_path):
    (tmp_path / "scan.pdf").write_bytes(b"%PDF")
    paper = a_read_paper(
        conn, [{"status": "correct", "read": "35", "state": "confirmed"}], tmp_path / "scan.pdf"
    )
    target = paper["results"][0]

    def stand_in(c, **kw):  # a reader that now reads one settled answer differently
        c.execute("update item_result set status = 'wrong' where id = %s", (target,))
        return {"results": [], "notes": []}

    monkeypatch.setattr(legacy, "import_scan", stand_in)
    out = reread.run(conn, commit=False)
    assert [c["item_result"] for c in out["changed"]] == [target]
    assert out["changed"][0]["was"] == "correct" and out["changed"][0]["now"] == "wrong"


def test_one_file_that_fails_does_not_stop_the_rest(conn, monkeypatch, tmp_path):
    for n in (1, 2):
        (tmp_path / f"{n}.pdf").write_bytes(b"%PDF")
        a_read_paper(conn, [{"status": "correct", "read": "35"}], tmp_path / f"{n}.pdf")
    calls = []

    def flaky(c, **kw):
        calls.append(kw["path"])
        if len(calls) == 1:
            raise RuntimeError("the reader could not be reached")
        return {"results": [], "notes": []}

    monkeypatch.setattr(legacy, "import_scan", flaky)
    out = reread.run(conn, commit=False)
    assert out["failed"] == 1 and out["read"] == len(calls) - 1


TRUST = "ny2_trust"  # a kind of question of the test's own
HELD = {
    "35": "read as a right answer; a person checks every answer of this kind until the reader is trusted on it"
    " (0 of the last 0 right)",
    "17": "read as a wrong answer; a person checks every wrong answer before it counts",
}


def test_answers_waiting_only_for_trust_leave_the_queue_the_moment_their_kind_earns_it(conn):
    """Nimish, 2026-10-10: "the number of data points that we then need to validate becomes lower". An answer read right
    but held because its kind was not yet trusted (ADR 0032) is marked again the moment the kind earns trust, and leaves
    the queue; one read wrong still waits for a person (ADR 0029). Before the kind is trusted, nothing moves. Trust is
    measured over three checks here, and no right answer is drawn for a spot-check."""
    import json

    from engine.w3_read import again

    conn.execute("update threshold set value = 3 where key = 'marking.agreement_window'")
    conn.execute("update threshold set value = 0 where key = 'marking.spot_check_rate'")
    waiting = a_read_paper(
        conn,
        [{"status": "needs_teacher", "read": "35"}, {"status": "needs_teacher", "read": "17"}],
        fmt=TRUST,
    )
    for rid, read in zip(waiting["results"], ("35", "17"), strict=True):
        raw = {"child_answer": read, "answer_state": "written", "confidence": 95.0, "why": HELD[read]}
        conn.execute("update item_result set raw_read = %s where id = %s", (json.dumps(raw), rid))
    a_read_paper(conn, [{"status": "correct", "read": "35", "state": "confirmed"}] * 2, fmt=TRUST)
    assert again.trusted(conn) == 0, "two checks of three: not trusted yet, and nothing moves"
    a_read_paper(conn, [{"status": "correct", "read": "35", "state": "confirmed"}], fmt=TRUST)
    assert again.trusted(conn) == 1
    status = {
        r["id"]: r["status"]
        for r in conn.execute(
            "select id, status from item_result where id = any(%s)", (waiting["results"],)
        ).fetchall()
    }
    assert status[waiting["results"][0]] == "correct", "read right, its kind trusted now: it settles"
    assert status[waiting["results"][1]] == "needs_teacher", (
        "read wrong: a person checks it whatever the trust"
    )
