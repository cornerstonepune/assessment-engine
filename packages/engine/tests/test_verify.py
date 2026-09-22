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
    base = {
        "format": "column_grid",
        "op": "-",
        "a": 582,
        "b": 346,
        "answer": 236,
        "stem": "",
        "missing": None,
        "misconceptions": [],
    }
    return base | kw


def test_a_correct_candidate_has_no_problems():
    assert verify.problems(cand(), HARD_SUB) == []


@pytest.mark.parametrize("a,b,answer", [(582, 236, 236), (643, 281, 281), (864, 391, 391)])
def test_spike_field_fill_errors_are_rejected_on_the_answer(a, b, answer):
    reasons = verify.problems(
        cand(format="missing_number", a=a, b=b, answer=answer, stem=f"{a} − □ = {answer}", missing="b"),
        HARD_SUB,
    )
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


def test_a_claim_the_predictor_cannot_check_is_dropped_and_the_item_survives():
    # 582 - 346 has no zero on top, so the across-zero predictor has nothing to say; the first
    # real fill rejected every item this way ("aligns from the left" on 243 - 27) and stored none.
    c = cand(misconceptions=[{"code": "M_ZERO_LENDER", "wrong_answer": 100}])
    assert verify.problems(c, HARD_SUB) == []
    assert "M_ZERO_LENDER" not in verify.to_item(c, "R10").responses[0].misconceptions


@pytest.mark.parametrize("delta", [1, -1])
def test_off_by_one_is_accepted_in_either_direction(delta):
    c = cand(misconceptions=[{"code": "M_FACT_PM1", "wrong_answer": 236 + delta}])
    assert verify.problems(c, HARD_SUB) == []
    assert any(
        "M_FACT_PM1" in r
        for r in verify.problems(
            cand(misconceptions=[{"code": "M_FACT_PM1", "wrong_answer": 236 + 2}]), HARD_SUB
        )
    )


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


def test_an_op_list_in_the_rule_accepts_either_operation():
    # R4 mixes + and - in one unit (ADR 0010's rungs are one skill_set per rung, not one per op).
    rule = {"op": ["+", "-"], "digits": [2, 2], "regroups": [0]}
    assert verify.problems(cand(format="bare_sum", op="+", a=23, b=45, answer=68), rule) == []
    assert verify.problems(cand(format="bare_sum", op="-", a=45, b=23, answer=22), rule) == []


# ---- dimension_problems: the item as measured against the band as declared (gate 4, amended)


def _tags_for(c, rung="R6"):
    from engine.assess import tags

    return tags.derive(verify.to_item(c, rung))


def test_an_item_inside_its_bands_region_has_no_dimension_problems():
    assert verify.dimension_problems(_tags_for(cand()), HARD_SUB) == []


def test_wrong_digit_count_is_a_dimension_problem_even_when_the_arithmetic_is_right():
    # 82 - 46 is a fine subtraction; it is just not a 3-digit-minus-3-digit one.
    probs = verify.dimension_problems(_tags_for(cand(a=82, b=46, answer=36)), HARD_SUB)
    assert any("digits" in p for p in probs), probs


def test_a_band_pinned_to_a_story_rejects_a_bare_sum():
    # R1's Hard band is "the same sums, told as a story" — a bare 3 + 4 filed there is in the
    # wrong band even though every number is right. This is the R1/R2 collision, caught by data.
    band = {"format": "word_1step", "op": "+", "digits": [1, 1], "regroups": [0], "max_total": 10}
    bare = cand(format="bare_sum", op="+", a=3, b=4, answer=7)
    assert any("word_1step" in p for p in verify.dimension_problems(_tags_for(bare, "R1"), band))
    story = cand(
        format="word_1step",
        op="+",
        a=3,
        b=4,
        answer=7,
        stem="Riya has 3 marbles. Kabir gives Riya 4 more. How many marbles does Riya have now?",
    )
    assert verify.dimension_problems(_tags_for(story, "R1"), band) == []


def test_dimensions_the_tags_do_not_carry_are_not_judged():
    # A balance-scale item's tags stop at the format level; a digits rule on it is not a mismatch,
    # it is simply unmeasured — and the format level is still checked.
    tags = {"context": "BARE_NUMBER", "reasoning_type": "BALANCE", "unknown_type": "WHOLE_NUMBER"}
    assert verify.dimension_problems(tags, {"format": "balance_scale", "hi": 150, "digits": [2, 2]}) == []
    assert verify.dimension_problems(tags, {"format": "find_mistake"}) != []


def test_an_op_not_in_the_rules_list_is_rejected():
    rule = {"op": ["+", "-"], "digits": [2, 2], "regroups": [0]}
    assert any(
        "op" in r for r in verify.problems(cand(format="bare_sum", op="×", a=23, b=45, answer=68), rule)
    )


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


def test_a_claim_under_a_name_of_the_models_own_survives_verify_and_is_dropped_at_the_bank():
    """`verify` is pure and cannot know the vocabulary, so it keeps the claim; `bank._strip_unnamed`
    drops it where a connection can check, and counts it. Kept on the item it would be unmarkable."""
    c = cand(op="×", a=56, b=3, answer=168, misconceptions=[{"code": "M_MULT_CONCAT", "wrong_answer": 1518}])
    it = verify.to_item(c, "R10")
    assert it.responses[0].misconceptions["M_MULT_CONCAT"] == 1518
    assert "M_MUL_CONCAT" in it.responses[0].misconceptions, "and the real one is computed alongside"

    from engine.w1_bank import bank

    dropped = bank._strip_unnamed(it, set(M.PREDICTED))
    assert dropped == 1 and "M_MULT_CONCAT" not in it.responses[0].misconceptions


@pytest.mark.parametrize("written,meant", [("−", "-"), ("–", "-"), ("x", "×"), ("*", "×"), ("+", "+")])
def test_the_models_symbol_for_an_operation_is_folded_to_ours(written, meant):
    # The first real run died on U+2212: the model wrote a typographic minus and the whole batch was refused.
    assert verify.normalise(cand(op=written))["op"] == meant
    assert verify.problems(verify.normalise(cand(op="−")), HARD_SUB) == []


def test_multiplication_is_predicted_now_that_a_rung_asks_for_it():
    """Was `predict is empty for it`, which was true and was the defect: MUL.1D produced 20 correct
    questions of which 14 had no named mistake to mark against, found by `engine goal`."""
    assert M.compute("×", 56, 3) == 168
    got = M.predict("×", 56, 3)
    assert got["M_MUL_CONCAT"] == 1518 and got["M_MUL_ONES_ONLY"] == 18
    assert got["M_MUL_ROW_OUT"] == 112 and got["M_WRONG_OP"] == 59
    assert 168 not in got.values(), "a distractor is never the right answer"
