"""The multiplication & division cases as `taxonomy_case` rows (goals/md1-taxonomy-rows.yaml).

Each case `research/md_taxonomy.py` drafted gets an example a kind of question could print (its numbers, its layout,
the method, story shape or mistake it states) and the tags it is about. Its match is those tags as the engine itself
reads them on that example (`engine.assess.tags.derive`): T07 is about its digits, a carry from the ones, an answer
that grows, a carry of one and no knock-on, and its match is what the engine measures those to be on 56 × 3. Nothing
in a match is typed; a tag given with a value (`("remainder", REMAINDERS)`) widens a case past its own example.

A straight calculation is printed in a line or in columns by its standard method; the methods, stories, missing
numbers and the rest are other kinds, each naming what it is. Every row names its taxonomy, as the addition and
subtraction rows do, so neither document's case can hold the other's question.

    packages/engine/.venv/bin/python research/md_taxonomy.py          # writes these rows into the seed
"""

import json
import re
from pathlib import Path
from typing import Any

from engine.assess import tags
from engine.assess.items import Item

R = Path(__file__).resolve().parents[1]
SEED = R / "supabase/seed/taxonomy_cases.json"
# A straight calculation is about its numbers; the methods it may be printed in are every written method of its
# operation (A1, ADR 0055 and goals/md3d-division-methods.yaml), each by the kind that prints it.
STRAIGHT_KINDS = {
    "×": ["bare_sum", "column_grid", "partitioning", "grid_method", "expanded_columns", "lattice"],
    "÷": ["bare_sum", "column_grid", "partitioning", "chunking", "long_division"],
}
STANDARD = {
    "×": ["LINE", "COLUMNS", "LONG_MULTIPLICATION", "EXPANDED", "PARTITIONING", "GRID", "LATTICE"],
    "÷": ["LINE", "SHORT_DIVISION", "LONG_DIVISION", "PARTITION_DIVIDEND", "CHUNKING"],
}
REMAINDERS = ["SOME", "LARGEST"]
D = ("operand_1_digits", "operand_2_digits")  # ÷ as written: 72 ÷ 4 is not 4 ÷ 72
# × either way round (assumption A10, both orders asked): 3 × 47 is 47 × 3's case, the longer number by the shorter;
# only T03 and T13 are about the 1-digit number coming first
DM = ("digits_max", "digits_min")
TC = (*DM, "regroup_at", "answer_digit_change", ("zero_pattern", ["NONE", "ANSWER_ZERO"]))
D3 = (*D, "first_digit_smaller", "regroup_at", "remainder", "quotient_zero")
TABLE = ["fact_table"]
# a table to 10 read backwards: the fact, in any of the tables a child learns to ten rows, never the 11 and 12 tables
TABLE_BACKWARDS = ("fact", ("fact_group", ["2-5-10", "3-4", "6-9"]))

# A straight calculation: its numbers are its example's own ("56 × 3"), so only what it is about is written here.
STRAIGHT: dict[str, list[Any]] = {
    "TF01": [("zero_operand", ["FIRST", "SECOND"]), "fact"],
    "TF02": [("one_operand", ["FIRST", "SECOND"]), "fact"],
    **{c: TABLE for c in ("TF03", "TF04", "TF05", "TF06", "TF07", "TF08", "TF09", "TF10", "TF11", "TF13", "TF14")},
    "TF12": ["equal_operands", "fact"],
    "TF15": ["fact_swapped"],
    "TF16": ["fact", ("method", "COLUMNS")],
    "TP01": ["place_value_factor", "fact", "zero_pattern"],
    "TP02": ["place_value_factor", "zero_pattern", "digits_max"],  # of a number to 3 digits
    "TP03": ["place_value_factor", ("digits_min", {"lte": 2})],  # of a number to 2 digits
    "TP04": ["place_value_factor", ("zero_pattern", ["TRAILING", "INTERNAL+TRAILING"])],
    "TP05": ["place_value_factor", ("zero_pattern", ["INTERNAL", "INTERNAL+TRAILING"]), "digits_max"],
    "TP11": ["place_value_factor", ("zero_pattern", ["TRAILING", "INTERNAL+TRAILING"]), "digits_max"],
    "TP06": ["place_value_factor", "scaled_fact", "fact_zero", "digits_min"],
    "TP07": ["place_value_factor", "digits_max"],
    "TP08": ["place_value_factor", "scaled_fact", "digits_min"],  # × 1 digit, a table fact under the zeros
    "TP09": ["place_value_factor", "fact_zero", "digits_min"],
    "TP10": ["place_value_factor", *DM],  # 23 × 30 and 11 × 20 alike: 2 digits × a 2-digit multiple of ten
    "T01": [*DM, "regrouping", "answer_digit_change"],  # Easy's numbers, printed in every method its level lists
    "T02": [*DM, ("method", "LINE")],  # in a line, MUL.2D1D's method as T14 is MUL.3D1D's and T22 MUL.2D2D's
    "T03": ["operand_order", "digits_max", "regrouping", "answer_digit_change"],  # 3 × 21: Easy regroups nothing, grows nothing
    "T04": [*DM, "regroup_at", "carry_size", "answer_digit_change"],
    "T05": [*DM, "regroup_at", "carry_size", "answer_digit_change"],
    "T06": [*DM, "regrouping", "answer_digit_change"],
    "T07": [*DM, "regroup_at", "answer_digit_change", "carry_size", "knock_on"],
    "T08": [*DM, "knock_on", "answer_zeros"],
    "T09": [*DM, "regroup_at", "answer_zeros"],
    "T10": [*DM, "carry_max"],
    "T11": [*DM, "regrouping", "answer_digit_change"],
    "T12": [*DM, ("regrouping", ["SINGLE", "MULTIPLE"])],
    "T13": [*D, ("method", "LINE")],
    "T14": [*DM, ("method", "LINE")],
    "T15": [*DM, "regrouping"],
    "T16": [*DM, ("regrouping", ["SINGLE", "MULTIPLE"])],
    "T17": [*DM, "row_regrouping", "partial_sum_regrouping", "answer_digits"],
    "T18": [*DM, "row_regrouping", "partial_sum_regrouping", "answer_digits"],
    "T19": [*DM, "row_regrouping", "partial_sum_regrouping", "answer_digits"],
    "T20": [*DM, "row_regrouping", ("partial_sum_regrouping", ["SINGLE", "MULTIPLE"]), "answer_digits"],
    "T21": [*DM, "partial_sum_regrouping", "answer_digits"],
    "T27": [*DM, ("partial_sum_regrouping", ["SINGLE", "MULTIPLE"]), "answer_digits"],
    "T28": [*DM, ("row_regrouping", ["NONE", "SOME"]), ("partial_sum_regrouping", ["SINGLE", "MULTIPLE"]), "answer_digits"],
    "T22": [*DM, ("method", "LINE")],
    "T23": [*DM],
    "T24": [*DM, "row_regrouping"],
    "T25": [("digits_max", {"gte": 5}), "digits_min"],
    "T26": [*DM, "multiplier_zero"],
    **{f"TC{n:02d}": list(TC) for n in range(1, 9)},
    "TC09": [*DM, "carry_size", "answer_digit_change"],
    "TC10": [*DM, "knock_on"],
    "TC11": [*DM, "regroup_at", "answer_zeros"],
    "TZ01": [*DM, "zero_pattern"],
    "TZ02": ["digits_min", "zero_pattern", "carry_into_zero", "answer_digit_change", ("zero_operand", "NONE")],
    "TZ09": ["digits_min", "zero_pattern", "carry_into_zero", "answer_digit_change", ("zero_operand", "NONE")],
    "TZ03": ["digits_min", "zero_pattern", "carry_into_zero", ("zero_operand", "NONE")],
    "TZ04": ["digits_max", ("zero_count", {"gte": 2})],
    "TZ05": [*DM, "answer_round"],
    "TZ06": [*DM, "answer_round"],
    "TZ07": [*DM, "multiplier_zero", "partial_products", ("method", "LONG_MULTIPLICATION")],
    "TZ08": ["place_value_factor", *DM],
    "Y04": [("zero_operand", ["FIRST", "SECOND"]), "fact"],
    "DF01": [("one_operand", "SECOND")],
    "DF02": ["equal_operands"],
    "DF03": [("zero_operand", "FIRST")],
    **{f"DF{n:02d}": TABLE for n in range(4, 15)},
    "DF16": ["operand_2_digits", "answer_digits"],  # about the divisor and the quotient: 100 ÷ 11 = 9 r 1 is one
    "DP01": ["place_value_factor", "fact", "remainder"],
    # a remainder by a power of ten waits for Advance (DR10), as ÷ 10's does: Medium printed 4567 ÷ 100 = 45 r 67
    "DP02": ["place_value_factor", ("remainder", "NONE")],
    "DP03": ["place_value_factor", ("remainder", "NONE")],
    # "÷ 1 digit", as their labels say: 240 ÷ 12 is a 2-digit divisor
    "DP04": ["place_value_factor", "scaled_fact", "fact_zero", "operand_2_digits"],
    "DP05": ["place_value_factor"],
    "DP06": ["fact_zero"],
    "DP07": ["place_value_factor", "fact_zero", "operand_2_digits"],
    "D01": [*D, "regrouping", "remainder"],  # Easy's numbers, printed in every method its level lists
    "D02": [*D, ("method", "LINE")],  # in a line, DIV.2D1D's method as D15 is DIV.3D1D's
    "D03": [*D, "regroup_at", "remainder", "first_digit_smaller", ("divisor_group", ["2-5-10", "3-4"])],
    "D04": [*D, "regroup_at", "remainder", "first_digit_smaller", "divisor_group"],
    "D05": [*D, "regrouping", "remainder", "quotient_zero", "first_digit_smaller"],
    **{f"D{n:02d}": list(D3) for n in range(6, 11)},
    "D11": [*D, "regrouping"],
    "D12": [*D, "first_digit_smaller", ("regrouping", ["SINGLE", "MULTIPLE"])],
    "D13": [*D, "answer_digits"],
    "D15": [*D, ("method", "LINE")],
    "D14": [*D, "estimate_corrected", "answer_digits"],
    "DZ01": [*D, "quotient_zero", "zero_pattern", "regrouping"],
    "DZ02": [*D, "quotient_zero", "remainder", "scaled_fact"],
    # the zero comes from a digit smaller than the divisor; one at the end of the number divided is beside it (210 ÷ 2)
    "DZ03": [*D, "quotient_zero", ("zero_pattern", ["ANSWER_ZERO", "TRAILING"])],
    "DZ04": [*D, "zero_pattern", "quotient_zero"],
    "DZ05": ["quotient_zero"],
    "DZ06": ["operand_1_digits", "first_digit_smaller", "quotient_zero"],
    "DZ07": [*D, "quotient_zero", ("remainder", REMAINDERS)],
    "DR01": ["operand_2_digits", "answer_digits", "remainder"],  # 7 ÷ 3 = 2 r 1 is one, not only 17 ÷ 5
    "DR02": ["remainder", "answer_digits"],
    "DR03": ["remainder"],
    "DR04": [*D, "regrouping", ("remainder", REMAINDERS), "answer_digits"],
    "DR05": [*D, "regrouping", ("remainder", REMAINDERS), "first_digit_smaller"],
    "DR06": [*D, ("remainder", REMAINDERS)],
    "DR07": ["quotient_zero", ("remainder", REMAINDERS)],
    "DR08": [*D, "first_digit_smaller", ("remainder", REMAINDERS)],
    "DR10": [("place_value_factor", ["X10", "X100", "X1000"]), ("remainder", REMAINDERS)],
}


def _x(a: int, b: int, op: str = "×", **more: Any) -> dict[str, Any]:
    return {"a": a, "b": b, "op": op, **more}


def _col(a: int, b: int, op: str, method: str) -> tuple[str, dict[str, Any], list[Any]]:
    return ("column_grid", _x(a, b, op, layout="column", method=method), ["method"])


def _story(a: int, b: int, op: str, structure: str, *about: Any, **more: Any) -> tuple[str, dict[str, Any], list[Any]]:
    return ("word_1step", _x(a, b, op, structure=structure, **more), ["structure", *about])


def _two_step(structure: str, ops: list[str], **numbers: int) -> tuple[str, dict[str, Any], list[Any]]:
    return ("word_2step", {**numbers, "ops": ops, "structure": structure}, ["structure"])


def _shape(fmt: str, shape: str, ops: list[str], **more: Any) -> tuple[str, dict[str, Any], list[Any]]:
    return (fmt, {"shape": shape, "ops": ops, **more}, ["shape"])


def _missing(text: str, *about: Any) -> tuple[str, dict[str, Any], list[Any]]:
    return ("missing_number", {"text": text}, list(about))


def _digit(a: str, b: str, c: str, op: str, solved: tuple[int, int], *about: Any) -> tuple[str, dict[str, Any], list[Any]]:
    return ("missing_digit", {"a": a, "b": b, "c": c, "op": op, "solved": {"a": solved[0], "b": solved[1]}}, list(about))


def _mistake(a: int, b: int, op: str, planted: str, wrong: Any) -> tuple[str, dict[str, Any], list[Any]]:
    return ("find_mistake", _x(a, b, op, planted=planted, wrong=wrong), ["planted"])


def _strategy(a: int, b: int, op: str, strategy: str) -> tuple[str, dict[str, Any], list[Any]]:
    return ("efficient_method", _x(a, b, op, strategy=strategy), ["strategy"])


# Every other case: the kind it is, the question it prints, and what it is about.
OTHER: dict[str, tuple[str, dict[str, Any], list[Any]]] = {
    "TF17": ("multiplication_square", _x(6, 9, rows=[5, 6, 7], cols=[8, 9, 10]), ["fact", "context"]),
    "DF15": ("bare_sum", _x(42, 6, "÷", shape="HOW_MANY_GROUPS"), ["shape", "fact"]),
    # methods and pictures
    "G01": ("equal_groups", _x(3, 4, shape="PICTURE"), ["method"]),
    "G02": ("equal_groups", _x(3, 4, shape="SUM"), ["method"]),
    "G03": ("skip_counting", _x(5, 5, method="SKIP_COUNTING"), ["method"]),
    "G04": ("number_line_jumps", _x(4, 3, method="NUMBER_LINE"), ["method"]),
    "G05": ("equal_groups", _x(3, 5, shape="ARRAY"), ["method"]),
    "G06": ("efficient_method", _x(14, 4, method="DOUBLING"), ["method"]),
    "G07": ("partitioning", _x(23, 4, method="PARTITIONING"), ["method"]),
    # a grid's size is its shorter number's (A10: 3 × 21 is 21 × 3's case), so a 1-digit number written first is 2 × 1
    "G08": ("grid_method", _x(23, 4, method="GRID"), ["method", "digits_min"]),
    "G09": ("grid_method", _x(34, 26, method="GRID"), ["method", "digits_min"]),
    "G10": ("expanded_columns", _x(34, 6, layout="column", method="EXPANDED"), ["method"]),
    "G11": _col(34, 6, "×", "COLUMNS"),
    "G12": _col(68, 17, "×", "LONG_MULTIPLICATION"),
    "G13": ("lattice", _x(47, 23, method="LATTICE"), ["method"]),
    "G14": _shape("equation", "SWAP_TO_A_KNOWN_TABLE", ["×"], text="9 × 2 = 2 × 9 = □"),
    "G15": ("equal_groups", _x(12, 3, "÷", method="SHARING"), ["method"]),
    "G16": ("equal_groups", _x(12, 4, "÷", method="GROUPING"), ["method"]),
    # a number taken away again and again is printed whole, a kind of its own as skip counting is (ADR 0062)
    "G17": ("repeated_subtraction", _x(15, 3, "÷", method="REPEATED_SUBTRACTION"), ["method"]),
    "G18": ("number_line_jumps", _x(20, 4, "÷", method="NUMBER_LINE"), ["method"]),
    "G19": ("equal_groups", _x(20, 4, "÷", method="ARRAY"), ["method"]),
    # the table backwards is answered twice, by dividing and by its fact; a check of a claimed answer (Y10) is not
    "G20": ("inverse_check", _x(42, 6, "÷", shape="TABLE_BACKWARDS"), ["reasoning_type", "fact", "shape"]),
    # a written division is a kind of its own, each step a box, as a written multiplication is (ADR 0055); short
    # division is the division layout, its exchanges written small, as compact columns are columns
    "G21": ("partitioning", _x(72, 4, "÷", method="PARTITION_DIVIDEND"), ["method"]),
    "G22": ("chunking", _x(96, 4, "÷", method="CHUNKING"), ["method"]),
    "G23": _col(72, 4, "÷", "SHORT_DIVISION"),
    "G24": ("long_division", _x(516, 4, "÷", method="LONG_DIVISION"), ["method"]),
    "G25": ("efficient_method", _x(96, 4, "÷", method="HALVING"), ["method"]),
    # missing numbers and digits
    "Q01": _missing("8 × □ = 72", "unknown_position", "fact", "answer_first"),
    "Q02": _missing("□ × 6 = 42", "unknown_position", "fact", "answer_first"),
    "Q03": _missing("□ ÷ 4 = 7", "unknown_position", "remainder"),
    "Q04": _missing("56 ÷ □ = 8", "unknown_position", "remainder"),
    "Q05": _missing("□ = 63 ÷ 9", "answer_first", "remainder"),  # exact, as Q03 and Q04: no "□ r □ = 17 ÷ 5"
    "Q06": _missing("□ × □ = 49", "unknown_position"),
    "Q07": _digit("2□", "4", "92", "×", (23, 4), "missing_in", "missing_count", "operand_1_digits"),
    "Q08": _digit("47", "3", "1□1", "×", (47, 3), "missing_in", "missing_count"),
    "Q09": _digit("7□", "4", "18", "÷", (72, 4), "missing_in", "missing_count"),
    "Q10": _digit("936", "3", "3□2", "÷", (936, 3), "missing_in", "missing_count"),
    "Q11": _digit("□7", "6", "3□2", "×", (57, 6), "missing_count"),
    "Q12": _missing("38 ÷ 5 = 7 r □", "unknown_position"),
    "Q13": _missing("38 ÷ □ = 7 r 3", "unknown_position", ("remainder", REMAINDERS)),
    # of a number to 2 digits, as TP03's × 1000 is: drawn unbounded it reached 9500 × 1000 at Grade 4. The bound is on
    # the number shown, written first; the shorter number's digits cannot bound it where the factor is 10 (4000 × 10)
    "Q14": _missing(
        "45 × □ = 4500",
        "unknown_position",
        ("place_value_factor", ["X10", "X100", "X1000"]),
        ("operand_1_digits", {"lte": 2}),
    ),
    "Q15": ("missing_number", {"text": "34 × 26 = 204 + □", "shape": "MISSING_ROW", "ops": ["×", "+"]}, ["shape"]),
    "Q16": _digit("3□4", "2", "708", "×", (354, 2), "missing_in", "missing_count", "operand_1_digits"),
    # equality, inverse, properties; multiples and factors
    "Y01": _shape("equation", "ORDER", ["×"], text="6 × 8 = 8 × □"),
    "Y02": _shape("equation", "GROUPED_EITHER_WAY", ["×"], text="(2 × 7) × 5 = 2 × (7 × 5) = □"),
    "Y03": _shape("equation", "PARTITION_A_FACTOR", ["×", "+"], text="7 × 12 = 7 × 10 + 7 × □"),
    "Y05": _shape("equation", "BY_ONE", ["×", "÷"], text="37 × 1 and 37 ÷ 1"),
    "Y06": _shape("equation", "BY_ITSELF_AND_OF_ZERO", ["÷"], text="9 ÷ 9 and 0 ÷ 9"),
    "Y07": _shape("equation", "TRUE_FALSE_DIVIDE_BY_ZERO", ["÷"], text="9 ÷ 0 = 0"),
    "Y08": _shape("equation", "TRUE_FALSE_DIVISION_ORDER", ["÷"], text="12 ÷ 3 = 3 ÷ 12"),
    "Y09": ("fact_family", _x(4, 7, shape="FROM_MULTIPLICATION"), ["shape"]),
    "Y10": ("inverse_check", _x(96, 4, "÷"), ["reasoning_type", "fact", "remainder"]),
    "DR09": ("inverse_check", _x(85, 4, "÷"), ["reasoning_type", ("remainder", REMAINDERS)]),
    "Y11": _shape("equation", "BALANCE_TIMES_AND_MINUS", ["×", "-"], text="3 × 8 = 30 − □"),
    "Y12": _shape("equation", "BALANCE_TIMES_AND_DIVIDE", ["×", "÷"], text="6 × 4 = 48 ÷ □"),
    "Y13": _shape("equation", "MISSING_SIGN", ["×", "÷"], text="6 □ 3 = 18 and 18 □ 3 = 6"),
    "Y14": _shape("equation", "COMPARE", ["×", "÷"], text="25 × 4 ○ 25 × 5 and 48 ÷ 6 ○ 48 ÷ 8"),
    "Y15": _shape("equation", "DOUBLE_A_FACTOR", ["×"], text="12 × 5 = 60, so 12 × 10 = □"),
    "Y16": _shape("equation", "TRUE_FALSE_ORDER", ["×"], text="7 × 6 = 6 × 7"),
    "F01": _shape("multiples", "MULTIPLES", ["×"], of=6, up_to=60),
    "F02": _shape("multiples", "IS_A_MULTIPLE", ["÷"], n=45, of=5),
    "F03": _shape("multiples", "FACTORS", ["÷"], of=12),
    "F04": _shape("multiples", "FACTOR_PAIRS", ["×"], of=24),
    "F05": _shape("multiples", "COMMON_MULTIPLES", ["×"], of=[3, 4], below=30),
    "F06": _shape("multiples", "DIVISIBLE_BY_2_5_10", ["÷"], n=340),
    "F07": _shape("multiples", "DIVISIBLE_BY_3", ["÷"], n=117),
    # a product odd or even, as V06 is: F08 asks it of a table fact, V06 of a product past the tables (M4b1)
    "F08": ("odd_even", _x(6, 7), [("fmt", "odd_even"), "fact"]),
    # efficient and mental
    "H01": _strategy(46, 5, "×", "TIMES_TEN_THEN_HALVE"),
    "H02": _strategy(23, 9, "×", "TIMES_TEN_LESS_A_GROUP"),
    "H03": _strategy(14, 11, "×", "TIMES_TEN_AND_A_GROUP"),
    "H04": _strategy(16, 5, "×", "DOUBLE_ONE_HALVE_THE_OTHER"),
    "H05": _strategy(13, 8, "×", "DOUBLE_THREE_TIMES"),
    "H06": _strategy(24, 25, "×", "TIMES_HUNDRED_THEN_QUARTER"),
    "H07": _strategy(19, 6, "×", "COMPENSATION"),
    "H08": _strategy(7, 9, "×", "FACT_DERIVED"),
    "H09": _strategy(240, 5, "÷", "DIVIDE_BY_TEN_THEN_DOUBLE"),
    "H10": _strategy(60, 7, "×", "SCALED_FACT"),
    # estimating and judging: each on its example's sizes, which say what it is as much as its shape does (M4b1). On a
    # level of cases with no shape of its own (MD.ESTIMATE) they are its only sizes; on the skill a case shares
    # (MUL.2D1D for 48 × 6) they are that skill's own
    "V01": ("estimate_then_calc", _x(48, 6, shape="ROUND_ONE"), ["shape", *DM]),
    "V02": ("estimate_then_calc", _x(38, 21, shape="ROUND_BOTH"), ["shape", *DM]),
    "V03": ("estimate_then_calc", _x(67, 75, shape="ANSWER_DIGITS"), ["shape", *DM]),
    "V04": ("estimate_then_calc", _x(156, 4, "÷", shape="ANSWER_DIGITS"), ["shape", *D]),
    "V05": ("possible_answer", _x(23, 4, claimed=812), [("fmt", "possible_answer"), *DM]),
    "V06": ("odd_even", _x(6, 13), [("fmt", "odd_even"), *DM, "fact"]),
    "V07": ("estimate_then_calc", _x(47, 3, shape="LAST_DIGIT"), ["shape", *DM]),
    "V08": ("choose_estimate", _x(52, 9, options=[360, 450, 540]), [("fmt", "choose_estimate"), *DM]),
    "V09": ("possible_answer", _x(47, 6, "÷", claimed="6 r 11"), [("fmt", "possible_answer"), *D]),
    "V10": ("estimate_then_calc", _x(412, 8, "÷", shape="ROUND_ONE"), ["shape", *D]),
    # word problems
    "B01": _story(4, 6, "×", "EQUAL_GROUPS"),
    # a story that shares or groups divides a table to 10 read backwards, as every one of its examples does (ADR 0062)
    "B02": _story(24, 4, "÷", "SHARING", *TABLE_BACKWARDS),
    "B03": _story(24, 6, "÷", "GROUPING", "remainder", *TABLE_BACKWARDS),
    "B04": _story(5, 7, "×", "ARRAY"),
    "B05": _story(35, 5, "÷", "ARRAY", *TABLE_BACKWARDS),
    "B06": _story(8, 6, "×", "RATE_TOTAL"),
    "B07": _story(48, 8, "÷", "RATE_UNIT", "remainder"),  # the cost of one is an exact division
    "B08": _story(4, 3, "×", "TIMES_AS_MANY_LARGER"),
    "B09": _story(12, 3, "÷", "TIMES_AS_MANY_SMALLER"),
    "B10": _story(12, 4, "÷", "HOW_MANY_TIMES"),
    "B11": _story(15, 2, "×", "TWICE_AS_MANY"),
    "B12": _story(3, 4, "×", "COMBINATIONS"),
    "B13": _story(6, 4, "×", "AREA"),
    "B14": _story(26, 4, "÷", "GROUPING", "remainder_use", remainder_use="ROUND_DOWN"),
    "B15": _story(26, 4, "÷", "GROUPING", "remainder_use", remainder_use="ROUND_UP"),
    "B16": _story(26, 4, "÷", "GROUPING", "remainder_use", remainder_use="REMAINDER_ASKED"),
    "B17": _story(26, 4, "÷", "GROUPING", "remainder_use", remainder_use="BOTH_ASKED"),
    "B18": _two_step("MULTIPLY_THEN_ADD", ["×", "+"], a=3, b=12, c=5),
    "B19": _two_step("MULTIPLY_THEN_SUBTRACT", ["×", "-"], a=100, b=4, c=15),
    "B20": _two_step("DIVIDE_THEN_MULTIPLY", ["÷", "×"], a=12, b=36, c=5),
    "B21": _two_step("TWO_PRODUCTS_ADDED", ["×", "×", "+"], a=4, b=6, c=3, d=8),
    "B22": _two_step("ADD_THEN_DIVIDE", ["+", "÷"], a=18, b=14, c=4),
    "B23": _two_step("BAR_MODEL_TIMES_AS_MANY", ["÷"], a=32, b=3),
    "B24": _story(30, 5, "÷", "GROUPING_BY_EACH", *TABLE_BACKWARDS),
    "B25": _story(8, 9, "×", "EXTRA_INFORMATION", extra=3),
    "B26": _story(3, 15, "×", "RATE_TOTAL", "context", table="PRICE_LIST"),
    "B27": _story(30, 2, "÷", "HALF_AS_MANY"),
    # finding the mistake
    "C01": _mistake(56, 3, "×", "M_MUL_CONCAT", 1518),
    "C02": _mistake(34, 6, "×", "M_MUL_NO_CARRY", 84),
    "C03": _mistake(68, 17, "×", "M_MUL_PLACEHOLDER", 544),
    "C04": _mistake(612, 6, "÷", "M_DIV_QUOTIENT_ZERO_DROPPED", 12),
    "C05": _mistake(85, 4, "÷", "M_DIV_REMAINDER_TOO_BIG", "20 r 5"),
    "C06": _mistake(23, 4, "×", "M_PARTITION_TENS_AS_ONES", 20),
    "C07": _mistake(516, 4, "÷", "M_DIV_BRING_DOWN_MISSED", "12 r 3"),
    "C08": ("explain_claim", _x(804, 4, "÷", claimed=21, ops=["÷"]), [("fmt", "explain_claim")]),
    "C09": _mistake(506, 7, "×", "M_MUL_CARRY_ONTO_ZERO_LOST", 3502),
}

_SUM = re.compile(r"(\d+) ([×÷]) (\d+)")


def measure(fmt: str, spec: dict[str, Any]) -> dict[str, Any]:
    return tags.derive(Item("x", "x", "R9", [], "P", fmt, False, "", spec, []))


def example(case: dict[str, Any]) -> tuple[str, dict[str, Any], list[Any], bool]:
    """(kind, spec, what it is about, straight) for one drafted case."""
    code = case["code"]
    if code in OTHER:
        return (*OTHER[code], False)
    if code == "TF16":
        a, op, b = 7, "×", 6  # "7 over 6 in columns"
    else:
        m = _SUM.match(case["example"])
        assert m, f"{code}: no sum in {case['example']!r}"
        a, op, b = int(m[1]), m[2], int(m[3])
    line = "in a line" in case["example"] + case["label"] or case["section"] in (2, 5) and code != "TF16"
    spec = {"a": a, "b": b, "op": op, "layout": "horizontal" if line else "column"}
    return ("bare_sum" if line else "column_grid", spec, STRAIGHT[code], True)


def match_of(code: str, fmt: str, spec: dict[str, Any], about: list[Any], straight: bool) -> dict[str, Any]:
    """The case as the engine measures its example: every tag it is about, at the value read there."""
    t = measure(fmt, spec)
    m: dict[str, Any] = {"taxonomy": "MUL_DIV"}
    if straight:
        m |= {"fmt": STRAIGHT_KINDS[spec["op"]], "method": STANDARD[spec["op"]]}
    else:
        m["fmt"] = fmt  # every other case names its kind, as addition's do, or nothing can draw it (M2b)
    if "operation" in t:
        m["operation"] = t["operation"]
    for a in about:
        key, value = (a, t.get(a)) if isinstance(a, str) else a
        if value is None:
            raise ValueError(f"{code}: its example {spec} has no {key}")
        m[key] = value
    return m


def rows(cases: list[dict[str, Any]], sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    names = {s["num"]: s["title"] for s in sections}
    out = []
    for c in cases:
        fmt, spec, about, straight = example(c)
        out.append(
            {
                "code": c["code"],
                "taxonomy": "MUL_DIV",
                "section": str(c["section"]),
                "section_name": names[c["section"]],
                "label": c["label"],
                "example_text": c["example"],
                "example": {"fmt": fmt, "spec": spec},
                "match": match_of(c["code"], fmt, spec, about, straight),
            }
        )
    return out


def faults(made: list[dict[str, Any]]) -> list[str]:
    """A case that does not hold its own example, or two cases with one match."""
    out, seen = [], {}
    for r in made:
        ex = r["example"]
        if not tags_hold(r["match"], ex["fmt"], measure(ex["fmt"], ex["spec"])):
            out.append(f"{r['code']}: does not hold its own example")
        key = json.dumps(r["match"], sort_keys=True)
        if key in seen:
            out.append(f"{r['code']}: the same match as {seen[key]}")
        seen[key] = r["code"]
    return out


def tags_hold(match: dict[str, Any], fmt: str, measured: dict[str, Any]) -> bool:
    from engine.assess import taxonomy

    return taxonomy.matches(match, fmt, measured)


def write(made: list[dict[str, Any]]) -> None:
    """The seed's addition and subtraction rows, each naming its taxonomy, then these."""
    seed = json.loads(SEED.read_text())["taxonomy_cases"]
    kept = []
    for r in seed:
        if r.get("taxonomy", "ADD_SUB") != "ADD_SUB":
            continue
        alts = r["match"] if isinstance(r["match"], list) else [r["match"]]
        named = [{"taxonomy": "ADD_SUB", **{k: v for k, v in m.items() if k != "taxonomy"}} for m in alts]
        row = {"code": r["code"], "taxonomy": "ADD_SUB"}
        row |= {k: v for k, v in r.items() if k not in ("code", "taxonomy")}
        row["match"] = named if isinstance(r["match"], list) else named[0]
        kept.append(row)
    SEED.write_text(json.dumps({"taxonomy_cases": kept + made}, ensure_ascii=False, indent=2) + "\n")
