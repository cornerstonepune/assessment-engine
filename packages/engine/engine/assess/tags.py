"""Derive taxonomy case tags from what a generator actually produced.

The dimensions are the school team's Addition & Subtraction Assessment Skill Taxonomy §12, plus the few
finer measurements its cases need (§2–§11: which columns carry, how many zeros an exchange passes
through, zeros in the answer, a zero operand, a missing digit's place, a story's shape). Tags are never
typed by a person: a generator is asked for a rung and a signal, and what it emits is measured here.
That is what makes the coverage report trustworthy — it reports the items that exist, not the items
someone meant to make. A case (`taxonomy_case.match`) is a combination of these tags.
"""

import re

from . import misconceptions as M
from . import words as W

FORMAT_REASONING = {
    "missing_number": "INVERSE",
    "missing_digit": "CONSTRAINT",
    "balance_scale": "BALANCE",
    "equation": "BALANCE",
    "fact_family": "INVERSE",
    "inverse_check": "INVERSE",
    "find_mistake": "ERROR_DIAGNOSIS",
    "explain_claim": "ERROR_DIAGNOSIS",
    "sort_into_table": "DIRECT",
    "estimate_then_calc": "DIRECT",
}
FORMAT_CONTEXT = {"word_1step": "WORD_PROBLEM", "word_2step": "WORD_PROBLEM"}
FORMAT_UNKNOWN = {
    "missing_digit": ("DIGIT", "MULTIPLE"),
    "balance_scale": ("WHOLE_NUMBER", "SECOND_OPERAND"),
}
MISSING_POSITION = {"a": "FIRST_OPERAND", "b": "SECOND_OPERAND", "answer": "RESULT"}
RUNG_STRATEGY = {"R7": "MENTAL", "R11": "ESTIMATION", "R13": "COMPENSATION"}
PLACES = ["ONES", "TENS", "HUNDREDS", "THOUSANDS", "TEN_THOUSANDS"]
SIDES = {(False, False): "NONE", (True, False): "FIRST", (False, True): "SECOND", (True, True): "BOTH"}


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
    da, db = M.digits(a, w), M.digits(b, w)
    # §5.1: a carry cascades when it lands on a column whose own digits make 9 — that column carries only
    # because of it (399 + 4, 391 + 9). Read where the carry lands, not where it leaves: 99 + 28 carries
    # twice, but its tens would carry anyway, so it is consecutive.
    if op == "+" and any(i - 1 in cols and da[i] + db[i] == 9 for i in cols):
        return "CASCADING"
    # §5.2: an exchange crosses a zero when the place it exchanges from shows 0 (402 − 185); a 0 in the
    # column that needs the exchange is not crossed (530 − 47 exchanges from the 3 and the 5).
    if op == "-" and any(i + 1 < w and da[i + 1] == 0 for i in cols):
        return "ACROSS_ZERO"
    adjacent = all(cols[i + 1] - cols[i] == 1 for i in range(len(cols) - 1))
    return "CONSECUTIVE" if adjacent else "NON_ADJACENT"


def _answer_change(ans, widest):
    if ans == 0:
        return "ZERO"
    lost = widest - len(str(ans))
    return {0: "SAME", -1: "+1", 1: "-1"}.get(lost, "-MULTIPLE" if lost > 1 else "+1")


def _answer_zeros(ans):
    s = str(ans)
    if ans == 0 or len(s) == 1:
        return "NONE"
    inside, end = "0" in s.rstrip("0")[1:], s.endswith("0")
    return {(False, False): "NONE", (True, False): "INTERNAL", (False, True): "TRAILING"}.get(
        (inside, end), "INTERNAL+TRAILING"
    )


def _has_lender_zero(n):
    """A zero in a column a regroup can pass through — any place but the ones (§2.7, §3.7)."""
    return "0" in str(n)[:-1]


def _exchange_zeros(a, b, cols):
    """How many zeros of the top number an exchange has to pass through: 402 − 185 → 1, 1000 − 476 → 2."""
    da = M.digits(a, len(str(a)))
    return sum(1 for i in cols if i + 1 < len(da) and da[i + 1] == 0)


def _carry_into_zero(a, b, cols):
    """A carry lands on a column where one number shows a 0 (208 + 96)."""
    w = max(len(str(a)), len(str(b)))
    da, db = M.digits(a, w), M.digits(b, w)
    return any(
        i - 1 in cols and ((i < len(str(a)) and da[i] == 0) or (i < len(str(b)) and db[i] == 0))
        for i in range(1, w)
    )


def _knock_on(a, b, cols):
    """An exchange makes the next column need one it would not otherwise have needed (342 − 148)."""
    w = len(str(a))
    da, db = M.digits(a, w), M.digits(b, w)
    return any(i - 1 in cols and da[i] >= db[i] and da[i] - 1 < db[i] for i in range(1, w))


def _round_operand(b):
    if b in (10, 100, 1000):
        return "POWER_OF_TEN"
    return "MULTIPLE_OF_TEN" if b >= 10 and b % 10 == 0 else "NONE"


def _near_round(n):
    """Within 2 of a hundred (298, 1002) or within 1 of a ten for a 2-digit number (29)."""
    if n >= 100:
        return min(n % 100, 100 - n % 100) <= 2
    return n >= 10 and min(n % 10, 10 - n % 10) <= 1


def _two_numbers(t, op, a, b, layout):
    d1, d2 = len(str(a)), len(str(b))
    ans = a + b if op == "+" else a - b
    cols = _regroup_columns(op, a, b)
    t |= {
        "operation": "ADD" if op == "+" else "SUB",
        "operand_1_digits": d1,
        "operand_2_digits": d2,
        "digits_max": max(d1, d2),
        "digits_min": min(d1, d2),
        "num_operands": 2,
        "operand_order": "EQUAL_LENGTH" if d1 == d2 else ("LONGER_FIRST" if d1 > d2 else "SHORTER_FIRST"),
        "presentation": "VERTICAL" if layout == "column" else "HORIZONTAL",
        "regrouping": {0: "NONE", 1: "SINGLE"}.get(len(cols), "MULTIPLE"),
        "regroup_columns": cols,
        "regroup_at": "+".join(PLACES[i] for i in cols) or "NONE",
        "regroup_pattern": _pattern(op, a, b, cols),
        "zero_pattern": _zero_pattern(op, a, b, ans),
        "zero_operand": SIDES[(a == 0, b == 0)],
        "zeros_in": SIDES[(_has_lender_zero(a), _has_lender_zero(b))],
        "zeros_max": max(str(a)[:-1].count("0"), str(b)[:-1].count("0")),
        "answer_digits": len(str(abs(ans))),
        "answer_digit_change": _answer_change(ans, max(d1, d2)),
        "answer_zeros": _answer_zeros(ans),
        "round_operand": _round_operand(b),
        "near_round": "YES" if _near_round(a) or _near_round(b) else "NO",
    }
    if ans in (10, 100, 1000):
        t["answer_power_of_ten"] = ans
    if op == "+":
        t["carry_into_zero"] = "YES" if _carry_into_zero(a, b, cols) else "NO"
    else:
        t["exchange_zeros"] = _exchange_zeros(a, b, cols)
        t["knock_on"] = "YES" if _knock_on(a, b, cols) else "NO"
        # §5.2 highest-place reduction: the leading digit lends (105 − 97 = 8); 76 − 73 only loses a digit
        t["highest_place_reduced"] = "YES" if len(str(a)) - 2 in cols else "NO"
        t["difference_small"] = "YES" if a >= 100 and 0 < ans <= 10 and a // 100 != b // 100 else "NO"
    # A shorter second operand, or a sum written in a line, both force the child to align it.
    t["alignment_required"] = "YES" if (d1 != d2 or t["presentation"] == "HORIZONTAL") else "NO"
    return t


def _many_numbers(t, xs, layout):
    """Three or more addends (§2.8): the column totals, the largest carry, the lengths."""
    w = max(len(str(x)) for x in xs)
    lengths = {len(str(x)) for x in xs}
    carry, carries, biggest = 0, [], 0
    for i in range(w):
        s = sum(M.digits(x, w)[i] for x in xs) + carry
        carry = s // 10
        biggest = max(biggest, carry)
        if carry:
            carries.append(i)
    return t | {
        "operation": "ADD",
        "num_operands": len(xs),
        "digits_max": w,
        "digits_min": min(lengths),
        "presentation": "VERTICAL" if layout == "column" else "HORIZONTAL",
        "alignment_required": "NO" if len(lengths) == 1 and layout == "column" else "YES",
        "operand_order": "EQUAL_LENGTH" if len(lengths) == 1 else "MIXED",
        "regrouping": {0: "NONE", 1: "SINGLE"}.get(len(carries), "MULTIPLE"),
        "regroup_at": "+".join(PLACES[i] for i in carries) or "NONE",
        "carry_max": biggest,
    }


def _missing_digit(t, sp):
    """Where the boxes are in a missing-digit question, and what the numbers do around them."""
    rows = {"FIRST": sp.get("a", ""), "SECOND": sp.get("b", ""), "RESULT": sp.get("c", "")}
    where = [name for name, s in rows.items() if "□" in str(s) or re.search(r"[A-Z]", str(s))]
    boxes = [(name, s) for name, s in rows.items() for s in [str(s)] if "□" in s]
    count = sum(s.count("□") for _, s in boxes) or len(
        {c for s in rows.values() for c in re.findall(r"[A-Z]", str(s))}
    )
    t |= {
        "operation": "ADD" if sp.get("op") == "+" else "SUB",
        "missing_count": count,
        "missing_in": "+".join(where),
        "unknown_type": "DIGIT" if count == 1 else "MULTIPLE_DIGITS",
    }
    if count == 1 and boxes:
        name, s = boxes[0]
        t["missing_place"] = PLACES[len(s) - 1 - s.index("□")]
    solved = sp.get("solved")
    if solved and {"a", "b"} <= solved.keys():
        cols = _regroup_columns(sp["op"], solved["a"], solved["b"])
        t["regrouping"] = {0: "NONE", 1: "SINGLE"}.get(len(cols), "MULTIPLE")
        if sp["op"] == "-":
            t["exchange_zeros"] = _exchange_zeros(solved["a"], solved["b"], cols)
    return t


def _missing_number(t, sp):
    """Which number the box hides, and how big it is (§6.1, §6.3)."""
    text = (sp.get("text") or "").replace("−", "-")
    terms = re.findall(r"□|\d+", text.split("=")[0]) if "=" in text else []
    if len(terms) >= 3:
        t["num_operands"] = len(terms)
    missing = sp.get("missing")
    if missing:
        t["unknown_position"] = MISSING_POSITION[missing]
        hidden = {"a": sp.get("a"), "b": sp.get("b")}.get(missing)
        if missing == "answer" and isinstance(sp.get("a"), int):
            hidden = sp["a"] + sp["b"] if sp.get("op") == "+" else sp["a"] - sp["b"]
        if isinstance(hidden, int):
            t["unknown_digits"] = len(str(hidden))
        return t
    m = re.fullmatch(r"\s*(□|\d+)\s*([+\-])\s*(□|\d+)\s*=\s*(□|\d+)\s*", text)
    if m:
        x, op, y, z = m.groups()
        t["operation"] = "ADD" if op == "+" else "SUB"
        pos = [x, y, z].index("□") if "□" in (x, y, z) else None
        t["unknown_position"] = (
            ["FIRST_OPERAND", "SECOND_OPERAND", "RESULT"][pos] if pos is not None else "RESULT"
        )
        if pos is not None:
            n = [int(v) for v in (x, y, z) if v != "□"]
            hidden = {
                0: n[0] + n[1] if op == "-" else n[1] - n[0],
                1: n[0] - n[1] if op == "-" else n[1] - n[0],
            }.get(pos, n[0] + n[1] if op == "+" else n[0] - n[1])
            t["unknown_digits"] = len(str(abs(hidden)))
    return t


def derive(item) -> dict:
    """Taxonomy tags for one generated Item. Unknowable dimensions are simply absent."""
    sp, fmt = item.spec, item.fmt
    t = {
        "context": FORMAT_CONTEXT.get(fmt, "BARE_NUMBER"),
        "reasoning_type": FORMAT_REASONING.get(fmt, "DIRECT"),
        "strategy": sp.get("strategy") or RUNG_STRATEGY.get(item.rung, "STANDARD"),
    }
    t["unknown_type"], t["unknown_position"] = FORMAT_UNKNOWN.get(fmt, ("NONE", "RESULT"))
    if fmt == "missing_number":
        t["unknown_type"] = "WHOLE_NUMBER"
    for key in ("shape", "structure", "planted", "round_to"):
        if sp.get(key) is not None:
            t[key] = sp[key]
    if fmt in FORMAT_CONTEXT and "structure" not in t:
        # a story's shape is its template's (`words.template_of`); a budget is taken away step by step
        t["structure"] = "SUB_SUB" if "budget" in sp else W.structure_of(item.stem)
        if t["structure"] is None:
            del t["structure"]
    if sp.get("table"):
        t["context"] = "TABLE_OR_CHART"

    if "budget" in sp:
        costs = sp.get("costs") or [sp[k] for k in ("a", "b", "c") if k in sp]
        t |= {
            "num_costs": len(costs),
            "budget": sp["budget"],
            "cost_is_a_product": "YES" if sp.get("children") else "NO",
        }
    if fmt == "missing_digit":
        return _missing_digit(t, sp)
    addends = sp.get("addends")
    if addends:
        return _many_numbers(t, addends, sp.get("layout", "column"))
    a, b, op = sp.get("a"), sp.get("b"), sp.get("op")
    if isinstance(a, int) and isinstance(b, int) and op in ("+", "-"):
        t = _two_numbers(
            t, op, a, b, sp.get("layout") or ("column" if fmt == "column_grid" else "horizontal")
        )
    if fmt == "missing_number":
        t = _missing_number(t, sp)
    return t
