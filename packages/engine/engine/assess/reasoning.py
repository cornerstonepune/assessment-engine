"""Judging an answer without working it out (taxonomy §8–§9), and breaking a number apart to add it.

- `choose_estimate` — which of three round numbers is closest to a sum or difference;
- `possible_answer` — could this answer be right, judged by its size alone;
- `odd_even` — will the answer be odd or even;
- `break_apart` — add or take the tens, then the ones (347 + 25 → 347 + 20, then + 5).
Deterministic given an RNG. A ticked answer's wrong option carries the mistake it shows.
"""

from . import misconceptions as M
from .items import Response, _cells, _item
from .rounding import half_up

MINUS = "−"
UNFIT = "these numbers do not make this question; draw again"


def _sign(op):
    return MINUS if op == "-" else "+"


def _pair(rng, op, digits):
    lo, hi = 10 ** (digits - 1), 10**digits - 1
    a, b = rng.randint(lo, hi), rng.randint(lo, hi)
    if op == "-" and b > a:
        a, b = b, a
    if a == b or a % 10 == 0 or b % 10 == 0:
        raise RuntimeError(UNFIT)
    return a, b


def choose_estimate(rng, rung, signal, op="+", digits=3):
    """Three hundreds in order, the nearest one right. It sits first, in the middle or last in turn, so
    ticking one place every time scores a third, not everything; an exact answer ending in 50 is equally
    near two of them, a question with two answers, so it is never asked."""
    a, b = _pair(rng, op, digits)
    exact = a + b if op == "+" else a - b
    if exact % 100 == 50:
        raise RuntimeError(UNFIT)
    near = half_up(exact, 100)
    one_rounded = half_up(half_up(a, 100) + b if op == "+" else half_up(a, 100) - b, 100)
    low = near - 100 * rng.choice((0, 1, 2))
    options = [low, low + 100, low + 200]
    if low <= 0:
        raise RuntimeError(UNFIT)
    mis = {"M_ROUNDS_ONE_NUMBER": one_rounded} if one_rounded in options and one_rounded != near else {}
    rs = [
        Response(
            "pick", "tick", str(near), options=[str(o) for o in options], label="closest", misconceptions=mis
        )
    ]
    spec = dict(a=a, b=b, op=op, options=options, right=options.index(near))
    return _item(
        "CLOSEST",
        rung,
        signal,
        "choose_estimate",
        f"Which is closest to {a} {_sign(op)} {b}? Do not work it out.",
        spec,
        rs,
        working_lines=0,
    )


def possible_answer(rng, rung, signal, op="+", digits=3):
    """Right or impossible by size: an extra digit, a lost digit, or the true answer."""
    a, b = _pair(rng, op, digits)
    exact = a + b if op == "+" else a - b
    kind = rng.choice(["true", "extra_digit", "lost_digit"])
    if kind == "true":
        claimed = exact
    elif kind == "extra_digit":
        s = str(exact)
        claimed = int(s[0] + str(rng.randint(0, 9)) + s[1:])
    else:
        claimed = exact // 10 if exact >= 100 else None
    if not claimed or claimed <= 0:
        raise RuntimeError(UNFIT)
    possible = claimed == exact
    name = rng.choice(["Aarav", "Riya", "Kabir", "Meera", "Ishaan", "Saee"])
    rs = [
        Response(
            "could",
            "tick",
            "yes" if possible else "no",
            options=["yes", "no"],
            label="Could it be right?",
            misconceptions={"M_IGNORES_SIZE": "yes"} if not possible else {},
        )
    ]
    spec = dict(a=a, b=b, op=op, claimed=claimed)
    stem = f"{name} says {a} {_sign(op)} {b} = {claimed:,}. Without working it out, could that be right?"
    return _item("POSSIBLE", rung, signal, "possible_answer", stem, spec, rs, working_lines=1)


def odd_even(rng, rung, signal, op="+", digits=3):
    a, b = _pair(rng, op, digits)
    exact = a + b if op == "+" else a - b
    answer = "even" if exact % 2 == 0 else "odd"
    rs = [
        Response(
            "parity",
            "tick",
            answer,
            options=["odd", "even"],
            label="odd or even",
            misconceptions={"M_PARITY_RULE": "odd" if answer == "even" else "even"},
        )
    ]
    spec = dict(a=a, b=b, op=op)
    return _item(
        "PARITY",
        rung,
        signal,
        "odd_even",
        f"Without working it out, will {a} {_sign(op)} {b} be odd or even?",
        spec,
        rs,
        working_lines=0,
    )


def break_apart(rng, rung, signal, op="+", digits=3):
    """347 + 25: add the tens, then the ones — two boxes, one after the other (§8)."""
    lo, hi = 10 ** (digits - 1), 10**digits - 1
    a, b = rng.randint(lo, hi), rng.randint(11, 89)
    if b % 10 == 0 or (op == "-" and b >= a):
        raise RuntimeError(UNFIT)
    tens, ones = (b // 10) * 10, b % 10
    land = a + tens if op == "+" else a - tens
    ans = a + b if op == "+" else a - b
    step = 10 if op == "+" else -10
    rs = [
        Response(
            "land1",
            "digits",
            str(land),
            cells=_cells(max(land, ans)),
            label=f"{a} {_sign(op)} {tens} =",
            misconceptions={"M_FACT_PM10": land + step},
        ),
        Response(
            "ans",
            "digits",
            str(ans),
            cells=_cells(max(land, ans)),
            label=f"then {_sign(op)} {ones} =",
            misconceptions=M.predict(op, a, b),
        ),
    ]
    spec = dict(a=a, b=b, op=op, tens=tens, ones=ones)
    stem = f"Work out {a} {_sign(op)} {b} in two steps: the tens first, then the ones."
    return _item("BREAK", rung, signal, "break_apart", stem, spec, rs, working_lines=0)
