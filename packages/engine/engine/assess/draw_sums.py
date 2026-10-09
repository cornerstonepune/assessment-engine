"""An addition's or a subtraction's numbers where its case is a construction, not a digit pattern. Deterministic given
an RNG; `assess/draw.py` asks it first, as it asks `assess/draw_times.py` for a multiplication's."""

import random
from typing import Any, cast


def built(rng: random.Random, alt: dict[str, Any]) -> tuple[int, int] | None:
    """The three cases whose numbers are a construction: add or take 10, 100 or 1000 (347 + 100); make 100 or 1000
    (68 + 32); count on across a hundred (503 − 498). None for every other case."""
    if alt.get("round_operand") == "POWER_OF_TEN":
        b = rng.choice([10, 100, 1000])
        a = rng.randint(b + 11, 9999 if b == 1000 else 999)
        return a, b
    if "answer_power_of_ten" in alt:
        raw: Any = alt["answer_power_of_ten"]  # one total, or several to choose from
        total = rng.choice(cast(list[int], raw) if isinstance(raw, list) else [int(raw)])
        a = rng.randint(total // 10 + 1, total - total // 10 - 1)
        return a, total - a
    if alt.get("difference_small") == "YES":
        hundred = rng.randint(1, 9) * 100
        a = hundred + rng.randint(1, 9)
        return a, hundred - rng.randint(1, 9)
    return None
