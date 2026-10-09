"""A multiplication's two numbers, as its case allows (goals/md2a-straight-multiplication.yaml). Deterministic given an
RNG; `assess/draw.py` asks it for the numbers of a × case and for the defaults a × question keeps.

A table fact is drawn from the tables, 0 to 12 (assumption A4); a level that leaves out the 11 and 12 tables says
so in its own numbers (`within`), and the drawing keeps only what the level holds. 10 is a table's number, not a round
one. A number a case lets be round (MUL.TENS) is a
number times 10, 100 or 1000. Every other pair is two numbers of their digits, never × 1 unless the case is about it.
"""

import random
from typing import Any

from . import taxonomy

LISTED = 20000  # pairs: 3 digits by 2 is 81 hundred
ROUND = ("X10", "X100", "X1000", "MULTIPLE_OF_TEN_ONE", "MULTIPLE_OF_HUNDRED_ONE", "MULTIPLE_OF_TEN_BOTH")


def round_ok(alt: dict[str, Any]) -> bool:
    """Whether a case lets the numbers be round: it allows a place-value factor."""
    return "place_value_factor" in alt and any(taxonomy.holds(alt["place_value_factor"], v) for v in ROUND)


def table(alt: dict[str, Any]) -> bool:
    """Whether a case is a table fact's."""
    return alt.get("fact") == "YES" or "fact_table" in alt or "fact_swapped" in alt


def _span(d: int, zero_ok: bool) -> range:
    return range(0 if (d == 1 and zero_ok) else (1 if d == 1 else 10 ** (d - 1)), 10**d)


def _number(rng: random.Random, d: int, zero_ok: bool) -> int:
    return rng.choice(_span(d, zero_ok))


def numbers(
    rng: random.Random, alt: dict[str, Any], about: set[str], d1: int, d2: int
) -> tuple[int, int] | None:
    """Two numbers to multiply, `d1` and `d2` digits where the case reads digits; None when the case's table is no
    table a level allows."""
    zero_ok = "zero_operand" in about
    if table(alt):
        lo, hi = (0 if zero_ok else 1), 12
        tables = [n for n in range(lo, 13) if "fact_table" not in alt or taxonomy.holds(alt["fact_table"], n)]
        return (rng.choice(tables), rng.randint(lo, hi)) if tables else None
    if round_ok(alt):
        za, zb = rng.randint(0, d1 - 1), rng.randint(0, d2 - 1)
        return _number(rng, d1 - za, zero_ok) * 10**za, _number(rng, d2 - zb, zero_ok) * 10**zb
    return _number(rng, d1, zero_ok), _number(rng, d2, zero_ok)


def every(alt: dict[str, Any], about: set[str], d1: int, d2: int) -> list[tuple[int, int]] | None:
    """Every pair `numbers` can draw for these digits, in order: the whole of a case, read when its random draws run
    dry, since a small level's last questions turn up once in thousands of draws (3 × 21 in MUL.2D1D Easy). None past
    LISTED pairs (× 1000 has 9000 four-digit numbers), a range no level drawn whole comes near (test_mul_levels.py)."""
    zero_ok = "zero_operand" in about
    if table(alt):
        lo = 0 if zero_ok else 1
        tables = [n for n in range(lo, 13) if "fact_table" not in alt or taxonomy.holds(alt["fact_table"], n)]
        return [(t, n) for t in tables for n in range(lo, 13)]

    def side(d: int) -> list[int]:
        return sorted(
            {x * 10**z for z in (range(d) if round_ok(alt) else [0]) for x in _span(d - z, zero_ok)}
        )

    xs, ys = side(d1), side(d2)
    return [(a, b) for a in xs for b in ys] if len(xs) * len(ys) <= LISTED else None


def usable(
    a: int, b: int, about: set[str], check: dict[str, Any], alt: dict[str, Any], lifts: set[str]
) -> bool:
    """The defaults a × question keeps unless its case is about what they rule out. `lifts` names the defaults the
    case lifts, as `assess/draw.py` reads them: "zero", "round", "size"."""
    if "zero" not in lifts and 0 in (a, b):
        return False
    if not ({"zero", "round"} & lifts or table(alt) or round_ok(alt)) and any(
        x >= 10 and x % 10 == 0 for x in (a, b)
    ):
        return False
    if 1 in (a, b) and "one_operand" not in about:
        return False
    if a == b and not ("size" in lifts or a < 10):
        return False
    return not (check.get("max_total") and a * b > check["max_total"])
