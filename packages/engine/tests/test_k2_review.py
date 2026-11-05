"""M1-11, D-073: a drafted part can be kept, changed or rejected by a person (goals/m1-11-k2-complete-v1.yaml).

These are the engine's three actions behind the screens' buttons. Each is tested for the 'drafted' mark it starts from
and the mark it ends with. A part the school wrote, or that is not marked drafted, is refused: the school's text is never
changed through here.
"""

import os

import pytest

from engine.w1_bank import k2_review as review
from engine.w1_bank import map_ledger
from tests import test_k2_draft as base

conn = base.conn  # the same database fixture, one place
AGREE, FULL, Scripted, _act, _marks, drafted, run = (
    base.AGREE,
    base.FULL,
    base.Scripted,
    base._act,
    base._marks,
    base.drafted,
    base.run,
)

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def page(conn):
    """A page whose objective is the school's and whose other parts are drafts, one of them doubted."""
    _act(conn, "KX-1", "A", objective="the school's own words")
    run(
        conn,
        Scripted(
            {
                ("k2_page_draft", "KX-1"): [drafted()],
                ("k2_page_check", "KX-1"): [base.FAULT],
            }
        ),
    )
    map_ledger.apply(conn, conn.t, conn.staff, True)
    return conn


def _text(conn, part):
    return conn.execute(f"select {part} as t from activity where code = 'KX-1'").fetchone()["t"]  # noqa: S608


def test_keeping_a_draft_leaves_its_words_clears_the_doubt_and_makes_it_the_persons(page):
    assert _marks(page, "KX-1")["steps"] == ("drafted", True)
    review.keep(page, page.t, page.staff, "KX-1", "steps")
    assert _text(page, "steps") == "\u2022 s"
    assert _marks(page, "KX-1")["steps"] == ("person", False)
    assert _marks(page, "KX-1")["thinking"] == ("drafted", True), "the other parts are untouched"


def test_changing_a_draft_writes_the_new_words_as_the_persons_and_the_history_says_who(page):
    review.change(
        page, page.t, page.staff, "KX-1", "steps", "Sit in a circle; show the blocks one at a time."
    )
    assert _text(page, "steps") == "Sit in a circle; show the blocks one at a time."
    assert _marks(page, "KX-1")["steps"] == ("person", False)
    seen = page.execute(
        "select before, after, changed_by from curriculum_edit where code = 'KX-1' and field = 'steps' order by created_at"
    ).fetchall()
    assert (seen[-1]["before"], seen[-1]["changed_by"]) == ("\u2022 s", f"staff:{page.staff}"), (
        "ids, never a name"
    )
    assert seen[-1]["after"].startswith("Sit in a circle")


def test_changing_a_draft_to_nothing_is_refused_use_reject_for_that(page):
    with pytest.raises(ValueError, match="reject"):
        review.change(page, page.t, page.staff, "KX-1", "steps", "   ")
    assert _text(page, "steps") == "\u2022 s"


def test_rejecting_a_draft_empties_the_part_and_takes_its_mark_away(page):
    review.reject(page, page.t, page.staff, "KX-1", "thinking")
    assert _text(page, "thinking") == "" and "thinking" not in _marks(page, "KX-1")
    assert _marks(page, "KX-1")["steps"] == ("drafted", True)


def test_the_schools_words_and_unmarked_parts_are_refused_by_all_three(page):
    for act in (
        lambda p: review.keep(page, page.t, page.staff, "KX-1", p),
        lambda p: review.change(page, page.t, page.staff, "KX-1", p, "x"),
        lambda p: review.reject(page, page.t, page.staff, "KX-1", p),
    ):
        with pytest.raises(ValueError, match="not a drafted part"):
            act("objective")  # the school's own words: no mark
    assert _text(page, "objective") == "the school's own words"
    with pytest.raises(ValueError, match="not a part"):
        review.keep(page, page.t, page.staff, "KX-1", "name; drop table activity")


def test_a_part_a_person_already_made_theirs_cannot_be_kept_changed_or_rejected_again_as_a_draft(page):
    review.keep(page, page.t, page.staff, "KX-1", "steps")
    with pytest.raises(ValueError, match="not a drafted part"):
        review.reject(page, page.t, page.staff, "KX-1", "steps")
    assert _text(page, "steps") == "\u2022 s"


def test_reverting_the_draft_afterwards_leaves_the_persons_part_alone(page):
    review.change(page, page.t, page.staff, "KX-1", "steps", "A person's own steps.")
    (p,) = map_ledger.standing(page, page.t, "applied")
    map_ledger.revert(page, page.t, p["id"], page.staff, "test")
    assert _text(page, "steps") == "A person's own steps."
    assert _marks(page, "KX-1") == {"steps": ("person", False)}, (
        "the draft's other marks go, the person's stays"
    )


def test_the_review_list_loses_a_page_once_every_doubt_on_it_is_cleared(page):
    page.execute("update threshold set value = 0 where key = 'map.audit_share'")
    assert [r["code"] for r in review.review_list(page, page.t)] == ["KX-1"]
    for part in ("thinking", "steps", "level_0", "level_1", "level_2", "level_3"):
        review.keep(page, page.t, page.staff, "KX-1", part)
    assert review.review_list(page, page.t) == []


def test_reverting_the_draft_never_wipes_a_part_a_person_kept_with_its_words_unchanged(page):
    review.keep(page, page.t, page.staff, "KX-1", "steps")  # same words, now the person's
    (p,) = map_ledger.standing(page, page.t, "applied")
    map_ledger.revert(page, page.t, p["id"], page.staff, "test")
    assert _text(page, "steps") == "\u2022 s", (
        "a person's approval is not undone by a revert of the machine's proposal"
    )
    assert _marks(page, "KX-1")["steps"] == ("person", False)
    assert _text(page, "thinking") == "" and "thinking" not in _marks(page, "KX-1"), (
        "the parts still drafted do go"
    )
