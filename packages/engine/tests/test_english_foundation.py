"""The English foundation for Grades 3 and 4, drafted from Cambridge Primary English 0058 (goals/english-foundation.yaml).

Nimish, 2026-10-21: "make the entire set of learning objectives, the difficulty levels, and everything as per Grade 3
and Grade 4 of the Cambridge board … Fundamental work can be done by you. The teacher will only go and approve or
edit." Grade 3 is Stage 3 and Grade 4 is Stage 4 (Nimish confirmed).

The rows are drafts in docs/drafts/english/, shaped like the maths seed tables; no database is needed. The framework
is read from the copy recorded in docs/crosswalk/sources.json, downloaded into data/crosswalk_sources/ on the first
run and refused if its fingerprint differs. research/english_check.py does the checking; these tests run it and show
that it catches what it says it catches.
"""

import copy
import importlib
import json
import subprocess
import sys

import pytest

from engine.core import db

RESEARCH = db.REPO_ROOT / "research"


def research(name):
    if str(RESEARCH) not in sys.path:
        sys.path.insert(0, str(RESEARCH))
    return importlib.import_module(name)


ec, es, er, ed = (
    research(m) for m in ("english_check", "english_samples", "english_rules", "english_derive")
)


@pytest.fixture(scope="module")
def t():
    return ec.load()


@pytest.fixture(scope="module")
def cambridge():
    return ec.framework()


def samples(t, cambridge):
    _, levels = ec.check_levels(t)
    _, used = ec.check_mistakes(t)
    return es.check(t, levels, used, *cambridge)


def test_every_stage_3_and_4_objective_is_on_a_paper_or_observed_by_an_educator(t, cambridge):
    objs, _ = cambridge
    assert ec.check_coverage(t, objs) == []
    index = json.loads((db.REPO_ROOT / "docs/crosswalk/statements/cam-pri-eng-0058.json").read_text())[
        "objectives"
    ]
    stages = {s: {o["code"] for o in index if o["stage"] == s} for s in (3, 4)}
    assert (len(stages[3]), len(stages[4])) == (102, 106)
    assert {c for c, o in objs.items() if o["stage"] in (3, 4)} == stages[3] | stages[4]
    paper = {c for s in t["skill"] for c in s["objectives"]}
    observed = {n["objective"] for n in t["not_on_paper"]}
    assert paper | observed == stages[3] | stages[4] and not paper & observed


def test_an_objective_dropped_or_invented_is_caught(t, cambridge):
    objs, _ = cambridge
    bad = copy.deepcopy(t)
    bad["not_on_paper"] = [n for n in bad["not_on_paper"] if n["objective"] != "3SLp.01"]
    bad["skill"][0]["objectives"] = [*bad["skill"][0]["objectives"], "3Rw.99"]
    faults = ec.check_coverage(bad, objs)
    assert any("3SLp.01" in f and "silently dropped" in f for f in faults)
    assert any("3Rw.99 is not an objective" in f for f in faults)


def test_every_skill_says_what_a_child_does_in_its_grade_and_teaching_order_and_none_repeats(t):
    assert ec.check_skills(t) == []
    for g in ("G3", "G4"):
        mine = [s for s in t["skill"] if s["grade"] == g]
        assert sorted(s["order"] for s in mine) == list(range(1, len(mine) + 1))


def test_a_before_that_points_nowhere_or_later_and_a_twin_skill_are_caught(t):
    bad = copy.deepcopy(t)
    first, second = bad["skill"][0], bad["skill"][1]
    first["before"] = ["EN3.NOT.A_SKILL", second["code"]]
    bad["skill"].append(
        dict(second, code="EN3.TWIN.COPY", order=len([s for s in bad["skill"] if s["grade"] == "G3"]) + 1)
    )
    faults = ec.check_skills(bad)
    assert any("EN3.NOT.A_SKILL is not another skill" in f for f in faults)
    assert any(f"{second['code']} comes before it but is taught after it" in f for f in faults)
    assert any("EN3.TWIN.COPY" in f and "the same skill" in f for f in faults)


def test_every_assessable_skill_has_four_levels_each_with_a_rule_and_three_examples_with_answers(
    t, cambridge
):
    faults, levels = ec.check_levels(t)
    assert faults == []
    order, _ = ec.vocabulary()
    assert len(levels) == 4 * len(t["skill"])
    for s in t["skill"]:
        for d in order:
            mine = [
                x for x in t["skill_level_sample"] if x["skill_code"] == s["code"] and x["difficulty"] == d
            ]
            assert sorted(x["n"] for x in mine) == [1, 2, 3] and all(
                x["answer"] not in (None, "") for x in mine
            )


def test_every_example_meets_its_level_and_code_works_its_answer_out_again(t, cambridge):
    faults, ran = samples(t, cambridge)
    assert faults == []
    recomputed = sum(n for k, n in ran.items() if k.startswith("answer recomputed"))
    assert recomputed > 150 and ran["answer in the passage"] > 50
    assert ran["not Cambridge's words"] == len(t["skill_level_sample"])


def test_a_wrong_key_a_missing_example_and_a_broken_rule_are_caught(t, cambridge):
    bad = copy.deepcopy(t)
    hop = next(s for s in bad["skill_level_sample"] if (s.get("check") or {}).get("base") == "clap")
    hop["answer"] = "claping"
    bad["skill_level_sample"] = [
        s
        for s in bad["skill_level_sample"]
        if not (s["skill_code"] == "EN3.SPELL.VERBEND" and s["n"] == 3 and s["difficulty"] == "Easy")
    ]
    faults, _ = samples(bad, cambridge)
    assert any("the rule gives 'clapping', the key says 'claping'" in f for f in faults)
    assert any("EN3.SPELL.VERBEND Easy: needs examples 1, 2 and 3" in f for f in faults)


def test_no_example_uses_cambridges_text_or_its_own_examples(t, cambridge):
    objs, text = cambridge
    bad = copy.deepcopy(t)
    one = next(s for s in bad["skill_level_sample"] if s["skill_code"] == "EN3.SPELL.CONSONANT")
    one["text"] = objs["3Ri.05"]["words"]  # an objective's own sentence, word for word
    other = next(
        s for s in bad["skill_level_sample"] if s["skill_code"] == "EN3.SPELL.CONSONANT" and s is not one
    )
    other["answer"] = "bridge"  # 3Ww.01's own example
    faults, _ = samples(bad, cambridge)
    assert any("shares Cambridge's words" in f for f in faults)
    assert any("uses Cambridge's own example ['bridge']" in f for f in faults)


def test_the_rules_code_computes_give_the_answers_an_educator_would(t):
    assert [er.add_ending(b, e) for b, e in [("hop", "ing"), ("bake", "ing"), ("cry", "ed"), ("wash", "s"), ("play", "ed")]] == [
        "hopping", "baking", "cried", "washes", "played"
    ]  # fmt: skip
    assert [er.plural("baby"), er.plural("box"), er.plural("leaf", f_to_ves=True), er.plural("wife", f_to_ves=True)] == [
        "babies", "boxes", "leaves", "wives"
    ]  # fmt: skip
    assert [er.possessive("girl"), er.possessive("girls", many=True), er.possessive("children", many=True)] == [
        "girl's", "girls'", "children's"
    ]  # fmt: skip
    assert [er.affix("happy", suffix="ness"), er.affix("create", suffix="ion"), er.affix("hope", suffix="less")] == [
        "happiness", "creation", "hopeless"
    ]  # fmt: skip
    assert er.alphabetical(["mango", "map", "melon"]) == (["mango", "map", "melon"], 3)
    assert er.contraction_fits("isn't", "is not") and not er.contraction_fits("isnt", "is not")


def test_every_mistake_is_named_with_its_wrong_answer_and_shows_in_a_skill(t):
    faults, used = ec.check_mistakes(t)
    assert faults == []
    assert all(len(v) >= 2 for v in used.values()) and len(used) == len(t["skill"])


def test_judged_writing_has_a_rubric_whose_four_levels_an_educator_and_a_model_read_alike(t):
    assert ec.check_rubrics(t) == []
    judged = {s["rubric"] for s in t["skill_level_sample"] if s["question_type"] in es.JUDGED}
    assert judged == {r["code"] for r in t["rubric"]}


def test_every_question_type_says_how_it_reaches_the_child_and_who_marks_it(t):
    kinds = {q["code"]: q for q in t["question_type"]}
    assert {q["marked_by"] for q in kinds.values()} == {"code", "model_rubric", "educator"}
    assert all(kinds[q]["reaches"] != "observed" for s in t["skill"] for q in s["question_types"])
    assert {n["question_type"] for n in t["not_on_paper"]} <= {
        c for c, q in kinds.items() if q["marked_by"] == "educator"
    }


def test_the_derived_rows_are_the_drafts_worked_out_again(t, cambridge):
    assert ed.stale(t, cambridge[0]) == []


def test_the_check_runs_from_any_directory_and_reports_its_counts(tmp_path):
    run = subprocess.run(
        [sys.executable, str(RESEARCH / "english_check.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=600,
    )
    assert run.returncode == 0, run.stdout[-3000:] + run.stderr[-3000:]
    counts = json.loads(run.stdout[: run.stdout.rindex("}") + 1])
    assert counts["G3"]["objectives"] == 102 and counts["G4"]["objectives"] == 106
    assert counts["G3"]["on_paper"] + counts["G3"]["observed_by_educator"] == 102
    assert counts["G4"]["on_paper"] + counts["G4"]["observed_by_educator"] == 106
    assert run.stdout.strip().endswith("0 faults")
