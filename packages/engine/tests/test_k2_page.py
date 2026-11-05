"""A drafted page reaches the page, can be applied over an earlier machine draft, and is read as bullets and slips
(goals/m1-12b-apply-and-edit.yaml, task M1-12b). Every row is the test's own, in a band of its own, rolled back."""

import os

import pytest

from engine.w1_bank import k2_page as page
from engine.w1_bank import k2_review as review
from engine.w1_bank import map_ledger
from engine.w1_bank.map_agents import Proposal
from tests import test_k2_draft as base

conn = base.conn
_act, run, drafted, Scripted, AGREE, FAULT, _marks = (
    base._act, base.run, base.drafted, base.Scripted, base.AGREE, base.FAULT, base._marks,
)  # fmt: skip
pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
STEPS = ["Show ten beads on the floor.", "Ask the child to count them aloud."]
SLIPS = [{"keyword": "counts twice", "spot": "Finger goes back."}]


def drafted_page(conn, code="KX-1", **school):
    _act(conn, code, "A", materials="Beads, Rope", **school)
    run(
        conn,
        Scripted(
            {
                ("k2_page_draft", code): [drafted(steps=STEPS, uses=["Beads"], slips=SLIPS)],
                ("k2_page_check", code): [AGREE],
            }
        ),
    )
    map_ledger.apply(conn, conn.t, conn.staff, True)


def row(conn, col, code="KX-1"):
    return conn.execute(f"select {col} as v from activity where code = %s", (code,)).fetchone()["v"]  # noqa: S608


def test_applying_a_draft_writes_the_text_and_the_lists_beside_it(conn):
    drafted_page(conn)
    assert row(conn, "steps") == "• Show ten beads on the floor.\n• Ask the child to count them aloud."
    assert row(conn, "steps_list") == STEPS
    assert row(conn, "thinking_doc") == {"idea": "t", "slips": SLIPS}
    assert row(conn, "objective") == "o" and row(conn, "level_1") == "names it"


def _again(conn, proposer, steps):
    map_ledger.record(
        conn, conn.t,
        [Proposal("page_part", "KX-1", {"parts": {"steps": steps, "objective": "new objective"}, "flags": []}, 0.9, proposer, "", [], "agree", "needs_person", "r")],
        conn.staff,
    )  # fmt: skip


def test_a_newer_draft_replaces_what_an_older_draft_wrote_and_the_older_one_is_set_aside(conn):
    drafted_page(conn)
    _again(conn, "k2_page_draft v4", ["Only step."])
    map_ledger.apply(conn, conn.t, conn.staff, True)
    assert row(conn, "steps_list") == ["Only step."] and row(conn, "steps") == "• Only step."
    assert row(conn, "objective") == "new objective"


def test_an_older_draft_waiting_is_never_applied_over_a_newer_one_and_says_why(conn):
    _act(conn, "KX-1", "A")
    map_ledger.record(
        conn, conn.t,
        [Proposal("page_part", "KX-1", {"parts": {"objective": "OLD"}, "flags": []}, 0.9, "k2_page_draft v3", "", [], "agree", "needs_person", "r")],
        conn.staff,
    )  # fmt: skip
    _again(conn, "k2_page_draft v4", ["New step."])
    map_ledger.apply(conn, conn.t, conn.staff, True)
    assert row(conn, "objective") == "new objective"
    old = next(p for p in map_ledger.standing(conn, conn.t) if p["proposer"].endswith("v3"))
    assert old["now"] == "rejected"
    why = conn.execute("select reason from curriculum_proposal where about = %s", (old["id"],)).fetchone()
    assert "newer draft" in why["reason"]


def test_a_redraft_never_writes_over_the_schools_words_or_a_persons(conn):
    drafted_page(conn, objective="the school's own")
    review.change(conn, conn.t, conn.staff, "KX-1", "level_1", "my own level one")
    _again(conn, "k2_page_draft v4", ["Newer step."])
    map_ledger.apply(conn, conn.t, conn.staff, True)
    assert row(conn, "objective") == "the school's own" and row(conn, "level_1") == "my own level one"
    assert row(conn, "steps_list") == ["Newer step."]


def test_the_page_reads_steps_as_bullets_and_the_thinking_as_an_idea_and_slips(conn):
    drafted_page(conn, objective="the school's own")
    view = page.read(conn, conn.t, "KX-1")
    parts = {p["part"]: p for p in view["parts"]}
    assert parts["steps"]["kind"] == "bullets" and parts["steps"]["items"] == STEPS
    assert (parts["thinking"]["idea"], parts["thinking"]["slips"]) == ("t", SLIPS)
    assert (parts["steps"]["source"], parts["steps"]["check_me"]) == ("drafted", True)
    assert parts["objective"]["source"] == "school" and parts["objective"]["check_me"] is False
    assert parts["level_2"]["kind"] == "text" and parts["level_2"]["text"] == "does it as shown"
    assert view["draft"]["verdict"] == "agree" and view["draft"]["maker"] == "k2_page_draft v4"


def test_a_list_that_no_longer_reads_as_its_text_is_not_trusted(conn):
    drafted_page(conn)
    conn.execute("update activity set steps = %s where code = 'KX-1'", ("• A line someone typed",))
    parts = {p["part"]: p for p in page.read(conn, conn.t, "KX-1")["parts"]}
    assert parts["steps"]["items"] == ["A line someone typed"], "the text wins; the stale list is not shown"


def test_the_schools_own_steps_are_shown_as_lines_and_its_thinking_as_prose(conn):
    _act(conn, "KX-1", "A", steps="1. Sit in a circle\n2. Show the blocks", thinking="Sizes can be compared.")
    parts = {p["part"]: p for p in page.read(conn, conn.t, "KX-1")["parts"]}
    assert (
        parts["steps"]["items"] == ["Sit in a circle", "Show the blocks"]
        and parts["steps"]["source"] == "school"
    )
    assert parts["thinking"]["idea"] is None and parts["thinking"]["text"] == "Sizes can be compared."


def test_changing_a_drafted_part_to_a_list_writes_the_text_and_the_list_as_the_persons(conn):
    drafted_page(conn)
    review.change(conn, conn.t, conn.staff, "KX-1", "steps", ["Sit down.", "Count the beads."])
    assert row(conn, "steps") == "• Sit down.\n• Count the beads."
    assert row(conn, "steps_list") == ["Sit down.", "Count the beads."]
    assert _marks(conn, "KX-1")["steps"] == ("person", False)
    review.change(conn, conn.t, conn.staff, "KX-1", "thinking", {"idea": "New idea.", "slips": SLIPS})
    assert row(conn, "thinking") == "New idea.\n• counts twice: Finger goes back."
    assert row(conn, "thinking_doc") == {"idea": "New idea.", "slips": SLIPS}


def test_changing_a_part_to_plain_words_clears_the_list_and_nothing_malformed_is_taken(conn):
    drafted_page(conn)
    review.change(conn, conn.t, conn.staff, "KX-1", "steps", "Plain words")
    assert row(conn, "steps") == "Plain words" and row(conn, "steps_list") is None
    for bad in (
        [],
        [""],
        ["ok", 3],
        {"idea": "", "slips": SLIPS},
        {"idea": "i", "slips": [{"keyword": "k"}]},
        {"idea": "i"},
    ):
        with pytest.raises(ValueError):
            review.change(conn, conn.t, conn.staff, "KX-1", "thinking", bad)
    assert _marks(conn, "KX-1")["thinking"] == ("drafted", True), "a refused change touches nothing"


def test_rejecting_a_drafted_part_empties_its_list_too(conn):
    drafted_page(conn)
    review.reject(conn, conn.t, conn.staff, "KX-1", "steps")
    assert row(conn, "steps") == "" and row(conn, "steps_list") is None


def test_reverting_a_proposal_empties_the_lists_it_wrote(conn):
    drafted_page(conn)
    (p,) = map_ledger.standing(conn, conn.t, "applied")
    map_ledger.revert(conn, conn.t, p["id"], conn.staff, "test")
    assert row(conn, "steps") == "" and row(conn, "steps_list") is None and row(conn, "thinking_doc") is None


def _prop(conn, code, parts, status="needs_person"):
    map_ledger.record(
        conn, conn.t,
        [Proposal("page_part", code, {"parts": parts, "flags": []}, 0.9, "k2_page_draft v4", "", [], "agree", status, "r")],
        conn.staff,
    )  # fmt: skip
    return [p for p in map_ledger.standing(conn, conn.t) if p["subject_code"] == code][-1]["id"]


def _now(conn, pid):
    return next(p["now"] for p in map_ledger.standing(conn, conn.t) if p["id"] == pid)


def test_a_newer_partial_draft_never_buries_the_parts_an_older_draft_has_that_it_lacks(conn):
    _act(conn, "KX-1", "A")
    old = _prop(conn, "KX-1", {"objective": "OLD OBJ", "steps": ["old step"]})
    new = _prop(conn, "KX-1", {"steps": ["new step"]})
    map_ledger.apply(conn, conn.t, conn.staff, True)
    assert row(conn, "objective") == "OLD OBJ", "the older draft's objective is still the page's"
    assert row(conn, "steps_list") == ["new step"], "and the newer draft wins the part it covers"
    assert (_now(conn, old), _now(conn, new)) == ("applied", "applied")


def test_a_newer_draft_a_person_turned_down_is_not_newer_at_all(conn):
    _act(conn, "KX-1", "A")
    _prop(conn, "KX-1", {"objective": "OLD OBJ", "steps": ["old step"]})
    new = _prop(conn, "KX-1", {"steps": ["new step"]})
    map_ledger.settle(conn, conn.t, new, False, conn.staff, "no")
    map_ledger.apply(conn, conn.t, conn.staff, True)
    assert row(conn, "steps_list") == ["old step"] and row(conn, "objective") == "OLD OBJ"


def test_a_part_a_person_approved_is_not_buried_by_a_newer_draft_nobody_has_read(conn):
    _act(conn, "KX-1", "A")
    old = _prop(conn, "KX-1", {"steps": ["approved step"]})
    map_ledger.settle(conn, conn.t, old, True, conn.staff, "good")
    new = _prop(conn, "KX-1", {"steps": ["unread step"], "objective": "new objective"})
    map_ledger.apply(conn, conn.t, conn.staff, True)
    assert row(conn, "steps_list") == ["approved step"], "the person's yes holds"
    assert row(conn, "objective") == "new objective", "the newer draft still writes the parts nobody approved"
    assert _now(conn, new) == "applied"


def test_a_draft_whose_every_part_a_newer_one_covers_is_set_aside_with_the_reason(conn):
    _act(conn, "KX-1", "A")
    old = _prop(conn, "KX-1", {"steps": ["old step"]})
    _prop(conn, "KX-1", {"steps": ["new step"], "objective": "o"})
    map_ledger.apply(conn, conn.t, conn.staff, True)
    assert _now(conn, old) == "rejected" and row(conn, "steps_list") == ["new step"]
