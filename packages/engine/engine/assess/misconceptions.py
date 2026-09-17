"""Deterministic misconception predictors.

Each predictor takes the operands and returns the wrong answer a child making
that specific mistake would write — or None if the mistake cannot occur on
these operands (e.g. 'forgets to carry' when there is no carry).

Seeded from Neha S's teacher-authored list (Maths planning.docx, Aug 2026) and
the arithmetic itself. Codes are the shared vocabulary for the `misconceptions` tab.
"""

def digits(n, width):
    return [int(c) for c in str(n).zfill(width)][::-1]   # index 0 = ones

def from_digits(ds):
    return int("".join(str(d) for d in ds[::-1])) if ds else 0

# ---------------- addition ----------------

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
    r = (a + b) % (10 ** w)
    return r if r != a + b else None

def off_by(n, delta):
    return n + delta

# ---------------- subtraction ----------------

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

# ---------------- registry ----------------

ADD_PREDICTORS = {
    "M_NOCARRY":       (add_nocarry, "Forgets to carry", "Place-value chart; exchange 10 ones for a ten with rods before recording"),
    "M_CARRY_SKIP":    (add_carry_skips_column, "Carry placed one column too far left", "Column chart with the carry written above the correct column; two worked examples"),
    "M_CONCAT":        (add_concat, "Writes the whole column sum instead of regrouping", "Ten-frame / rods: 'only one digit fits in a column'"),
    "M_DROP_CARRYOUT": (add_drop_carry_out, "Drops the final carry-out (76+54 -> 30)", "Estimate first; 'can the answer be smaller than the bigger number?'"),
    "M_FACT_PM1":      (lambda a, b: off_by(a + b, 1), "Fact off by one", "Number bonds; ten-frame fluency"),
    "M_FACT_PM10":     (lambda a, b: off_by(a + b, 10), "Tens miscounted", "Count in tens on a 100-square"),
    "M_WRONG_OP":      (wrong_operation_sub, "Subtracted instead of adding", "Read the question aloud; identify the operation word"),
}
SUB_PREDICTORS = {
    "M_SMALL_FROM_LARGE": (sub_smaller_from_larger, "Subtracts the smaller digit from the larger regardless of row ('neeche wala number')", "Rods: show that the top number is the whole; act out the exchange"),
    "M_NO_DECREMENT":     (sub_no_decrement, "Exchanges but does not reduce the lender column", "Cross out and rewrite the lender digit before subtracting"),
    "M_ZERO_LENDER":      (sub_across_zero_lender_not_decremented, "Across zero: zero lends but the column to its left is not reduced", "Three-column rods; exchange a hundred for ten tens first"),
    "M_ZERO_NOT_NINE":    (sub_across_zero_zero_not_reduced, "Across zero: zero becomes 10 and stays 10 (should be 9)", "Number line count-up as a check"),
    "M_FACT_PM1":         (lambda a, b: off_by(a - b, -1), "Fact off by one", "Number bonds; count-up on a number line"),
    "M_FACT_PM10":        (lambda a, b: off_by(a - b, 10), "Tens miscounted", "Count back in tens on a 100-square"),
    "M_WRONG_OP":         (wrong_operation_add, "Added instead of subtracting", "Read the question aloud; identify the operation word"),
}

def predict(op, a, b):
    """Return {code: wrong_answer} for every misconception that can occur on these operands."""
    table = ADD_PREDICTORS if op == "+" else SUB_PREDICTORS
    out = {}
    correct = a + b if op == "+" else a - b
    for code, (fn, _, _) in table.items():
        try:
            v = fn(a, b)
        except Exception:
            v = None
        if v is not None and v != correct and v >= 0:
            out[code] = v
    return out

def catalogue():
    rows = []
    for op, table in (("+", ADD_PREDICTORS), ("-", SUB_PREDICTORS)):
        for code, (_, name, repair) in table.items():
            rows.append(dict(code=code, op=op, name=name, repair=repair))
    return rows
