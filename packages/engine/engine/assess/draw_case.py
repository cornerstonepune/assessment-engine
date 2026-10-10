"""What a taxonomy case allows a drawing (`assess/draw.py`): the kinds it names, the operation an attempt draws, the
digits of its two numbers, one value of a condition, and the written methods its level prints it in. Deterministic
given an RNG; the case rule is read through `assess/taxonomy.py`, so drawing for a case and measuring a question
against it read one rule alike."""

import random
from collections.abc import Iterable
from typing import Any, cast

from . import taxonomy

DIGITS = range(1, 5)
OPS = {"ADD": "+", "SUB": "-", "MUL": "×", "DIV": "÷"}
LAYOUT = {
    "LINE": "HORIZONTAL",
    "COLUMNS": "VERTICAL",
    "LONG_MULTIPLICATION": "VERTICAL",
    "EXPANDED": "VERTICAL",
    "SHORT_DIVISION": "VERTICAL",
    "LONG_DIVISION": "VERTICAL",
}  # a method, as printed: a division's in the division layout


def alternatives(match: Any) -> list[dict[str, Any]]:
    """A case's match: one set of conditions, or a list any one of which may hold."""
    return cast(list[dict[str, Any]], match) if isinstance(match, list) else [match]


def fmts(alt: dict[str, Any]) -> list[Any]:
    """The kinds of question one set of conditions names."""
    f = alt.get("fmt")
    return cast(list[Any], f) if isinstance(f, list) else [f]


def pick(rng: random.Random, want: Any, pool: Iterable[Any]) -> Any:
    """One value of `pool` a case condition allows, or None when none does."""
    ok = [v for v in pool if want is None or taxonomy.holds(want, v)]
    return rng.choice(ok) if ok else None


def op(rng: random.Random, alt: dict[str, Any], check: dict[str, Any]) -> str | None:
    """The operation this attempt draws: one the case allows, or None when it allows neither of ours."""
    if alt.get("operation"):
        picked = pick(rng, alt["operation"], list(OPS))
        return OPS[picked] if picked else None
    ops: Any = check.get("op", ["+", "-"])
    return rng.choice(cast(list[str], ops)) if isinstance(ops, list) else ops


def pairs(alt: dict[str, Any], check: dict[str, Any], op: str) -> list[tuple[int, int]]:
    """The (digits of the first number, digits of the second) a case and its level both allow."""
    level = check.get("digits")
    allowed = {tuple(p) for p in (level if isinstance(level[0], list) else [level])} if level else None
    out: list[tuple[int, int]] = []
    for d1 in DIGITS:
        for d2 in DIGITS:
            if (op == "-" and d2 > d1) or (allowed and (d1, d2) not in allowed):
                continue
            measured = {
                "operand_1_digits": d1,
                "operand_2_digits": d2,
                "digits_max": max(d1, d2),
                "digits_min": min(d1, d2),
            }
            if all(taxonomy.holds(alt[k], v) for k, v in measured.items() if k in alt):
                out.append((d1, d2))
    return out


def _first(alt: dict[str, Any]) -> bool:
    """The case writes the 1-digit number first (3 × 21)."""
    one, two = alt.get("operand_1_digits"), alt.get("operand_2_digits")
    return alt.get("operand_order") == "SHORTER_FIRST" or (
        isinstance(one, int) and isinstance(two, int) and one < two
    )


def _crossed(case: dict[str, Any], method: dict[str, Any]) -> dict[str, Any] | None:
    """A case's numbers printed in one method, or None when they cannot be: the method contradicts the case, or sets
    the longer number on top (in columns) where the case writes the 1-digit number first."""
    try:
        both = cast(dict[str, Any], taxonomy.within(case, method))
    except ValueError:
        return None
    return None if _first(both) and LAYOUT.get(both.get("method") or "") == "VERTICAL" else both


def ways(match: Any, methods: list[Any]) -> list[Any]:
    """A case on its level, once for each written method the level prints it in (`methods`, assumption A1), in the
    level's order: each a match the drawing fills in its share. A level that lists no method draws the case as it is."""
    out: list[Any] = []
    for method in methods:
        crossed = [x for a in alternatives(match) for b in alternatives(method) if (x := _crossed(a, b))]
        if crossed:
            out.append(crossed if len(crossed) > 1 else crossed[0])
    return out or [match]
