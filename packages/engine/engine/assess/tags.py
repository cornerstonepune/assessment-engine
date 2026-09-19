"""Derive taxonomy case tags from what a generator actually produced.

The dimensions are the school team's Addition & Subtraction Assessment Skill Taxonomy §12,
plus `word_structure` from §10.1. Tags are never typed by a person: a generator is asked for
a rung and a signal, and what it emits is measured here. That is what makes the coverage
report trustworthy — it reports the items that exist, not the items someone meant to make.
"""

from . import misconceptions as M

FORMAT_REASONING = {
    "missing_number": "INVERSE",
    "missing_digit": "CONSTRAINT",
    "balance_scale": "BALANCE",
    "find_mistake": "ERROR_DIAGNOSIS",
    "explain_claim": "ERROR_DIAGNOSIS",
    "sort_into_table": "DIRECT",
    "estimate_then_calc": "DIRECT",
}
FORMAT_CONTEXT = {"word_1step": "WORD_PROBLEM", "word_2step": "WORD_PROBLEM"}
FORMAT_UNKNOWN = {
    "missing_number": ("WHOLE_NUMBER", "SECOND_OPERAND"),
    "missing_digit": ("DIGIT", "MULTIPLE"),
    "balance_scale": ("WHOLE_NUMBER", "SECOND_OPERAND"),
}
RUNG_STRATEGY = {"R7": "MENTAL", "R11": "ESTIMATION", "R13": "COMPENSATION"}


def _regroup_columns(op, a, b):
    """Which column indices regroup — 0 = ones. Mirrors the arithmetic, not a guess."""
    w = max(len(str(a)), len(str(b)))
    da, db = M.digits(a, w), M.digits(b, w)
    cols, carry = [], 0
    for i in range(w):
        if op == "+":
            s = da[i] + db[i] + carry
            carry = 1 if s >= 10 else 0
            if carry:
                cols.append(i)
        else:
            x = da[i] - carry
            if x < db[i]:
                cols.append(i)
                carry = 1
            else:
                carry = 0
    return cols


def _zero_pattern(op, a, b, ans):
    """Taxonomy §3.7 / §2.7. A zero only changes the regrouping demand when it sits in a column
    that can be borrowed from or carried into — never the ones column, which is why the slice
    drops the last digit rather than the first."""
    zeros = str(a)[:-1].count("0") + str(b)[:-1].count("0")
    if zeros > 1:
        return "MULTIPLE"
    if zeros == 1:
        return "INTERNAL"
    return "ANSWER_ZERO" if "0" in str(ans) else "NONE"


def _pattern(op, a, b, cols):
    if not cols:
        return "NONE"
    if len(cols) == 1:
        return "ISOLATED"
    w = max(len(str(a)), len(str(b)))
    da = M.digits(a, w)
    # a carry landing on a 9 propagates: that is cascading, not merely consecutive
    if op == "+" and any(da[i] == 9 for i in cols[:-1]):
        return "CASCADING"
    if op == "-" and any(da[i] == 0 for i in cols):
        return "ACROSS_ZERO"
    adjacent = all(cols[i + 1] - cols[i] == 1 for i in range(len(cols) - 1))
    return "CONSECUTIVE" if adjacent else "NON_ADJACENT"


def derive(item) -> dict:
    """Taxonomy §12 tags for one generated Item. Unknowable dimensions are simply absent."""
    sp, fmt = item.spec, item.fmt
    t = {
        "context": FORMAT_CONTEXT.get(fmt, "BARE_NUMBER"),
        "reasoning_type": FORMAT_REASONING.get(fmt, "DIRECT"),
        "strategy": RUNG_STRATEGY.get(item.rung, "STANDARD"),
    }
    if fmt in FORMAT_UNKNOWN:
        t["unknown_type"], t["unknown_position"] = FORMAT_UNKNOWN[fmt]
    else:
        t["unknown_type"], t["unknown_position"] = "NONE", "RESULT"

    addends = sp.get("addends")
    if addends:
        t |= {
            "operation": "ADD",
            "num_operands": len(addends),
            "presentation": "VERTICAL",
            "alignment_required": "NO",
            "operand_order": "EQUAL_LENGTH",
        }
        return t

    a, b, op = sp.get("a"), sp.get("b"), sp.get("op")
    if not (isinstance(a, int) and isinstance(b, int) and op in ("+", "-")):
        return t

    d1, d2 = len(str(a)), len(str(b))
    ans = a + b if op == "+" else a - b
    cols = _regroup_columns(op, a, b)
    t |= {
        "operation": "ADD" if op == "+" else "SUB",
        "operand_1_digits": d1,
        "operand_2_digits": d2,
        "num_operands": 2,
        "operand_order": "EQUAL_LENGTH" if d1 == d2 else ("LONGER_FIRST" if d1 > d2 else "SHORTER_FIRST"),
        "presentation": "VERTICAL" if sp.get("layout") == "column" else "HORIZONTAL",
        "regrouping": {0: "NONE", 1: "SINGLE"}.get(len(cols), "MULTIPLE"),
        "regroup_columns": cols,
        "regroup_pattern": _pattern(op, a, b, cols),
        "zero_pattern": _zero_pattern(op, a, b, ans),
        "answer_digit_change": {0: "SAME", 1: "+1"}.get(len(str(ans)) - max(d1, d2), "-1"),
    }
    # A shorter second operand, or a sum written in a line, both force the child to align it.
    t["alignment_required"] = "YES" if (d1 != d2 or t["presentation"] == "HORIZONTAL") else "NO"
    return t
