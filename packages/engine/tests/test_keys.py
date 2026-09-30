"""A paper question's right answer (`w3_read/keys.py`): shown as stored on every answer a person checks, changed by an
educator for every child at once once code has checked it, and kept when the paper is entered again (goal s26,
ADR 0045). Nimish, 2026-09-30: "the key can be changed by an educator, not an issue. also in any correction, the
system should show what the right answer is as stored in the system"."""

import json
import re

import pytest

from engine.core import db
from engine.w3_read import again, keys, legacy, marking
from tests import test_legacy as legacy_tests

KEYS = {
    "code": "TEST-KEYS",
    "title": "test",
    "band": "G4",
    "week": "test",
    "date": "2026-09-11",
    "pages": [{"n": 1, "mask": 0}],
    "items": [
        {"n": 4, "part": "a", "page": 1, "expr": "48 + 35", "question": "48 + 35 ="},
        # the number line's first box after 48 + 30, typed 80 in the file where the paper's key is 78
        {"n": 4, "part": "b", "page": 1, "kind": "missing", "rung": "R7", "answer": 80, "question": "the number line"},
        {"n": 11, "part": "b", "page": 1, "kind": "missing", "rung": "X1", "answer": "Not true", "question": "odd + odd"},
        {"n": 5, "part": "a", "page": 1, "kind": "missing", "rung": "R27", "answer": 30, "question": "638 = 600 +",
         "holds": "638 = 600 + {5a} + {5b}"},
        {"n": 5, "part": "b", "page": 1, "kind": "missing", "rung": "R27", "answer": 8, "question": "638 = 600 +",
         "holds": "638 = 600 + {5a} + {5b}"},
        {"n": 12, "page": 1, "kind": "text", "rung": "X1", "question": "Explain why Leroy cannot be correct."},
    ],
}  # fmt: skip
READS = {"4a": "", "4b": "", "11b": "", "5a": "", "5b": "", "12": "because"}  # every box goes to a person


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _child(conn, roll):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    cid = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s,%s,'TESTKEYS','G4') returning id",
        (tenant, roll),
    ).fetchone()["id"]
    conn.execute(
        "insert into pii.child (tenant_id, child_id, first_name) values (%s,%s,'Test')", (tenant, cid)
    )
    return cid


def _papers(conn, tmp_path, monkeypatch, n):
    """`n` children, each with the paper read → [(child, box, marks, save)]."""
    out = []
    for i in range(n):
        child, where = _child(conn, str(i + 1)), tmp_path / f"c{i}"
        where.mkdir()
        out.append((child, *legacy_tests._read_split(conn, child, where, monkeypatch, KEYS, READS)))
    return out


def _item(conn, key):
    return conn.execute(
        "select id, item_key, spec, responses, source from item where item_key = %s",
        (f"legacy/TEST-KEYS/{key}",),
    ).fetchone()


@legacy_tests.pytestmark_db
def test_every_answer_a_person_checks_says_its_right_answer_as_stored(conn, tmp_path, monkeypatch):
    """Nimish, 2026-09-30: "in any correction, the system should show what the right answer is as stored in the
    system; that would remove any suspicion or confusion". Question 4A's card said "48 + 35 =" and nothing of 83, and
    a 78 from the number line was typed into it. `keys.shown` is what every answer's card prints beside what the child
    wrote: the stored answer, the equation a box is marked by, or that a person judges it; and who changed it."""
    _papers(conn, tmp_path, monkeypatch, 1)
    capture = conn.execute(
        "select r.capture_id from item_result r join item i on i.id = r.item_id where i.item_key = 'legacy/TEST-KEYS/4a'"
    ).fetchone()["capture_id"]
    shown = {row["slot"]: row["right"] for row in keys.shown(conn, capture)}
    paper = conn.execute("select sheet_instance_id from capture where id = %s", (capture,)).fetchone()
    assert keys.shown(conn, paper["sheet_instance_id"]) == keys.shown(conn, capture), (
        "asked by the paper, as the page asks"
    )
    assert shown == {
        "4a": "83",
        "4b": "80",
        "11b": "Not true",
        "5a": "any answer that makes 638 = 600 + [5a] + [5b] true (the paper's own: 30)",
        "5b": "any answer that makes 638 = 600 + [5a] + [5b] true (the paper's own: 8)",
        "12": "a person judges this one",
    }
    keys.change(conn, _item(conn, "4b")["id"], "78", "neha@school")
    changed = next(row for row in keys.shown(conn, capture) if row["slot"] == "4b")
    assert (changed["right"], changed["was"], changed["by"]) == ("78", "80", "neha@school")


@legacy_tests.pytestmark_db
def test_code_refuses_a_right_answer_the_question_itself_contradicts(conn, tmp_path, monkeypatch):
    """Nimish, 2026-09-30: "it validates it". What code can compute it checks: a sum's right answer is its arithmetic
    (78 for 48 + 35 is refused, and says so — 78 was the number line's box), a box of an equation is marked by its
    equation, a number stays a whole number and a claim stays true or not true. Nothing is written when it refuses."""
    _papers(conn, tmp_path, monkeypatch, 1)
    refused = {
        "4a": ("78", "48 + 35 is 83"),
        "5a": ("19", "marked by its equation"),
        "12": ("yes", "a person judges"),
        "4b": ("seventy-eight", "a whole number"),
        "11b": ("maybe", "True or Not true"),
    }
    for key, (answer, why) in refused.items():
        with pytest.raises(ValueError, match=re.escape(why)):
            keys.change(conn, _item(conn, key)["id"], answer, "neha@school")
    with pytest.raises(ValueError, match="already"):
        keys.change(conn, _item(conn, "4b")["id"], "80", "neha@school")
    assert (
        conn.execute(
            "select count(*) as n from key_correction where item_key like 'legacy/TEST-KEYS/%'"
        ).fetchone()["n"]
        == 0
    ), "a refused change writes nothing"


@legacy_tests.pytestmark_db
def test_an_educator_changes_a_right_answer_and_every_childs_answer_is_marked_again(
    conn, tmp_path, monkeypatch, every_kind_trusted
):
    """Nimish, 2026-09-30: "the key can be changed by an educator, not an issue". 4B's key was typed 80 where the
    paper's is 78. An educator changes it once, on one child's paper, and every child's answer to 4B is marked again:
    one signed off with a new batch of evidence in the educator's name (the old batch kept), one not yet signed off in
    place, and a child who wrote 80 is now wrong. The change is a row with the key it replaced."""
    (a, box_a, marks_a, save_a), (b, box_b, marks_b, save_b), (c, box_c, marks_c, save_c) = _papers(
        conn, tmp_path, monkeypatch, 3
    )
    save_a("4b", "78"), save_b("4b", "78"), save_c("4b", "80")
    marking.confirm(conn, a, "nimish")
    assert (marks_a("4b"), marks_b("4b"), marks_c("4b")) == (
        {"4b": "wrong"},
        {"4b": "wrong"},
        {"4b": "correct"},
    )

    done = keys.change(conn, _item(conn, "4b")["id"], " 78 ", "neha@school")
    assert (done["was"], done["now"], done["left"]) == ("80", "78", [])
    assert sorted(done["changed"]) == sorted(
        [("legacy/TEST-KEYS/4b", "wrong", "correct")] * 2 + [("legacy/TEST-KEYS/4b", "correct", "wrong")]
    )
    assert (marks_a("4b"), marks_b("4b"), marks_c("4b")) == (
        {"4b": "correct"},
        {"4b": "correct"},
        {"4b": "wrong"},
    )
    evidence = conn.execute(
        "select correct, confirmed_by from evidence_event where item_result_id = %s order by created_at",
        (box_a("4b")["id"],),
    ).fetchall()
    assert [(e["correct"], e["confirmed_by"]) for e in evidence] == [(False, "nimish"), (True, "neha@school")]
    placed = conn.execute(
        "select correct from evidence_placed where item_result_id = %s", (box_a("4b")["id"],)
    ).fetchall()
    assert [p["correct"] for p in placed] == [True], "the graph reads the new batch"
    row = conn.execute(
        "select was, answer, by from key_correction where item_key = 'legacy/TEST-KEYS/4b'"
    ).fetchone()
    assert dict(row) == {"was": "80", "answer": "78", "by": "neha@school"}


@legacy_tests.pytestmark_db
def test_a_changed_right_answer_survives_the_paper_being_entered_again(
    conn, tmp_path, monkeypatch, every_kind_trusted
):
    """Nimish, 2026-09-30: "and then these questions become right for all the students". Every deploy enters each
    paper again from its file (ADR 0043), and the file still says 80: the change is put back over it at once, so the
    answers marked right stay right and nothing is marked again."""
    ((child, box, marks, save),) = _papers(conn, tmp_path, monkeypatch, 1)
    save("4b", "78")
    keys.change(conn, _item(conn, "4b")["id"], "78", "neha@school")
    path = tmp_path / "again.json"
    path.write_text(json.dumps(KEYS))
    legacy.load_paper(conn, path)
    assert keys.reapply(conn, "TEST-KEYS") == 1
    assert _item(conn, "4b")["responses"][0]["answer"] == "78"
    assert marks("4b") == {"4b": "correct"}
    assert again.mark_again(conn, "the marking rule", _item(conn, "4b")["id"]) == ([], [])


@legacy_tests.pytestmark_db
def test_a_changed_right_answer_reaches_what_was_signed_off_as_read_and_leaves_what_a_person_decided(
    conn, tmp_path, monkeypatch, every_kind_trusted
):
    """Nimish, 2026-09-30: "these questions become right for all the students", and a person's own call is never
    overwritten on the way. Five children's 4B, each signed off; only a mark its reading gives by the old 80 came from
    that key:
    - the engine read 80, right by 80, and nobody typed it: marked by the new right answer, with a new batch of evidence;
    - a person typed 78: marked again by the new right answer, as any reading a person typed is;
    - a person judged a 78 Wrong, as 80 marked it: a judgement is never changed by the engine, so it stays, and the
      educator is told the new right answer marks it right;
    - the engine misread 18, and a person judged it Right, once with a row saying so and once before judgements left one
      (U3): no key decided that mark, so it stays, and nothing about the change is theirs to hear.
    Marking every answer again, as a deploy does, touches none of the five: only what a person typed is marked again."""
    reads = {"80": "80", "typed": "78", "judged": "78", "overrode": "18", "unrecorded": "18"}
    kids = {}
    for i, (who, wrote) in enumerate(reads.items()):
        child, where = _child(conn, str(i + 1)), tmp_path / who
        where.mkdir()
        kids[who] = (
            child,
            *legacy_tests._read_split(conn, child, where, monkeypatch, KEYS, {**READS, "4b": wrote}),
        )
    box = {who: kids[who][1]("4b")["id"] for who in kids}
    kids["typed"][3]("4b", "78")
    conn.execute("select resolve_result(%s, 'wrong', '{}', 'nimish')", (box["judged"],))
    conn.execute("select resolve_result(%s, 'correct', '{}', 'nimish')", (box["overrode"],))
    # before U3 a paper's Right / Wrong / Blank set the mark and signed it off, and left no row saying so
    conn.execute("update item_result set status = 'correct', misconception_codes = '{}' where id = %s",
                 (box["unrecorded"],))  # fmt: skip
    for child, *_ in kids.values():
        marking.confirm(conn, child, "nimish")
    before = {
        "80": "correct",
        "typed": "wrong",
        "judged": "wrong",
        "overrode": "correct",
        "unrecorded": "correct",
    }
    assert {who: kids[who][2]("4b")["4b"] for who in kids} == before
    assert {kids[who][1]("4b")["state"] for who in kids} == {"confirmed"}

    done = keys.change(conn, _item(conn, "4b")["id"], "78", "neha@school")
    k = "legacy/TEST-KEYS/4b"
    assert sorted(done["changed"]) == [(k, "correct", "wrong"), (k, "wrong", "correct")]
    assert done["left"] == [
        (k, "wrong", "a person judged it by the old right answer; the new one marks its reading, 78, correct")
    ]
    after = {**before, "80": "wrong", "typed": "correct"}
    assert {who: kids[who][2]("4b")["4b"] for who in kids} == after
    evidence = conn.execute(
        "select correct, confirmed_by from evidence_placed where item_result_id = %s", (box["80"],)
    ).fetchall()
    assert [(e["correct"], e["confirmed_by"]) for e in evidence] == [(False, "neha@school")]
    assert again.mark_again(conn, "the marking rule", _item(conn, "4b")["id"]) == ([], [])
