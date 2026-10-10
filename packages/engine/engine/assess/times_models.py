"""Multiplication as the models a child meets first, beyond equal groups and the number line's equal jumps
(goals/md2d1-multiplication-models.yaml): counting on in equal steps, and a cell of the multiplication square. Pure,
no I/O.

Each draws its numbers from its level's rule — `groups` (how many steps, or which rows), `size` (which columns),
`known` (the tables the level counts as known) — computes the answer, and names the mistake behind each wrong answer
it predicts. `pictures` draws each from the same numbers, so what the child sees and the key cannot part.
"""

from random import Random
from typing import Any

from engine.assess import misconceptions as M
from engine.assess.counting import named
from engine.assess.items import Item, Response, cells, item

UNFIT = "these numbers do not make this question; draw again"


def _span(rule: dict[str, Any], key: str, lo: int, hi: int) -> tuple[int, int]:
    """A level's [lo, hi] for one of its numbers, or the kind's own when the level names none."""
    got: list[int] = rule.get(key) or [lo, hi]
    return int(got[0]), int(got[-1])


def skip_counting(rng: Random, rung: str, signal: str, rule: dict[str, Any]) -> Item:
    """5, 10, 15, 20, □: the next number, counting on in equal steps from the step itself. The step is one of the
    tables the level counts as known (`known`); the count is `groups` long, three at least, so that two printed steps
    show the step. The answer is a × b: `a` steps of `b`. Writing the last printed number again is one group fewer."""
    known: list[int] = rule.get("known") or []
    if not known:
        raise ValueError(
            "skip counting counts in the tables its level counts as known; the level names none (`known`)"
        )
    lo, hi = _span(rule, "groups", 3, 10)
    if hi < 3:
        raise ValueError(
            f"skip counting needs three steps or more, so two show the step; the level allows {hi}"
        )
    a, b = rng.randint(max(lo, 3), hi), int(rng.choice(known))
    r = Response(
        "ans",
        "digits",
        str(a * b),
        cells=cells(a * b),
        misconceptions=named(a * b, [("M_GROUP_MISSED", (a - 1) * b)]),
    )
    spec = {"a": a, "b": b, "op": "×", "method": "SKIP_COUNTING"}
    return item(
        "SKIP",
        rung,
        signal,
        "skip_counting",
        "Count on in equal steps. Write the next number.",
        spec,
        [r],
        working_lines=0,
    )


def _window(rng: Random, at: int, top: int) -> list[int]:
    """Three neighbouring rows (or columns) of the square holding `at`, none past the square's last, `top`."""
    first = rng.randint(max(1, at - 2), max(1, min(at, top - 2)))
    return [first, first + 1, first + 2]


def multiplication_square(rng: Random, rung: str, signal: str, rule: dict[str, Any]) -> Item:
    """A cell of the multiplication square found from its row and its column: three rows and three columns of the
    square around it, headed, every other cell printed, so the child reads across and down or counts on from a
    neighbour. Row `a` (`groups`), column `b` (`size`); the answer is a × b, and the next row of the table, the
    numbers added and the rest of a fact's mistakes are named as for any fact (`misconceptions.predict`). A window in
    which another cell holds the answer is drawn again: the answer is never printed."""
    (alo, ahi), (blo, bhi) = _span(rule, "groups", 2, 10), _span(rule, "size", 2, 10)
    a, b = rng.randint(alo, ahi), rng.randint(blo, bhi)
    rows, cols = _window(rng, a, ahi), _window(rng, b, bhi)
    if any(r * c == a * b for r in rows for c in cols if (r, c) != (a, b)):
        raise RuntimeError(UNFIT)
    r = Response("ans", "digits", str(a * b), cells=cells(a * b), misconceptions=M.predict("×", a, b))
    spec = {"a": a, "b": b, "op": "×", "rows": rows, "cols": cols}
    stem = "Write the missing number in the multiplication square."
    return item("SQUARE", rung, signal, "multiplication_square", stem, spec, [r], working_lines=0)
