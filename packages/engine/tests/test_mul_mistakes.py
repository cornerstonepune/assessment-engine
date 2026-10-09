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


@pytest.mark.parametrize("short, long", [(3, 21), (6, 125), (4, 36), (7, 506)])
def test_a_number_written_first_is_still_the_number_multiplied(short, long):
    """3 × 21 is worked as 21 × 3, the longer number on top and the 1-digit number the multiplier (assumption A10:
    both orders are asked): every column mistake is the same whichever is written first."""
    assert M.predict("×", short, long) == M.predict("×", long, short)


def test_no_prediction_is_the_right_answer_or_below_zero():
    for a in range(0, 130, 3):
        for b in range(0, 60, 7):
            right = a * b
            for code, v in M.predict("×", a, b).items():
                assert v != right and v >= 0, (a, b, code, v)


def test_every_predicted_mistake_is_a_named_mistake_row():
    """A predicted code with no row would be stripped from every question that carries it (bank._strip_unnamed)."""
    import json
    import pathlib

    seed = pathlib.Path(__file__).resolve().parents[3] / "supabase/seed/misconceptions.json"
    named = {(m["code"], m["op"]) for m in json.loads(seed.read_text())["misconceptions"]}
    for code in M.TABLES["×"]:
        assert (code, "×") in named, code
