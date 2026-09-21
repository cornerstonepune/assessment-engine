"""The predictors are what make marking diagnostic instead of binary.

Each test is a worked example taken from the predictor's own docstring, which in turn came from
a teacher's list of what children actually do. If one of these stops reproducing, diagnosis
silently degrades to "wrong answer" — no error, no alert, just a worse product.
"""

from engine.assess import misconceptions as M


def test_forgets_to_carry():
    assert M.add_nocarry(47, 38) == 75


def test_carry_written_one_column_too_far_left():
    assert M.add_carry_skips_column(47, 38) == 175


def test_writes_the_whole_column_sum_instead_of_regrouping():
    assert M.add_concat(47, 38) == 715


def test_drops_the_final_carry_out():
    assert M.add_drop_carry_out(76, 54) == 30


def test_subtracts_smaller_digit_from_larger_regardless_of_row():
    assert M.sub_smaller_from_larger(62, 27) == 45


def test_exchanges_without_reducing_the_lender_column():
    assert M.sub_no_decrement(62, 27) == 45


def test_across_zero_lender_column_not_decremented():
    assert M.sub_across_zero_lender_not_decremented(302, 178) == 224


def test_across_zero_zero_left_as_ten_instead_of_nine():
    assert M.sub_across_zero_zero_not_reduced(302, 178) == 134


def test_a_predictor_returns_none_when_its_mistake_cannot_occur():
    # 21 + 34 needs no carry at all, so "forgot to carry" is not an available error here
    assert M.add_nocarry(21, 34) is None


def test_predict_never_offers_the_correct_answer_as_a_misconception():
    for op, a, b in (("+", 47, 38), ("+", 76, 54), ("-", 62, 27), ("-", 302, 178)):
        correct = a + b if op == "+" else a - b
        for code, wrong in M.predict(op, a, b).items():
            assert wrong != correct, f"{code} predicts the correct answer for {a}{op}{b}"


def test_predict_never_offers_a_negative_answer():
    for code, wrong in M.predict("-", 302, 178).items():
        assert wrong >= 0, code


def test_catalogue_gives_every_code_a_repair_hint():
    rows = M.catalogue()
    assert rows, "catalogue is empty"
    for r in rows:
        assert r["repair"].strip(), f"{r['code']} has no repair hint for the teacher"
