"""What a taxonomy case allows a drawing (`assess/draw.py`): the kinds it names, the operation an attempt draws, the
digits of its two numbers, one value of a condition. Deterministic given an RNG; the case rule is read through
`assess/taxonomy.py`, so drawing for a case and measuring a question against it read one rule alike."""

import random
from collections.abc import Iterable
from typing import Any, cast

from . import taxonomy

DIGITS = range(1, 5)
OPS = {"ADD": "+", "SUB": "-", "MUL": "×"}


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
