"""An educator removes a question from a child's paper or adds one from the bank (goals/paper_review_add_remove.yaml),
against the real schema, rolled back. The handwriting reader is stood in, as in `test_read_back.py`."""

import pytest

from engine.w1_bank import retire
from engine.w2_print import edit_paper, maker
from tests import test_maker
from tests.test_maker import _child
from tests.test_read_back import _items
from tests.test_the_loop import _counted, _planted, _round, _slots

conn = test_maker.conn  # the real schema, rolled back

SECTION = "EDITTEST"
WEEK = "2026-W44-edit"
BY = "educator@school.test"
ASK = [
    {"skill_set": "MUL.2D1D", "level": "Medium", "n": 4},
    {"skill_set": "ADD.2D2D", "level": "Easy", "n": 2},
]


@pytest.fixture
def paper(conn):
    """A home assessment for one child, approved as the panel approves it: four MUL.2D1D Medium, two 2-digit adds."""
    kid = _child(conn, "1", SECTION)
    return maker.make(conn, SECTION, [kid], WEEK, "focus", "each", BY, ASK)["qrs"][0]


def _row(conn, qr):
    return conn.execute(
        "select si.print_status, si.approved_by, si.key, t.item_ids from sheet_instance si"
        " join sheet_template t on t.id = si.sheet_template_id where si.qr_code = %s",
        (qr,),
    ).fetchone()


def _ids(conn, qr):
    return [str(i) for i in _row(conn, qr)["item_ids"]]


def _another(conn, qr, skill="MUL.2D1D", level="Medium"):
    return next(q for q in edit_paper.bank(conn, qr, "x", skill, level)["questions"])


def test_removing_a_question_makes_the_paper_one_shorter_and_says_what_it_no_longer_covers(conn, paper):
    before = edit_paper.review(conn, paper)
    assert [c["n"] for c in before["covers"]] == [4, 2] and len(before["questions"]) == 6
    first_add = [q["id"] for q in before["questions"] if q["skill_set"] == "ADD.2D2D"]
    one = edit_paper.remove(conn, paper, first_add[0], BY)
    assert one["n"] == 5 and one["uncovered"] == [], one
    two = edit_paper.remove(conn, one["qr"], first_add[1], BY)
    assert two["n"] == 4 and len(two["uncovered"]) == 1 and two["uncovered"][0].endswith("· Easy"), two
    after = edit_paper.review(conn, two["qr"])
    assert [q["id"] for q in after["questions"]] == [q["id"] for q in before["questions"][:4]], "order kept"
    for q in after["questions"]:
        assert q["text"] and q["skill"] and q["topic_name"] and q["level"] and q["kind"], q


def test_a_question_added_from_the_bank_goes_where_the_educator_puts_it(conn, paper):
    ids = _ids(conn, paper)
    new = _another(conn, paper)
    put = edit_paper.add(conn, paper, new["id"], BY, at=2)
    assert put["qr"] != paper and _ids(conn, put["qr"]) == [ids[0], new["id"], *ids[1:]]
    last = _another(conn, put["qr"])
    end = edit_paper.add(conn, put["qr"], last["id"], BY)
    assert _ids(conn, end["qr"])[-1] == last["id"] and end["n"] == 8
    with pytest.raises(ValueError, match="already on this paper"):
        edit_paper.add(conn, end["qr"], last["id"], BY)


def test_the_dropdowns_narrow_topic_skill_level_kind_question_from_rows_and_never_offer_a_retired_kind(
    conn, paper
):
    b = edit_paper.bank(conn, paper)
    topics = {t["code"] for t in b["topics"]}
    skill_topic = conn.execute("select topic_code from skill where code = 'MUL.2D1D'").fetchone()[
        "topic_code"
    ]
    assert skill_topic in topics and not b["skills"] and not b["questions"]
    skills = {s["code"] for s in edit_paper.bank(conn, paper, skill_topic)["skills"]}
    assert "MUL.2D1D" in skills
    levels = [x["code"] for x in edit_paper.bank(conn, paper, skill_topic, "MUL.2D1D")["levels"]]
    order = [r["code"] for r in conn.execute("select code from difficulty order by ord")]
    assert levels and levels == [x for x in order if x in levels], "levels in the difficulty rows' order"
    at = edit_paper.bank(conn, paper, skill_topic, "MUL.2D1D", "Medium")
    assert at["kinds"] and at["questions"]
    on = set(_ids(conn, paper))
    assert not on & {q["id"] for q in at["questions"]}, "a question on the paper is not offered again"
    kind = at["kinds"][0]["code"]
    narrowed = edit_paper.bank(conn, paper, skill_topic, "MUL.2D1D", "Medium", kind)["questions"]
    assert narrowed and all(q["kind"] == kind for q in narrowed)
    assert len(at["kinds"]) > 1, "a level keeps one kind in use: stopping one needs another"
    assert retire.stop(conn, "MUL.2D1D", kind, BY, "Medium")["stopped"]
    left = edit_paper.bank(conn, paper, skill_topic, "MUL.2D1D", "Medium")
    assert kind not in {k["code"] for k in left["kinds"]}
    assert all(q["kind"] != kind for q in left["questions"])
    with pytest.raises(LookupError, match="no longer used"):
        edit_paper.add(conn, paper, narrowed[0]["id"], BY)


def test_a_question_given_lately_is_offered_with_its_days(conn, paper):
    child = conn.execute("select child_id from sheet_instance where qr_code = %s", (paper,)).fetchone()[
        "child_id"
    ]
    q = _another(conn, paper)
    conn.execute(
        "insert into item_exposure (tenant_id, child_id, item_id, week, created_at)"
        " select tenant_id, %s, %s, 'earlier', now() - interval '9 days' from child where id = %s",
        (child, q["id"], child),
    )
    offered = {x["id"]: x for x in edit_paper.bank(conn, paper, "x", "MUL.2D1D", "Medium")["questions"]}
    assert offered[q["id"]]["days"] == 9, "flagged, not hidden"
    assert edit_paper.add(conn, paper, q["id"], BY)["n"] == 7, "and it may still be chosen"


def test_editing_an_approved_paper_withdraws_its_approval_and_every_edit_is_a_row_never_changed(conn, paper):
    assert edit_paper.review(conn, paper)["state"] == "approved"
    out = edit_paper.remove(conn, paper, _ids(conn, paper)[0], BY)
    assert out["withdrew_approval"] is True
    assert _row(conn, paper)["print_status"] == "void", (
        "the earlier copy is void, never changed in its questions"
    )
    new = _row(conn, out["qr"])
    assert (new["print_status"], new["approved_by"]) == ("new", None)
    assert edit_paper.review(conn, out["qr"])["state"] == "waiting"
    assert edit_paper.review(conn, paper)["newer"] == out["qr"]
    edit = conn.execute("select * from paper_edit where qr_before = %s", (paper,)).fetchone()
    assert (edit["qr_after"], edit["changed_by"], edit["withdrew_approval"]) == (out["qr"], BY, True)
    assert [str(i) for i in edit["removed"]] == [_ids(conn, paper)[0]] and edit["added"] == []
    with pytest.raises(Exception, match="never changed|cannot|not allowed|forbid"):
        conn.execute("savepoint s")
        conn.execute("update paper_edit set changed_by = 'someone else' where id = %s", (edit["id"],))
    conn.execute("rollback to savepoint s")
    with pytest.raises(PermissionError):
        edit_paper.remove(conn, paper, _ids(conn, paper)[1], BY)
    approved = edit_paper.approve(conn, out["qr"], BY)
    assert approved["approved_by"] == BY and edit_paper.review(conn, out["qr"])["state"] == "approved"


def test_a_printed_paper_or_one_with_answers_uploaded_cannot_be_edited(conn, paper, tmp_path):
    edit_paper.print_opened(conn, [paper], BY)
    shown = edit_paper.review(conn, paper)
    assert shown["state"] == "printed" and shown["why_not"].startswith(
        "This paper is already printed. Make a new one to change it."
    )
    with pytest.raises(PermissionError, match="already printed"):
        edit_paper.remove(conn, paper, _ids(conn, paper)[0], BY)
    kid = _child(conn, "2", SECTION)
    other = maker.make(conn, SECTION, [kid], WEEK, "focus", "each", BY, ASK[:1])["qrs"][0]
    conn.execute(
        "insert into capture (tenant_id, path, sheet_instance_id, status)"
        " select tenant_id, 'scan.pdf', id, 'processed' from sheet_instance where qr_code = %s",
        (other,),
    )
    with pytest.raises(PermissionError, match="uploaded"):
        edit_paper.add(conn, other, _another(conn, other)["id"], BY)
    assert _row(conn, other)["print_status"] == "printed", "the child's uploaded answers keep their paper"


def test_the_fewest_and_most_questions_are_rows_and_a_full_paper_takes_no_more(conn, paper):
    conn.execute("update threshold set value = 6 where key = 'assessment.max_questions'")
    with pytest.raises(ValueError, match="at most 6 questions"):
        edit_paper.add(conn, paper, _another(conn, paper)["id"], BY)
    conn.execute("update threshold set value = 6 where key = 'assessment.min_questions'")
    with pytest.raises(ValueError, match="at least 6 questions"):
        edit_paper.remove(conn, paper, _ids(conn, paper)[0], BY)
    assert _row(conn, paper)["print_status"] == "printed", "a refused edit writes nothing"
    conn.execute("delete from threshold where key = 'assessment.min_questions'")
    with pytest.raises(LookupError, match="threshold rows"):
        edit_paper.review(conn, paper)


def test_an_edited_paper_is_read_and_marked_against_its_new_questions_and_the_old_copy_as_itself(
    conn, paper, tmp_path, monkeypatch, every_kind_trusted
):
    out = edit_paper.remove(conn, paper, _ids(conn, paper)[-1], BY)
    out = edit_paper.add(conn, out["qr"], _another(conn, out["qr"])["id"], BY, at=1)
    edit_paper.approve(conn, out["qr"], BY)
    copy = _items(conn, out["qr"])
    assert len(_row(conn, out["qr"])["key"]["items"]) == len(copy["item_ids"]) == 6, (
        "the key is the new questions"
    )
    mistake, on = _planted(_slots(conn, copy["item_ids"]))
    assert on, "a question on the edited paper can show a mistake"
    planted = _round(conn, copy["child_id"], out["qr"], copy["pdf_path"], copy["item_ids"], mistake,
                     tmp_path / "edited.pdf", monkeypatch, f"edited paper {out['qr']}")  # fmt: skip
    assert _counted(conn, copy["child_id"], mistake) == planted
    old = _items(conn, paper)
    assert old["item_ids"] != copy["item_ids"] and old["pdf_path"] != copy["pdf_path"], (
        "the old copy is its own"
    )
