"""Marking is chosen by the question's own eval_type, not guessed from its shape (ADR 0012).

The point of the dispatch is that a question whose kind the engine cannot yet judge is refused
loudly. A silent wrong mark is worse than no mark: it reaches a child's record as fact.
"""

import pytest

from engine.assess import evaluate


def test_computable_marks_an_exact_answer_and_names_the_mistake():
    r = {"kind": "digits", "answer": "225", "misconceptions": {"M_SMALL_FROM_LARGE": 235, "M_FACT_PM1": 224}}
    assert evaluate.judge("computable", r, "225") == ("correct", [])
    assert evaluate.judge("computable", r, "235") == ("wrong", ["M_SMALL_FROM_LARGE"])


def test_computable_records_an_unrecognised_wrong_answer_rather_than_forcing_a_label():
    r = {"kind": "digits", "answer": "225", "misconceptions": {"M_FACT_PM1": 224}}
    status, codes = evaluate.judge("computable", r, "811")
    assert (status, codes) == ("wrong", []), "an unknown wrong answer is wrong with no diagnosis"


def test_computable_honours_a_tolerance_so_an_estimate_is_not_marked_to_the_digit():
    r = {"kind": "digits", "answer": "600", "tolerance": 10, "misconceptions": {}}
    assert evaluate.judge("computable", r, "605")[0] == "correct"
    assert evaluate.judge("computable", r, "650")[0] == "wrong"


def test_computable_keeps_blank_and_unreadable_apart_from_wrong():
    r = {"kind": "digits", "answer": "225", "misconceptions": {}}
    assert evaluate.judge("computable", r, "")[0] == "blank"
    assert evaluate.judge("computable", r, "2?5")[0] == "unreadable"


def test_a_tick_is_judged_against_its_options():
    r = {"kind": "tick", "answer": "ones column", "options": ["ones column", "tens column"]}
    assert evaluate.judge("computable", r, "ones column") == ("correct", [])
    assert evaluate.judge("computable", r, "tens column") == ("wrong", [])


def test_open_response_never_auto_marks_it_goes_to_a_person_with_the_rubric():
    r = {"kind": "text", "answer": None, "rubric": "Names the mistake: Forgets to carry"}
    assert evaluate.judge("open_response", r, "he forgot to carry the one") == ("needs_teacher", [])


def test_a_kind_with_no_evaluator_refuses_loudly_instead_of_marking():
    r = {"kind": "digits", "answer": "Paris", "misconceptions": {}}
    for kind in ("closed_set", "rule_governed"):
        with pytest.raises(NotImplementedError, match=kind):
            evaluate.judge(kind, r, "Lyon")


def test_an_unknown_eval_type_is_rejected():
    with pytest.raises(ValueError, match="eval_type"):
        evaluate.judge("vibes", {"kind": "digits", "answer": "1"}, "1")


def test_the_vocabulary_is_the_four_kinds_the_architecture_names():
    assert set(evaluate.EVAL_TYPES) == {"computable", "closed_set", "rule_governed", "open_response"}
