"""English for Grades 3 and 4, ready for the English educator (goals/english-kinds-and-samples.yaml).

Nimish's locked scope of 22 Oct 2026: "the English content (skills, kinds of question, samples for the English
educator to approve) is prepared now, content only". These tests read the seed rows in supabase/seed/english/
directly, apart from the code that drafted and checked them: every sample has an answer, a level, a kind, and
likely wrong answers that each name a real mistake of its skill; three samples for every kind a level uses; every
kind says whether code checks its one right answer or a person reads every open answer; every objective that is not
on a paper is a milestone an educator marks yes, sometimes or not yet. The rows are not loaded: a loader comes with
the build.
"""

import copy
import importlib
import json
import sys
from collections import Counter

import pytest

from engine.core import db

SEED = db.REPO_ROOT / "supabase/seed/english"
LEVELS = ["Easy", "Medium", "Hard", "Advance"]


def rows(name):
    return next(iter(json.loads((SEED / f"{name}.json").read_text()).values()))


@pytest.fixture(scope="module")
def t():
    return {n: rows(n) for n in ("skill", "skill_level", "skill_level_sample", "misconception", "skill_mistake",
                                 "question_type", "not_on_paper", "observed_skill")}  # fmt: skip


def faults(t):
    """Every sample's answer, level, kind and wrong answers, checked from the rows alone."""
    skills = {s["code"]: s for s in t["skill"]}
    levels = {(lv["skill_code"], lv["difficulty"]) for lv in t["skill_level"]}
    kinds = {q["code"]: q for q in t["question_type"]}
    real = {m["code"] for m in t["misconception"]}
    linked = {(x["skill_code"], x["misconception_code"]) for x in t["skill_mistake"]}
    out = []
    for s in t["skill_level_sample"]:
        label = f"{s['skill_code']} {s['difficulty']} {s['question_type']} #{s['n']}"
        if s["answer"] in (None, "", [], {}):
            out.append(f"{label}: no answer")
        if s["difficulty"] not in LEVELS or (s["skill_code"], s["difficulty"]) not in levels:
            out.append(f"{label}: not a level of its skill")
        skill = skills.get(s["skill_code"])
        if s["question_type"] not in kinds or not skill or s["question_type"] not in skill["question_types"]:
            out.append(f"{label}: not a kind its skill uses")
        if not s.get("wrong"):
            out.append(f"{label}: no likely wrong answer")
        for wrong, code in (s.get("wrong") or {}).items():
            if code not in real:
                out.append(f"{label}: {wrong!r} names {code}, which is not one of the named mistakes")
            elif (s["skill_code"], code) not in linked:
                out.append(f"{label}: {wrong!r} names {code}, which is not a mistake of this skill")
    return out


def test_every_sample_has_an_answer_a_level_a_kind_and_wrong_answers_naming_real_mistakes(t):
    assert faults(t) == []
    assert len(t["skill_level_sample"]) > 2400
    assert len({m["code"] for m in t["misconception"]}) == 340


def test_every_kind_a_level_uses_has_three_samples(t):
    per = Counter((s["skill_code"], s["difficulty"], s["question_type"]) for s in t["skill_level_sample"])
    numbers = {}
    for s in t["skill_level_sample"]:
        numbers.setdefault((s["skill_code"], s["difficulty"], s["question_type"]), []).append(s["n"])
    assert all(sorted(v) == [1, 2, 3] for v in numbers.values())
    assert set(per.values()) == {3}
    for s in t["skill"]:
        assert {d for k, d, _ in per if k == s["code"]} == set(LEVELS)
        assert {q for k, _, q in per if k == s["code"]} == set(s["question_types"])


def test_a_made_up_mistake_a_missing_level_and_an_empty_wrong_answer_are_caught(t):
    bad = copy.deepcopy(t)
    one, two, three = bad["skill_level_sample"][:3]
    one["wrong"] = {"bakeing": "M_ENG_NOT_A_MISTAKE"}
    two["difficulty"] = "Tricky"
    three["wrong"] = {}
    found = faults(bad)
    assert any("M_ENG_NOT_A_MISTAKE, which is not one of the named mistakes" in f for f in found)
    assert any("Tricky" in f and "not a level of its skill" in f for f in found)
    assert any("no likely wrong answer" in f for f in found)


def test_every_kind_says_one_right_answer_code_checks_or_an_open_answer_a_person_reads(t):
    kinds = {q["code"]: q for q in t["question_type"]}
    on_paper = {q for s in t["skill"] for q in s["question_types"]}
    for code in on_paper:
        q = kinds[code]
        assert (q["answer"], q["marked_by"]) in {("one", "code"), ("open", "educator")}, code
        if q["answer"] == "open":
            assert q["first_answers"] == "every answer seen by a person"
    assert {kinds[c]["answer"] for c in on_paper} == {"one", "open"}


def test_every_objective_not_on_a_paper_is_a_milestone_marked_yes_sometimes_or_not_yet(t):
    off = [n["objective"] for n in t["not_on_paper"]]
    placed = Counter(o for x in t["observed_skill"] for o in x["objectives"])
    assert sorted(placed) == sorted(off) and set(placed.values()) == {1}
    for x in t["observed_skill"]:
        assert x["scale"] == ["yes", "sometimes", "not yet"]
        assert x["milestone"].strip() and len(x["milestone"].split()) <= 30
        assert x["grade"] == f"G{x['objectives'][0][0]}"


def research(name):
    path = str(db.REPO_ROOT / "research")
    if path not in sys.path:
        sys.path.insert(0, path)
    return importlib.import_module(name)


def test_a_wrong_answer_a_rule_gives_is_the_one_the_rule_gives(t):
    ew = research("english_wrong")
    mistakes = {}
    for x in t["skill_mistake"]:
        mistakes.setdefault(x["skill_code"], []).append(x["misconception_code"])
    reproduced = 0
    for s in t["skill_level_sample"]:
        found, ran = ew.check(s, mistakes[s["skill_code"]])
        assert not [f for f in found if " gives " in f], found
        reproduced += ran.get("wrong answer reproduced from its mistake", 0)
    assert reproduced > 100
    bake = {"question_type": "ENG.WRITE_WORD", "answer": "baking", "check": {"compute": "add_ending", "base": "bake",
            "ending": "ing"}, "wrong": {"bakking": "M_ENG_E_KEPT"}}  # fmt: skip
    assert any("M_ENG_E_KEPT gives" in f for f in ew.check(bake, ["M_ENG_E_KEPT"])[0])
