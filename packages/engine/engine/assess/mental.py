"""Mental multiplication and division, each method worked the way it is named (goals/md4a-mental-methods.yaml).

A mental method is asked as the sums it works out, each in a box with its sum printed beside it, then the answer's:
13 × 8 as 13 × 2 = □, 13 × 4 = □, 13 × 8 = □, doubled three times. A step is printed as a sum, never as the step before
it doubled, so no box gives away another's key, and every key is the sum beside it. Seven methods are made here (ADR
0064). × 5 as × 10 then halved and a number near a round one are `times_kinds.shortcut`'s, a fact from a known fact and
a fact scaled by ten `facts_kinds`', ÷ 5 as ÷ 10 then doubled `divide_kinds`'; their own mistakes are named here too
(`own`), so every mental method names its mistakes from one place, before the slips of the sum: one wrong answer names
one mistake, and on a question that asks for a method its own is the likelier.
"""

import dataclasses
import random
from typing import Any

from . import misconceptions as M
from . import operations as O
from .items import Item, Response, cells, item
from .misconceptions import named

STOPS = "M_MENTAL_STOPS_SHORT"  # a step's answer written as the answer: 13 × 8 doubled twice, 52
WRONG_WAY = "M_COMPENSATION_SIGN"  # put right the wrong way, as subtraction names it: 23 × 9 as 230 + 23
ONE = "M_MENTAL_ONE_NOT_GROUP"  # one taken away or added for a whole group: 23 × 9 as 230 − 1
BOTH = "M_CONFUSES_COMPENSATION"  # both numbers changed the same way, as addition names it: 16 × 5 as 32 × 10

# G06 and G25 name a method; H02 to H06 a strategy (`taxonomy_case.match`)
METHODS = ("DOUBLING", "HALVING")
STRATEGIES = (
    "DOUBLE_THREE_TIMES",
    "TIMES_TEN_LESS_A_GROUP",
    "TIMES_TEN_AND_A_GROUP",
    "DOUBLE_ONE_HALVE_THE_OTHER",
    "TIMES_HUNDRED_THEN_QUARTER",
)
TIMES = {
    "DOUBLE_THREE_TIMES": 8,
    "TIMES_TEN_LESS_A_GROUP": 9,
    "TIMES_TEN_AND_A_GROUP": 11,
    "TIMES_HUNDRED_THEN_QUARTER": 25,
}
TWO_DIGITS = [
    n for n in range(11, 100) if n % 10
]  # the number a method works on: 2 digits, never a round one


def _nearest_ten(a: int) -> int:
    return (a + 5) // 10 * 10


def own(way: str, a: int, b: int) -> list[tuple[str, int]]:
    """A mental method's own mistakes on its answer, with the wrong answer each gives: the step before written as the
    answer, the answer put right the wrong way, one taken away or added for a whole group, both numbers doubled."""
    if way in ("DOUBLING", "HALVING"):
        return [(STOPS, a * 2 if way == "DOUBLING" else a // 2)] if b == 4 else []
    if way == "DOUBLE_THREE_TIMES":
        return [(STOPS, a * 4)]
    if way in ("TIMES_TEN_LESS_A_GROUP", "TIMES_TEN_AND_A_GROUP"):
        less = way == "TIMES_TEN_LESS_A_GROUP"
        return [(STOPS, a * 10), (WRONG_WAY, a * (11 if less else 9)), (ONE, a * 10 + (-1 if less else 1))]
    if way == "TIMES_HUNDRED_THEN_QUARTER":
        return [(STOPS, a * 100)]
    if way == "TIMES_TEN_THEN_HALVE":
        return [(STOPS, a * 10)]
    if way == "DIVIDE_BY_TEN_THEN_DOUBLE":
        return [(STOPS, a // 10)]
    if way == "COMPENSATION":  # 19 × 6 from 20 × 6: 120 put right by one 6
        r = _nearest_ten(a)
        return [(STOPS, r * b), (WRONG_WAY, 2 * r * b - a * b), (ONE, r * b + (1 if a > r else -1))]
    if way == "DOUBLE_ONE_HALVE_THE_OTHER":
        return [(BOTH, 4 * a * b)]
    return []


def answer_box(way: str, a: int, b: int, box: Response) -> Response:
    """The answer's box of a mental method: its own mistakes first, each value theirs alone (14 × 11 answered 140 is a
    step short, not the table's row out), then the slips its sum already names, as that operation names them (a value
    two of division's mistakes write names both, `div_mistakes.in_box`)."""
    mine = named(int(box.answer), own(way, a, b))
    rest = {c: v for c, v in box.misconceptions.items() if v not in mine.values() and c not in mine}
    return dataclasses.replace(box, misconceptions={**mine, **rest})


def _sum(rid: str, x: int, op: str, y: int) -> Response:
    """A step or the answer: the sum it works out printed beside its box, its key, and that sum's slips."""
    n = x * y if op == "×" else x // y
    return Response(
        rid,
        "digits",
        str(n),
        cells=cells(n),
        label=f"{x} {op} {y} =",
        misconceptions=M.predict(op, x, y),  # as its operation names them
    )


def _halved(a: int, b: int) -> int:
    """Which of the two numbers is halved: the even one whose partner doubles to a round number (16 × 5: 16, as 5
    doubles to 10; 35 × 4: 4, as 35 doubles to 70)."""
    for i, (h, d) in enumerate(((a, b), (b, a))):
        if h % 2 == 0 and h > 2 and (d * 2) % 10 == 0:
            return i
    raise O.CannotMake(f"{a} × {b} has no even number whose partner doubles to a round one: draw again")


def _steps(way: str, a: int, b: int) -> list[tuple[int, str, int]]:
    """The sums a method works out, in order; the last is the question's own."""
    if way == "DOUBLING":
        if b not in (2, 4):
            raise O.CannotMake(
                "doubling is × 2 and × 4; × 8 by doubling three times is a strategy of its own (H05)"
            )
        return [(a, "×", 2)] + ([(a, "×", 4)] if b == 4 else [])
    if way == "HALVING":
        if b not in (2, 4) or a % b:
            raise O.CannotMake(f"{a} ÷ {b} does not halve into whole numbers: draw again")
        return [(a, "÷", 2)] + ([(a, "÷", 4)] if b == 4 else [])
    if way in TIMES:
        if b != TIMES[way]:
            raise O.CannotMake(f"{way} multiplies by {TIMES[way]}, not {b}")
        first = {8: [(a, "×", 2), (a, "×", 4)], 9: [(a, "×", 10)], 11: [(a, "×", 10)], 25: [(a, "×", 100)]}[b]
        return [*first, (a, "×", b)]
    if way == "DOUBLE_ONE_HALVE_THE_OTHER":
        halve_a = _halved(a, b) == 0
        return [(a, "÷" if halve_a else "×", 2), (b, "×" if halve_a else "÷", 2), (a, "×", b)]
    raise ValueError(f"{way} is no mental method made here: {', '.join((*METHODS, *STRATEGIES))}")


def _stem(way: str, a: int, b: int) -> str:
    if way == "DOUBLING":
        return (
            f"Work out {a} × {b} by doubling: double {a}, then double again."
            if b == 4
            else f"Work out {a} × 2 by doubling {a}."
        )
    if way == "HALVING":
        return (
            f"Work out {a} ÷ {b} by halving: halve {a}, then halve again."
            if b == 4
            else f"Work out {a} ÷ 2 by halving {a}."
        )
    if way == "DOUBLE_THREE_TIMES":
        return f"Work out {a} × 8 by doubling three times: double {a}, double again, then double once more."
    if way == "TIMES_TEN_LESS_A_GROUP":
        return f"Work out {a} × 9. First work out {a} × 10, then take away one {a}."
    if way == "TIMES_TEN_AND_A_GROUP":
        return f"Work out {a} × 11. First work out {a} × 10, then add one more {a}."
    if way == "TIMES_HUNDRED_THEN_QUARTER":
        return f"Work out {a} × 25. First work out {a} × 100, then divide it by 4."
    h, d = (a, b) if _halved(a, b) == 0 else (b, a)
    return f"Work out {a} × {b}. Halve {h} and double {d}, then multiply the new numbers."


def make(way: str, a: int, b: int, rung: str, signal: str = "Procedural") -> Item:
    """One mental method on these numbers: a box for every step, its sum beside it, then the answer's. CannotMake for
    numbers the method cannot work (14 × 8 by doubling is × 8's own strategy; 98 ÷ 4 does not halve twice)."""
    sums = _steps(way, a, b)
    rs = [_sum(f"s{k}", *s) for k, s in enumerate(sums[:-1], start=1)]
    rs.append(answer_box(way, a, b, _sum("ans", *sums[-1])))
    op = sums[-1][1]
    spec: dict[str, Any] = {
        "a": a,
        "b": b,
        "op": op,
        **({"method": way} if way in METHODS else {"strategy": way}),
    }
    return item("EFFICIENT", rung, signal, "efficient_method", _stem(way, a, b), spec, rs, working_lines=1)


def _numbers(rng: random.Random, way: str, b: Any) -> tuple[int, int]:
    """Two numbers a method works: a 2-digit number (LO-G2-0496 at Grade 2, and on through Grade 4) and the method's
    own; for doubling and halving, × or ÷ 2 or 4 as the case allows."""
    if way == "DOUBLING":
        return rng.choice(TWO_DIGITS), rng.choice([2, 4] if b is None else [b])
    if way == "HALVING":
        by = rng.choice([2, 4] if b is None else [b])
        return rng.choice([n for n in TWO_DIGITS if n % by == 0 and n > 2 * by]), by
    if way == "DOUBLE_ONE_HALVE_THE_OTHER":  # 16 × 5 = 8 × 10, or 35 × 4 = 70 × 2
        if rng.random() < 0.5:
            return rng.choice([n for n in TWO_DIGITS if n % 2 == 0]), 5
        return rng.choice([15, 25, 35, 45]), rng.choice([4, 6, 8])
    return rng.choice(TWO_DIGITS), TIMES[way]


def drawn(rng: random.Random, rung: str, signal: str, check: dict[str, Any]) -> Item:
    """A mental method the case names, drawn on its own numbers (`_numbers`)."""
    way = check.get("method") if check.get("method") in METHODS else check.get("strategy")
    if not isinstance(way, str) or way not in (*METHODS, *STRATEGIES):
        raise ValueError(f"no mental method named: {check.get('method')} {check.get('strategy')}")
    a, b = _numbers(rng, way, check.get("b"))
    return make(way, a, b, rung, signal)
