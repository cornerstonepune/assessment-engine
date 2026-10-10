"""The column skills' Advance kinds, ÷ (goals/md3b2-divide-advance.yaml): a digit missing in the number divided or in the
quotient, the remainder missing, how many digits a quotient has, the number divided rounded, whether an answer could
be right, a division checked by multiplying, and ÷ 5 as ÷ 10 then doubled. Each is built on the two numbers its case
draws (`draw._pair`, ADR 0057), and each box is keyed by the act that finds it (ADR 0058): a digit in the number divided
by the multiplication that finds it, a remainder by the taking away, a digit in the quotient by the division's own
mistakes whose quotient fits the printed boxes. Measured over every question a level can hold (STATE.md "M3b2 —
measured before the build"). Deterministic given an RNG; pure: no I/O.

A box worked in another operation from its question's names no "wrong operation" (M_WRONG_OP), whose name is the
question's (`core/mistake_names.py`, ADR 0057)."""

import dataclasses
import random
from collections.abc import Callable
from typing import Any, cast

from . import div_mistakes as DM
from . import division as D
from . import estimate as E
from . import misconceptions as M
from . import operations as O
from . import words as W
from .items import Item, Response, cells, item

Build = Callable[[random.Random, int, int, str, dict[str, Any]], Item]


def _at(n: int, place: int) -> int | None:
    """`n`'s digit `place` from the ones (0 is the ones); None past its lead."""
    s = str(n)
    return int(s[-1 - place]) if place < len(s) else None


def _other_op(predicted: dict[str, Any]) -> dict[str, int]:
    """Whole-number predictions of a box worked in the other operation, its "wrong operation" left out (ADR 0057)."""
    return {k: v for k, v in predicted.items() if k != "M_WRONG_OP" and isinstance(v, int) and v >= 0}


def divided_digit_mistakes(a: int, b: int, place: int) -> dict[str, int]:
    """What a child writes in the box hiding digit `place` (0 the ones) of a number divided exactly, a = q × b (7□ ÷ 4 =
    18): the multiplication that finds it worked wrong, its digit at that place copied (18 × 4 with the carry left out
    is 42: 4 in a tens box); and each division mistake that, made with another digit there, gives the quotient shown.
    Measured: every 2-digit question names one, and all but 2.4% of 3-digit ones."""
    q, right = a // b, _at(a, place)
    out: dict[str, int] = {}
    for code, p in _other_op(M.predict("×", q, b)).items():
        d = _at(p, place)
        if d is not None and d != right:
            out.setdefault(code, d)
    lead = place == len(str(a)) - 1
    for d in range(10):
        if d == right or (lead and d == 0) or right is None:
            continue
        for code, (q2, r2) in DM.predict(a + (d - right) * 10**place, b).items():
            if q2 == q and not r2:
                out.setdefault(code, d)
    return out


def quotient_digit_mistakes(a: int, b: int, pos: int) -> dict[str, int]:
    """What a child writes in the box hiding the quotient's digit `pos` (from its lead, 936 ÷ 3 = 3□2): each division
    mistake whose quotient is as long as the printed one, its digit there. A wrong quotient of another length does not
    fit the printed boxes and says nothing about this one (measured: 11% of questions name none)."""
    q = str(a // b)
    out: dict[str, int] = {}
    for code, (q2, _r) in DM.predict(a, b).items():
        w = str(q2)
        if len(w) == len(q) and w[pos] != q[pos]:
            out.setdefault(code, int(w[pos]))
    return out


def remainder_mistakes(a: int, b: int) -> dict[str, int]:
    """What a child writes in the remainder's box of a ÷ b = q r □ (85 ÷ 4 = 21 r □). No division mistake keeps the
    printed quotient (measured: 556 of 556), so it is keyed by the taking away that finds it, a − q × b: that
    subtraction's mistakes, and the multiplication's with its product taken away rightly; and one group short leaves
    the division's own remainder too big (r + b)."""
    q, r = O.divide(a, b)
    out: dict[str, int] = {}
    for code, v in _other_op(M.predict("-", a, q * b)).items():
        if v != r:
            out.setdefault(code, v)
    for code, p in _other_op(M.predict("×", q, b)).items():
        if 0 <= a - p != r:
            out.setdefault(code, a - p)
    out.setdefault("M_DIV_REMAINDER_TOO_BIG", r + b)
    return out


def digit(rng: random.Random, a: int, b: int, rung: str, alt: dict[str, Any]) -> Item:
    """7□ ÷ 4 = 18 (Q09) or 936 ÷ 3 = 3□2 (Q10): one digit missing in the number divided or in the quotient of an exact
    division, as the case says, keyed by the act that finds it; a draw whose box names no mistake is drawn again."""
    named = alt.get("missing_in")
    where = rng.choice(cast(list[str], named)) if isinstance(named, list) else named
    if where not in ("FIRST", "RESULT"):
        raise O.CannotMake(
            f"a division's missing digit is in the number divided or the quotient, not {where!r}"
        )
    if not b or a % b:
        raise RuntimeError("a missing digit here is in an exact division: draw again")
    q = a // b
    s = str(a) if where == "FIRST" else str(q)
    pos = rng.randrange(len(s))
    if where == "FIRST":
        mis = divided_digit_mistakes(a, b, len(s) - 1 - pos)
    else:
        mis = quotient_digit_mistakes(a, b, pos)
    if not mis:
        raise RuntimeError("no mistake writes a digit in this box: draw again")
    masked = s[:pos] + "□" + s[pos + 1 :]
    shown_a, shown_q = (masked, str(q)) if where == "FIRST" else (str(a), masked)
    text = f"{shown_a} ÷ {b} = {shown_q}"
    spec = {"a": shown_a, "b": str(b), "c": shown_q, "op": "÷", "solved": {"a": a, "b": b}, "text": text}
    r = Response("d1", "digits", s[pos], cells=1, label="box 1", misconceptions=mis)
    stem = f"{text}. Write the missing digit."
    return item("MISSING.DIGIT", rung, "Conceptual", "missing_digit", stem, spec, [r], working_lines=2)


def estimate(rng: random.Random, a: int, b: int, rung: str, alt: dict[str, Any]) -> Item:
    """How many digits 156 ÷ 4's quotient has (V04), or 412 ÷ 8 with the number divided rounded to the nearest hundred
    (V10, asked only where the divisor divides that hundred: 400 ÷ 8 = 50); then the quotient and any remainder, keyed
    as the division asked the usual way (`division.boxes`)."""
    shape = alt.get("shape")
    est, ra = E.divided(shape if isinstance(shape, str) else "", a, b)
    what = "how many digits" if shape == "ANSWER_DIGITS" else "estimate"
    ask = (
        f"Without working it out, say how many digits {a} ÷ {b} has"
        if shape == "ANSWER_DIGITS"
        else f"Round {a} to the nearest hundred and estimate {a} ÷ {b}"
    )
    rs = [Response("est", "digits", str(est), cells=cells(max(est, 9)), label=what), *D.boxes(a, b)]
    spec = dict(a=a, b=b, op="÷", ra=ra, rb=b, shape=shape)
    return item(
        "ESTIMATE",
        rung,
        "Conceptual",
        "estimate_then_calc",
        f"{ask}. Then work it out.",
        spec,
        rs,
        scaffolded=True,
        working_lines=2,
    )


def could_be(rng: random.Random, a: int, b: int, rung: str, alt: dict[str, Any]) -> Item:
    """85 ÷ 4 = 20 r 5: could it be right? (V09) A claim with a remainder, the right one or one group short, its
    remainder not less than the divisor, one as often as the other. A yes to the remainder too big is that mistake; a
    no to the right answer reverses its truth."""
    q, r = O.divide(a, b)
    if not r or q < 2:
        raise RuntimeError(
            "the remainder is what is judged, against a quotient of a group or more: draw again"
        )
    right = rng.random() < 0.5
    claimed = f"{q} r {r}" if right else f"{q - 1} r {r + b}"
    tick = Response(
        "could",
        "tick",
        "yes" if right else "no",
        options=["yes", "no"],
        label="Could it be right?",
        misconceptions={"M_REVERSES_CLAIM_TRUTH": "no"} if right else {"M_DIV_REMAINDER_TOO_BIG": "yes"},
    )
    stem = f"{rng.choice(W.NAMES)} says {a} ÷ {b} = {claimed}. Without working it out, could that be right?"
    spec = dict(a=a, b=b, op="÷", claimed=claimed)
    return item("POSSIBLE", rung, "Conceptual", "possible_answer", stem, spec, [tick], working_lines=1)


def _layout_slips(a: int, b: int) -> list[tuple[int, int]]:
    """What the division layout's own named mistakes write for a ÷ b, each (quotient, remainder): its digits divided
    alone, a remainder added, the last digit not brought down. ÷ read as − or × is no slip of the layout."""
    return sorted(
        {
            (g[0], g[1] or 0)
            for c, g in DM.predict(a, b).items()
            if c.startswith("M_DIV_") and c != "M_DIV_SUBTRACTED"
        }
    )


def checked(rng: random.Random, a: int, b: int, rung: str, alt: dict[str, Any]) -> Item:
    """96 ÷ 4 = 24? Check it by multiplying: 24 × 4 = □ (Y10). The claim is right, or what a named mistake of the
    division layout writes, its remainder with it (96 ÷ 4 = 21 r 2), one as often as the other. The check multiplies
    the claim back and adds its remainder, its box keyed by the multiplication's mistakes (ADR 0057)."""
    if not b or a % b:
        raise RuntimeError("a claimed answer is checked here against an exact division: draw again")
    slips = _layout_slips(a, b)
    right = rng.random() < 0.5
    if not right and not slips:
        raise RuntimeError("no slip of the layout to claim: draw again")
    cq, cr = (a // b, 0) if right else rng.choice(slips)
    claimed = f"{cq} r {cr}" if cr else str(cq)
    check = f"{cq} × {b} + {cr} = □" if cr else f"{cq} × {b} = □"
    value = cq * b + cr
    rs = [
        Response(
            "check",
            "digits",
            str(value),
            cells=cells(max(value, a)),
            label=check,
            misconceptions={c: p + cr for c, p in _other_op(M.predict("×", cq, b)).items() if p != cq * b},
        ),
        Response(
            "right",
            "tick",
            "yes" if right else "no",
            options=["yes", "no"],
            label="Is the answer right?",
            misconceptions={"M_REVERSES_CLAIM_TRUTH": "no" if right else "yes"},
        ),
    ]
    shown = f"{a} ÷ {b} = {claimed}"
    spec = dict(a=a, b=b, op="÷", claimed=claimed, shown=shown, check=check, ops=["÷", "×"])
    return item(
        "CHECK",
        rung,
        "Conceptual",
        "inverse_check",
        f"Check {shown} by multiplying.",
        spec,
        rs,
        working_lines=2,
    )


def ten_then_doubled(rng: random.Random, a: int, b: int, rung: str, alt: dict[str, Any]) -> Item:
    """240 ÷ 5 as 240 ÷ 10 = 24, then doubled: 48 (H09). The number divided is the case's own with its ones made 0, a
    3-digit number whose tens are no multiple of 5 (250 ÷ 5 is a fact under its zero, `DIV.TENS`'s); the divisor 5.
    The step names one zero fewer taken away among its division's slips; the answer what 240 ÷ 5 asked the usual way
    names."""
    t = a // 10
    if not 10 <= t <= 99 or t % 5 == 0:
        raise RuntimeError("no 3-digit number of tens without a fact under its zero: draw again")
    n = t * 10
    step = Response(
        "step", "digits", str(t), cells=cells(n), label=f"{n} ÷ 10 =", misconceptions=DM.in_box(n, 10, 0)
    )
    ans = dataclasses.replace(D.boxes(n, 5)[0], label=f"{n} ÷ 5 =")
    spec = {"a": n, "b": 5, "op": "÷", "strategy": "DIVIDE_BY_TEN_THEN_DOUBLE"}
    stem = f"Work out {n} ÷ 5. First work out {n} ÷ 10, then double it."
    return item("EFFICIENT", rung, "Conceptual", "efficient_method", stem, spec, [step, ans], working_lines=2)


BUILT: dict[tuple[str, str, str | None], Build] = {
    ("missing_digit", "DIV", None): digit,
    ("estimate_then_calc", "DIV", "ANSWER_DIGITS"): estimate,
    ("estimate_then_calc", "DIV", "ROUND_ONE"): estimate,
    ("possible_answer", "DIV", None): could_be,
    ("inverse_check", "DIV", None): checked,
    ("efficient_method", "DIV", "DIVIDE_BY_TEN_THEN_DOUBLE"): ten_then_doubled,
}


def builder(alt: dict[str, Any], fmt: str) -> Build | None:
    """The kind a ÷ case is built as on its own two numbers, or None for one this module does not make."""
    op = alt.get("operation")
    if op != "DIV":
        return None
    what = next((alt[k] for k in ("shape", "strategy") if isinstance(alt.get(k), str)), None)
    return BUILT.get((fmt, op, what)) or BUILT.get((fmt, op, None))
