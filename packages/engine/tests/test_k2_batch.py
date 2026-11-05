"""M1-11: a batch of pages is judged item by item (goals/m1-11-k2-complete-v1.yaml).

Several pages go to the model in one call to keep the run inside Nimish's $25. One bad page in a reply must not cost
the others: every item is checked on its own by code, the good ones are kept, and only the bad or missing ones go
round again. Nothing here calls a model; `call` is whatever answers for the keys it is given.
"""

import json
from collections import Counter

from engine.w1_bank import k2_batch as batch

WANT = {"A": ["objective", "steps"], "B": ["thinking"], "C": ["level_0", "level_1", "level_2", "level_3"]}
LEVELS = {
    "level_0": "stays out",
    "level_1": "names the shapes",
    "level_2": "builds as shown",
    "level_3": "builds her own",
}


def page(key, **parts):
    return {"key": key, "flags": [], "confidence": 0.9, "reason": "r", **parts}


def test_a_good_page_is_kept_and_only_what_was_asked_for_is_taken_from_it():
    good, bad = batch.judge_pages([page("A", objective="o", steps="s", thinking="not asked for")], WANT)
    assert good == {"A": {"objective": "o", "steps": "\u2022 s"}} and bad["B"] == "missing from the reply"


def test_a_page_with_a_part_left_empty_or_missing_is_bad_and_says_which():
    good, bad = batch.judge_pages(
        [page("A", objective="o", steps="  "), page("B"), page("C", **LEVELS)], {k: WANT[k] for k in "ABC"}
    )
    assert set(good) == {"C"}
    assert bad == {"A": "steps is empty", "B": "thinking is empty"}


def test_four_levels_that_say_the_same_thing_are_bad_because_a_rubric_must_tell_them_apart():
    same = {**LEVELS, "level_2": "Names The Shapes."}
    good, bad = batch.judge_pages([page("C", **same)], {"C": WANT["C"]})
    assert good == {} and "level_1 and level_2" in bad["C"]


def test_a_key_nobody_asked_for_and_a_repeated_key_are_ignored_or_refused_not_trusted():
    good, bad = batch.judge_pages(
        [page("Z", thinking="x"), page("B", thinking="first"), page("B", thinking="second")], {"B": WANT["B"]}
    )
    assert good == {} and bad == {"B": "answered twice"}, "a repeated key is not trusted either way"


def test_a_reply_that_is_not_a_list_of_objects_judges_every_page_bad_without_raising():
    good, bad = batch.judge_pages("nope", WANT)
    assert good == {} and set(bad) == set(WANT)
    good, bad = batch.judge_pages([None, 3, "x"], {"A": WANT["A"]})
    assert good == {} and bad == {"A": "missing from the reply"}


def test_only_the_bad_and_missing_pages_go_round_again_and_a_good_page_is_never_asked_twice():
    asked: list[list[str]] = []

    def call(keys):
        asked.append(list(keys))
        if len(asked) == 1:  # first reply: A good, B empty, C missing
            return [page("A", objective="o", steps="s"), page("B", thinking="")]
        return [page(k, thinking="t", **LEVELS) for k in keys if k != "A"]

    done = batch.run(WANT, call, size=3, rounds=2)
    assert asked == [["A", "B", "C"], ["B", "C"]]
    assert set(done.good) == {"A", "B", "C"} and done.bad == {} and done.calls == 2


def test_a_page_still_bad_after_the_last_round_is_reported_with_why_and_the_run_stops_asking():
    asked: list[list[str]] = []

    def call(keys):
        asked.append(list(keys))
        return [page("A", objective="o", steps="s")]

    done = batch.run({"A": WANT["A"], "B": WANT["B"]}, call, size=4, rounds=2)
    assert asked == [["A", "B"], ["B"]], (
        "B failed the same rule twice: a third ask would only buy the same failure"
    )
    assert set(done.good) == {"A"} and done.bad == {"B": "missing from the reply"} and done.calls == 2
    assert done.stuck == {"B": "missing"}


def test_a_page_failing_a_different_rule_each_time_is_still_asked_again_until_the_rounds_are_spent():
    asked: list[list[str]] = []

    def call(keys):
        asked.append(list(keys))
        return [page("B", thinking="")] if len(asked) == 1 else []

    done = batch.run({"B": WANT["B"]}, call, size=4, rounds=2)
    assert len(asked) == 3 and done.stuck == {"B": "missing"}, (
        "empty, then missing, then missing again: stopped"
    )


def test_every_failure_is_counted_by_the_rule_it_broke_for_the_run_log():
    def call(keys):
        return [page("A", objective="o", steps="s")]

    done = batch.run({"A": WANT["A"], "B": WANT["B"], "C": WANT["C"]}, call, size=4, rounds=2)
    assert done.faults == {"missing": 4}, "B and C missing on the first ask, again on the second"
    assert batch.line_of(done.faults) == "missing 4"
    assert batch.line_of(Counter()) == "no failures"


def test_a_failure_in_words_names_one_rule_and_every_wording_the_judges_make_is_known():
    said = {
        "steps must be a list of lines": "steps_not_list",
        "steps is empty": "steps_empty",
        "steps has 9 lines, at most 8": "steps_too_many",
        "steps line 3 has 15 words, at most 14": "step_too_long",
        "slips: 1 to 4 wanted, got 0": "slips_count",
        "slips item 2 is not a keyword and a spot": "slip_shape",
        "slips item 1 keyword must be 2 to 4 words": "keyword_length",
        "slips item 1 spot must be one short sentence of at most 20 words": "spot_length",
        "idea is empty": "idea_empty",
        "idea has 30 words, at most 25": "idea_too_long",
        "uses 'Rope': not in the school's materials": "uses_unlisted",
        "steps line 2 uses 'chalk', which the school's materials do not name": "step_word_unlisted",
        "answered twice": "answered_twice",
        "missing from the reply": "missing",
        "objective is empty": "part_empty",
        "level_0 and level_1 say the same thing": "levels_alike",
        "objective says 'she': a draft says \"the child\", never he or she": "gendered",
        "steps compares children ('better than'): a draft never sets one child against another": "compares",
        "something nobody wrote": "other",
    }
    assert {w: batch.rule_of(w) for w in said} == said


def test_pages_are_sent_in_batches_of_the_size_the_row_says_and_a_refused_call_ends_the_run_cleanly():
    asked: list[list[str]] = []
    want = {str(i): ["thinking"] for i in range(10)}

    def call(keys):
        asked.append(list(keys))
        if len(asked) == 2:
            raise batch.Stop("campaign m1-11 stopped: $23.01 spent")
        return [page(k, thinking="t") for k in keys]

    done = batch.run(want, call, size=4, rounds=1)
    assert [len(a) for a in asked] == [4, 4], "the third batch is never sent"
    assert len(done.good) == 4 and done.stopped == "campaign m1-11 stopped: $23.01 spent"
    assert len(done.bad) == 6 and all(v == "not asked: the run stopped" for v in done.bad.values())


def test_a_material_line_must_name_something_the_schools_own_text_names_with_a_real_quantity_or_none():
    text = "Green and yellow Arch-1 each, 10 wooden cubes, red thin square slabs-1 each"
    items = [
        {"name": "wooden cube", "quantity": 10, "unit": "piece"},
        {"name": "square slab", "quantity": None, "unit": "piece"},
        {"name": "magic wand", "quantity": 1, "unit": "piece"},
        {"name": "arch", "quantity": 0, "unit": "piece"},
        {"name": "arch", "quantity": 1, "unit": " "},
    ]
    good, bad = batch.judge_materials(items, text)
    assert [g["name"] for g in good] == ["wooden cube", "square slab"]
    assert bad == [
        "magic wand: not in the school's text",
        "arch: quantity must be a number above 0, or empty",
        "arch: unit is empty",
    ]


def test_each_verdict_is_judged_on_its_own_and_a_verdict_for_a_page_not_asked_is_ignored():
    got = [
        {"key": "A", "verdict": "agree", "why": "ok"},
        {"key": "B", "verdict": "maybe", "why": "?"},
        {"key": "Q", "verdict": "agree", "why": "stray"},
        {"key": "C", "verdict": "disagree", "why": "levels say the same"},
    ]
    good, bad = batch.judge_verdicts(got, ["A", "B", "C"])
    assert good == {"A": ("agree", "ok"), "C": ("disagree", "levels say the same")}
    assert bad == {"B": "verdict is not agree or disagree"}


def test_a_reply_the_model_wrapped_as_an_object_with_its_list_is_unwrapped():
    reply = {"pages": [page("B", thinking="t")]}
    assert batch.items(reply, "pages")[0]["key"] == "B" and batch.items(json.dumps(reply), "pages") == []


def test_a_material_name_must_be_a_phrase_of_the_text_with_its_number_and_unit_beside_it():
    text = "5 red counters, 2 blue dice, 1 set of paints"
    names = lambda items: [g["name"] for g in batch.judge_materials(items, text)[0]]  # noqa: E731
    one = lambda name, q, u: [{"name": name, "quantity": q, "unit": u}]  # noqa: E731
    assert names(one("red counter", 5, "piece")) == ["red counter"]
    assert names(one("red dice", 99, "piece")) == [], "'red' and 'dice' are in the text, but never together"
    assert names(one("blue dice", 99, "piece")) == [], "99 is not beside the dice"
    assert names(one("blue dice", 2, "box")) == [], "a box is not in the text"
    assert names(one("paint", 1, "set")) == ["paint"]
    assert names(one("blue dice", None, "piece")) == ["blue dice"], "no quantity asked, none needed"
    bad = batch.judge_materials(one("red dice", 1, "piece"), text)[1]
    assert bad == ["red dice: not in the school's text"]


def test_a_materials_text_is_split_where_the_school_separates_things_and_not_inside_brackets():
    got = batch.pieces_of("Crayons (red, blue, green), Paper; Tape\nGlue")
    assert [p.strip() for p in got] == ["Crayons (red, blue, green)", "Paper", "Tape", "Glue"]
    assert batch.pieces_of("") == [] and [p.strip() for p in batch.pieces_of("Beads")] == ["Beads"]


def test_a_word_is_one_word_whether_plural_or_british_and_a_word_ending_in_ss_is_not_a_plural():
    same = [
        ("boxes", "box"),
        ("glasses", "glass"),
        ("berries", "berry"),
        ("colours", "colors"),
        ("colour", "color"),
    ]
    for a, b in same:
        assert batch._tokens(a) == batch._tokens(b), (a, b)
    assert batch._tokens("glass") == ["glass"] and batch._tokens("class") == ["class"]
    assert batch._tokens("bus") == ["bus"] and batch._tokens("beads") == ["bead"]
