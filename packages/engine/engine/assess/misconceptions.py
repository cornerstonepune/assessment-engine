"""Deterministic misconception predictors.

Each predictor takes the operands and returns the wrong answer a child making
that specific mistake would write — or None if the mistake cannot occur on
these operands (e.g. 'forgets to carry' when there is no carry).

Seeded from Neha S's teacher-authored list (Maths planning.docx, Aug 2026) and
the arithmetic itself. Codes are the shared vocabulary for the `misconceptions` tab.
"""

from collections.abc import Callable
from typing import Any

from engine.assess import div_mistakes as DM  # division's own, a quotient and a remainder (goals/md3a-…)
from engine.assess.mul_mistakes import PREDICTORS as MUL_PREDICTORS  # multiplication's own (goals/md2a-…)
from engine.assess.operations import compute, digits, from_digits, sign  # what an operation is has one owner


def add_nocarry(a, b):
    """Writes each column sum mod 10 and never carries. 47+38 -> 75."""
    w = max(len(str(a)), len(str(b)))
    da, db = digits(a, w), digits(b, w)
    out = [(x + y) % 10 for x, y in zip(da, db)]
    r = from_digits(out)
    return r if r != a + b else None


def add_carry_skips_column(a, b):
    """Carry is added two columns left instead of one. 47+38 -> 175."""
    w = max(len(str(a)), len(str(b)))
    da, db = digits(a, w), digits(b, w)
    cols = [x + y for x, y in zip(da, db)]
    out, carries = [], {}
    for i, s in enumerate(cols):
        s += carries.get(i, 0)
        out.append(s % 10)
        if s >= 10:
            carries[i + 2] = carries.get(i + 2, 0) + s // 10
    i = len(out)
    while i in carries or any(k >= i for k in carries):
        s = carries.get(i, 0)
        out.append(s % 10)
        if s >= 10:
            carries[i + 2] = carries.get(i + 2, 0) + s // 10
        i += 1
        if i > w + 3:
            break
    r = from_digits(out)
    return r if r != a + b else None


def add_concat(a, b):
    """Writes the full column sums side by side. 47+38 -> 715."""
    w = max(len(str(a)), len(str(b)))
    da, db = digits(a, w), digits(b, w)
    cols = [x + y for x, y in zip(da, db)]
    if all(c < 10 for c in cols):
        return None
    r = int("".join(str(c) for c in cols[::-1]))
    return r if r != a + b else None


def add_drop_carry_out(a, b):
    """Drops the final carry-out. 76+54 -> 30."""
    w = max(len(str(a)), len(str(b)))
    r = (a + b) % (10**w)
    return r if r != a + b else None


def off_by(n, delta):
    return n + delta


def sub_smaller_from_larger(a, b):
    """Subtracts the smaller digit from the larger in every column, whatever the row. 62-27 -> 45."""
    w = max(len(str(a)), len(str(b)))
    da, db = digits(a, w), digits(b, w)
    out = [abs(x - y) for x, y in zip(da, db)]
    r = from_digits(out)
    return r if r != a - b else None


def sub_no_decrement(a, b):
    """Exchanges (adds 10 to the column) but never reduces the lender column. 62-27 -> 45."""
    w = max(len(str(a)), len(str(b)))
    da, db = digits(a, w), digits(b, w)
    out = []
    for x, y in zip(da, db):
        if x < y:
            x += 10
        out.append(x - y)
    r = from_digits(out)
    return r if r != a - b and r >= 0 else None


def sub_across_zero_lender_not_decremented(a, b):
    """Borrowing across a zero: the zero becomes 10 and lends 1 (-> 9) but the column
    left of the zero is never decremented. 302-178 -> 224."""
    w = max(len(str(a)), len(str(b)))
    da, db = digits(a, w), digits(b, w)
    if 0 not in da[1:]:
        return None
    da = da[:]
    out = []
    for i in range(w):
        if da[i] < db[i]:
            j = i + 1
            while j < w and da[j] == 0:
                da[j] = 9
                j += 1
            # correct algorithm decrements da[j]; this misconception does not when a zero was crossed
            crossed_zero = j > i + 1
            if j < w and not crossed_zero:
                da[j] -= 1
            da[i] += 10
        out.append(da[i] - db[i])
    r = from_digits(out)
    return r if r != a - b and r >= 0 else None


def sub_exchange_from_wrong_column(a, b):
    """The ones need an exchange and the ten is taken from the hundreds, the tens left as they were:
    the top number becomes a − 100 + 10 and the rest is done right, so the answer is 90 short
    (taxonomy §11, "borrow from wrong place"). Only where there is a hundreds digit to take from."""
    w = len(str(a))
    da, db = digits(a, w), digits(b, w)
    if w < 3 or da[0] >= db[0] or da[2] == 0:
        return None
    wrong = a - b - 90
    return wrong if wrong >= 0 else None


def sub_across_zero_zero_not_reduced(a, b):
    """Borrowing across a zero: takes from the left column correctly but leaves the zero
    as 10 instead of 9. 302-178 -> 134."""
    w = max(len(str(a)), len(str(b)))
    da, db = digits(a, w), digits(b, w)
    if 0 not in da[1:]:
        return None
    da = da[:]
    out = []
    for i in range(w):
        if da[i] < db[i]:
            j = i + 1
            while j < w and da[j] == 0:
                da[j] = 10
                j += 1
            if j < w:
                da[j] -= 1
            da[i] += 10
        out.append(da[i] - db[i])
    r = from_digits(out)
    return r if r != a - b and r >= 0 else None


def wrong_operation_add(a, b):
    return a + b


def wrong_operation_sub(a, b):
    return abs(a - b)


def align_left(op, a, b):
    """Unequal lengths aligned from the left instead of the ones column.

    342 + 5 written with the 5 under the 3 is read by the child as 342 + 500 -> 842.
    Only possible when the operands differ in length, which is why the blueprints have
    to generate that case at all. Returns None when both operands are the same length.
    """
    d1, d2 = len(str(a)), len(str(b))
    if d1 == d2:
        return None
    shifted = b * 10 ** (d1 - d2) if d1 > d2 else b
    if d1 < d2:  # a is the shorter one; it slides left instead
        a, shifted = a * 10 ** (d2 - d1), b
    r = a + shifted if op == "+" else a - shifted
    correct = (a + b) if op == "+" else (a - b)
    return r if r != correct and r >= 0 else None


def zero_dropped(result):
    """A placeholder zero is left out when the answer is written. 495 + 505 -> 100, not 1000.

    The leading digit is never the one dropped, so the scan starts at index 1.
    """
    s = str(result)
    for i, ch in enumerate(s):
        if ch == "0" and i > 0:
            out = s[:i] + s[i + 1 :]
            return int(out) if out else None
    return None


def carry_always_one(addends):
    """Three or more addends can make a column total of 20 or more, and the carry is then 2.

    A child who has only ever seen a carry of 1 writes the right ones digit and carries 1
    regardless. Two-operand columns can never exceed 19, so this error is invisible until
    a sheet asks for three addends — which is the whole reason R12 exists.
    """
    w = max(len(str(x)) for x in addends)
    digs = [digits(x, w) for x in addends]
    out, carry = [], 0
    for i in range(w):
        s = sum(d[i] for d in digs) + carry
        out.append(s % 10)
        carry = 1 if s >= 10 else 0  # the mistake: always 1, never s // 10
    while carry:
        out.append(carry % 10)
        carry //= 10
    r = from_digits(out)
    return r if r != sum(addends) else None


def digit_dropped(right, wrote):
    """A digit lost while copying out a long answer: 62413 written as 6243. Read off the right answer
    rather than the operands, because any one of its digits can be the one that goes."""
    r, w = str(right), str(wrote)
    # ponytail: four digits or more — under that a missing digit is as likely another mistake
    return len(r) >= 4 and len(w) == len(r) - 1 and any(r[:i] + r[i + 1 :] == w for i in range(len(r)))


def multi_concat(addends):
    """Writes each column's whole total side by side, with three or more addends. 4321+2456+3212
    -> columns 9, 9, 11, 9 written out as 99119.

    `add_concat` is the two-operand version of the same mistake; with several addends the column
    totals are larger and the wrong answer is a different number, so the pair predictor cannot
    stand in for it. Without this, a multi-addend band could name the mistake in its spec and have
    nothing able to mark it — which is how a spec comes to claim more than the engine can do.
    """
    w = max(len(str(x)) for x in addends)
    digs = [digits(x, w) for x in addends]
    cols = [sum(d[i] for d in digs) for i in range(w)]
    if all(c < 10 for c in cols):
        return None
    r = int("".join(str(c) for c in cols[::-1]))
    return r if r != sum(addends) else None


# fmt: off
# Each mistake by how it is made, one to a line: what it is called and what the school does about it are its row, the
# words the school edits (`supabase/seed/misconceptions.json`, rule 1), never a copy here (goals/md3b3-…).
ADD_PREDICTORS = {
    "M_NOCARRY":       add_nocarry,
    "M_CARRY_SKIP":    add_carry_skips_column,
    "M_CONCAT":        add_concat,
    "M_DROP_CARRYOUT": add_drop_carry_out,
    "M_FACT_PM1":      lambda a, b: off_by(a + b, 1),
    "M_FACT_PM10":     lambda a, b: off_by(a + b, 10),
    "M_WRONG_OP":      wrong_operation_sub,
    "M_ALIGN_LEFT":    lambda a, b: align_left("+", a, b),
    "M_ZERO_DROPPED":  lambda a, b: zero_dropped(a + b),
}
SUB_PREDICTORS = {
    "M_SMALL_FROM_LARGE": sub_smaller_from_larger,
    "M_NO_DECREMENT":     sub_no_decrement,
    "M_ZERO_LENDER":      sub_across_zero_lender_not_decremented,
    "M_ZERO_NOT_NINE":    sub_across_zero_zero_not_reduced,
    "M_EXCHANGE_WRONG_PLACE": sub_exchange_from_wrong_column,
    "M_FACT_PM1":         lambda a, b: off_by(a - b, -1),
    "M_FACT_PM10":        lambda a, b: off_by(a - b, 10),
    "M_WRONG_OP":         wrong_operation_add,
    "M_ALIGN_LEFT":       lambda a, b: align_left("-", a, b),
    "M_ZERO_DROPPED":     lambda a, b: zero_dropped(a - b),
}

MULTI_PREDICTORS = {
    "M_CARRY_ALWAYS_1": carry_always_one,
    "M_CONCAT":         multi_concat,
    "M_ZERO_DROPPED":   lambda xs: zero_dropped(sum(xs)),
}

# fmt: on


def predict_multi(addends):
    """Errors that only become visible with three or more addends, so they need the whole list."""
    correct = sum(addends)
    out = {}
    for code, fn in MULTI_PREDICTORS.items():
        try:
            v = fn(addends)
        except Exception:
            v = None
        if v is not None and v != correct and v >= 0:
            out[code] = v
    return out


# A comparison asks for a sign, not a number, so its one predictable mistake is the other sign.
COMPARE_PREDICTORS = {
    "M_COMPARE_REVERSED": lambda sign: {"<": ">", ">": "<"}.get(sign),
}

# A mistake read off the right answer itself, not off the operands: several numbers can show it, so
# it is a rule the marker applies when no predicted wrong answer matched, never a number on an item.
ANSWER_RULES = {
    "M_DIGIT_DROPPED": digit_dropped,
}

# fmt: on

# the predictors by code, for each operation that has a table
TABLES: dict[str, dict[str, Callable[..., int | None]]] = {
    "+": ADD_PREDICTORS,
    "-": SUB_PREDICTORS,
    "×": MUL_PREDICTORS,
}

# Every code a predictor computes, in one place. A caller that re-types this union is one
# table away from a silent gap — which is how multiplication came to have none.
PREDICTED = {
    code
    for table in (
        ADD_PREDICTORS,
        SUB_PREDICTORS,
        MUL_PREDICTORS,
        DM.PREDICTORS,
        MULTI_PREDICTORS,
        COMPARE_PREDICTORS,
        ANSWER_RULES,
    )
    for code in table
}


def predict_sign(answer):
    """{code: wrong sign} for a question whose answer is a comparison sign; {} for anything else."""
    out = {}
    for code, fn in COMPARE_PREDICTORS.items():
        v = fn(str(answer).strip())
        if v:
            out[code] = v
    return out


def named(right: int, predicted: list[tuple[str, int]]) -> dict[str, Any]:
    """{mistake: the answer it gives}, in the order given (the likelier first), leaving out one whose answer is the right one or another's:
    a wrong answer two mistakes give names neither for certain."""
    out: dict[str, Any] = {}
    for code, wrong in predicted:
        if wrong != right and wrong not in out.values():
            out[code] = wrong
    return out


def predict(op: str, a: int, b: int) -> dict[str, int]:
    """Return {code: wrong_answer} for every misconception that can occur on these operands. A division has one
    answer only when it is exact: its quotient's box (`div_mistakes.in_box`); one with a remainder has two, and none
    here (`division.boxes` keys both)."""
    if (sign(op) or op) == "÷":
        return DM.in_box(a, b, 0) if b > 0 and a >= 0 and not a % b else {}
    table = TABLES.get(sign(op) or op)
    if not table:
        return {}
    out: dict[str, int] = {}
    correct = compute(op, a, b)
    for code, fn in table.items():
        try:
            v = fn(a, b)
        except Exception:
            v = None
        if v is not None and v != correct and v >= 0:
            out[code] = v
    return out


def applicable(pairs):
    """Every known misconception that can actually occur on these (op, a, b) triples.

    This is the deterministic half of a skill set's mistake list: given the numbers a band allows,
    code — not a model — says which named wrong methods are reachable in it. A band with no exchange
    cannot produce an exchange mistake, and this is where that is decided by running the predictors
    rather than by anyone remembering it.
    """
    out = set()
    for op, a, b in pairs:
        out |= set(predict(op, a, b))
    return sorted(out)
