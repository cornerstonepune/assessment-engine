"""Estimate first, then work it out (§9): both numbers rounded to the nearest `round_to`, the estimate within a
tolerance of that, the exact answer marked with every mistake the numbers can show — and, on a judged level, whether
someone's answer is close to the estimate.

A multiplication (goals/md2b-times-advance.yaml) asks one of four judgements before the exact product, each its
`shape`: the larger number rounded to the ten (48 × 6 ≈ 50 × 6), both rounded (38 × 21 ≈ 40 × 20), how many digits
the product has, the digit it ends in. The question says how to round, so the estimate is the one its rounding
gives, not one within a tolerance."""

import random
from typing import Any

from . import misconceptions as M
from . import operations as O
from .items import Item, Response, cells, item, sample_add, sample_sub
from .rounding import half_up
from .times_kinds import number

NAMES = ["Zoya", "Aarav", "Meera", "Kabir", "Riya", "Dev"]


# a multiplication's judgement: (what it is, the stem's request, the judged value from a and b)
TIMES = {
    "ROUND_ONE": ("estimate", "Round {big} to the nearest ten and estimate {a} × {b}"),
    "ROUND_BOTH": ("estimate", "Round both numbers to the nearest ten and estimate {a} × {b}"),
    "ANSWER_DIGITS": ("how many digits", "Without working it out, say how many digits {a} × {b} has"),
    "LAST_DIGIT": ("the last digit", "Without working it out, say the digit {a} × {b} ends in"),
}


def _judged(shape: str, a: int, b: int) -> tuple[int, int, int]:
    """(the judgement, the first number as rounded, the second as rounded) for one × shape."""
    big = max(a, b)
    if shape == "ROUND_ONE":
        ra, rb = (half_up(a, 10), b) if a == big else (a, half_up(b, 10))
        return ra * rb, ra, rb
    if shape == "ROUND_BOTH":
        return half_up(a, 10) * half_up(b, 10), half_up(a, 10), half_up(b, 10)
    return (len(str(a * b)) if shape == "ANSWER_DIGITS" else a * b % 10), a, b


def rounded(spec: dict[str, Any]) -> tuple[int, int]:
    """The two numbers a printed estimate shows, as its question rounds them: both to the nearest `round_to`, or what
    a × estimate's `shape` rounds (the larger number, both, or neither where it asks the digits). The one rule
    `verify.key_problems` holds a stored estimate to."""
    if O.sign(spec.get("op")) == "×" and spec.get("shape") in TIMES:
        _, ra, rb = _judged(spec["shape"], spec["a"], spec["b"])
        return ra, rb
    to = spec.get("round_to", 10)
    return half_up(spec["a"], to), half_up(spec["b"], to)


def times(rng: random.Random, rung: str, signal: str, shape: str, sizes: tuple[int, int]) -> Item:
    """One × estimate of this `shape`, its numbers `sizes` digits long."""
    if shape not in TIMES:
        raise ValueError(f"{shape!r} is no multiplication estimate: {', '.join(TIMES)}")
    if min(sizes) < 2 and shape == "ROUND_BOTH" or max(sizes) < 2 and shape == "ROUND_ONE":
        raise O.CannotMake(f"{shape} rounds a 1-digit number to the nearest ten, which makes it 0 or 10")
    a, b = number(rng, sizes[0]), number(rng, sizes[1])
    est, ra, rb = _judged(shape, a, b)
    what, ask = TIMES[shape]
    rs = [
        Response("est", "digits", str(est), cells=cells(max(est, 9)), label=what),
        Response(
            "ans",
            "digits",
            str(a * b),
            cells=cells(a * b),
            misconceptions=M.predict("×", a, b),
            label="exact",
        ),
    ]
    spec = dict(a=a, b=b, op="×", ra=ra, rb=rb, shape=shape)
    stem = ask.format(a=a, b=b, big=max(a, b)) + ". Then work it out."
    return item(
        "ESTIMATE", rung, signal, "estimate_then_calc", stem, spec, rs, scaffolded=True, working_lines=2
    )


def estimate_then_calc(
    rng: random.Random,
    rung: str,
    signal: str,
    op: str,
    digits_a: int,
    digits_b: int,
    regroups: Any,
    round_to: int = 10,
    judged: bool = False,
    tolerance: int | None = None,
    shape: str | None = None,
) -> Item:
    """Estimate by rounding both numbers to the nearest `round_to`, then work it out (§9). `judged` adds
    the question the taxonomy asks next: is the exact answer close to the estimate? A × estimate is one of
    `TIMES`, named by its `shape`."""
    op = O.require("estimate_then_calc", op, makes=("+", "-", "×"))
    if op == "×":
        return times(rng, rung, signal, shape or "ROUND_ONE", (digits_a, digits_b))
    if op == "+":
        a, b = sample_add(rng, digits_a, digits_b, regroups)
    else:
        a, b = sample_sub(rng, digits_a, digits_b, regroups)
    ra, rb = half_up(a, round_to), half_up(b, round_to)
    est = ra + rb if op == "+" else ra - rb
    ans = a + b if op == "+" else a - b
    rs = [
        Response(
            "est",
            "digits",
            str(est),
            cells=cells(max(est, ans)),
            tolerance=tolerance or round_to,
            label="estimate",
        ),
        Response(
            "ans",
            "digits",
            str(ans),
            cells=cells(max(est, ans)),
            misconceptions=M.predict(op, a, b),
            label="exact",
        ),
    ]
    spec = dict(a=a, b=b, op=op, ra=ra, rb=rb)
    if round_to != 10:
        spec["round_to"] = round_to
    if judged:
        # Someone else's answer to judge against the estimate: the right one, or what a named mistake gives when
        # that lands outside the tolerance. Asked of the child's own answer it was "yes" for every child who
        # worked it out — ticked, not judged (audit: no choice is answered by ticking one place).
        tol = tolerance or round_to
        far = sorted({v for v in rs[1].misconceptions.values() if isinstance(v, int) and abs(v - est) > tol})
        shown = rng.choice(far) if far and rng.random() < 0.5 else ans
        close = abs(shown - est) <= tol
        name = rng.choice(NAMES)
        spec |= {"shape": "JUDGED", "shown": shown, "name": name}
        rs.append(
            Response(
                "sense",
                "tick",
                "yes" if close else "no",
                options=["yes", "no"],
                label=f"{name} got {shown}. Is that close to your estimate?",
                misconceptions={"M_COMPARE_ESTIMATE_EXACT": "no" if close else "yes"},
            )
        )
    return item(
        "ESTIMATE",
        rung,
        signal,
        "estimate_then_calc",
        f"Estimate first, then work out {a} {op} {b}.",
        spec,
        rs,
        scaffolded=True,
        working_lines=2,
    )
