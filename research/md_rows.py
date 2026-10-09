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
STRAIGHT_KINDS = ["bare_sum", "column_grid"]
STANDARD = {"×": ["LINE", "COLUMNS", "LONG_MULTIPLICATION"], "÷": ["LINE", "SHORT_DIVISION", "LONG_DIVISION"]}
REMAINDERS = ["SOME", "LARGEST"]
D = ("operand_1_digits", "operand_2_digits")
TC = (*D, "regroup_at", "answer_digit_change", ("zero_pattern", ["NONE", "ANSWER_ZERO"]))
D3 = (*D, "first_digit_smaller", "regroup_at", "remainder", "quotient_zero")
TABLE = ["fact_table"]

# A straight calculation: its numbers are its example's own ("56 × 3"), so only what it is about is written here.
STRAIGHT: dict[str, list[Any]] = {
    "TF01": [("zero_operand", ["FIRST", "SECOND"]), "fact"],
    "TF02": [("one_operand", ["FIRST", "SECOND"]), "fact"],
    **{c: TABLE for c in ("TF03", "TF04", "TF05", "TF06", "TF07", "TF08", "TF09", "TF10", "TF11", "TF13", "TF14")},
    "TF12": ["equal_operands", "fact"],
    "TF15": ["fact_swapped"],
    "TF16": ["fact", ("method", "COLUMNS")],
    "TP01": ["place_value_factor", "fact", "zero_pattern"],
    "TP02": ["place_value_factor", "zero_pattern"],
    "TP03": ["place_value_factor"],
    "TP04": ["place_value_factor", "zero_pattern"],
    "TP05": ["place_value_factor", "zero_pattern"],
    "TP06": ["place_value_factor", "scaled_fact", "fact_zero"],
    "TP07": ["place_value_factor", "digits_max"],
    "TP08": ["place_value_factor"],
    "TP09": ["place_value_factor", "fact_zero"],
    "TP10": ["place_value_factor", "scaled_fact", "operand_2_digits"],
    "T01": [*D, "regrouping", ("method", "COLUMNS"), "answer_digit_change"],
    "T02": [*D, "regrouping", ("method", "LINE")],
    "T03": ["operand_order", "digits_max"],
    "T04": [*D, "regroup_at", "carry_size", "answer_digit_change"],
    "T05": [*D, "regroup_at", "carry_size", "answer_digit_change"],
    "T06": [*D, "regrouping", "answer_digit_change"],
    "T07": [*D, "regroup_at", "answer_digit_change", "carry_size", "knock_on"],
    "T08": [*D, "knock_on", "answer_zeros"],
    "T09": [*D, "regroup_at", "answer_zeros"],
    "T10": [*D, "carry_max"],
    "T11": [*D, "regrouping"],
    "T12": [*D, ("regrouping", ["SINGLE", "MULTIPLE"])],
    "T13": ["operand_order", "digits_max", ("method", "LINE")],
    "T14": [*D, ("method", "LINE")],
    "T15": [*D, "regrouping"],
    "T16": [*D, ("regrouping", ["SINGLE", "MULTIPLE"])],
    "T17": [*D, "row_regrouping", "partial_sum_regrouping", "answer_digits"],
    "T18": [*D, "row_regrouping", "partial_sum_regrouping", "answer_digits"],
    "T19": [*D, "row_regrouping", "partial_sum_regrouping", "answer_digits"],
    "T20": [*D, "row_regrouping", ("partial_sum_regrouping", ["SINGLE", "MULTIPLE"]), "answer_digits"],
    "T21": [*D, "partial_sum_regrouping", "answer_digits"],
    "T22": [*D, ("method", "LINE")],
    "T23": [*D],
    "T24": [*D, "row_regrouping"],
    "T25": [("operand_1_digits", {"gte": 5}), "operand_2_digits"],
    "T26": [*D, "multiplier_zero"],
    **{f"TC{n:02d}": list(TC) for n in range(1, 9)},
    "TC09": [*D, "carry_size", "answer_digit_change"],
    "TC10": [*D, "knock_on"],
    "TC11": [*D, "regroup_at", "answer_zeros"],
    "TZ01": [*D, "zero_pattern"],
    "TZ02": ["operand_2_digits", "zero_pattern", "carry_into_zero"],
    "TZ03": ["operand_2_digits", "zero_pattern", "carry_into_zero"],
    "TZ04": ["operand_1_digits", "zero_pattern"],
    "TZ05": [*D, "answer_round"],
    "TZ06": [*D, "answer_round"],
    "TZ07": ["multiplier_zero", "partial_products", ("method", "LONG_MULTIPLICATION")],
    "TZ08": ["place_value_factor", "operand_1_digits"],
    "Y04": [("zero_operand", ["FIRST", "SECOND"]), "fact"],
    "DF01": [("one_operand", "SECOND")],
    "DF02": ["equal_operands"],
    "DF03": [("zero_operand", "FIRST")],
    **{f"DF{n:02d}": TABLE for n in range(4, 15)},
    "DF16": [*D, "answer_digits"],
    "DP01": ["place_value_factor", "fact", "remainder"],
    "DP02": ["place_value_factor"],
    "DP03": ["place_value_factor"],
    "DP04": ["place_value_factor", "scaled_fact", "fact_zero"],
    "DP05": ["place_value_factor"],
    "DP06": ["fact_zero"],
    "DP07": ["place_value_factor", "fact_zero"],
    "D01": [*D, "regrouping", "remainder", ("method", "SHORT_DIVISION")],
    "D02": [*D, "regrouping", "remainder", ("method", "LINE")],
    "D03": [*D, "regroup_at", "remainder", "first_digit_smaller", ("divisor_group", ["2-5-10", "3-4"])],
    "D04": [*D, "regroup_at", "remainder", "first_digit_smaller", "divisor_group"],
    "D05": [*D, "regrouping", "remainder", "quotient_zero", "first_digit_smaller"],
    **{f"D{n:02d}": list(D3) for n in range(6, 11)},
    "D11": [*D, "regrouping"],
    "D12": [*D, "first_digit_smaller", ("regrouping", ["SINGLE", "MULTIPLE"])],
    "D13": [*D, "answer_digits"],
    "D14": [*D, "estimate_corrected", "answer_digits"],
    "DZ01": [*D, "quotient_zero", "zero_pattern", "regrouping"],
    "DZ02": [*D, "quotient_zero", "remainder", "scaled_fact"],
    "DZ03": [*D, "quotient_zero", "zero_pattern"],
    "DZ04": [*D, "zero_pattern", "quotient_zero"],
    "DZ05": ["quotient_zero"],
    "DZ06": ["operand_1_digits", "first_digit_smaller", "quotient_zero"],
    "DZ07": [*D, "quotient_zero", ("remainder", REMAINDERS)],
    "DR01": [*D, "answer_digits", "remainder"],
    "DR02": ["remainder", "answer_digits"],
    "DR03": ["remainder"],
    "DR04": [*D, "regrouping", ("remainder", REMAINDERS), "answer_digits"],
    "DR05": [*D, "regrouping", ("remainder", REMAINDERS), "first_digit_smaller"],
    "DR06": [*D, ("remainder", REMAINDERS)],
    "DR07": ["quotient_zero", ("remainder", REMAINDERS)],
    "DR08": [*D, "first_digit_smaller", ("remainder", REMAINDERS)],
    "DR10": ["place_value_factor", ("remainder", REMAINDERS)],
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
    "TF17": ("bare_sum", _x(6, 9, table="MULTIPLICATION_SQUARE"), ["fact", "context"]),
    "DF15": ("bare_sum", _x(42, 6, "÷", shape="HOW_MANY_GROUPS"), ["shape", "fact"]),
    # methods and pictures
    "G01": ("equal_groups", _x(3, 4, shape="PICTURE"), ["method"]),
    "G02": ("equal_groups", _x(3, 4, shape="SUM"), ["method"]),
    "G03": ("bare_sum", _x(5, 5, method="SKIP_COUNTING"), ["method"]),
    "G04": ("number_line_jumps", _x(4, 3, method="NUMBER_LINE"), ["method"]),
    "G05": ("equal_groups", _x(3, 5, method="ARRAY"), ["method"]),
    "G06": ("efficient_method", _x(14, 4, method="DOUBLING"), ["method"]),
    "G07": ("break_apart", _x(23, 4, method="PARTITIONING"), ["method"]),
    "G08": ("column_grid", _x(23, 4, layout="column", method="GRID"), ["method", "operand_2_digits"]),
    "G09": ("column_grid", _x(34, 26, layout="column", method="GRID"), ["method", "operand_2_digits"]),
    "G10": _col(34, 6, "×", "EXPANDED"),
    "G11": _col(34, 6, "×", "COLUMNS"),
    "G12": _col(68, 17, "×", "LONG_MULTIPLICATION"),
    "G13": _col(47, 23, "×", "LATTICE"),
    "G14": _shape("equation", "SWAP_TO_A_KNOWN_TABLE", ["×"], text="9 × 2 = 2 × 9 = □"),
    "G15": ("equal_groups", _x(12, 3, "÷", method="SHARING"), ["method"]),
    "G16": ("equal_groups", _x(12, 4, "÷", method="GROUPING"), ["method"]),
    "G17": ("bare_sum", _x(15, 3, "÷", method="REPEATED_SUBTRACTION"), ["method"]),
    "G18": ("number_line_jumps", _x(20, 4, "÷", method="NUMBER_LINE"), ["method"]),
    "G19": ("equal_groups", _x(20, 4, "÷", method="ARRAY"), ["method"]),
    "G20": ("inverse_check", _x(42, 6, "÷"), ["reasoning_type", "fact"]),
    "G21": ("break_apart", _x(72, 4, "÷", method="PARTITION_DIVIDEND"), ["method"]),
    "G22": _col(96, 4, "÷", "CHUNKING"),
    "G23": _col(72, 4, "÷", "SHORT_DIVISION"),
    "G24": _col(516, 4, "÷", "LONG_DIVISION"),
    "G25": ("efficient_method", _x(96, 4, "÷", method="HALVING"), ["method"]),
    # missing numbers and digits
    "Q01": _missing("8 × □ = 72", "unknown_position", "fact", "answer_first"),
    "Q02": _missing("□ × 6 = 42", "unknown_position", "fact", "answer_first"),
    "Q03": _missing("□ ÷ 4 = 7", "unknown_position", "remainder"),
    "Q04": _missing("56 ÷ □ = 8", "unknown_position", "remainder"),
    "Q05": _missing("□ = 63 ÷ 9", "answer_first"),
    "Q06": _missing("□ × □ = 49", "unknown_position"),
    "Q07": _digit("2□", "4", "92", "×", (23, 4), "missing_in", "missing_count", "operand_1_digits"),
    "Q08": _digit("47", "3", "1□1", "×", (47, 3), "missing_in", "missing_count"),
    "Q09": _digit("7□", "4", "18", "÷", (72, 4), "missing_in", "missing_count"),
    "Q10": _digit("936", "3", "3□2", "÷", (936, 3), "missing_in", "missing_count"),
    "Q11": _digit("□7", "6", "3□2", "×", (57, 6), "missing_count"),
    "Q12": _missing("38 ÷ 5 = 7 r □", "unknown_position"),
    "Q13": _missing("38 ÷ □ = 7 r 3", "unknown_position", ("remainder", REMAINDERS)),
    "Q14": _missing("45 × □ = 4500", "unknown_position", ("place_value_factor", ["X10", "X100", "X1000"])),
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
    "F08": ("odd_even", _x(6, 7, shape="PARITY_OF_A_PRODUCT"), ["shape"]),
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
    # estimating and judging
    "V01": ("estimate_then_calc", _x(48, 6, shape="ROUND_ONE"), ["shape"]),
    "V02": ("estimate_then_calc", _x(38, 21, shape="ROUND_BOTH"), ["shape"]),
    "V03": ("estimate_then_calc", _x(67, 75, shape="ANSWER_DIGITS"), ["shape"]),
    "V04": ("estimate_then_calc", _x(156, 4, "÷", shape="ANSWER_DIGITS"), ["shape"]),
    "V05": ("possible_answer", _x(23, 4, claimed=812), [("fmt", "possible_answer")]),
    "V06": ("odd_even", _x(7, 9), [("fmt", "odd_even")]),
    "V07": ("estimate_then_calc", _x(47, 3, shape="LAST_DIGIT"), ["shape"]),
    "V08": ("choose_estimate", _x(52, 9, options=[400, 450, 500]), [("fmt", "choose_estimate")]),
    "V09": ("possible_answer", _x(47, 6, "÷", claimed="6 r 11"), [("fmt", "possible_answer")]),
    "V10": ("estimate_then_calc", _x(412, 8, "÷", shape="ROUND_ONE"), ["shape"]),
    # word problems
    "B01": _story(4, 6, "×", "EQUAL_GROUPS"),
    "B02": _story(24, 4, "÷", "SHARING"),
    "B03": _story(24, 6, "÷", "GROUPING", "remainder"),
    "B04": _story(5, 7, "×", "ARRAY"),
    "B05": _story(35, 5, "÷", "ARRAY"),
    "B06": _story(8, 6, "×", "RATE_TOTAL"),
    "B07": _story(48, 8, "÷", "RATE_UNIT"),
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
    "B24": _story(30, 5, "÷", "GROUPING_BY_EACH"),
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
        m |= {"fmt": STRAIGHT_KINDS, "method": STANDARD[spec["op"]]}
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
