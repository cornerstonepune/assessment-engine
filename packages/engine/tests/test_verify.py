"""The verifier is the guarantee behind ADR 0005: a model writes the items, code decides which
ones exist. Every rejection reason here is a way a printed sheet could otherwise carry a wrong
key or test the wrong thing. The three `spike_*` cases are the malformed items the first real
run produced (research/2026-09-17-prompt-generation-spike.md)."""
import pytest

from engine.assess import items as I
from engine.assess import misconceptions as M
from engine.assess import verify

HARD_SUB = {"op": "-", "digits": [3, 3], "regroups": [1], "no_zero_top": True}


def cand(**kw):
    base = {"format": "column_grid", "op": "-", "a": 582, "b": 346, "answer": 236, "stem": "",
            "missing": None, "misconceptions": []}
    return base | kw


def test_a_correct_candidate_has_no_problems():
    assert verify.problems(cand(), HARD_SUB) == []


@pytest.mark.parametrize("a,b,answer", [(582, 236, 236), (643, 281, 281), (864, 391, 391)])
def test_spike_field_fill_errors_are_rejected_on_the_answer(a, b, answer):
    reasons = verify.problems(cand(format="missing_number", a=a, b=b, answer=answer,
                                   stem=f"{a} − □ = {answer}", missing="b"), HARD_SUB)
    assert any(r.startswith("answer") for r in reasons), reasons


def test_wrong_regroup_count_is_rejected():
    assert any("regroup" in r for r in verify.problems(cand(a=987, b=123, answer=864), HARD_SUB))


def test_zero_in_top_number_is_rejected_when_the_rule_forbids_it():
    assert any("zero" in r for r in verify.problems(cand(a=502, b=346, answer=156), HARD_SUB))


def test_digit_counts_are_checked():
    assert any("digit" in r for r in verify.problems(cand(a=82, b=46, answer=36), HARD_SUB))


def test_misconception_claim_that_disagrees_with_the_predictor_is_rejected():
    truth = M.predict("-", 582, 346)["M_SMALL_FROM_LARGE"]
    bad = cand(misconceptions=[{"code": "M_SMALL_FROM_LARGE", "wrong_answer": truth + 1}])
    assert any("M_SMALL_FROM_LARGE" in r for r in verify.problems(bad, HARD_SUB))


def test_misconception_claim_that_cannot_occur_here_is_rejected():
    # 582 - 346 has no zero on top, so the across-zero mistakes cannot happen on it
    bad = cand(misconceptions=[{"code": "M_ZERO_LENDER", "wrong_answer": 100}])
    assert any("M_ZERO_LENDER" in r for r in verify.problems(bad, HARD_SUB))


def test_misconception_claim_matching_the_predictor_is_accepted():
    truth = M.predict("-", 582, 346)
    good = cand(misconceptions=[{"code": k, "wrong_answer": v} for k, v in truth.items()])
    assert verify.problems(good, HARD_SUB) == []


def test_claims_are_accepted_when_no_predictor_table_exists_for_the_operation():
    mult = {"op": "×", "digits": [2, 1], "regroups": [1]}
    c = cand(op="×", a=56, b=3, answer=168, misconceptions=[{"code": "M_MULT_CONCAT", "wrong_answer": 1518}])
    assert not any("M_MULT_CONCAT" in r for r in verify.problems(c, mult))


def test_forbidden_word_in_a_stem_is_rejected():
    c = cand(format="word_1step", stem="Riya borrows 346 rupees from her 582. How much is left?")
    assert any("borrow" in r for r in verify.problems(c, HARD_SUB))


def test_word_items_need_a_stem_and_bare_items_must_not_have_one():
    assert any("stem" in r for r in verify.problems(cand(format="word_1step", stem=""), HARD_SUB))
    assert any("stem" in r for r in verify.problems(cand(format="bare_sum", stem="hello"), HARD_SUB))


def test_word_stem_must_contain_both_numbers():
    c = cand(format="word_1step", stem="A bus has 582 seats. Some are taken. How many are empty?")
    assert any("stem" in r for r in verify.problems(c, HARD_SUB))


def test_unknown_format_is_rejected():
    assert any("format" in r for r in verify.problems(cand(format="area_model"), HARD_SUB))


def test_across_zero_rule_requires_a_zero_in_a_lender_column():
    rule = {"op": "-", "digits": [3, 3], "regroups": [1, 2], "across_zero": True}
    assert any("zero" in r for r in verify.problems(cand(a=582, b=346, answer=236), rule))
    assert verify.problems(cand(a=502, b=346, answer=156), rule) == []


# ---- to_item: the accepted candidate must be indistinguishable from a generator's Item

def test_bare_candidate_becomes_the_same_item_shape_the_generator_makes():
    it = verify.to_item(cand(), "R10")
    assert it.fmt == "column_grid" and it.rung == "R10" and it.skills == I.RUNGS["R10"]["skills"]
    assert it.spec == {"a": 582, "b": 346, "op": "-", "layout": "column"}
    assert it.responses[0].rid == "ans" and it.responses[0].answer == "236"
    assert it.responses[0].misconceptions == M.predict("-", 582, 346)
    assert it.item_id == verify.to_item(cand(), "R10").item_id


def test_word_candidate_gets_the_wrong_operation_distractor_like_the_generator():
    stem = "Riya had 582 rupees and spent 346 on a kite. How much is left?"
    it = verify.to_item(cand(format="word_1step", stem=stem), "R10")
    assert it.fmt == "word_1step" and it.signal == "Application" and it.stem == stem
    assert it.responses[0].misconceptions["M_WRONG_OP"] == 582 + 346


def test_missing_number_candidate_keeps_the_hidden_number_as_the_answer():
    it = verify.to_item(cand(format="missing_number", stem="582 − □ = 236", missing="b"), "R10")
    assert it.fmt == "missing_number" and it.spec["text"] == "582 − □ = 236" and it.spec["missing"] == "b"
    assert it.responses[0].answer == "346"


def test_accepted_claims_without_a_predictor_are_kept_on_the_item():
    c = cand(op="×", a=56, b=3, answer=168, misconceptions=[{"code": "M_MULT_CONCAT", "wrong_answer": 1518}])
    it = verify.to_item(c, "R10")
    assert it.responses[0].misconceptions == {"M_MULT_CONCAT": 1518}


@pytest.mark.parametrize("written,meant", [("−", "-"), ("–", "-"), ("x", "×"), ("*", "×"), ("+", "+")])
def test_the_models_symbol_for_an_operation_is_folded_to_ours(written, meant):
    # The first real run died on U+2212: the model wrote a typographic minus and the whole batch was refused.
    assert verify.normalise(cand(op=written))["op"] == meant
    assert verify.problems(verify.normalise(cand(op="−")), HARD_SUB) == []


def test_compute_covers_multiplication_and_predict_is_empty_for_it():
    assert M.compute("×", 56, 3) == 168
    assert M.predict("×", 56, 3) == {}
