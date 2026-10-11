"""Two numbers for a case (`assess/draw.py`): the defaults every question keeps unless its case is about the very thing
they rule out, and a pair drawn inside them — a sum's from its digits, a multiplication's from `draw_times`, a
division's from its listing (`draw_divide`). Deterministic given an RNG.

A written method sets out only the numbers it can (`written.prints`): a multiplication's needs no zero, partitioning a
division needs tens of lots and a rest. A case printed in one draws again where its numbers do not fit."""

import random
from typing import Any

from . import draw_case as K
from . import draw_divide as DD
from . import draw_sums as S
from . import draw_times as T
from . import written as WR

ZERO_KEYS = {"zero_operand", "zeros_in", "zeros_max", "exchange_zeros", "carry_into_zero", "answer_zeros"}
ROUND_KEYS = {"round_operand", "answer_power_of_ten"}
SIZE_KEYS = {"answer_digit_change", "difference_small", "unknown_digits", "equal_operands"}


def sets_out(alt: dict[str, Any], a: int, b: int) -> bool:
    """Whether the written method a case is printed in can set out these numbers; any number, where it names none."""
    method = alt.get("method")
    return not (isinstance(method, str) and method in WR.KINDS) or WR.prints(method, a, b)


def number(rng: random.Random, d: int, zero_ok: bool) -> int:
    return rng.randint(0 if (d == 1 and zero_ok) else (1 if d == 1 else 10 ** (d - 1)), 10**d - 1)


def usable(
    op: str, a: int, b: int, about: set[str], check: dict[str, Any], alt: dict[str, Any] | None = None
) -> bool:
    """The defaults every question keeps unless its case is about the very thing they rule out."""
    zero_case, round_case, size_case = about & ZERO_KEYS, about & ROUND_KEYS, about & SIZE_KEYS
    if not sets_out(alt or {}, a, b):
        return (
            False  # a zero case lifts the rule against a zero, but a written method sets out only what it can
        )
    if op == "×":
        lifts = {name for name, on in (("zero", zero_case), ("round", round_case), ("size", size_case)) if on}
        return T.usable(a, b, about, check, alt or {}, lifts)
    if op == "-" and a < b:
        return False
    if not zero_case and 0 in (a, b):
        return False
    if not (zero_case or round_case) and any(x >= 10 and x % 10 == 0 for x in (a, b)):
        return False
    if a == b and not (size_case or a < 10):
        return False
    if op == "-" and a == b and not size_case:
        return False
    if op == "-" and a >= 10 and a - b < 5 and not size_case:
        return False
    top = a + b if op == "+" else a
    return not (check.get("max_total") and top > check["max_total"])


def pair(
    rng: random.Random,
    alt: dict[str, Any],
    check: dict[str, Any],
    op: str,
    about: set[str],
    fix: tuple[int, int] | None = None,
) -> tuple[int, int] | None:
    """Two numbers for this case, or None. `fix` pins one number's digit count (a missing number)."""
    built = S.built(rng, alt) or T.built(rng, alt)  # numbers some cases construct (`draw_sums`, `draw_times`)
    if built:
        return built
    pairs = [p for p in K.pairs(alt, check, op) if not fix or p[fix[0]] == fix[1]]
    if not pairs:
        return None
    if op == "÷":  # one of the case's own, listed (`draw_divide.every`): its defaults are kept there
        got = DD.numbers(rng, alt, pairs)
        return got if got and sets_out(alt, *got) else None
    d1, d2 = rng.choice(pairs)
    zero_ok = "zero_operand" in about
    if op == "×":
        got = T.numbers(rng, alt, about, d1, d2)
        return got if got and usable(op, *got, about, check, alt) else None
    a, b = number(rng, d1, zero_ok), number(rng, d2, zero_ok)
    shrink = K.pick(rng, alt.get("answer_digit_change"), ["-1", "-MULTIPLE", "ZERO"]) if op == "-" else None
    if shrink and "answer_digit_change" in alt:
        # An answer that loses digits is rare among random pairs (105 − 97): choose the answer, then b.
        size = {"-1": d1 - 1, "-MULTIPLE": rng.randint(1, d1 - 2) if d1 > 2 else 0, "ZERO": 0}[shrink]
        answer = 0 if shrink == "ZERO" else (number(rng, size, False) if size else None)
        if answer is None:
            return None
        if shrink == "ZERO":
            b = a
        else:
            a = answer + b  # the answer and the number taken away first; the top number follows
            if len(str(a)) != d1:
                return None
    return (a, b) if usable(op, a, b, about, check) else None
