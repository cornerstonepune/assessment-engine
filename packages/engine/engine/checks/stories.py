"""The two-step stories with × and ÷ worked out from their own numbers and their shape (goals/md4d1-times-stories.yaml),
a second time and apart from the template rows that wrote them: a scenario holds a story's answer to this, not to the
formula its template carries. A one-step story is its sum's (`scenarios._sum_is_right`)."""

from collections.abc import Callable
from typing import Any


def _exact(top: int, by: int) -> int | None:
    return top // by if by and top % by == 0 else None


# what each shape asks, from the numbers its story prints
TWO_STEP: dict[str, Callable[[dict[str, Any]], int | None]] = {
    "MULTIPLY_THEN_ADD": lambda s: s["a"] * s["b"] + s["c"],  # 3 boxes of 12 pencils and 5 loose
    "MULTIPLY_THEN_SUBTRACT": lambda s: s["a"] - s["b"] * s["c"],  # ₹100, 4 pens at ₹15
    "DIVIDE_THEN_MULTIPLY": lambda s: (q * s["c"]) if (q := _exact(s["b"], s["a"])) is not None else None,
    "TWO_PRODUCTS_ADDED": lambda s: s["a"] * s["b"] + s["c"] * s["d"],  # 4 packets of 6 and 3 of 8
    "ADD_THEN_DIVIDE": lambda s: _exact(s["a"] + s["b"], s["c"]),  # 18 red and 14 blue shared by 4
    "BAR_MODEL_TIMES_AS_MANY": lambda s: _exact(s["a"], s["b"] + 1),  # 32 in all, one has 3 times the other
}


def checks(fmt: str, spec: dict[str, Any], stated: dict[str, str]) -> list[bool]:
    """[whether a two-step story's answer is the one its numbers make] for a shape here; [] for any other question."""
    if fmt != "word_2step" or spec.get("structure") not in TWO_STEP:
        return []
    want = TWO_STEP[spec["structure"]](spec)
    return [want is not None and stated.get("ans") == str(want)]
