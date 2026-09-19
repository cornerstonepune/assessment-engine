"""The three predictors the taxonomy's error list (§11) added that the ladder alone missed.

Each is seeded as `detectable_by: answer_lookup`, which is a promise: given the operands, the
engine can say what number this specific mistake produces, so a marker can tag it without a
model. A seeded code with no predictor is a silent lie — the code exists in the vocabulary and
can never once be assigned.
"""

import pytest

from engine.assess import misconceptions as M


def test_align_left_shifts_the_shorter_operand_into_the_wrong_columns():
    # 342 + 5 with the 5 written under the 3 reads as 342 + 500
    assert M.align_left("+", 342, 5) == 842


def test_align_left_cannot_occur_when_both_operands_are_the_same_length():
    assert M.align_left("+", 342, 155) is None
    assert M.align_left("-", 62, 27) is None


def test_align_left_returns_none_rather_than_a_negative_answer():
    # 342 - 5 misaligned would be 342 - 500; a child does not write a negative here
    assert M.align_left("-", 342, 5) is None


def test_zero_dropped_loses_a_placeholder_but_never_the_leading_digit():
    assert M.zero_dropped(1000) == 100
    assert M.zero_dropped(504) == 54
    assert M.zero_dropped(123) is None


def test_carry_always_one_is_invisible_with_two_operands():
    # two single digits can total at most 18, so the carry is always 1 and the error cannot show
    assert M.carry_always_one([9, 8]) is None


def test_carry_always_one_shows_when_a_column_totals_twenty_or_more():
    # 9 + 8 + 7 = 24 in the ones column: carry is 2, a child who always carries 1 writes 14
    assert M.carry_always_one([9, 8, 7]) == 14


def test_carry_always_one_returns_none_when_no_column_reaches_twenty():
    assert M.carry_always_one([12, 13, 14]) is None


@pytest.mark.parametrize("code", ["M_ALIGN_LEFT", "M_ZERO_DROPPED"])
def test_new_codes_are_reachable_through_the_predictor_registry(code):
    assert code in M.ADD_PREDICTORS
    assert code in M.SUB_PREDICTORS


def test_align_left_is_actually_produced_on_an_unequal_length_item():
    """The blueprint slots added for unequal lengths exist so this tag can ever be assigned."""
    predicted = M.predict("+", 342, 5)
    assert predicted.get("M_ALIGN_LEFT") == 842


def test_every_predictor_table_is_in_the_one_registry():
    """Superseded the seed-vs-table check: that union was re-typed here and missed MUL_PREDICTORS
    entirely, so multiplication had no predictors and nothing said so. The seed side is now
    `engine audit`'s "every answer-lookup code is computed somewhere", which also covers the codes
    the item generators compute inline."""
    for table in (M.ADD_PREDICTORS, M.SUB_PREDICTORS, M.MUL_PREDICTORS, M.MULTI_PREDICTORS):
        assert set(table) <= M.PREDICTED
