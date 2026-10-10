"""What a division a child works can be worked wrong as (goals/md3a-straight-division.yaml), each from the question's
own numbers, as `mul_mistakes.py` does for a column multiplication: the fourteen the drafted document names for a
calculation (docs/design/multiplication-division-taxonomy.md), and × in place of ÷.

A wrong answer is a quotient and a remainder. A mistake that is the quotient's alone leaves the right remainder; one
that leaves no remainder to write says None. Each is predicted only where it can be made and changes the answer, and
not where another, more particular mistake is the same act on these numbers (17 ÷ 5 → 1 r 2 is the 1 skipped, not an
exchange lost): one wrong answer names one mistake where two would be the same act, and every mistake it matches where
two meet by chance, as marking names every match (`mul_mistakes.py`, second reader 2026-10-09). Pure: no I/O."""

from collections.abc import Callable

Answer = tuple[int, int | None]


def _digits(n: int) -> list[int]:
    return [int(x) for x in str(n)]


def _carried(a: int, b: int) -> list[int]:
    """Short division from the left: the remainder each digit passes to the next, the last digit's left out."""
    out: list[int] = []
    r = 0
    for x in _digits(a):
        r = (r * 10 + x) % b
        out.append(r)
    return out[:-1]


def _zeros(n: int) -> int:
    return len(str(n)) - len(str(n).rstrip("0")) if n else 0


def zero_dropped(a: int, b: int) -> Answer | None:
    """804 ÷ 4 written 21: the zero left out of the quotient."""
    q = a // b
    return (int(str(q).replace("0", "") or 0), a % b) if q >= 10 and "0" in str(q) else None


def exchange_lost(a: int, b: int) -> Answer | None:
    """72 ÷ 4 written 10: each digit divided alone, the remainder never exchanged into the next. Where the only exchange
    is a first digit smaller than the divisor, losing it is skipping that digit (`lead_dropped`)."""
    if b >= 10 or len(str(a)) < 2 or not any(_carried(a, b)):
        return None
    if _digits(a)[0] < b and not any(_carried(int(str(a)[1:]), b)):
        return None
    return int("".join(str(x // b) for x in _digits(a))), _digits(a)[-1] % b


def remainder_added(a: int, b: int) -> Answer | None:
    """72 ÷ 4 written 11 r 1: the remainder added to the next digit (3 + 2), where it makes tens of it (30 + 2)."""
    if b >= 10 or len(str(a)) < 2 or not any(_carried(a, b)):
        return None
    q, r = "", 0
    for x in _digits(a):
        q, r = q + str((r + x) // b), (r + x) % b
    return int(q), r


def lead_dropped(a: int, b: int) -> Answer | None:
    """156 ÷ 4 written 14: a first digit smaller than the divisor skipped, and the rest divided."""
    if b >= 10 or len(str(a)) < 2 or _digits(a)[0] >= b:
        return None
    return divmod(int(str(a)[1:]), b)


def bring_down_missed(a: int, b: int) -> Answer | None:
    """516 ÷ 4 written 12 r 3: stopped before the last digit was brought down. Where an exact quotient's only zero is its
    last digit, stopping there is leaving that zero out (`zero_dropped`: 840 ÷ 4 written 21)."""
    q = a // b
    if b >= 10 or len(str(a)) < 2 or q < 10 or (a % b == 0 and q % 10 == 0 and "0" not in str(q // 10)):
        return None
    return divmod(a // 10, b)


def remainder_too_big(a: int, b: int) -> Answer | None:
    """85 ÷ 4 written 20 r 5: one group short, the remainder not less than the divisor."""
    q, r = divmod(a, b)
    return (q - 1, r + b) if r and q else None


def remainder_as_digit(a: int, b: int) -> Answer | None:
    """85 ÷ 4 written 211: the remainder written as the quotient's next digit."""
    q, r = divmod(a, b)
    return (int(f"{q}{r}"), None) if r else None


def swapped(a: int, b: int) -> Answer | None:
    """17 ÷ 5 written 2 r 3: the quotient and the remainder the wrong way round."""
    q, r = divmod(a, b)
    return (r, q) if r else None


def bigger_by_smaller(a: int, b: int) -> Answer | None:
    """3 ÷ 5 written 1 r 2: the bigger number divided by the smaller, whichever comes first."""
    return divmod(b, a) if 0 < a < b else None


def self_as_zero(a: int, b: int) -> Answer | None:
    """7 ÷ 7 written 0: a number divided by itself read as nothing left."""
    return (0, None) if a == b > 0 else None


def zero_divided(a: int, b: int) -> Answer | None:
    """0 ÷ 5 written 5: the divisor answered when zero is divided."""
    return (b, None) if a == 0 < b else None


def tens_zero_left(a: int, b: int) -> Answer | None:
    """4500 ÷ 100 written 450: one zero fewer taken away."""
    return (a // b * 10, None) if b in (10, 100, 1000) and a % b == 0 else None


def tens_zero_extra(a: int, b: int) -> Answer | None:
    """200 ÷ 4 written 500: the fact borrows one of the zeros (20 ÷ 4 = 5), then every zero is written back."""
    k = _zeros(a)
    if b >= 10 or not k or a % b or a // 10**k >= b:
        return None
    return a // 10**k * 10 // b * 10**k, None


def multiplied(a: int, b: int) -> Answer | None:
    """84 ÷ 4 written 336: × in place of ÷."""
    return (a * b, None) if b > 1 else None


def subtracted(a: int, b: int) -> Answer | None:
    """84 ÷ 4 written 80: the divisor taken away once. A number taken from itself is ÷ itself read as nothing left."""
    return (a - b, None) if 0 < b < a else None


PREDICTORS: dict[str, Callable[[int, int], Answer | None]] = {
    "M_DIV_QUOTIENT_ZERO_DROPPED": zero_dropped,
    "M_DIV_EXCHANGE_LOST": exchange_lost,
    "M_DIV_REMAINDER_ADDED": remainder_added,
    "M_DIV_LEAD_DROPPED": lead_dropped,
    "M_DIV_BRING_DOWN_MISSED": bring_down_missed,
    "M_DIV_REMAINDER_TOO_BIG": remainder_too_big,
    "M_DIV_REMAINDER_AS_DIGIT": remainder_as_digit,
    "M_DIV_SWAPPED": swapped,
    "M_DIV_BIGGER_BY_SMALLER": bigger_by_smaller,
    "M_DIV_SELF_AS_ZERO": self_as_zero,
    "M_DIV_ZERO_DIVIDED": zero_divided,
    "M_DIV_TENS_ZERO_LEFT": tens_zero_left,
    "M_DIV_TENS_ZERO_EXTRA": tens_zero_extra,
    "M_WRONG_OP": multiplied,
    "M_DIV_SUBTRACTED": subtracted,
}


def wrong(a: int, b: int, got: Answer) -> bool:
    """Whether `got` is a wrong answer to a ÷ b: its quotient differs, or a remainder it writes does."""
    q, r = divmod(a, b)
    return got[0] != q or (got[1] is not None and got[1] != r)


def in_box(a: int, b: int, box: int) -> dict[str, int]:
    """{mistake: what it writes in the quotient's box (0) or the remainder's (1)} wherever that is not the box's key.
    A box is marked by itself, so a value two mistakes write there names both (17 ÷ 5's quotient written 2 is the two
    swapped or one group short), and the other box tells them apart."""
    right = divmod(a, b)[box]
    return {code: v for code, got in predict(a, b).items() if (v := got[box]) is not None and v != right}


def predict(a: int, b: int) -> dict[str, Answer]:
    """{mistake: (quotient, remainder or None)} for a ÷ b, every one that can be made and changes the answer."""
    if b <= 0 or a < 0:
        return {}
    return {
        code: got
        for code, f in PREDICTORS.items()
        if (got := f(a, b)) is not None and got[0] >= 0 and wrong(a, b, got)
    }
