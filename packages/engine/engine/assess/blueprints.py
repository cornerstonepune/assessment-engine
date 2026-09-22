"""Blueprints: grade × level -> ordered slots. Each slot is (label, fn(rng) -> Item).
Counted in scorable responses. The last slot of every sheet is the probe from the rung above.
"""

from . import diagnosis as D
from . import items as I
from . import missing_digits as MD
from . import words as W


def col(op, da, db, regroups, rung, signal="Procedural", across_zero=False):
    return lambda rng: I.bare_sum(
        rng, rung, signal, op, da, db, set(regroups), across_zero=across_zero, layout="column"
    )


def bare(op, da, db, regroups, rung, signal="Procedural", max_total=None, across_zero=False):
    return lambda rng: I.bare_sum(
        rng,
        rung,
        signal,
        op,
        da,
        db,
        set(regroups),
        max_total=max_total,
        across_zero=across_zero,
        layout="horizontal",
    )


BLUEPRINTS = {
    ("G1", "Lm"): [
        ("R1 sums within 10", bare("+", 1, 1, {0}, "R1", "Foundational", 10)),
        ("R1", bare("+", 1, 1, {0}, "R1", "Procedural", 10)),
        ("R1", bare("+", 1, 1, {0}, "R1", "Procedural", 10)),
        ("R1", bare("+", 1, 1, {0}, "R1", "Procedural", 10)),
        ("R1 take-away within 10", bare("-", 1, 1, {0}, "R1", "Procedural")),
        ("R1", bare("-", 1, 1, {0}, "R1", "Procedural")),
        ("R1 missing part", lambda r: I.missing_part_20(r, "R1", "Conceptual")),
        ("R1 word", lambda r: W.word_1step(r, "R1", "Application", 1, (0,))),
        ("R1 word", lambda r: W.word_1step(r, "R1", "Application", 1, (0,))),
        ("probe R2 crossing 10", bare("+", 1, 1, {1}, "R2", "Stretch", 18)),
    ],
    ("G1", "L0"): [
        ("R1 foundational", bare("+", 1, 1, {0}, "R1", "Foundational", 10)),
        ("R1 foundational", bare("-", 1, 1, {0}, "R1", "Foundational")),
        ("R2 crossing 10", bare("+", 1, 1, {1}, "R2", "Procedural", 18)),
        ("R2", bare("+", 1, 1, {1}, "R2", "Procedural", 18)),
        ("R2", bare("+", 1, 1, {1}, "R2", "Procedural", 18)),
        ("R2", bare("+", 1, 1, {1}, "R2", "Procedural", 18)),
        ("R3 subtract within 20", bare("-", 2, 1, {1}, "R3", "Procedural", 20)),
        ("R3", bare("-", 2, 1, {1}, "R3", "Procedural", 20)),
        ("R3", bare("-", 2, 1, {0}, "R3", "Procedural", 20)),
        ("R3", bare("-", 2, 1, {1}, "R3", "Procedural", 20)),
        ("R2 part-part-whole", lambda r: I.missing_part_20(r, "R2", "Conceptual")),
        ("R2 part-part-whole", lambda r: I.missing_part_20(r, "R2", "Conceptual")),
        ("R3 word", lambda r: W.word_1step(r, "R3", "Application", 1, (0, 1))),
        ("R2 word", lambda r: W.word_1step(r, "R2", "Application", 1, (0, 1))),
        ("probe R4", col("+", 2, 2, {0}, "R4", "Stretch")),
    ],
    ("G1", "Lp"): [
        ("R2 foundational", bare("+", 1, 1, {1}, "R2", "Foundational", 18)),
        ("R3 foundational", bare("-", 2, 1, {1}, "R3", "Foundational", 20)),
        ("R4 add no regroup", col("+", 2, 2, {0}, "R4")),
        ("R4", col("+", 2, 2, {0}, "R4")),
        ("R4", col("+", 2, 2, {0}, "R4")),
        ("R4 sub no regroup", col("-", 2, 2, {0}, "R4")),
        ("R4", col("-", 2, 2, {0}, "R4")),
        ("R4", col("-", 2, 2, {0}, "R4")),
        ("R4 missing number", lambda r: I.missing_number(r, "R4", "Conceptual", "add_missing_addend", 50)),
        ("R4 number wall", lambda r: I.number_wall(r, "R4", "Procedural", 20)),
        ("R4 word", lambda r: W.word_1step(r, "R4", "Application", 2, (0,))),
        ("R4 word", lambda r: W.word_1step(r, "R4", "Application", 2, (0,))),
        ("probe R5", col("+", 2, 2, {1}, "R5", "Stretch")),
    ],
    ("G2", "Lm"): [
        ("R3 foundational", bare("-", 2, 1, {1}, "R3", "Foundational", 20)),
        ("R3 foundational", bare("+", 1, 1, {1}, "R2", "Foundational", 18)),
        ("R4 add", col("+", 2, 2, {0}, "R4")),
        ("R4 add", col("+", 2, 2, {0}, "R4")),
        ("R4 2d+1d alignment", col("+", 2, 1, {0}, "R4")),
        ("R4 sub", col("-", 2, 2, {0}, "R4")),
        ("R4 sub", col("-", 2, 2, {0}, "R4")),
        ("R4 2d-1d alignment", col("-", 2, 1, {0}, "R4")),
        ("R4 missing", lambda r: I.missing_number(r, "R4", "Conceptual", "add_missing_addend", 100)),
        ("R4 missing", lambda r: I.missing_number(r, "R4", "Conceptual", "sub_missing_subtrahend", 100)),
        ("R4 wall", lambda r: I.number_wall(r, "R4", "Procedural", 30)),
        ("R4 word", lambda r: W.word_1step(r, "R4", "Application", 2, (0,))),
        ("R4 word", lambda r: W.word_1step(r, "R4", "Application", 2, (0,))),
        ("probe R5", col("+", 2, 2, {1}, "R5", "Stretch")),
    ],
    ("G2", "L0"): [
        ("R4 foundational", col("+", 2, 2, {0}, "R4", "Foundational")),
        ("R4 foundational", col("-", 2, 2, {0}, "R4", "Foundational")),
        ("R5 add one regroup", col("+", 2, 2, {1}, "R5")),
        ("R5 horizontal", bare("+", 2, 2, {1}, "R5")),
        ("R5 2d+1d alignment", col("+", 2, 1, {1}, "R5")),
        ("R6 sub with exchange", col("-", 2, 2, {1}, "R6")),
        ("R6 horizontal", bare("-", 2, 2, {1}, "R6")),
        ("R6 2d-1d alignment", col("-", 2, 1, {1}, "R6")),
        ("R6 recognise regrouping", lambda r: I.sort_into_table(r, "R6", "Conceptual", "-")),
        ("R7 number line", lambda r: I.number_line_jumps(r, "R7", "Conceptual", "+", 100)),
        ("R7 missing", lambda r: I.missing_number(r, "R7", "Conceptual", "add_missing_addend", 100)),
        ("R7 missing", lambda r: I.missing_number(r, "R7", "Conceptual", "sub_missing_minuend", 100)),
        ("R7 balance", lambda r: I.balance_scale(r, "R7", "Conceptual", 100)),
        ("R8 word", lambda r: W.word_1step(r, "R8", "Application", 2, (1,))),
        ("R8 word", lambda r: W.word_1step(r, "R8", "Application", 2, (1,))),
        ("probe R9", col("+", 3, 2, {1}, "R9", "Stretch")),
    ],
    ("G2", "Lp"): [
        ("R5 foundational", col("+", 2, 2, {1}, "R5", "Foundational")),
        ("R6 foundational", col("-", 2, 2, {1}, "R6", "Foundational")),
        ("R7 efficient", lambda r: I.efficient_method(r, "R7", "Procedural")),
        ("R7 efficient", lambda r: I.efficient_method(r, "R7", "Procedural")),
        ("R7 missing to 1000", lambda r: I.missing_number(r, "R7", "Conceptual", "add_missing_addend", 1000)),
        ("R7 missing", lambda r: I.missing_number(r, "R7", "Conceptual", "sub_missing_minuend", 1000)),
        ("R9 add", col("+", 3, 3, {1}, "R9")),
        ("R9 add two regroups", col("+", 3, 3, {2}, "R9")),
        ("R9 sub", col("-", 3, 3, {1}, "R9")),
        ("R9 sub two regroups", col("-", 3, 3, {2}, "R9")),
        ("R11 estimate", lambda r: I.estimate_then_calc(r, "R11", "Application", "+", 3, 2, {1})),
        ("R8 two-step", lambda r: W.word_2step(r, "R8", "Application", 2)),
        ("X1 claim", lambda r: D.explain_claim(r, "X1", "Conceptual")),
        ("probe R10", col("-", 3, 3, {1, 2}, "R10", "Stretch", across_zero=True)),
    ],
}
BLUEPRINTS[("G3", "Lm")] = BLUEPRINTS[("G2", "L0")]
BLUEPRINTS[("G3", "L0")] = [
    ("R6 foundational", col("-", 2, 2, {1}, "R6", "Foundational")),
    ("R5 foundational", col("+", 2, 2, {1}, "R5", "Foundational")),
    ("R9 add one regroup", col("+", 3, 3, {1}, "R9")),
    ("R9 add two regroups", col("+", 3, 3, {2}, "R9")),
    ("R9 sub horizontal", bare("-", 3, 3, {1}, "R9")),
    ("R9 3d+2d alignment", col("+", 3, 2, {1}, "R9")),
    ("R10 across zero", col("-", 3, 3, {1, 2}, "R10", across_zero=True)),
    ("R10 across zero, horizontal 3d-2d", bare("-", 3, 2, {1, 2}, "R10", across_zero=True)),
    ("R9 partition", lambda r: I.partition_scaffold(r, "R9", "Conceptual", {1})),
    ("R11 estimate", lambda r: I.estimate_then_calc(r, "R11", "Application", "+", 3, 3, {1})),
    ("R11 estimate", lambda r: I.estimate_then_calc(r, "R11", "Application", "-", 3, 2, {1})),
    ("R7 missing", lambda r: I.missing_number(r, "R7", "Conceptual", "sub_missing_minuend", 1000)),
    ("R7 balance", lambda r: I.balance_scale(r, "R7", "Conceptual", 1000)),
    ("R8 two-step", lambda r: W.word_2step(r, "R8", "Application", 3)),
    ("probe R12", col("-", 4, 4, {1, 2, 3}, "R12", "Stretch", across_zero=True)),
]
BLUEPRINTS[("G3", "Lp")] = [
    ("R9 foundational", col("+", 3, 3, {2}, "R9", "Foundational")),
    ("R10 foundational", col("-", 3, 3, {1, 2}, "R10", "Foundational", across_zero=True)),
    ("R12 multi-addend", lambda r: I.multi_add(r, "R12", "Procedural", 3, 4)),
    ("R12 sub across zeros", col("-", 4, 4, {1, 2, 3}, "R12", across_zero=True)),
    ("R12", col("-", 4, 4, {1, 2, 3}, "R12", across_zero=True)),
    (
        "R13 missing digits",
        lambda r: MD.one(
            r, "R13", "Conceptual", {"op": "+", "width": 3, "missing_count": 2, "missing_in": "FIRST+SECOND"}
        ),
    ),
    (
        "R13 missing digits",
        lambda r: MD.one(
            r, "R13", "Conceptual", {"op": "-", "width": 3, "missing_count": 2, "missing_in": "FIRST+SECOND"}
        ),
    ),
    ("R13 efficient", lambda r: I.efficient_method(r, "R13", "Procedural")),
    ("R13 efficient", lambda r: I.efficient_method(r, "R13", "Procedural")),
    ("R13 digit cards", lambda r: I.digit_cards(r, "R13", "Stretch", 3)),
    ("X1 claim", lambda r: D.explain_claim(r, "X1", "Conceptual")),
    ("X2 find the mistake", lambda r: D.find_mistake(r, "X2", "Conceptual", "-")),
    ("probe R14 budget", lambda r: W.word_budget(r, "R14", "Stretch")),
]
BLUEPRINTS[("G4", "Lm")] = BLUEPRINTS[("G3", "L0")]
BLUEPRINTS[("G4", "L0")] = [
    ("R10 foundational", col("-", 3, 3, {1, 2}, "R10", "Foundational", across_zero=True)),
    ("R9 foundational", col("+", 3, 3, {2}, "R9", "Foundational")),
    ("R12 multi-addend", lambda r: I.multi_add(r, "R12", "Procedural", 3, 4)),
    ("R12 multi-addend", lambda r: I.multi_add(r, "R12", "Procedural", 4, 4)),
    ("R12 sub across zeros", col("-", 4, 4, {1, 2, 3}, "R12", across_zero=True)),
    ("R12 horizontal 4d-2d", bare("-", 4, 2, {1, 2, 3}, "R12", across_zero=True)),
    (
        "R13 missing digits",
        lambda r: MD.one(
            r, "R13", "Conceptual", {"op": "+", "width": 3, "missing_count": 2, "missing_in": "FIRST+SECOND"}
        ),
    ),
    (
        "R13 missing digits",
        lambda r: MD.one(
            r, "R13", "Conceptual", {"op": "-", "width": 3, "missing_count": 2, "missing_in": "FIRST+SECOND"}
        ),
    ),
    ("R13 efficient", lambda r: I.efficient_method(r, "R13", "Procedural")),
    ("R13 efficient", lambda r: I.efficient_method(r, "R13", "Procedural")),
    ("R11 estimate 4-digit", lambda r: I.estimate_then_calc(r, "R11", "Application", "-", 4, 4, {1, 2})),
    ("R13 digit cards", lambda r: I.digit_cards(r, "R13", "Stretch", 3)),
    ("R14 two-step", lambda r: W.word_2step(r, "R14", "Application", 3)),
    ("R14 budget", lambda r: W.word_budget(r, "R14", "Application")),
    ("probe X2", lambda r: D.find_mistake(r, "X2", "Stretch", "+")),
]
BLUEPRINTS[("G4", "Lp")] = [
    ("R12 foundational", col("-", 4, 4, {1, 2, 3}, "R12", "Foundational", across_zero=True)),
    ("R13 efficient", lambda r: I.efficient_method(r, "R13", "Procedural")),
    ("R13 efficient", lambda r: I.efficient_method(r, "R13", "Procedural")),
    (
        "R13 missing digits",
        lambda r: MD.one(
            r, "R13", "Conceptual", {"op": "-", "width": 3, "missing_count": 2, "missing_in": "FIRST+SECOND"}
        ),
    ),
    (
        "R13 missing digits",
        lambda r: MD.one(
            r, "R13", "Conceptual", {"op": "+", "width": 4, "missing_count": 2, "missing_in": "FIRST+SECOND"}
        ),
    ),
    ("R13 digit cards", lambda r: I.digit_cards(r, "R13", "Stretch", 4)),
    ("X1 claim", lambda r: D.explain_claim(r, "X1", "Conceptual")),
    ("X2 find the mistake", lambda r: D.find_mistake(r, "X2", "Conceptual", "+")),
    ("X2 find the mistake", lambda r: D.find_mistake(r, "X2", "Conceptual", "-")),
    ("R14 budget", lambda r: W.word_budget(r, "R14", "Application")),
    ("R14 budget", lambda r: W.word_budget(r, "R14", "Application")),
    ("R12 four addends", lambda r: I.multi_add(r, "R12", "Stretch", 4, 4)),
]
