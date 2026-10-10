"""A case's question when it is no straight calculation and no missing number: its kind's own generator
(`bands.NATIVE_GENERATORS`), told what the case is about — a story's shape, a planted mistake, the method it is printed
by — through the same rule keys a level can set, and the numbers' size the case and its level allow. Deterministic given
an RNG; `assess/draw.py` asks it for every such kind."""

import random
from typing import Any, cast

from . import bands
from . import draw_case as K
from . import items as I
from . import operations as O

HINTS = (
    "structure",
    "shape",
    "planted",
    "round_to",
    "missing_count",
    "missing_in",
    "missing_place",
    "strategy",
    "method",
)


def _one_value(rng: random.Random, v: Any) -> Any:
    """A hint the generator can use: one of a list, or a number inside a range (two or more boxes)."""
    if isinstance(v, list):
        return rng.choice(cast(list[Any], v))
    if isinstance(v, dict):
        r = cast(dict[str, int], v)
        return rng.randint(r.get("gte", 1), r.get("lte", r.get("gte", 1) + 1))
    return v


def native(
    rng: random.Random, alt: dict[str, Any], check: dict[str, Any], rung: str, k: int
) -> I.Item | None:
    fmt = rng.choice([f for f in K.fmts(alt) if bands.makes(f, alt)] or K.fmts(alt))
    hints: dict[str, Any] = {key: _one_value(rng, v) for key in HINTS if (v := alt.get(key)) is not None}
    if alt.get("context") == "TABLE_OR_CHART":
        hints["table"] = True
    if alt.get("operation"):
        hints["op"] = K.op(rng, alt, check)
        if hints["op"] is None:
            return None  # the case allows neither operation this drawer writes
    # The numbers' size, from the case as its level narrowed it (`within`), where the level's rule does not
    # already say: a story or a number line left to its generator's own default wrote 2-digit numbers on a
    # 1-digit level, and every one was refused by the case it was drawn for.
    if "digits" not in check and any(
        k in alt for k in ("operand_1_digits", "operand_2_digits", "digits_max")
    ):
        pairs = K.pairs(alt, check, hints.get("op") or "+")
        if not pairs:
            return None
        d1, d2 = rng.choice(pairs)
        hints["digits"] = [d1, d2]
        if "hi" not in check:
            hints["hi"] = 10**d1 - 1 + (10**d2 - 1 if hints.get("op", "+") == "+" else 0)
    try:
        return bands.native_item(fmt, {**check, **hints}, rng, rung, "Conceptual")
    except O.CannotMake:
        raise  # the case asks this kind for an operation it does not make: no draw can give it, say so
    except RuntimeError:
        return None  # numbers that did not fit, drawn again; a rule the kind cannot read is raised, not drawn past
