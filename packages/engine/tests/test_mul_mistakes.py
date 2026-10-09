"""The wrong answers a column multiplication can be given, each predicted from the question's own numbers
(goals/md2a-straight-multiplication.yaml). The examples and their wrong answers are the drafted document's error
table (docs/design/multiplication-division-taxonomy.md, "Error diagnosis"); every wrong answer here is the one the
document computed, and each is also worked out in the test by hand."""

import pytest

from engine.assess import misconceptions as M


@pytest.mark.parametrize(
    "a, b, code, wrong",
    [
        # existing: a 1-digit multiplier
        (34, 6, "M_MUL_NO_CARRY", 84),  # 4×6=24 writes 4, 3×6=18 writes 8
        (56, 3, "M_MUL_CONCAT", 1518),  # 15 and 18 side by side
        (34, 6, "M_MUL_CARRY_FIRST", 304),  # (3+2)×6 = 30
        (34, 6, "M_MUL_ONES_ONLY", 24),
        (56, 3, "M_MUL_UNITS_REVERSED", 85),
        (7, 8, "M_MUL_ROW_OUT", 49),
        (34, 6, "M_WRONG_OP", 40),
        # new: a 2-digit multiplier
        (68, 17, "M_MUL_PLACEHOLDER", 544),  # 476 + 68: the second row not moved a place
        (68, 17, "M_MUL_ONE_ROW", 476),  # 68 × 7 and stop
        (68, 17, "M_MUL_COLUMNWISE", 656),  # 6×1 = 6, 8×7 = 56
        (47, 23, "M_MUL_STALE_CARRY", 1281),  # 141, then 4×2 + 1 + the first row's 2 again = 114 → 1140
        # new: zeros and the tables' edges
        (506, 7, "M_MUL_CARRY_ONTO_ZERO_LOST", 3502),  # 0 × 7 written 0, the 4 carried onto it lost
        (45, 100, "M_TENS_ZERO_DROPPED", 450),
        (23, 40, "M_TENS_ZERO_DROPPED", 92),
        (7, 0, "M_ZERO_AS_ONE", 7),
        (0, 9, "M_ZERO_AS_ONE", 9),
        (7, 1, "M_ONE_ADDED", 8),
        (1, 8, "M_ONE_ADDED", 9),
    ],
)
def test_every_column_mistake_the_document_names_is_predicted(a, b, code, wrong):
    assert M.predict("×", a, b).get(code) == wrong


@pytest.mark.parametrize(
    "a, b, code",
    [
        (34, 6, "M_MUL_PLACEHOLDER"),  # one row: nothing to move
        (34, 6, "M_MUL_ONE_ROW"),
        (34, 6, "M_MUL_COLUMNWISE"),  # a 1-digit multiplier has no tens to pair
        (234, 12, "M_MUL_COLUMNWISE"),  # three digits against two pair nothing up
        (21, 13, "M_MUL_STALE_CARRY"),  # 1×3 carries nothing, so there is nothing to add again
        (302, 3, "M_MUL_CARRY_ONTO_ZERO_LOST"),  # no carry reaches the zero
        (34, 6, "M_TENS_ZERO_DROPPED"),  # no zero in either number
        (25, 4, "M_TENS_ZERO_DROPPED"),  # the answer's zeros are the fact's own (100), not a factor's
        (7, 8, "M_ZERO_AS_ONE"),
        (7, 8, "M_ONE_ADDED"),
        (23, 40, "M_MUL_ONE_ROW"),  # its ones row is all zeros: no child stops there
    ],
)
def test_a_mistake_that_cannot_happen_on_these_numbers_is_not_predicted(a, b, code):
    assert code not in M.predict("×", a, b)


@pytest.mark.parametrize(
    "a, b, want",
    [
        # 3 × 56 is worked as 56 × 3: 6 × 3 = 18, 5 × 3 = 15 (assumption A10, both orders asked)
        (3, 56, {"M_MUL_NO_CARRY": 58, "M_MUL_CONCAT": 1518, "M_MUL_CARRY_FIRST": 188, "M_MUL_ONES_ONLY": 18,
                 "M_MUL_UNITS_REVERSED": 85, "M_MUL_ROW_OUT": 112, "M_WRONG_OP": 59}),
        # 7 × 506 as 506 × 7: 6 × 7 = 42, the 4 carried onto the 0 lost
        (7, 506, {"M_MUL_CARRY_ONTO_ZERO_LOST": 3502}),
    ],
)  # fmt: skip
def test_a_number_written_first_is_still_the_number_multiplied(a, b, want):
    """Worked out here by hand: a 1-digit number written first is still the multiplier, so its mistakes are the
    column mistakes of the longer number times it, not none."""
    got = M.predict("×", a, b)
    assert {code: got.get(code) for code in want} == want


@pytest.mark.parametrize(
    "a, b, want",
    [
        (7, 1, {"M_ONE_ADDED": 8}),  # adding the numbers is the same act: × 1 taken as adding one
        (7, 0, {"M_ZERO_AS_ONE": 7}),
        (0, 1, {"M_ZERO_AS_ONE": 1}),
        (45, 100, {"M_WRONG_OP": 145, "M_TENS_ZERO_DROPPED": 450}),  # × 100 is placing zeros, never rows
    ],
)
def test_one_wrong_answer_names_one_mistake_where_two_would_be_the_same_act(a, b, want):
    """A wrong answer two predictors give on every such question, by what they are rather than by chance, names the
    more particular one: marking names every match (`w3_read/marking.py`), and a child is charged once for one act
    (second reader, 2026-10-09)."""
    assert M.predict("×", a, b) == want


@pytest.mark.parametrize(
    "a, b, code",
    [
        (23, 40, "M_MUL_PLACEHOLDER"),  # its one row is a zero dropped (92)
        (80, 20, "M_MUL_COLUMNWISE"),  # 160 is a zero dropped
        (21, 22, "M_MUL_COLUMNWISE"),  # 42 is one row: the multiplier is one digit twice
        (7, 8, "M_MUL_UNITS_REVERSED"),  # one digit has no order to reverse: 6 is no carry
        (20, 4, "M_MUL_UNITS_REVERSED"),  # 8 is a zero dropped
        (105, 2, "M_MUL_NO_CARRY"),  # its one carry lands on the zero: 200 is that mistake
        (68, 17, "M_MUL_ROW_OUT"),  # 17 has no table to be one row out in
        (34, 10, "M_MUL_ROW_OUT"),  # 34 × 9 is no table slip
        (30, 6, "M_MUL_ONES_ONLY"),  # 0 × 6 = 0 is no answer this mistake writes
    ],
)
def test_a_mistake_that_is_another_on_these_numbers_names_none(a, b, code):
    assert code not in M.predict("×", a, b)


def test_a_table_fact_by_ten_is_still_one_row_out():
    assert (
        M.predict("×", 7, 10)["M_MUL_ROW_OUT"] == 60  # worked as 10 × 7, the row before: 10 × 6
        and M.predict("×", 105, 2)["M_MUL_CARRY_ONTO_ZERO_LOST"] == 200
    )


def test_no_predictor_gives_the_right_answer_nothing_or_below_zero():
    """Each predictor itself, not `predict`, which filters these out after the fact."""
    from engine.assess.mul_mistakes import PREDICTORS

    for a in range(0, 130, 3):
        for b in (*range(0, 13), *range(13, 130, 7), 100, 1000):
            for code, (fn, _, _) in PREDICTORS.items():
                v = fn(a, b)
                assert v is None or (v != a * b and v > 0), (a, b, code, v)


def test_every_predicted_mistake_is_a_named_mistake_row():
    """A predicted code with no row would be stripped from every question that carries it (bank._strip_unnamed)."""
    import json
    import pathlib

    seed = pathlib.Path(__file__).resolve().parents[3] / "supabase/seed/misconceptions.json"
    named = {(m["code"], m["op"]) for m in json.loads(seed.read_text())["misconceptions"]}
    for code in M.TABLES["×"]:
        assert (code, "×") in named, code
