"""The wrong answers a multiplication can be given, each worked from the question's own numbers (goals/md2a-straight-
multiplication.yaml). Pure: numbers in, a wrong answer or None out.

A predictor returns the answer a child making that one mistake writes, or None when the mistake cannot happen on these
numbers: no carry to lose, no second row to move — and when another, more particular mistake is the same act on them
(7 × 1 → 8 is × 1 taken as adding one, not adding the numbers), so one wrong answer names one mistake, not two by
construction. A question is worked the longer number by the shorter, whichever is
written first (3 × 21 is 21 × 3 in columns, assumption A10); two numbers of one length are worked as written, the
second the multiplier, as a long multiplication sets them out. The mistakes are the drafted document's error table
(docs/design/multiplication-division-taxonomy.md); the rows they are named in are `supabase/seed/misconceptions.json`.
"""

from collections.abc import Callable

from engine.assess.operations import digits, from_digits, times_columns

Predictor = Callable[[int, int], int | None]


def worked(a: int, b: int) -> tuple[int, int]:
    """(the number multiplied, the multiplier) as a child sets `a × b` out in columns."""
    return (b, a) if len(str(a)) < len(str(b)) else (a, b)


def _by_ten(a: int, m: int) -> bool:
    """× 10, 100 or 1000: a question about placing zeros, never worked in rows (`tens_zero_dropped` names its mistake)."""
    return a in (10, 100, 1000) or m in (10, 100, 1000)


def _wrong(r: int, a: int, m: int) -> int | None:
    return r if r != a * m else None


# ---------------------------------------------------------------------------------------------- by one digit


def no_carry(a: int, m: int) -> int | None:
    """Writes the last digit of each column's product and drops every carry. 34 × 6 → 84 (24 writes 4, 18 writes 8)."""
    if m >= 10:
        return None
    r = _wrong(from_digits([(d * m) % 10 for d in digits(a, len(str(a)))]), a, m) or None  # never a written 0
    return None if r == carry_onto_zero_lost(a, m) else r  # every carry lands on a zero: that mistake's


def concat(a: int, m: int) -> int | None:
    """Writes each digit's whole product side by side. 56 × 3 → 1518."""
    if m >= 10:
        return None
    return _wrong(int("".join(str(int(d) * m) for d in str(a))), a, m)


def carry_first(a: int, m: int) -> int | None:
    """Adds the carry to the next digit and then multiplies, instead of multiplying then adding. 34 × 6 → 304."""
    if m >= 10:
        return None
    out: list[int] = []
    carry = 0
    for d in digits(a, len(str(a))):
        product = (d + carry) * m
        out.append(product % 10)
        carry = product // 10
    while carry:
        out.append(carry % 10)
        carry //= 10
    return _wrong(from_digits(out), a, m)


def ones_only(a: int, m: int) -> int | None:
    """Multiplies the ones digit and stops. 34 × 6 → 24."""
    if m >= 10:
        return None
    return _wrong((a % 10) * m, a, m) or None  # 30 × 6 → 0 is no answer this mistake writes


def row_out(a: int, m: int) -> int | None:
    """One row out in the multiplier's table: 7 × 8 answered as 7 × 7, 34 × 6 as 34 × 5. Only a multiplier with a table
    (to 12) has a row to be out by: 68 × 17 → 1088 is no table's."""
    if m > 12 or (_by_ten(a, m) and max(a, m) > 12):  # 34 × 10 → 306 is no table's slip; 7 × 10 → 63 is
        return None
    r = a * (m - 1)
    return r if r > 0 and r != a * m else None


def added(a: int, m: int) -> int | None:
    """Adds where the question multiplies. 34 × 6 → 40. Not × 0 or × 1, where adding is what `zero_as_one` and
    `one_added` name."""
    if {0, 1} & {a, m}:
        return None
    return _wrong(a + m, a, m)


def units_reversed(a: int, m: int) -> int | None:
    """Writes only the units digit of each digit's product, ones column first. 56 × 3 → 85 (18, 15)."""
    if m >= 10 or a < 10 or a % 10 == 0:  # 7 × 8 → 6 is `no_carry`'s; 20 × 4 → 8 a zero dropped
        return None
    return _wrong(int("".join(str(d * m % 10) for d in digits(a, len(str(a))))), a, m) or None


def carry_onto_zero_lost(a: int, m: int) -> int | None:
    """A carry that lands on a zero digit is forgotten: 0 × 7 is written as 0. 506 × 7 → 3502 (the 4 from 42 lost)."""
    if m >= 10:
        return None
    out: list[int] = []
    carry = 0
    for col in times_columns(a, m):
        value = col["product"] + (carry if col["digit"] else 0)
        out.append(value % 10)
        carry = value // 10
    return _wrong(int(str(carry or "") + "".join(str(d) for d in reversed(out))), a, m)


# ---------------------------------------------------------------------------------------------- by two digits


def placeholder(a: int, m: int) -> int | None:
    """Long multiplication with the second row not moved a place (the zero left out). 68 × 17 → 476 + 68 = 544."""
    if m < 10 or m % 10 == 0 or _by_ten(a, m):  # 23 × 40: its one row is `tens_zero_dropped`'s
        return None
    return _wrong(sum(a * d for d in digits(m, len(str(m)))), a, m)


def one_row(a: int, m: int) -> int | None:
    """Multiplies by the multiplier's ones and stops. 68 × 17 → 476. Not when the ones are 0 (23 × 40): that row is
    nothing to stop at."""
    if m < 10 or m % 10 == 0 or _by_ten(a, m):
        return None
    return _wrong(a * (m % 10), a, m)


def columnwise(a: int, m: int) -> int | None:
    """2 digits by 2: tens by tens and ones by ones, as if adding. 68 × 17 → 6 × 1 = 6, 8 × 7 = 56 → 656."""
    if not (10 <= a < 100 and 10 <= m < 100) or (a % 10 == 0 and m % 10 == 0) or m % 11 == 0 or _by_ten(a, m):
        return None  # 80 × 20 → 160 is a zero dropped; 21 × 22 → 42 one row (a multiplier of one digit twice)
    return _wrong(int("".join(str(int(x) * int(y)) for x, y in zip(str(a), str(m), strict=True))), a, m)


def stale_carry(a: int, m: int) -> int | None:
    """2 digits by 2: the first row's carry is left written above the tens and added again in the second row.
    47 × 23 → 141 + 1140 = 1281 (the second row's tens are 4 × 2 + 1 + the first row's 2 again)."""
    if not (10 <= a < 100 and 10 <= m < 100):
        return None
    (a1, a0), (m1, m0) = divmod(a, 10), divmod(m, 10)
    first_carry, ones = (a0 * m0) // 10, a0 * m1
    second = (a1 * m1 + ones // 10 + first_carry) * 10 + ones % 10
    return _wrong(a * m0 + second * 10, a, m)


# ---------------------------------------------------------------------------------------------- zeros and ones


def _trailing(n: int) -> int:
    return len(str(n)) - len(str(n).rstrip("0")) if n else 0


def tens_zero_dropped(a: int, m: int) -> int | None:
    """One zero fewer than the numbers' own zeros make: 45 × 100 → 450, 23 × 40 → 92. Not when the zeros are the
    product's own (25 × 4 = 100): there is no factor of ten to place."""
    if not (_trailing(a) + _trailing(m)) or not a * m:
        return None
    return _wrong(a * m // 10, a, m)


def zero_as_one(a: int, m: int) -> int | None:
    """× 0 kept as the number: 7 × 0 → 7."""
    if (a == 0) == (m == 0):
        return None
    return _wrong(a or m, a, m)


def one_added(a: int, m: int) -> int | None:
    """× 1 taken as adding one: 7 × 1 → 8."""
    if 1 not in (a, m) or 0 in (a, m):  # 0 × 1 → 1 is × 0 kept
        return None
    return _wrong((m if a == 1 else a) + 1, a, m)


def _as_worked(fn: Predictor) -> Predictor:
    return lambda a, b: fn(*worked(a, b))


# fmt: off
PREDICTORS: dict[str, Predictor] = {
    "M_MUL_NO_CARRY":       _as_worked(no_carry),
    "M_MUL_CONCAT":         _as_worked(concat),
    "M_MUL_CARRY_FIRST":    _as_worked(carry_first),
    "M_MUL_ONES_ONLY":      _as_worked(ones_only),
    "M_MUL_ROW_OUT":        _as_worked(row_out),
    "M_WRONG_OP":           _as_worked(added),
    "M_MUL_UNITS_REVERSED": _as_worked(units_reversed),
    "M_MUL_CARRY_ONTO_ZERO_LOST": _as_worked(carry_onto_zero_lost),
    "M_MUL_PLACEHOLDER":    _as_worked(placeholder),
    "M_MUL_ONE_ROW":        _as_worked(one_row),
    "M_MUL_COLUMNWISE":     _as_worked(columnwise),
    "M_MUL_STALE_CARRY":    _as_worked(stale_carry),
    "M_TENS_ZERO_DROPPED":  _as_worked(tens_zero_dropped),
    "M_ZERO_AS_ONE":        _as_worked(zero_as_one),
    "M_ONE_ADDED":          _as_worked(one_added),
}
# fmt: on
