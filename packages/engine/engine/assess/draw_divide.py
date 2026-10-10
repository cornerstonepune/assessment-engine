"""A division's two numbers, as its case allows (goals/md3a-straight-division.yaml). Deterministic given an RNG;
`assess/draw.py` asks it for the numbers of a ÷ case, as `draw_times.py` gives a × case's.

A division is drawn as it is checked: a divisor, a quotient and a remainder, the number divided made of them
(q × b + r), so an exact division is never a needle among random pairs. Three kinds of case, as the four skills' own
numbers are (`skill_sets.json`, `within`):

- a table read backwards (`from_table`): a divisor to 12 and a quotient to 12, or under 10 with a remainder (A4);
- place value (`place_value_factor`): ÷ 10, 100 or 1000 of a number to 4 digits, or a round number that is a table
  fact with its zeros put back (200 ÷ 4 is 20 ÷ 4, 800 ÷ 40 is 8 ÷ 4);
- every other: a number of its digits by a 1-digit number, worked digit by digit. A 2-digit divisor worked so is long
  division (D13, D14), which no level holds yet.

A remainder only where the case is about one, except that a case worked digit by digit and silent on it has either.
Never ÷ 0; ÷ 1, 0 ÷ a number and a number ÷ itself only where the case is about it. The four's numbers are few enough
to list (÷ 10, 100 or 1000 of a number to 4 digits, the most, is under 30,000), so every draw is one of the list
(`every`), and a case's last questions are found by reading it, not by luck."""

import functools
import json
import random
from collections.abc import Iterator
from typing import Any

from . import taxonomy

POWERS = {"X10": 10, "X100": 100, "X1000": 1000}
ROUND = ("MULTIPLE_OF_TEN_ONE", "MULTIPLE_OF_HUNDRED_ONE", "MULTIPLE_OF_TEN_BOTH")
TOP = 9999  # the four divide numbers to 4 digits


def table(alt: dict[str, Any]) -> bool:
    """Whether a case is a table's, read backwards."""
    return alt.get("from_table") == "YES" or alt.get("fact") == "YES" or "fact_table" in alt


def _place(alt: dict[str, Any]) -> list[str]:
    """The place-value kinds a case allows, none where it is not about place value."""
    want = alt.get("place_value_factor")
    return [v for v in (*POWERS, *ROUND) if want is not None and taxonomy.holds(want, v)]


def _triples(alt: dict[str, Any], d1s: set[int]) -> Iterator[tuple[int, int, int]]:
    """(divisor, quotient, remainder) for every division the case's kind holds, before its own conditions."""
    if table(alt):
        yield from ((b, q, r) for b in range(1, 13) for q in range(13) for r in range(b) if r == 0 or q <= 9)
    elif _place(alt):
        for v in _place(alt):
            if v in POWERS:
                b = POWERS[v]
                yield from ((b, q, r) for q in range(TOP // b + 1) for r in range(b))
            else:  # a fact's numbers with zeros: the divisor's own (40) when both are round, the quotient's (20)
                js = (1, 2) if v == "MULTIPLE_OF_TEN_BOTH" else (0,)
                yield from (
                    (d * 10**j, f * 10**k, 0)
                    for d in range(2, 10)
                    for j in js
                    for f in range(1, 13)
                    for k in range(4)
                )
    else:
        yield from (
            (b, *divmod(a, b)) for b in range(1, 10) for d in d1s for a in range(10 ** (d - 1), 10**d)
        )


def _rest(r: int, q: int, b: int) -> str:
    """What a remainder is, as a case names it: none, some, the largest there can be, or all of a number too small."""
    return "NONE" if r == 0 else "DIVIDEND_SMALLER" if q == 0 else "LARGEST" if r == b - 1 else "SOME"


@functools.lru_cache(maxsize=512)
def _listed(key: str, pairs: tuple[tuple[int, int], ...]) -> tuple[tuple[int, int], ...]:
    alt: dict[str, Any] = json.loads(key)
    about = taxonomy.keys(alt)
    loose = not table(alt) and not _place(alt)  # worked digit by digit: a remainder or none, unless it says
    want = alt.get("remainder", None if loose else "NONE")
    out: set[tuple[int, int]] = set()
    for b, q, r in _triples(alt, {d for d, _ in pairs}):
        a = q * b + r
        if (
            (len(str(a)), len(str(b))) in pairs
            and (b != 1 or "one_operand" in about)
            and (a != 0 or "zero_operand" in about)
            and (a != b or "equal_operands" in about)
            and (want is None or taxonomy.holds(want, _rest(r, q, b)))
        ):
            out.add((a, b))
    return tuple(sorted(out))


def every(alt: dict[str, Any], pairs: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Every (number divided, divisor) a case can be, its numbers' digits one of `pairs`, in order."""
    return list(_listed(json.dumps(alt, sort_keys=True), tuple(sorted(pairs))))


def numbers(rng: random.Random, alt: dict[str, Any], pairs: list[tuple[int, int]]) -> tuple[int, int] | None:
    """One (number divided, divisor) of the case's, or None when it holds none of these digits."""
    listed = _listed(json.dumps(alt, sort_keys=True), tuple(sorted(pairs)))
    return rng.choice(listed) if listed else None
