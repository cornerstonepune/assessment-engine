"""The gold-set eval of the curriculum mapping agents (goals/m1-05-mapping-agents.yaml, engine/w1_bank/map_eval.py).

Pure code: a recorded run over placeholder activities, scored against what people mapped. No model is called.
"""

import json

from engine.w1_bank.map_eval import Scored, held_out, lo_skill_pairs, score

RECORDED = json.loads(
    """
    {"gold": {"A1": ["NUM.CNT.01"], "A2": ["NUM.CNT.01", "MOT.FMS.01"], "A3": ["ART.CLR.01"], "A4": ["LIT.PHO.01"],
              "A5": ["NUM.CNT.02"]},
     "run": [
       {"activity": "A1", "skills": ["NUM.CNT.01"], "status": "auto_passed"},
       {"activity": "A2", "skills": ["NUM.CNT.01"], "status": "auto_passed"},
       {"activity": "A3", "skills": ["ART.CLR.02"], "status": "auto_passed"},
       {"activity": "A4", "skills": ["LIT.PHO.01"], "status": "needs_person"},
       {"activity": "A5", "skills": ["NUM.CNT.09"], "status": "rejected"}]}
    """
)


def test_a_recorded_gold_run_is_scored_by_code_against_what_people_mapped():
    s = score(
        [Scored(r["activity"], frozenset(r["skills"]), r["status"]) for r in RECORDED["run"]],
        {a: frozenset(v) for a, v in RECORDED["gold"].items()},
    )
    # auto-passed: A1 all right, A2 all right (one of two found), A3 wrong → 2 of 3 all right
    assert s["skill_all_right"] == 2 / 3
    # of the 4 links people made on auto-passed activities, 2 were found
    assert s["skill_found"] == 2 / 4
    assert s["auto_passed"] == 3 / 5
    assert s["n"] == 5


def test_nothing_auto_passed_scores_zero_never_a_free_pass():
    s = score([Scored("A1", frozenset({"NUM.CNT.01"}), "needs_person")], {"A1": frozenset({"NUM.CNT.01"})})
    assert s["skill_all_right"] == 0.0 and s["skill_found"] == 0.0 and s["auto_passed"] == 0.0


def test_the_held_out_share_is_the_same_every_run_and_drawn_from_every_subject():
    acts = {f"ACT-K2-{i:04d}": ("Maths" if i % 3 else "Clay") for i in range(1, 101)}
    one, two = held_out(acts, 0.2), held_out(acts, 0.2)
    assert one == two
    assert {acts[a] for a in one} == {"Maths", "Clay"}
    assert len(one) == round(0.2 * 67) + round(0.2 * 33)


def test_a_subject_with_one_activity_still_gives_one_to_the_held_out_share():
    assert held_out({"A1": "Hindi", "A2": "Maths", "A3": "Maths"}, 0.2) == {"A1"} | (
        held_out({"A2": "Maths", "A3": "Maths"}, 0.2)
    )


def test_an_objective_takes_a_skill_by_code_only_where_its_activity_leaves_no_doubt():
    pairs = lo_skill_pairs(
        objectives={"A1": {"LO1"}, "A2": {"LO2", "LO3"}, "A3": {"LO4", "LO5"}},
        skills={"A1": {"S1", "S2"}, "A2": {"S3"}, "A3": {"S4", "S5"}},
    )
    # A1: one objective, it tests both skills; A2: one skill, both objectives test it; A3: two and two, no guess
    assert pairs == {("LO1", "S1"): "A1", ("LO1", "S2"): "A1", ("LO2", "S3"): "A2", ("LO3", "S3"): "A2"}
