"""The checks every English sample passes before it is stored (goals/edt_edit_samples_and_kinds.yaml): code, never a model.

Nimish, 2026-10-24: "It should simply have the capability to edit the skill … or change the nature of the question." An
educator may now change a sample; what they save is checked here first. Each rule has a good case and a bad one, and
every sample of the seed passes them all, so the port from research/english_check.py and english_wrong.py lost nothing.
"""

import json

import pytest

from engine.core import db
from engine.w1_bank import english_check as ec
from engine.w1_bank import english_form as ef

MISTAKES = {"M_ENG_A": "Picks the word that looks like it", "M_ENG_B": "Keeps the printed order"}


def ctx(**kw):
    base = {"open": False, "mistakes": MISTAKES, "rule": {}, "rubrics": {"R_ENG_WRITE"}, "passage": ""}
    return ec.Context(**{**base, **kw})


def choose(**kw):
    s = {
        "question_type": "ENG.CHOOSE",
        "ask": "Tick the word that names a colour.",
        "text": None,
        "options": ["red", "run", "ran"],
        "answer": "red",
        "accept": [],
        "wrong": [{"answer": "run", "mistake_code": "M_ENG_A"}],
    }
    return {**s, **kw}


def fields(faults):
    return sorted(faults)


def test_a_good_choice_has_no_fault():
    assert ec.faults(choose(), ctx()) == {}


def test_a_choice_needs_its_right_answer_among_the_options():
    f = ec.faults(choose(answer="blue"), ctx())
    assert "answer" in f and "not one of the options" in f["answer"][0]


def test_a_choice_needs_two_different_options():
    assert "options" in ec.faults(choose(options=["red", "red"], wrong=[]), ctx())


def test_a_gap_needs_its_gap_and_its_answer_in_the_word_bank():
    gap = choose(
        question_type="ENG.GAP",
        text="The sky is ___.",
        options=["blue", "glue"],
        answer="blue",
        wrong=[{"answer": "glue", "mistake_code": "M_ENG_A"}],
    )
    assert ec.faults(gap, ctx()) == {}
    assert "text" in ec.faults({**gap, "text": "The sky is blue."}, ctx())
    assert "answer" in ec.faults({**gap, "answer": "grey"}, ctx())
    assert "text" in ec.faults({**gap, "text": "The ___ is ___."}, ctx())


def test_a_wrong_answer_must_differ_from_the_right_one_and_from_each_other():
    f = ec.faults(choose(wrong=[{"answer": "red", "mistake_code": "M_ENG_A"}]), ctx())
    assert "is a right answer" in " ".join(f["wrong.0"])
    f = ec.faults(
        choose(
            wrong=[{"answer": "run", "mistake_code": "M_ENG_A"}, {"answer": "Run", "mistake_code": "M_ENG_B"}]
        ),
        ctx(),
    )
    assert "twice" in " ".join(f["wrong.1"])


def test_a_wrong_answer_names_one_of_the_skills_mistakes():
    f = ec.faults(choose(wrong=[{"answer": "run", "mistake_code": "M_ENG_ZZZ"}]), ctx())
    assert "mistakes of this skill" in " ".join(f["wrong.0"])
    f = ec.faults(choose(wrong=[{"answer": "run", "mistake_code": ""}]), ctx())
    assert "wrong.0" in f


def test_a_sample_needs_at_least_one_likely_wrong_answer():
    assert "wrong" in ec.faults(choose(wrong=[]), ctx())


def test_a_wrong_choice_is_a_printed_option():
    f = ec.faults(choose(wrong=[{"answer": "blue", "mistake_code": "M_ENG_A"}]), ctx())
    assert "not one of the printed options" in " ".join(f["wrong.0"])


def order(**kw):
    s = {
        "question_type": "ENG.ORDER",
        "ask": "Put the words in dictionary order.",
        "text": None,
        "options": ["cat", "ant", "bee"],
        "answer": ["ant", "bee", "cat"],
        "accept": [],
        "wrong": [{"answer": "cat, ant, bee", "mistake_code": "M_ENG_B"}],
    }
    return {**s, **kw}


def test_an_order_is_every_item_once_and_a_wrong_order_is_a_real_reorder():
    assert ec.faults(order(), ctx()) == {}
    assert "answer" in ec.faults(order(answer=["ant", "bee"]), ctx())
    f = ec.faults(order(wrong=[{"answer": "cat, ant", "mistake_code": "M_ENG_B"}]), ctx())
    assert "every item once" in " ".join(f["wrong.0"])
    f = ec.faults(order(wrong=[{"answer": "ant, bee, cat", "mistake_code": "M_ENG_B"}]), ctx())
    assert "wrong.0" in f


def match(**kw):
    s = {
        "question_type": "ENG.MATCH",
        "ask": "Draw a line from each word to what it means.",
        "text": None,
        "options": {"left": ["rebuild", "painless"], "right": ["build again", "without pain"]},
        "answer": [["rebuild", "build again"], ["painless", "without pain"]],
        "accept": [],
        "wrong": [{"answer": "rebuild - without pain", "mistake_code": "M_ENG_A"}],
    }
    return {**s, **kw}


def test_a_match_pairs_every_left_item_and_a_wrong_pair_is_one_the_key_does_not_make():
    assert ec.faults(match(), ctx()) == {}
    assert "answer" in ec.faults(match(answer=[["rebuild", "build again"]]), ctx())
    f = ec.faults(match(wrong=[{"answer": "rebuild - build again", "mistake_code": "M_ENG_A"}]), ctx())
    assert "a pair the key makes" in " ".join(f["wrong.0"])


def sort(**kw):
    s = {
        "question_type": "ENG.SORT",
        "ask": "Write each word under the key word with the same ea sound.",
        "text": "tea / bed",
        "options": ["head", "seat", "bread", "leaf"],
        "answer": {"ea as in tea": ["seat", "leaf"], "ea as in bed": ["head", "bread"]},
        "accept": [],
        "wrong": [{"answer": "head: ea as in tea", "mistake_code": "M_ENG_A"}],
    }
    return {**s, **kw}


def test_a_sort_puts_every_item_in_one_group_and_a_wrong_answer_in_another():
    assert ec.faults(sort(), ctx()) == {}
    assert "answer" in ec.faults(
        sort(answer={"ea as in tea": ["seat"], "ea as in bed": ["head", "bread"]}), ctx()
    )
    f = ec.faults(sort(wrong=[{"answer": "seat: ea as in tea", "mistake_code": "M_ENG_A"}]), ctx())
    assert "where the key puts it" in " ".join(f["wrong.0"])


def test_marked_words_are_words_in_the_text():
    s = {
        "question_type": "ENG.MARK_WORDS",
        "ask": "Underline the verbs.",
        "text": "Meera runs and jumps.",
        "options": None,
        "answer": ["runs", "jumps"],
        "accept": [],
        "wrong": [{"answer": "Meera", "mistake_code": "M_ENG_A"}],
    }
    assert ec.faults(s, ctx()) == {}
    assert "answer" in ec.faults({**s, "answer": ["runs", "swims"]}, ctx())
    assert "wrong.0" in ec.faults({**s, "wrong": [{"answer": "swims", "mistake_code": "M_ENG_A"}]}, ctx())


def test_punctuating_keeps_the_words():
    s = {
        "question_type": "ENG.PUNCTUATE",
        "ask": "Write the sentence again with its capital letter and full stop.",
        "text": "the dog ran home",
        "options": None,
        "answer": "The dog ran home.",
        "accept": [],
        "wrong": [{"answer": "The dog ran home", "mistake_code": "M_ENG_A"}],
    }
    assert ec.faults(s, ctx()) == {}
    assert "answer" in ec.faults({**s, "answer": "The cat ran home."}, ctx())
    assert "wrong.0" in ec.faults(
        {**s, "wrong": [{"answer": "A cat ran home", "mistake_code": "M_ENG_A"}]}, ctx()
    )


def test_copied_words_are_in_the_passage():
    s = {
        "question_type": "ENG.COPY",
        "ask": "Copy the words that tell you where the fort is.",
        "text": None,
        "options": None,
        "answer": "on a hill",
        "accept": [],
        "wrong": [{"answer": "near the sea", "mistake_code": "M_ENG_A"}],
    }
    f = ec.faults(s, ctx(passage="The fort stands on a hill near Pune."))
    assert "is not copied from the passage" in " ".join(f["wrong.0"])
    assert "answer" in ec.faults(
        {**s, "answer": "by the river"}, ctx(passage="The fort stands on a hill near Pune.")
    )


def test_british_spelling_and_the_schools_words():
    f = ec.faults(choose(ask="Tick the word that names a color."), ctx())
    assert "color" in " ".join(f["ask"])
    f = ec.faults(choose(ask="Tick the word you would carry over."), ctx())
    assert "carry" in " ".join(f["ask"])
    # a word shown on purpose that is not one: listed, and the dictionary must not know it
    s = choose(
        question_type="ENG.WRITE_WORD",
        options=None,
        ask="Write the word that ends in ough.",
        answer="cough",
        not_words=["ough"],
        wrong=[{"answer": "cof", "mistake_code": "M_ENG_A"}],
    )
    assert ec.faults(s, ctx()) == {}
    assert "answer" in ec.faults({**s, "not_words": None, "answer": "ough"}, ctx())


def test_an_open_kind_needs_its_rubric_and_what_a_right_answer_does():
    s = {
        "question_type": "ENG.SHORT_WRITE",
        "ask": "Write two commands telling a friend how to water a plant.",
        "text": None,
        "options": None,
        "answer": "Fill the can with water. Pour it slowly round the plant.",
        "accept": [],
        "rubric_code": "R_ENG_WRITE",
        "key_points": ["two sentences", "each starts with a bossy verb"],
        "wrong": [{"answer": "You pour water on the plant", "mistake_code": "M_ENG_A"}],
    }
    assert ec.faults(s, ctx(open=True)) == {}
    assert "rubric" in ec.faults({**s, "rubric_code": None}, ctx(open=True))
    assert "key_points" in ec.faults({**s, "key_points": []}, ctx(open=True))


def test_the_levels_rule_holds():
    f = ec.faults(choose(), ctx(rule={"options": 4}))
    assert "options" in f and "4" in f["options"][0]
    assert ec.faults(choose(), ctx(rule={"options": 3})) == {}


def test_a_fault_is_said_in_words_a_person_reads():
    f = ec.faults(choose(answer="blue", wrong=[{"answer": "red", "mistake_code": "M_ENG_ZZZ"}]), ctx())
    for lines in f.values():
        for line in lines:
            assert line[0].isupper() and line.endswith(".") and "M_ENG" not in line and "ENG." not in line


def _seed(name, key):
    return json.loads((db.REPO_ROOT / "supabase/seed/english" / name).read_text())[key]


def test_every_sample_of_the_seed_passes_the_engines_checks():
    """The research checks found 0 faults in the seed; the engine's port must agree on every sample."""
    levels = {
        (lv["skill_code"], lv["difficulty"]): lv["rule"] for lv in _seed("skill_level.json", "skill_levels")
    }
    mistakes = {}
    for m in _seed("skill_mistake.json", "skill_mistakes"):
        mistakes.setdefault(m["skill_code"], {})[m["misconception_code"]] = m["misconception_code"]
    rubrics = {}
    for r in _seed("rubric.json", "rubrics"):
        for k in r["skill_codes"]:
            rubrics.setdefault(k, set()).add(r["code"])
    opened = {q["code"] for q in _seed("question_type.json", "question_types") if q["answer"] == "open"}
    passages = {p["code"]: p["text"] for p in _seed("passage.json", "passages")}
    bad = {}
    for s in _seed("skill_level_sample.json", "samples"):
        sample = {
            **s,
            "rubric_code": s.get("rubric"),
            "wrong": [{"answer": a, "mistake_code": m} for a, m in s["wrong"].items()],
        }
        c = ec.Context(
            open=s["question_type"] in opened,
            mistakes=mistakes.get(s["skill_code"], {}),
            rule=levels[(s["skill_code"], s["difficulty"])],
            rubrics=rubrics.get(s["skill_code"], set()),
            passage=passages.get(s["passage"] or "", ""),
        )
        if f := ec.faults(sample, c):
            bad[f"{s['skill_code']} {s['difficulty']} {s['question_type']} #{s['n']}"] = f
    assert bad == {}, f"{len(bad)} seed samples fail: {list(bad.items())[:3]}"


@pytest.mark.parametrize(
    "kind", ["ENG.CHOOSE", "ENG.ORDER", "ENG.MATCH", "ENG.SORT", "ENG.TABLE", "ENG.SHORT_WRITE"]
)
def test_a_form_reads_back_into_the_sample_it_was_made_from(kind):
    """What the educator's form sends (one line per option, pair, group or box) is read into the stored shape."""
    lost = []
    for s in (x for x in _seed("skill_level_sample.json", "samples") if x["question_type"] == kind):
        back = ef.from_form(kind, ef.to_form(kind, s))
        if (back["options"], back["answer"], back["accept"]) != (s["options"], s["answer"], s["accept"]):
            lost.append((s["skill_code"], s["difficulty"], s["n"]))
    assert lost == []


def test_a_fault_is_numbered_as_the_forms_rows_are_and_a_mistake_needs_its_wrong_answer():
    rows = [{"answer": "", "mistake_code": ""}, {"answer": "blue", "mistake_code": "M_ENG_A"}]
    f = ec.faults(choose(wrong=rows), ctx())
    assert "wrong.1" in f and "wrong.0" not in f, "the fault sits on the row that has it, empty rows counted"
    f = ec.faults(choose(wrong=[*choose()["wrong"], {"answer": "", "mistake_code": "M_ENG_B"}]), ctx())
    assert "Write the wrong answer" in f["wrong.1"][0]
