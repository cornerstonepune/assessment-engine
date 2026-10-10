"""Two kinds an Advance asks for that only a multiplication has (goals/md2b-times-advance.yaml): a shortcut worked
the way it is named, and a long multiplication's missing row. Deterministic given an RNG.

A level's numbers are its own shape's (`within`): 2 digits by 1 for MUL.2D1D, 2 by 2 for MUL.2D2D. A number is no
table fact and not round, so every question stays inside its level's shape (`fact` NO, `place_value_factor` NONE).
"""

import random
from typing import Any

from . import misconceptions as M
from . import operations as O
from .items import Item, Response, cells, item

STRATEGIES = ("TIMES_TEN_THEN_HALVE", "COMPENSATION")


def digits(check: dict[str, Any]) -> tuple[int, int] | None:
    """The digits of a × level's two numbers, longer first, read from its shape as it says them (2 by 1 as the
    longer and the shorter, 2 by 2 as each number's); None for any other rule."""
    within: dict[str, Any] = check.get("within") or {}
    keys = (
        ("digits_max", "digits_min") if "digits_max" in within else ("operand_1_digits", "operand_2_digits")
    )
    first, second = within.get(keys[0]), within.get(keys[1])
    if check.get("op") != "×" or not isinstance(first, int) or not isinstance(second, int):
        return None
    return max(first, second), min(first, second)


def sizes(check: dict[str, Any]) -> tuple[int, int]:
    """A × level's digits (`digits`), else the two its rule names: an estimate's rule says them itself."""
    found = digits(check)
    if found:
        return found
    named: list[int] = check["digits"]
    return int(named[0]), int(named[1])


def number(rng: random.Random, d: int) -> int:
    """A `d`-digit number a level of no table facts and nothing round can use: 2 to 9, or 13 and up, never x0."""
    if d == 1:
        return rng.randint(2, 9)
    while True:
        n = rng.randint(10 ** (d - 1), 10**d - 1)
        if n > 12 and n % 10:
            return n


def shortcut(rng: random.Random, rung: str, signal: str, strategy: str, sizes: tuple[int, int]) -> Item:
    """× 5 as × 10 then halved (46 × 5: 460, then 230), or a number near a round one (19 × 6: 20 × 6, then one
    group of 6 fewer). The step is asked, then the answer."""
    if strategy == "TIMES_TEN_THEN_HALVE":
        if sizes[0] < 2:
            raise O.CannotMake(
                "× 5 as × 10 then halved needs a number of 2 digits or more: 1 digit × 5 is a table fact"
            )
        a, b = number(rng, sizes[0]), 5
        step, said = a * 10, f"{a} × 10"
        stem = f"Work out {a} × 5. First work out {a} × 10, then halve it."
    elif strategy == "COMPENSATION":
        if sizes[0] != 2:
            raise O.CannotMake(
                "a number near a round one is a 2-digit number one from a ten (19, 41): no other size"
            )
        a, b = rng.choice([n for n in range(13, 100) if n % 10 in (1, 9)]), number(rng, sizes[1])
        r = (a + 5) // 10 * 10
        step, said = r * b, f"{r} × {b}"
        stem = f"Work out {a} × {b}. Start from {r} × {b}, then put it right."
    else:
        raise ValueError(f"{strategy} is no multiplication shortcut: {', '.join(STRATEGIES)}")
    rs = [
        Response("step", "digits", str(step), cells=cells(step), label=f"{said} ="),
        Response(
            "ans",
            "digits",
            str(a * b),
            cells=cells(step),
            label=f"{a} × {b} =",
            misconceptions=M.predict("×", a, b),
        ),
    ]
    spec = {"a": a, "b": b, "op": "×", "strategy": strategy}
    return item("EFFICIENT", rung, signal, "efficient_method", stem, spec, rs, working_lines=2)


def missing_row(rng: random.Random, rung: str) -> Item:
    """34 × 26 = 204 + □: the box is the second row, 34 × 20. A child who does not move the row a place writes 68
    (M_MUL_PLACEHOLDER)."""
    a, b = number(rng, 2), number(rng, 2)
    ones, tens = a * (b % 10), a * (b // 10) * 10
    text = f"{a} × {b} = {ones} + □"
    spec = {"a": a, "b": b, "op": "×", "text": text, "shape": "MISSING_ROW", "missing": "row"}
    r = Response(
        "ans", "digits", str(tens), cells=cells(tens), misconceptions={"M_MUL_PLACEHOLDER": tens // 10}
    )
    return item(
        "MISSING.ROW",
        rung,
        "Conceptual",
        "missing_number",
        "Write the missing row.",
        spec,
        [r],
        working_lines=2,
    )
