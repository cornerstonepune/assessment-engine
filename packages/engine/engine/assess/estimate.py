"""Estimate first, then work it out (§9): both numbers rounded to the nearest `round_to`, the estimate within a
tolerance of that, the exact answer marked with every mistake the numbers can show — and, on a judged level, whether
someone's answer is close to the estimate."""

from . import misconceptions as M
from . import operations as O
from .items import Response, cells, item, sample_add, sample_sub
from .rounding import half_up

NAMES = ["Zoya", "Aarav", "Meera", "Kabir", "Riya", "Dev"]


def estimate_then_calc(
    rng, rung, signal, op, digits_a, digits_b, regroups, round_to=10, judged=False, tolerance=None
):
    """Estimate by rounding both numbers to the nearest `round_to`, then work it out (§9). `judged` adds
    the question the taxonomy asks next: is the exact answer close to the estimate?"""
    op = O.require("estimate_then_calc", op)
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
