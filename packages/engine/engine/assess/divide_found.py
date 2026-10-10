"""Finding the mistake in a division (goals/md3b3-divide-mistakes-and-stories.yaml): a worked answer with one named
mistake made on its case's own two numbers (ADR 0057) — the zero left out of the quotient (C04: 612 ÷ 6 = 12), a
remainder too big (C05: 85 ÷ 4 = 20 r 5), the last digit never brought down (C07: 516 ÷ 4 = 12 r 3). The child writes
the right answer in the division's own boxes, keyed as a straight division's are (`division.boxes`), and says why, which
a person reads against the mistake's own row (`diagnosis.why`). No step is ticked: for the last digit missed its answer
would always be "bring down", which a child ticking the same box every time would score (`diagnosis.asks_where`'s
rule), so the step is said in the why. Measured over every division each level holds (STATE.md "M3b3 — measured
before the build"). Deterministic given an RNG; pure: no I/O."""

import random
from typing import Any

from . import diagnosis as D
from . import div_mistakes as DM
from . import division as DV
from .items import Item, item


def shown(got: DM.Answer) -> str:
    """A worked answer as a child writes it: 20 r 5, or 12 with nothing left over."""
    q, r = got
    return f"{q} r {r}" if r else str(q)


def found(rng: random.Random, a: int, b: int, rung: str, alt: dict[str, Any]) -> Item:
    """a ÷ b worked with its case's planted mistake, then the right answer and why; drawn again where the mistake
    changes nothing on these numbers."""
    code = alt.get("planted")
    made = DM.PREDICTORS.get(code) if isinstance(code, str) else None
    if made is None:
        raise ValueError(f"{code!r} is not a mistake a worked division shows")
    wrote = made(a, b)
    if wrote is None or not DM.wrong(a, b, wrote):
        raise RuntimeError("the mistake changes nothing on these numbers: draw again")
    stem = f"{rng.choice(D.NAMES)} worked out {a} ÷ {b} and wrote {shown(wrote)}. That is not right."
    spec: dict[str, Any] = dict(a=a, b=b, op="÷", wrong=shown(wrote), planted=code)
    return item(
        "FTM", rung, "Conceptual", "find_mistake", stem, spec, [*DV.boxes(a, b), D.why()], working_lines=2
    )
