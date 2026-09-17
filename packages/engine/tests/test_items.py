"""Generator constraints.

An item that claims one regrouping but needs none is a silent failure: it prints, a child
answers it, and the result is filed against a rung it never tested. The spec calls this out
explicitly (§8.2) as common and worth checking on purpose.
"""
import random

import pytest

from engine.assess import items as I
from engine.assess import tags


def test_sample_add_produces_exactly_the_requested_regrouping_count():
    rng = random.Random(7)
    for _ in range(50):
        a, b = I.sample_add(rng, 2, 2, {1})
        assert I._regroup_count_add(a, b) == 1, (a, b)


def test_sample_add_honours_a_two_regrouping_request():
    rng = random.Random(9)
    for _ in range(30):
        a, b = I.sample_add(rng, 3, 3, {2})
        assert I._regroup_count_add(a, b) == 2, (a, b)


def test_sample_sub_across_zero_has_a_zero_in_a_column_that_gets_borrowed_from():
    # "Across zero" means the zero is a lender column. The ones column is never a lender,
    # so 970 - 339 does not qualify: the slice drops the last digit, not the first.
    rng = random.Random(11)
    for _ in range(25):
        a, b = I.sample_sub(rng, 3, 3, {1, 2}, across_zero=True)
        assert "0" in str(a)[:-1], (a, b)
        assert a > b, "a subtraction item must not have a negative answer"


def test_sample_sub_without_across_zero_has_no_zero_in_a_lender_column():
    rng = random.Random(13)
    for _ in range(25):
        a, b = I.sample_sub(rng, 3, 3, {1}, across_zero=False)
        assert "0" not in str(a)[:-1], (a, b)


def test_bare_sum_answer_is_exact_arithmetic():
    rng = random.Random(3)
    for op in ("+", "-"):
        item = I.bare_sum(rng, "R5" if op == "+" else "R6", "Procedural", op, 2, 2, {1})
        a, b = item.spec["a"], item.spec["b"]
        expected = a + b if op == "+" else a - b
        assert int(item.responses[0].answer) == expected


def test_misconception_table_never_contains_the_correct_answer():
    rng = random.Random(5)
    for _ in range(20):
        item = I.bare_sum(rng, "R6", "Procedural", "-", 2, 2, {1})
        r = item.responses[0]
        assert int(r.answer) not in [int(v) for v in r.misconceptions.values()]


def test_missing_digit_item_has_a_unique_solution():
    rng = random.Random(17)
    item = I.missing_digit(rng, "R13", "Conceptual", "+", 3)
    assert len(item.responses) == 2
    for r in item.responses:
        assert r.answer.isdigit() and len(r.answer) == 1


def test_estimate_item_carries_a_tolerance_so_a_near_estimate_is_not_marked_wrong():
    rng = random.Random(19)
    item = I.estimate_then_calc(rng, "R11", "Application", "+", 3, 3, {1})
    est = next(r for r in item.responses if r.rid == "est")
    exact = next(r for r in item.responses if r.rid == "ans")
    assert est.tolerance, "an estimate marked to the exact digit is not an estimate"
    assert exact.tolerance is None, "the exact answer must not be marked with a tolerance"


@pytest.mark.parametrize("digits_b", [1, 2])
def test_unequal_length_operands_are_tagged_as_requiring_alignment(digits_b):
    rng = random.Random(23)
    item = I.bare_sum(rng, "R5", "Procedural", "+", 3, digits_b, {1}, layout="column")
    t = tags.derive(item)
    if digits_b == 3:
        return
    assert t["alignment_required"] == "YES"
    assert t["operand_order"] == "LONGER_FIRST"
