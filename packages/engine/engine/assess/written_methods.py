"""The written methods of multiplication, a calculation printed as its method's steps, each a box (ADR 0055).

Partitioning (23 × 4 is 20 × 4 and 3 × 4, then added), a grid (every part of one number times every part of the other,
then the cells added), expanded columns (each product written in full in a row of its own, then added) and a lattice
(every digit times every digit, two digits across a cell's diagonal, then added along the diagonals). Every step is a
`Response` with its own key, so the reader reads it and marking marks it by itself; the total is `ans`. Pure, no I/O.

What a step or total can be worked wrong as, each from the numbers: a part with its tens taken as ones (20 × 4 written
8, `M_PARTITION_TENS_AS_ONES`), a grid added without its ones-by-ones cell (`M_GRID_CELL_DROPPED`), the steps added
without a carry (`M_NOCARRY`, addition's: assumption A11), the numbers added instead (`M_WRONG_OP`); a step is a small
multiplication, so it names a small multiplication's mistakes too. A column method's own slips (a carry dropped, the
second row not moved) belong to columns, so a method's total does not name them.
"""

from random import Random
from typing import Any

from engine.assess import misconceptions as M
from engine.assess import operations as O
from engine.assess.items import Item, Response, cells, item
from engine.assess.misconceptions import named
from engine.assess.times_kinds import number

# the method, as printed: the kind of question that prints it
KINDS = {
    "PARTITIONING": "partitioning",
    "GRID": "grid_method",
    "EXPANDED": "expanded_columns",
    "LATTICE": "lattice",
}
STEMS = {
    "PARTITIONING": "Partition the larger number. Multiply each part, then add.",
    "GRID": "Multiply in the grid, then add the cells.",
    "EXPANDED": "Write each product in full, then add.",
    "LATTICE": "Multiply into the lattice, then add along the diagonals.",
}


def parts(n: int) -> list[int]:
    """23 → [20, 3]; 302 → [300, 2]: a number partitioned by place, its zero places left out."""
    s = str(n)
    return [int(d) * 10 ** (len(s) - 1 - i) for i, d in enumerate(s) if d != "0"]


def ones(p: int) -> int:
    """20 → 2, 300 → 3: a part with its tens or hundreds taken as ones."""
    return int(str(p)[0])


def nocarry(xs: list[int]) -> int:
    """The numbers added column by column, each column's last digit written and nothing carried: 76 + 190 → 166."""
    width = max(len(str(x)) for x in xs)
    columns = [sum(M.digits(x, width)[i] for x in xs) % 10 for i in range(width)]
    return M.from_digits(columns)


def rows_added(a: int, b: int) -> dict[str, int]:
    """A long multiplication's rows added without a carry (19 × 14: 76 + 190 written 166), when they carry; nothing for
    one row or a sum of rows that carries nothing (`answer_space._rows_worked` draws the same rows)."""
    top, multiplier = (a, b) if len(str(a)) >= len(str(b)) else (b, a)
    rows = O.rows(top, multiplier)
    wrong = nocarry(rows) if len(rows) >= 2 else a * b
    return {"M_NOCARRY": wrong} if wrong != a * b else {}


def _step(x: int, y: int, label: str, digits: int = 0) -> Response:
    """One step, x × y: a part with its tens taken as ones, then a small multiplication's own slips."""
    right = x * y
    as_ones = ones(x) * ones(y) if max(x, y) >= 10 else right
    mis = named(right, [("M_PARTITION_TENS_AS_ONES", as_ones), *M.predict("×", x, y).items()])
    key = str(right).zfill(digits)
    return Response("", "digits", key, cells=len(key) + 1, misconceptions=mis, label=label)


def _total(a: int, b: int, own: list[tuple[str, int]]) -> Response:
    mis = named(a * b, [*own, ("M_WRONG_OP", a + b)])
    return Response("ans", "digits", str(a * b), cells=cells(a * b), misconceptions=mis, label=f"{a} × {b} =")


def _partitioning(a: int, b: int) -> tuple[list[Response], list[tuple[str, int]]]:
    first = len(str(a)) < len(str(b))  # 3 × 21: the 1-digit number written first keeps its place
    n, m = (b, a) if first else (a, b)
    steps = [_step(p, m, f"{m} × {p} =" if first else f"{p} × {m} =") for p in parts(n)]
    tens = sum(ones(p) * m for p in parts(n))
    return steps, [("M_PARTITION_TENS_AS_ONES", tens), ("M_NOCARRY", nocarry([p * m for p in parts(n)]))]


def grid_axes(a: int, b: int) -> tuple[list[int], list[int], bool]:
    """(the parts across the top, the parts down the side, whether `a`'s are on top): the number with more parts goes
    across the top, as a grid is drawn, so 3 × 21 has 20 and 1 along the top and 3 at the side."""
    on_top = len(parts(a)) >= len(parts(b))
    return (parts(a), parts(b), True) if on_top else (parts(b), parts(a), False)


def _grid(a: int, b: int) -> tuple[list[Response], list[tuple[str, int]]]:
    top, side, a_on_top = grid_axes(a, b)
    # a cell for every part down the side times every part across the top, a row at a time; each named as the question
    # orders its numbers (3 × 20, never 20 × 3, for 3 × 21)
    pairs = [(t, s) if a_on_top else (s, t) for s in side for t in top]
    steps = [_step(p, q, f"{p} × {q} =") for p, q in pairs]
    dropped = a * b - (a % 10) * (b % 10)
    tens = sum(ones(p) * ones(q) for p, q in pairs)
    added = nocarry([p * q for p, q in pairs])
    return steps, [("M_GRID_CELL_DROPPED", dropped), ("M_PARTITION_TENS_AS_ONES", tens), ("M_NOCARRY", added)]


def _expanded(a: int, b: int) -> tuple[list[Response], list[tuple[str, int]]]:
    n, m = (a, b) if len(str(a)) >= len(str(b)) else (b, a)  # in columns the longer number is on top
    rows = list(reversed(parts(n)))  # the ones first, as columns are worked
    steps = [_step(p, m, f"{p} × {m} =") for p in rows]
    tens = sum(ones(p) * m for p in rows)
    return steps, [("M_PARTITION_TENS_AS_ONES", tens), ("M_NOCARRY", nocarry([p * m for p in rows]))]


def _lattice(a: int, b: int) -> tuple[list[Response], list[tuple[str, int]]]:
    placed = [
        (int(x), int(y), 10 ** (len(str(a)) - 1 - i + len(str(b)) - 1 - j))
        for j, y in enumerate(str(b))
        for i, x in enumerate(str(a))
    ]  # a row for each digit of b
    steps = [_step(x, y, f"{x} × {y} =", digits=2) for x, y, _ in placed]
    return steps, [("M_NOCARRY", nocarry([x * y * place for x, y, place in placed]))]


WORK = {"PARTITIONING": _partitioning, "GRID": _grid, "EXPANDED": _expanded, "LATTICE": _lattice}


def prints(a: int, b: int) -> bool:
    """Whether a written method can set out `a × b`: it multiplies the numbers' parts, and a zero has none."""
    return bool(a and b)


def make(method: str, a: int, b: int, rung: str) -> Item:
    """`a × b` printed in `method`, a box for every step and then the total. A column method sets the longer number on
    top, as the school writes it; the others keep the order the question gives."""
    if method not in WORK:
        raise O.CannotMake(f"no written method {method!r}: {', '.join(WORK)}")
    if not prints(a, b):
        raise O.CannotMake(f"{a} × {b} in {method}: a written method multiplies parts, and a zero has none")
    if method == "EXPANDED" and len(str(a)) < len(str(b)):
        a, b = b, a
    steps, own = WORK[method](a, b)
    for k, r in enumerate(steps, start=1):
        r.rid = f"s{k}"
    spec: dict[str, Any] = {"a": a, "b": b, "op": "×", "method": method}
    if method == "EXPANDED":
        spec["layout"] = "column"
    return item(
        method,
        rung,
        "Procedural",
        KINDS[method],
        STEMS[method],
        spec,
        [*steps, _total(a, b, own)],
        working_lines=0,
    )


# a method drawn on its own, from a level's rule (`bands.NATIVE_GENERATORS`): the digits of its two numbers
DIGITS = {"PARTITIONING": (2, 1), "GRID": (2, 1), "EXPANDED": (2, 1), "LATTICE": (2, 2)}


def drawn(method: str, rng: Random, rung: str, rule: dict[str, Any]) -> Item:
    d1, d2 = rule.get("digits") or DIGITS[method]
    return make(method, number(rng, int(d1)), number(rng, int(d2)), rung)


def partitioning(rng: Random, rung: str, signal: str, rule: dict[str, Any]) -> Item:
    return drawn("PARTITIONING", rng, rung, rule)


def grid(rng: Random, rung: str, signal: str, rule: dict[str, Any]) -> Item:
    return drawn("GRID", rng, rung, rule)


def expanded(rng: Random, rung: str, signal: str, rule: dict[str, Any]) -> Item:
    return drawn("EXPANDED", rng, rung, rule)


def lattice(rng: Random, rung: str, signal: str, rule: dict[str, Any]) -> Item:
    return drawn("LATTICE", rng, rung, rule)
