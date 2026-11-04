"""M1-11: a batch of pages is judged item by item (goals/m1-11-k2-complete-v1.yaml).

Several pages go to the model in one call to keep the run inside Nimish's $25. One bad page in a reply must not cost
the others: every item is checked on its own by code, the good ones are kept, and only the bad or missing ones go
round again. Nothing here calls a model; `call` is whatever answers for the keys it is given.
"""

import json

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
    assert good == {"A": {"objective": "o", "steps": "s"}} and bad["B"] == "missing from the reply"


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
    assert asked == [["A", "B"], ["B"], ["B"]], "the first ask and two more rounds, B alone"
    assert set(done.good) == {"A"} and done.bad == {"B": "missing from the reply"} and done.calls == 3


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
