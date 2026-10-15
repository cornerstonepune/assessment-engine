"""Stories that divide (goals/md3b1-facts-advance.yaml, goals/md3b3-divide-mistakes-and-stories.yaml): exactly (B07: 8
pencils cost ₹48. What does one cost?), or with something left over, used as the story needs — the full boxes (B14, the
remainder dropped), the rickshaws needed (B15, one more for those left), how many are left over (B16), or both (B17).
The words are a template row that says its shape and what it does with the remainder (`word_templates.json`, the file
the school edits); the numbers are the case's own (ADR 0057). Each box names the mistakes a child makes finding it, by
the act that finds it (ADR 0058): the division's own in the quotient's box and the remainder's; for the groups everyone
needs, the remainder not rounded up and each division slip then rounded up as the child would round it.
Deterministic given an RNG; pure: no I/O."""

import dataclasses
import random
from typing import Any

from . import div_mistakes as DM
from . import division as DV
from . import operations as O
from . import own_stories as OS
from . import words as W
from .items import Item, Response, cells, item

NOT_UP = "M_REMAINDER_NOT_ROUNDED_UP"


def _kept(mis: dict[str, int], right: int) -> dict[str, int]:
    return {k: v for k, v in mis.items() if v != right and v >= 0}


def rounded_up(a: int, b: int) -> dict[str, int]:
    """What a child writes for the groups everyone needs (26 children, 4 to a rickshaw: 7): the full groups alone, the
    remainder not rounded up; and each division slip rounded up as the child would round it, one more where the slip
    leaves its own remainder. A slip that rounds to the full groups alone (one group short, 5 r 6, rounded to 6) writes
    what the remainder not rounded up writes on every such story, with no other box to tell them apart, so the 6 names
    the one act alone."""
    q = a // b
    slips = {c: v for c, g in DM.predict(a, b).items() if (v := g[0] + (1 if g[1] else 0)) != q}
    return _kept({NOT_UP: q} | slips, q + 1)


def answered(use: str | None, a: int, b: int) -> tuple[int, int | None]:
    """What a story asks of a ÷ b, as it uses what is left over: the quotient (exact, or the remainder dropped), one more
    group for those left, the remainder alone, or both (the quotient, and the remainder beside it)."""
    q, r = divmod(a, b)
    if use == "BOTH_ASKED":
        return q, r
    if use == "REMAINDER_ASKED":
        return r, None
    return (q + 1 if use == "ROUND_UP" and r else q), None


def boxes(use: str | None, a: int, b: int) -> list[Response]:
    """The answer a story asks (`answered`) in its boxes: the quotient's box alone, one more group for those left, the
    remainder alone in the answer's box, or both, as a division writes them (6 r 2)."""
    ans, _ = answered(use, a, b)
    if use == "BOTH_ASKED":
        return DV.boxes(a, b)
    if use == "REMAINDER_ASKED":
        return [Response("ans", "digits", str(ans), cells=cells(b), misconceptions=DM.in_box(a, b, 1))]
    if use == "ROUND_UP":
        return [
            Response("ans", "digits", str(ans), cells=cells(max(ans, a)), misconceptions=rounded_up(a, b))
        ]
    return [
        Response(
            "ans", "digits", str(ans), cells=cells(max(ans, a)), misconceptions=_kept(DM.in_box(a, b, 0), ans)
        )
    ]


def story(rng: random.Random, a: int, b: int, rung: str, alt: dict[str, Any]) -> Item:
    """A story dividing a by b, its words a template row of its shape and of what it does with what is left over:
    exact where its case says nothing of a remainder, with one where it does; drawn again where the numbers are not."""
    shape, use = alt.get("structure"), alt.get("remainder_use")
    shape, use = (shape if isinstance(shape, str) else None), (use if isinstance(use, str) else None)
    own = OS.pool("word_1step", shape, "÷", False) if use is None else []
    if own:  # a shape whose template says its own numbers (half as many is ÷ 2): drawn on those, not the case's pair
        return OS.make(rng, rung, rng.choice(own))
    pool = [t for t in W.older("word_1step", "÷", shape) if t.get("remainder_use") == use]
    if not pool:
        raise O.CannotMake(f"no one-step story divides for shape {shape!r} using its remainder as {use!r}")
    if b == 0 or bool(a % b) != bool(use):
        raise RuntimeError(
            "the story's division leaves something over where it should not, or nothing: draw again"
        )
    tpl = W.fitting(rng, rng.choice(pool), pool, a=a, b=b)
    n, n2 = rng.sample(W.NAMES, 2)
    rs = [
        dataclasses.replace(r, misconceptions=W.wrong_op_as(tpl, r.misconceptions or {}))
        for r in boxes(use, a, b)
    ]
    stem = tpl["text"].format(a=a, b=b, n=n, n2=n2)
    return item(
        "WP1", rung, "Application", "word_1step", stem, W.story_spec(tpl, a=a, b=b), rs, working_lines=3
    )
