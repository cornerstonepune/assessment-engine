"""Judging an answer without working it out (taxonomy §8–§9), and breaking a number apart to add it.

- `choose_estimate` — which of three round numbers is closest to a sum or difference;
- `possible_answer` — could this answer be right, judged by its size alone;
- `odd_even` — will the answer be odd or even;
- `break_apart` — add or take the tens, then the ones (347 + 25 → 347 + 20, then + 5).
A product is judged the same three ways (goals/md4b1-estimates.yaml), each built on the two numbers its case draws, as
a division's estimates are (`divide_kinds`): `parity_of_product`, `closest_product`, `possible_product` (`builder`).
Deterministic given an RNG. Every question names a mistake its wrong answer shows, or is drawn again: a ticked
answer's wrong option carries the mistake it shows, and ticking no to a right claim judges a true claim false.
"""

import random
from typing import Any

from . import misconceptions as M
from . import operations as O
from .facts_kinds import Build
from .items import Item, Response, cells, item
from .rounding import half_up

UNFIT = "these numbers do not make this question; draw again"
TRIES = 200  # pairs drawn for one place of the right option, before the question is drawn again
NAMES = ["Aarav", "Riya", "Kabir", "Meera", "Ishaan", "Saee"]


def _sign(op: str) -> str:
    return O.PRINTED.get(op, "+")


def _pair(rng: random.Random, op: str, digits: int) -> tuple[int, int]:
    lo, hi = 10 ** (digits - 1), 10**digits - 1
    a, b = rng.randint(lo, hi), rng.randint(lo, hi)
    if op == "-" and b > a:
        a, b = b, a
    if a == b or a % 10 == 0 or b % 10 == 0:
        raise RuntimeError(UNFIT)
    return a, b


def _up(n: int, to: int) -> int:
    return -(-n // to) * to


def _closest(
    rng: random.Random,
    rung: str,
    signal: str,
    a: int,
    b: int,
    op: str,
    options: list[int],
    named: dict[str, int],
) -> Item:
    """Three round numbers in order, the one nearest the exact answer right; each wrong option a named mistake gives
    carries that mistake, and a question none of whose wrong options is one is drawn again."""
    right = min(options, key=lambda o: abs(o - M.compute(op, a, b)))
    mis = M.named(right, [(code, v) for code, v in named.items() if v in options])
    if not mis:
        raise RuntimeError("no wrong option is a mistake a child makes: draw again")
    rs = [
        Response(
            "pick", "tick", str(right), options=[str(o) for o in options], label="closest", misconceptions=mis
        )
    ]
    spec = dict(a=a, b=b, op=op, options=options, right=options.index(right))
    stem = f"Which is closest to {a} {_sign(op)} {b}? Do not work it out."
    return item("CLOSEST", rung, signal, "choose_estimate", stem, spec, rs, working_lines=0)


def choose_estimate(rng: random.Random, rung: str, signal: str, op: str = "+", digits: int = 3) -> Item:
    """Three hundreds in order, the nearest one right. Where it sits, first, in the middle or last, is drawn first, so
    ticking one place every time scores a third, not everything; an exact answer ending in 50 is equally near two of
    them, a question with two answers, so it is never asked. A wrong option is what rounding done wrong gives: one
    number rounded and the other left, or both rounded up always, or down always; the numbers are drawn until one of
    those shows among the options. Drawn the other way round, numbers first and a place they showed a slip in, a
    subtraction's right option sat in the middle half the time: its slips sit next to the right answer."""
    op = O.require("choose_estimate", op)
    place = rng.choice((0, 1, 2))
    for _ in range(TRIES):
        try:
            a, b = _pair(rng, op, digits)
        except RuntimeError:
            continue
        exact = M.compute(op, a, b)
        near = half_up(exact, 100)
        low = near - 100 * place
        if exact % 100 == 50 or low <= 0:
            continue
        options = [low, low + 100, low + 200]
        named = {
            "M_ROUNDS_ONE_NUMBER": half_up(M.compute(op, half_up(a, 100), b), 100),
            "M_ROUNDS_AWAY_ZERO": M.compute(op, _up(a, 100), _up(b, 100)),
            "M_ROUNDS_TOWARD_ZERO": M.compute(op, a // 100 * 100, b // 100 * 100),
        }
        if any(v in options and v != near for v in named.values()):
            return _closest(rng, rung, signal, a, b, op, options, named)
    raise RuntimeError(UNFIT)


def closest_product(rng: random.Random, a: int, b: int, rung: str, alt: dict[str, Any]) -> Item:
    """52 × 9 is closest to 360, 450 or 540? (V08) The larger number rounded to three tens in a row, each times the
    other, the nearest ten right. A wrong option is what rounding the larger number the wrong way gives, up always (52
    as 60) or down always (58 as 50), and the one it names is always among them: the right option sits first, in the
    middle or last a third of the time each. A number ending in 5 is as near two tens, so it is never asked."""
    big, small = max(a, b), min(a, b)
    ones = big % 10
    if small < 2 or big < 10 or ones in (0, 5):
        raise RuntimeError(UNFIT)
    t = half_up(big, 10) // 10
    down = ones < 5  # rounding down is right, so a child who always rounds up shows the option above it
    place = rng.choice((0, 0, 1) if down else (1, 2, 2))  # each place a third of the time over both halves
    tens = [t - place + k for k in range(3)]
    if tens[0] < 1:
        raise RuntimeError(UNFIT)
    named = (
        {"M_ROUNDS_AWAY_ZERO": (t + 1) * 10 * small}
        if down
        else {"M_ROUNDS_TOWARD_ZERO": (t - 1) * 10 * small}
    )
    return _closest(rng, rung, "Conceptual", a, b, "×", [x * 10 * small for x in tens], named)


def _possible(rng: random.Random, rung: str, signal: str, a: int, b: int, op: str, claimed: int) -> Item:
    """Someone's answer to judge by its size: yes to a wrong one accepts it without checking its size, no to the right
    one judges a true claim false."""
    possible = claimed == M.compute(op, a, b)
    name = rng.choice(NAMES)
    rs = [
        Response(
            "could",
            "tick",
            "yes" if possible else "no",
            options=["yes", "no"],
            label="Could it be right?",
            misconceptions={"M_REVERSES_CLAIM_TRUTH": "no"} if possible else {"M_IGNORES_SIZE": "yes"},
        )
    ]
    spec = dict(a=a, b=b, op=op, claimed=claimed)
    stem = f"{name} says {a} {_sign(op)} {b} = {claimed:,}. Without working it out, could that be right?"
    return item("POSSIBLE", rung, signal, "possible_answer", stem, spec, rs, working_lines=1)


def possible_answer(rng: random.Random, rung: str, signal: str, op: str = "+", digits: int = 3) -> Item:
    """Right or impossible by size: an extra digit, a lost digit, or the true answer."""
    op = O.require("possible_answer", op)
    a, b = _pair(rng, op, digits)
    exact = M.compute(op, a, b)
    # right as often as wrong: drawn evenly from one right kind and two wrong ones, "no" was the answer two times in
    # three, and past `bank.choice_answer_max_share` on some builds (audit: no choice is answered by ticking one place)
    kind = "true" if rng.random() < 0.5 else rng.choice(["extra_digit", "lost_digit"])
    if kind == "true":
        claimed = exact
    elif kind == "extra_digit":
        s = str(exact)
        claimed = int(s[0] + str(rng.randint(0, 9)) + s[1:])
    else:
        claimed = exact // 10 if exact >= 100 else None
    if not claimed or claimed <= 0:
        raise RuntimeError(UNFIT)
    return _possible(rng, rung, signal, a, b, op, claimed)


def possible_product(rng: random.Random, a: int, b: int, rung: str, alt: dict[str, Any]) -> Item:
    """Riya says 23 × 4 = 812; could that be right? (V05) The product, or what a named slip of it gives with another
    number of digits (812 is 23 × 4 with its products written side by side), one as often as the other: a claim the
    right size but wrong is found only by working it out, which the question says not to."""
    exact = a * b
    slips = sorted({v for v in M.predict("×", a, b).values() if v > 0 and len(str(v)) != len(str(exact))})
    if not slips:
        raise RuntimeError("no slip of this product is the wrong size to judge: draw again")
    claimed = exact if rng.random() < 0.5 else rng.choice(slips)
    return _possible(rng, rung, "Conceptual", a, b, "×", claimed)


def _parity(rung: str, signal: str, a: int, b: int, op: str) -> Item:
    answer = "even" if M.compute(op, a, b) % 2 == 0 else "odd"
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
    stem = f"Without working it out, will {a} {_sign(op)} {b} be odd or even?"
    return item("PARITY", rung, signal, "odd_even", stem, spec, rs, working_lines=0)


def odd_even(rng: random.Random, rung: str, signal: str, op: str = "+", digits: int = 3) -> Item:
    op = O.require("odd_even", op)
    a, b = _pair(rng, op, digits)
    return _parity(rung, signal, a, b, op)


def parity_of_product(rng: random.Random, a: int, b: int, rung: str, alt: dict[str, Any]) -> Item:
    """Will 6 × 13 be odd or even? (V06, and F08 on a table fact) Three products in four are even, so a child who always
    ticked even would score three in four: an even product is kept one time in three, and odd and even are asked about
    as often."""
    if a * b % 2 == 0 and rng.random() >= 1 / 3:
        raise RuntimeError("odd about as often as even: draw again")
    return _parity(rung, "Conceptual", a, b, "×")


BUILT: dict[tuple[str, str], Build] = {
    ("odd_even", "MUL"): parity_of_product,
    ("choose_estimate", "MUL"): closest_product,
    ("possible_answer", "MUL"): possible_product,
}


def builder(alt: dict[str, Any], fmt: str) -> Build | None:
    """The kind a × judging case is built as on its own two numbers, or None for one this module does not make."""
    op = alt.get("operation")
    return BUILT.get((fmt, op)) if isinstance(op, str) else None


def break_apart(rng: random.Random, rung: str, signal: str, op: str = "+", digits: int = 3) -> Item:
    """347 + 25: add the tens, then the ones — two boxes, one after the other (§8)."""
    op = O.require("break_apart", op)
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
            cells=cells(max(land, ans)),
            label=f"{a} {_sign(op)} {tens} =",
            misconceptions={"M_FACT_PM10": land + step},
        ),
        Response(
            "ans",
            "digits",
            str(ans),
            cells=cells(max(land, ans)),
            label=f"then {_sign(op)} {ones} =",
            misconceptions=M.predict(op, a, b),
        ),
    ]
    spec = dict(a=a, b=b, op=op, tens=tens, ones=ones)
    stem = f"Work out {a} {_sign(op)} {b} in two steps: the tens first, then the ones."
    return item("BREAK", rung, signal, "break_apart", stem, spec, rs, working_lines=0)
