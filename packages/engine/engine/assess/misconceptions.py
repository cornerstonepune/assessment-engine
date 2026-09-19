"""Deterministic misconception predictors.

Each predictor takes the operands and returns the wrong answer a child making
that specific mistake would write — or None if the mistake cannot occur on
these operands (e.g. 'forgets to carry' when there is no carry).

Seeded from Neha S's teacher-authored list (Maths planning.docx, Aug 2026) and
the arithmetic itself. Codes are the shared vocabulary for the `misconceptions` tab.
"""


def digits(n, width):
    return [int(c) for c in str(n).zfill(width)][::-1]  # index 0 = ones


def from_digits(ds):
    return int("".join(str(d) for d in ds[::-1])) if ds else 0


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


def mul_no_carry(a, b):
    """Multiplies each digit and writes only the last digit of each product, dropping every carry.
    34 x 6 -> 84 (4x6=24 writes 4, 3x6=18 writes 8)."""
    if b >= 10:
        return None
    r = from_digits([(d * b) % 10 for d in digits(a, len(str(a)))])
    return r if r != a * b else None


def mul_concat(a, b):
    """Writes each digit's whole product side by side. 34 x 6 -> 1824."""
    if b >= 10:
        return None
    ds = digits(a, len(str(a)))[::-1]  # most significant first, as it is written
    r = int("".join(str(d * b) for d in ds))
    return r if r != a * b else None


def mul_carry_added_before_multiplying(a, b):
    """Adds the carry to the next digit and then multiplies it, instead of multiplying then adding.
    34 x 6 -> 304 (4x6=24, write 4 carry 2; then (3+2)x6=30)."""
    if b >= 10:
        return None
    out, carry = [], 0
    for d in digits(a, len(str(a))):
        product = (d + carry) * b
        out.append(product % 10)
        carry = product // 10
    while carry:
        out.append(carry % 10)
        carry //= 10
    r = from_digits(out)
    return r if r != a * b else None


def mul_ones_only(a, b):
    """Multiplies the ones digit and stops. 34 x 6 -> 24."""
    if b >= 10:
        return None
    r = (a % 10) * b
    return r if r != a * b else None


def mul_row_out(a, b):
    """One row out in the table: 34 x 6 answered as 34 x 5."""
    r = a * (b - 1)
    return r if r != a * b and r > 0 else None


def mul_added_instead(a, b):
    """Adds where the question multiplies. 34 x 6 -> 40."""
    r = a + b
    return r if r != a * b else None


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
ADD_PREDICTORS = {
    "M_NOCARRY":       (add_nocarry, "Forgets to carry", "Place-value chart; exchange 10 ones for a ten with rods before recording"),
    "M_CARRY_SKIP":    (add_carry_skips_column, "Carry placed one column too far left", "Column chart with the carry written above the correct column; two worked examples"),
    "M_CONCAT":        (add_concat, "Writes the whole column sum instead of regrouping", "Ten-frame / rods: 'only one digit fits in a column'"),
    "M_DROP_CARRYOUT": (add_drop_carry_out, "Drops the final carry-out (76+54 -> 30)", "Estimate first; 'can the answer be smaller than the bigger number?'"),
    "M_FACT_PM1":      (lambda a, b: off_by(a + b, 1), "Fact off by one", "Number bonds; ten-frame fluency"),
    "M_FACT_PM10":     (lambda a, b: off_by(a + b, 10), "Tens miscounted", "Count in tens on a 100-square"),
    "M_WRONG_OP":      (wrong_operation_sub, "Subtracted instead of adding", "Read the question aloud; identify the operation word"),
    "M_ALIGN_LEFT":    (lambda a, b: align_left("+", a, b), "Aligns unequal-length operands from the left, not the ones", "Place-value columns; write the ones digit first and build leftwards"),
    "M_ZERO_DROPPED":  (lambda a, b: zero_dropped(a + b), "Drops a placeholder zero when writing the answer", "Read the answer aloud in place value: 'one thousand' has three zeros"),
}
SUB_PREDICTORS = {
    "M_SMALL_FROM_LARGE": (sub_smaller_from_larger, "Subtracts the smaller digit from the larger regardless of row ('neeche wala number')", "Rods: show that the top number is the whole; act out the exchange"),
    "M_NO_DECREMENT":     (sub_no_decrement, "Exchanges but does not reduce the lender column", "Cross out and rewrite the lender digit before subtracting"),
    "M_ZERO_LENDER":      (sub_across_zero_lender_not_decremented, "Across zero: zero lends but the column to its left is not reduced", "Three-column rods; exchange a hundred for ten tens first"),
    "M_ZERO_NOT_NINE":    (sub_across_zero_zero_not_reduced, "Across zero: zero becomes 10 and stays 10 (should be 9)", "Number line count-up as a check"),
    "M_FACT_PM1":         (lambda a, b: off_by(a - b, -1), "Fact off by one", "Number bonds; count-up on a number line"),
    "M_FACT_PM10":        (lambda a, b: off_by(a - b, 10), "Tens miscounted", "Count back in tens on a 100-square"),
    "M_WRONG_OP":         (wrong_operation_add, "Added instead of subtracting", "Read the question aloud; identify the operation word"),
    "M_ALIGN_LEFT":       (lambda a, b: align_left("-", a, b), "Aligns unequal-length operands from the left, not the ones", "Place-value columns; write the ones digit first and build leftwards"),
    "M_ZERO_DROPPED":     (lambda a, b: zero_dropped(a - b), "Drops a placeholder zero when writing the answer", "Read the answer aloud in place value; check the column count"),
}

MULTI_PREDICTORS = {
    "M_CARRY_ALWAYS_1": (carry_always_one, "Carries 1 when the column total is 20 or more", "Three-addend columns with rods; count the tens being exchanged, not the act of exchanging"),
    "M_CONCAT":         (multi_concat, "Writes the whole column sum instead of regrouping", "Ten-frame / rods: 'only one digit fits in a column'"),
    "M_ZERO_DROPPED":   (lambda xs: zero_dropped(sum(xs)), "Drops a placeholder zero when writing the answer", "Read the answer aloud in place value before writing it"),
}

def predict_multi(addends):
    """Errors that only become visible with three or more addends, so they need the whole list."""
    correct = sum(addends)
    out = {}
    for code, (fn, _, _) in MULTI_PREDICTORS.items():
        try:
            v = fn(addends)
        except Exception:
            v = None
        if v is not None and v != correct and v >= 0:
            out[code] = v
    return out

MUL_PREDICTORS = {
    "M_MUL_NO_CARRY":    (mul_no_carry, "Multiplies each digit and drops the carry", "Column multiplication with the carry written above; say 'twenty-four is two tens and four ones'"),
    "M_MUL_CONCAT":      (mul_concat, "Writes each digit's whole product side by side", "Grid (area) method first, then the column method beside it"),
    "M_MUL_CARRY_FIRST": (mul_carry_added_before_multiplying, "Adds the carry before multiplying instead of after", "Say the order aloud: multiply, then add what was carried"),
    "M_MUL_ONES_ONLY":   (mul_ones_only, "Multiplies the ones digit and stops", "Grid method: show that both parts of the number are multiplied"),
    "M_MUL_ROW_OUT":     (mul_row_out, "One row out in the times table", "Count on in that table; check against a known fact"),
    "M_WRONG_OP":        (mul_added_instead, "Added instead of multiplying", "Read the question aloud; identify the operation word"),
}

# fmt: on

TABLES = {"+": ADD_PREDICTORS, "-": SUB_PREDICTORS, "×": MUL_PREDICTORS}

# Every code a predictor computes, in one place. A caller that re-types this union is one
# table away from a silent gap — which is how multiplication came to have none.
PREDICTED = {
    code for table in (ADD_PREDICTORS, SUB_PREDICTORS, MUL_PREDICTORS, MULTI_PREDICTORS) for code in table
}


def compute(op, a, b):
    return {"+": a + b, "-": a - b, "×": a * b}[op]


def chain(op, numbers):
    """The answer to a question with however many numbers it has, read left to right: `8000 - 25 - 40`
    is 7935, not 7975. A budget question is a chain, and reading only its first two numbers is how a
    proposal about one came to be thrown away for arithmetic that was never wrong.
    """
    total = numbers[0]
    for n in numbers[1:]:
        total = compute(op, total, n)
    return total


def predict(op, a, b):
    """Return {code: wrong_answer} for every misconception that can occur on these operands.
    An operation with no predictor table yet (multiplication) returns {} — the verifier then
    accepts a model's claims for it unchecked, by design (ADR 0005)."""
    table = TABLES.get(op, {})
    out = {}
    correct = compute(op, a, b)
    for code, (fn, _, _) in table.items():
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


def catalogue():
    rows = []
    for op, table in (("+", ADD_PREDICTORS), ("-", SUB_PREDICTORS), ("+", MULTI_PREDICTORS)):
        for code, (_, name, repair) in table.items():
            if any(r["code"] == code and r["op"] == op for r in rows):
                continue
            rows.append(dict(code=code, op=op, name=name, repair=repair))
    return rows
