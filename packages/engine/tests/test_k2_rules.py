"""What drafted K2 text may never say, checked by code on drafted text only (goals/m1-11f-draft-rules.yaml).

2026-11-04, the first draft_dev run: the drafter wrote "her" for the child, mixed numbered and plain step lines against
the school's bulleted ones, and put two children side by side to see who is tall. A prompt asking nicely is not a rule;
these are rules code applies to what the model wrote, and the words that make them are a config row. The school's own
words are never read by any of this.
"""

import json

import pytest

from engine.core import db
from engine.w1_bank import k2_batch as batch

RULES = next(
    c
    for c in json.loads((db.REPO_ROOT / "supabase/seed/config.json").read_text())["config"]
    if c["key"] == "k2.draft_rules"
)["value"]
WANT = {"A": ["objective", "steps"]}


def reply(**parts):
    return [{"key": "A", "objective": "The child sorts colours.", "steps": "• Show the tray.", **parts}]


def judged(**parts):
    return batch.judge_pages(reply(**parts), WANT, RULES)


@pytest.mark.parametrize("word", ["her", "she", "his", "he", "him", "herself", "girl", "boys"])
def test_a_drafted_part_that_genders_a_child_is_refused_naming_the_word_and_the_part(word):
    good, bad = judged(steps=f"• The child picks it up and puts {word} hand on the tray.")
    assert good == {} and "steps" in bad["A"] and f"'{word}'" in bad["A"]


@pytest.mark.parametrize(
    "text",
    [
        "• The child sorts the other three, then there is the shed.",
        "• The educator places the tray. The child helps.",
    ],
)
def test_the_words_inside_other_words_and_the_child_or_educator_by_name_are_fine(text):
    good, bad = judged(steps=text)
    assert bad == {} and good["A"]["steps"] == text


@pytest.mark.parametrize(
    "text",
    [
        "• Stand two children side by side and ask who is taller.",
        "• Ask the children who is the fastest in the class.",
        "• Compare the children by their height.",
        "• Say which child is bigger than the other child.",
    ],
)
def test_a_drafted_part_that_sets_children_against_each_other_is_refused_saying_so(text):
    good, bad = judged(steps=text)
    assert good == {} and "compares children" in bad["A"] and "steps" in bad["A"]


def test_comparing_things_that_are_not_children_is_fine():
    good, bad = judged(steps="• Line the blocks up from the shortest to the tallest and ask which is longer.")
    assert bad == {} and good


def test_the_rules_are_read_from_the_row_so_a_new_word_is_data_not_code():
    custom = {"gendered": ["wizard"], "compare": []}
    assert "'wizard'" in batch.judge_pages(reply(steps="• A wizard waves."), WANT, custom)[1]["A"]
    assert batch.judge_pages(reply(steps="• She waves."), WANT, custom)[1] == {}, "she is not in this row"
    assert batch.judge_pages(reply(steps="• She waves."), WANT)[1] == {}, "no rules, no check"


def test_a_part_the_page_was_not_asked_for_is_never_read():
    """Only the asked-for (empty) parts are drafted text; a part the school wrote is not in the reply's judged set."""
    good, bad = batch.judge_pages(
        reply(steps="• She waves.", objective="The child sorts."), {"A": ["objective"]}, RULES
    )
    assert bad == {} and good == {"A": {"objective": "The child sorts."}}


def test_a_page_refused_once_is_asked_for_again_and_kept_when_the_next_reply_is_clean():
    replies = iter([reply(steps="• Her hand."), reply(steps="• The child's hand.")])
    done = batch.run(WANT, lambda keys: next(replies), 4, 2, RULES)
    assert done.good["A"]["steps"] == "• The child's hand." and done.bad == {} and done.calls == 2


def test_a_page_refused_every_time_is_left_for_a_person_with_the_reason():
    done = batch.run(WANT, lambda keys: reply(steps="• Her hand."), 4, 1, RULES)
    assert done.good == {} and "'Her'" in done.bad["A"] or "'her'" in done.bad["A"]


@pytest.mark.parametrize(
    "raw, want",
    [
        ("1. Show the tray.\n2) Name the colours.\n- Mix them up.\n* Match them.\n• Put them back.",
         "• Show the tray.\n• Name the colours.\n• Mix them up.\n• Match them.\n• Put them back."),
        ("Show the tray.\n\n  Name the colours.  ", "• Show the tray.\n• Name the colours."),
        ("• Already as the school writes them.", "• Already as the school writes them."),
        ("Step 1: Show the tray.", "• Step 1: Show the tray."),
    ],
)  # fmt: skip
def test_drafted_steps_come_out_as_the_schools_own_bulleted_lines(raw, want):
    assert batch.normalise_steps(raw) == want
    assert batch.normalise_steps(want) == want, "normalising twice changes nothing"


def test_only_the_steps_are_put_in_that_form():
    good, _ = judged(steps="1. Show the tray.\n2. Name it.", objective="1. The child sorts colours.")
    assert good["A"]["steps"] == "• Show the tray.\n• Name it."
    assert good["A"]["objective"] == "1. The child sorts colours.", (
        "a number in another part is not a step marker"
    )


def test_the_seeded_row_names_words_and_patterns_and_every_pattern_is_a_regex():
    import re

    assert RULES["gendered"] and RULES["compare"]
    for pattern in RULES["compare"]:
        re.compile(pattern)


def test_the_checker_is_shown_the_schools_objective_and_materials_beside_the_draft():
    from engine.w1_bank import k2_draft as draft

    row = {
        "code": "KX-1", "name": "Spindle box", "strand": "Sensorial", "materials": "Two boxes, 0 to 9 in each.",
        "objective": "The child will match a count to a numeral.", "steps": "", "thinking": "",
        "level_0": "", "level_1": "", "level_2": "", "level_3": "",
    }  # fmt: skip
    text = draft._block(row, [], None, {"steps": ["Count the spindles into each compartment."]})
    assert "materials: Two boxes, 0 to 9 in each." in text
    assert "objective: The child will match a count to a numeral." in text
    assert "• Count the spindles" in text
