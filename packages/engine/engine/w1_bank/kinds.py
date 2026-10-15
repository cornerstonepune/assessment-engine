"""The kinds of question a level draws, read from their rows (`question_format`, ADR 0075) for the card engine
(`assess/cards.py`), which reads no database. A level's rule names its kinds (`check["cards"]`); `resolve` hands the
drawer the rule with the rows themselves in `check["kinds"]`, never stored."""

import random
from typing import Any

from engine.assess import cards


def of(conn) -> dict[str, dict[str, Any]]:
    """{code: kind} for every kind in the database."""
    return {r["code"]: r["kind"] for r in conn.execute("select code, kind from question_format").fetchall()}


def resolve(conn, check: dict[str, Any], held: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """A card level's rule with its kinds' rows (`check["kinds"]`); any other rule as it is. A kind the rule names
    that no row holds is refused: the level would print fewer kinds than it says."""
    if check.get("format") != "card":
        return check
    held = of(conn) if held is None else held
    missing = [c for c in check["cards"] if c not in held]
    if missing:
        raise ValueError(f"the level names kinds no row holds: {', '.join(missing)}")
    return {**check, "kinds": [held[c] for c in check["cards"]]}


def can_make(check: dict[str, Any]) -> int:
    """How many different questions a resolved card level can make: each of its kinds' count, added."""
    return sum(cards.count(k, check) for k in check["kinds"])


def listed(check: dict[str, Any], rng: random.Random, rung: str) -> list[Any]:
    """Every question a resolved card level can make, each kind's, in a random order."""
    out = [it for k in check["kinds"] for it in cards.every(k, check, rung, "Conceptual")]
    rng.shuffle(out)
    return out
