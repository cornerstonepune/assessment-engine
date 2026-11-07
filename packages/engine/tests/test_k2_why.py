"""Why a draft's steps name a thing the materials do not, in counts (goals/m1-12o-draft-why.yaml).

A step that names a prop the page's materials list does not is held back. Before the rule is changed, this says what
kind of word the hits are: named elsewhere on the school's own page, a variant of a listed word, a prop most pages
list, or named nowhere. No model, no school text: counts and plain single words only (the log is public)."""

import json

from engine.w1_bank import k2_format as fmt
from engine.w1_bank import k2_why as why

FMT = {"step_words": 14, "always_there": ["child", "floor"], "function_words": ["the", "a", "with"]}
BLANK = {"name": "", "objective": "", "level_0": "", "level_1": "", "level_2": "", "level_3": ""}
ROWS = {
    "A": BLANK | {"materials": "Chalk, Rope, Paper", "objective": "Count the beads along the rope."},
    "B": BLANK | {"materials": "Beads, Paper, Crayons", "name": "Rolling"},
    "C": BLANK | {"materials": "Beadwork, Paper", "name": "Cloth fun"},
    "D": BLANK | {"materials": "Cloth", "name": "Folding"},
    "E": BLANK | {"materials": "Rope", "objective": "Beads for the rope."},
}
STEPS = {
    "A": ["Lay the rope.", "Place a bead on it."],  # bead: the page's objective names it
    "C": ["Take the beadwork.", "Count a bead."],  # bead: a variant of the listed beadwork
    "D": [
        "Fold the cloth.",
        "Draw on the paper with a crayon.",
    ],  # paper: most pages list it; crayon: nowhere
    "E": ["Hold the rope.", "Place a bead."],  # bead again, named by the objective
}
VOCAB = fmt.vocabulary(r["materials"] for r in ROWS.values())


def run(steps=None, rows=None):
    return why.why(STEPS if steps is None else steps, rows or ROWS, VOCAB, FMT)


def test_every_step_word_the_materials_do_not_name_is_listed_not_only_the_first():
    got = fmt.unlisted_step_words(STEPS["D"], ROWS["D"]["materials"], VOCAB, FMT)
    assert got == [(2, "paper"), (2, "crayon")]


def test_a_page_whose_steps_name_only_listed_things_has_none():
    assert fmt.unlisted_step_words(["Lay the rope."], "Rope", VOCAB, FMT) == []
    assert fmt.unlisted_step_words(["Lay the rope."], "", VOCAB, FMT) == [], (
        "a page with no list is not judged"
    )


def test_each_hit_is_put_in_the_first_class_that_fits_it():
    hits = run()["hits"]
    assert hits == {
        "named_on_the_page": 2,
        "variant_of_a_listed_word": 1,
        "listed_on_most_pages": 1,
        "not_named_anywhere": 1,
    }


def test_pages_that_would_clear_the_rule_if_the_first_classes_were_accepted_one_at_a_time():
    got = run()
    assert got["pages"] == 4
    assert got["pages_clear_if"] == {
        "named_on_the_page": 2,
        "plus_variant_of_a_listed_word": 3,
        "plus_listed_on_most_pages": 3,
    }


def test_a_plain_word_seen_twice_is_shown_under_its_class_and_one_seen_once_is_only_counted():
    got = run()
    assert got["words"] == {"named_on_the_page": {"bead": 2}}
    assert got["once"] == 3


def test_the_summary_holds_no_phrase_of_the_schools():
    text = json.dumps(run())
    assert "Count the beads" not in text and "rope" not in text and "Rolling" not in text


def test_nothing_to_judge_is_all_zero():
    got = run(steps={})
    assert got["pages"] == 0 and all(v == 0 for v in got["hits"].values())


def test_the_latest_kept_draft_of_a_page_is_the_one_read():
    kept = [
        ("accepted", {"pages": [{"key": "A", "steps": ["Old."]}, {"key": "Z", "steps": ["Not a page."]}]}),
        ("refused", {"pages": [{"key": "A", "steps": ["Refused."]}]}),
        ("accepted", {"pages": [{"key": "A", "steps": ["Newer."]}, {"key": "B", "steps": "not a list"}]}),
    ]
    assert why.latest_steps(kept, {"A", "B"}) == {"A": ["Newer."]}
