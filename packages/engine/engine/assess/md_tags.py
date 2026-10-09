"""The tags of a multiplication or a division (goals/md1-taxonomy-rows.yaml), measured from its own numbers as
`tags.py` measures an addition's. Deterministic, no I/O.

The dimensions are the multiplication & division taxonomy's master tagging matrix
(docs/design/multiplication-division-taxonomy.md, rows in `case_dimension`): the fact and its table, a place-value
factor, which columns carry and how far, the rows of a long multiplication, short division's exchanges, a zero in
the quotient, how big the remainder is. A few are what the kind that made the question states rather than its
numbers — the method it prints (`method`), a story's shape (`structure`), what a remainder is used for
(`remainder_use`) — read from its spec, as `tags.py` reads a story's shape. Nothing here is typed by a person.
"""

import math
import re
from typing import Any

from . import operations as O

PLACES = ["ONES", "TENS", "HUNDREDS", "THOUSANDS", "TEN_THOUSANDS"]
SIDES = {(False, False): "NONE", (True, False): "FIRST", (False, True): "SECOND", (True, True): "BOTH"}
# the fact groups the school teaches the tables in, easiest first; a fact is in the easiest that holds it
GROUP = {
    **{n: "0-1" for n in (0, 1)},
    **{n: "2-5-10" for n in (2, 5, 10)},
    **{n: "3-4" for n in (3, 4)},
    **{n: "6-9" for n in (6, 7, 8, 9)},
    **{n: "11-12" for n in (11, 12)},
}
ORDER = ["0-1", "2-5-10", "3-4", "6-9", "11-12"]
POWERS = {10: "X10", 100: "X100", 1000: "X1000"}
# what an equal-groups question's shape says it is: a picture of groups, the groups added, or a story of them
SHAPES: dict[str, dict[str, str]] = {
    "PICTURE": {"method": "GROUPS"},
    "SUM": {"method": "REPEATED_ADDITION"},
    "STORY": {"structure": "EQUAL_GROUPS", "context": "WORD_PROBLEM"},
}
MISSING = {
    "a": "FIRST_OPERAND",
    "b": "SECOND_OPERAND",
    "answer": "RESULT",
    "remainder": "REMAINDER",
    "both": "MULTIPLE",
}
_N = r"(□|\d+)"
# the signs `skills.operations` reads a question's operation from, so a box it calls × is one this solves, and no other
_SUM = re.compile(rf"\s*{_N}\s*([×÷])\s*{_N}\s*=\s*{_N}(?:\s*r\s*{_N})?\s*")
_FIRST = re.compile(rf"\s*{_N}\s*=\s*{_N}\s*([×÷])\s*{_N}\s*")


def yes(flag: bool) -> str:
    return "YES" if flag else "NO"


def place(i: int) -> str:
    """The name of column `i` from the ones; past ten thousands, by its count (a question may run that long)."""
    return PLACES[i] if i < len(PLACES) else f"PLACE_{i + 1}"


def answer_zeros(ans: int) -> str:
    """Where an answer's zeros sit: none, inside it (108), at its end (240), or both (2010)."""
    s = str(ans)
    if ans == 0 or len(s) == 1:
        return "NONE"
    inside, end = "0" in s.rstrip("0")[1:], s.endswith("0")
    return {(False, False): "NONE", (True, False): "INTERNAL", (False, True): "TRAILING"}.get(
        (inside, end), "INTERNAL+TRAILING"
    )


def _trailing(n: int) -> int:
    return len(str(n)) - len(str(n).rstrip("0")) if n else 0


def _fact_group(a: int, b: int) -> str:
    """The easiest table holding a × b within its first ten rows: 8 × 3 is the 3 table's, 7 × 0 and 0 × 12 the 0's."""
    if a in (0, 1) or b in (0, 1):
        return "0-1"
    options = [GROUP[f] for f, other in ((a, b), (b, a)) if f in GROUP and other <= 10]
    return min(options, key=ORDER.index) if options else "11-12"


def _is_fact(a: int, b: int) -> bool:
    return 0 <= a <= 12 and 0 <= b <= 12


def _fact(one: str, a: int, b: int, q: int, r: int) -> dict[str, Any]:
    """A table fact: × of two numbers to 12; ÷ that is one read backwards. Its table is the first number's (the
    divisor's), and a fact whose second number's table is the easier one is that table read the other way."""
    x, y = (a, b) if one == "×" else (b, q)
    if not (_is_fact(a, b) if one == "×" else b > 0 and r == 0 and _is_fact(b, q)):
        return {"fact": "NO"}
    out: dict[str, Any] = {"fact": "YES", "fact_table": x, "fact_group": _fact_group(x, y)}
    if one == "×":
        out["fact_swapped"] = yes(b >= 2 and ORDER.index(GROUP[b]) < ORDER.index(GROUP[a]))
    return out


def _place_value(one: str, a: int, b: int) -> dict[str, str]:
    """By 10, 100 or 1000; or round numbers, one or both, whose fact once the zeros are off is a table fact
    (30 × 4 is 3 × 4; 200 ÷ 4 is 20 ÷ 4, a fact that uses one of the zeros)."""
    for n in (b,) if one == "÷" else (b, a):
        if n in POWERS:
            return {"place_value_factor": POWERS[n]}
    za, zb = _trailing(a), _trailing(b)
    if not (za or zb) or one == "÷" and not za or not (a and b):
        return {"place_value_factor": "NONE"}
    if za and zb:
        kind = "MULTIPLE_OF_TEN_BOTH"
    else:
        kind = "MULTIPLE_OF_HUNDRED_ONE" if max(za, zb) >= 2 else "MULTIPLE_OF_TEN_ONE"
    if one == "×":
        x, y = int(str(a).rstrip("0")), int(str(b).rstrip("0"))
        scaled, zero = _is_fact(x, y), (x * y) % 10 == 0
    else:
        common = 0  # the zeros both numbers end in, taken off together: 200 ÷ 40 is 20 ÷ 4
        while a % 10 == 0 and b % 10 == 0:
            a, b, common = a // 10, b // 10, common + 1
        za = _trailing(a)
        # a fact read off the number divided once k of its zeros are off; k = 0 counts only when zeros came off both
        ks = range(za, -1 if common else 0, -1)
        found = [k for k in ks if (a // 10**k) % b == 0 and (a // 10**k) // b <= 12 and b <= 12]
        scaled, zero = bool(found), bool(found) and found[0] < za
    out = {"place_value_factor": kind, "scaled_fact": yes(scaled)}
    if scaled:
        out["fact_zero"] = yes(zero)
    return out


def _zeros(n: int, answer: int) -> dict[str, Any]:
    """Where the zeros of the number worked on sit — inside it (302), at its end (230), or both (4050) — and how
    many it has (1008 has two); none there but one in the answer is its own case (25 × 4 = 100)."""
    s = str(n)
    if not n or "0" not in s:
        return {"zero_pattern": "ANSWER_ZERO" if "0" in str(answer) else "NONE", "zero_count": 0}
    inside, end = "0" in s.rstrip("0")[1:], s.endswith("0")
    where = {(True, False): "INTERNAL", (False, True): "TRAILING"}.get((inside, end), "INTERNAL+TRAILING")
    return {"zero_pattern": where, "zero_count": s.count("0")}


def _regrouped(places: list[int]) -> dict[str, Any]:
    """The columns that carry (×) or exchange (÷), named from the ones up either way: ONES+TENS, TENS+HUNDREDS."""
    places = sorted(places)
    return {
        "regrouping": {0: "NONE", 1: "SINGLE"}.get(len(places), "MULTIPLE"),
        "regroup_columns": places,
        "regroup_at": "+".join(place(i) for i in places) or "NONE",
    }


def _times(a: int, b: int, p: int) -> dict[str, Any]:
    """In columns: a 1-digit multiplier column by column, or a longer one as long multiplication's rows."""
    longer, shorter = (b, a) if len(str(a)) < len(str(b)) else (a, b)
    # the number worked on: never the 10, 100 or 1000 it is multiplied by, whose zeros are the factor's own
    worked = a if b in POWERS else (b if a in POWERS else longer)
    out: dict[str, Any] = {
        "answer_digit_change": "FULL" if len(str(p)) == len(str(a)) + len(str(b)) else "ONE_FEWER",
        "multiplier_zero": "NONE",
    }
    out |= _zeros(worked, p)
    if len(str(shorter)) == 1:
        cols = O.times_columns(longer, shorter)
        carries = [c["carry_out"] for c in cols[:-1]]
        out |= _regrouped([i for i, c in enumerate(carries) if c])
        out["carry_size"] = "NONE" if not any(carries) else ("ONE" if max(carries) == 1 else "MORE_THAN_ONE")
        out["carry_max"] = max(carries, default=0)
        out["knock_on"] = yes(any(c["product"] < 10 <= c["value"] for c in cols))
        out["carry_into_zero"] = yes(any(c["digit"] == 0 and c["carry_in"] for c in cols))
        return out
    rows = O.rows(longer, shorter)
    carrying = [
        any(c["carry_out"] for c in O.times_columns(longer, int(x))[:-1]) for x in str(shorter) if x != "0"
    ]
    carry, added = 0, 0
    for i in range(len(str(sum(rows)))):
        carry = (sum((r // 10**i) % 10 for r in rows) + carry) // 10
        added += 1 if carry else 0
    zeros = str(shorter).rstrip("0")
    out |= {
        "partial_products": len(rows),
        "row_regrouping": "NONE" if not any(carrying) else ("ALL" if all(carrying) else "SOME"),
        "partial_sum_regrouping": {0: "NONE", 1: "SINGLE"}.get(added, "MULTIPLE"),
        "multiplier_zero": "TRAILING"
        if str(shorter).endswith("0")
        else ("INTERNAL" if "0" in zeros else "NONE"),
    }
    return out


def _divide(a: int, b: int, q: int, r: int) -> dict[str, Any]:
    """Short division left to right: where a remainder is exchanged into the next digit, whether the first digit is
    smaller than the divisor, where the quotient has a zero, and how big the remainder is."""
    steps, lead = O.short_division(a, b), len(str(b))
    width = len(steps)
    qs = str(q)
    out: dict[str, Any] = _regrouped([width - 1 - i for i, s in enumerate(steps[:-1]) if s["r"]])
    out |= {
        "first_digit_smaller": yes(len(str(a)) > lead and int(str(a)[:lead]) < b),
        "answer_digit_change": "FULL" if len(qs) == len(str(a)) - lead + 1 else "ONE_FEWER",
        "quotient_zero": "NONE"
        if q < 10
        else (
            "MULTIPLE"
            if qs.count("0") >= 2
            else "MIDDLE"
            if "0" in qs[:-1]
            else "END"
            if qs[-1] == "0"
            else "NONE"
        ),
        "remainder": "NONE"
        if r == 0
        else ("DIVIDEND_SMALLER" if a < b else "LARGEST" if r == b - 1 else "SOME"),
    }
    out |= _zeros(a, q)
    if b in GROUP:
        out["divisor_group"] = GROUP[b]  # the table a 1-digit divisor's steps are read from
    if lead >= 2:
        near = (b + 5) // 10 * 10  # the divisor to its nearest ten, a half up as the school rounds
        out["estimate_corrected"] = yes(any(s["value"] >= b and s["value"] // near != s["q"] for s in steps))
    return out


def standard_method(one: str, a: int, b: int, layout: str) -> str:
    """The way a straight calculation is worked when its kind names no other: in a line, or in columns —
    long multiplication for a 2-digit multiplier, long division for a 2-digit divisor."""
    if layout != "column":
        return "LINE"
    if one == "×":
        return "COLUMNS" if min(len(str(a)), len(str(b))) == 1 else "LONG_MULTIPLICATION"
    return "SHORT_DIVISION" if len(str(b)) == 1 else "LONG_DIVISION"


def two_numbers(
    t: dict[str, Any], fmt: str, op: str, a: int, b: int, layout: str, sp: dict[str, Any]
) -> dict[str, Any]:
    """Every tag of `a op b`, × or ÷, onto `t`."""
    one = O.sign(op) or op
    d1, d2 = len(str(a)), len(str(b))
    t |= {
        "operation": O.NAMES[one],
        "operand_1_digits": d1,
        "operand_2_digits": d2,
        "digits_max": max(d1, d2),
        "digits_min": min(d1, d2),
        "num_operands": 2,
        "operand_order": "EQUAL_LENGTH" if d1 == d2 else ("LONGER_FIRST" if d1 > d2 else "SHORTER_FIRST"),
        "presentation": "VERTICAL" if layout == "column" else "HORIZONTAL",
        "method": sp.get("method") or standard_method(one, a, b, layout),
        "zero_operand": SIDES[(a == 0, b == 0)],
        "one_operand": SIDES[(a == 1, b == 1)],
        "equal_operands": yes(a == b),
    }
    if fmt == "equal_groups":  # what its shape says it is, unless it names its method itself
        t |= {
            k: v
            for k, v in SHAPES.get(sp.get("shape") or "", {}).items()
            if not (k == "method" and sp.get("method"))
        }
    if sp.get("remainder_use"):
        t["remainder_use"] = sp["remainder_use"]
    if one == "÷" and b == 0:
        return t  # 9 ÷ 0 has no answer to measure: a claim about it is judged, never worked
    q, r = O.divide(a, b) if one == "÷" else (a * b, 0)
    t |= {"answer_digits": len(str(q)), "answer_zeros": answer_zeros(q)}
    t["answer_round"] = yes(q >= 10 and str(q).rstrip("0") == str(q)[0])
    t |= _fact(one, a, b, q, r) | _place_value(one, a, b)
    return t | (_times(a, b, q) if one == "×" else _divide(a, b, q, r))


def _num(v: str | None) -> int | None:
    return None if v is None or v == "□" else int(v)


def solved(sp: dict[str, Any]) -> dict[str, Any]:
    """A missing-number question kept as its text alone (`□ × 6 = 42`, `38 ÷ 5 = 7 r □`, `□ = 63 ÷ 9`), given the
    numbers behind its box: a, b, which is hidden, and whether the answer is written first."""
    if "missing" in sp:
        return sp
    text = sp.get("text") or ""
    m, first = _SUM.fullmatch(text), _FIRST.fullmatch(text)
    if first:
        z, x, op, y, w = first[1], first[2], first[3], first[4], None
    elif m:
        x, op, y, z, w = m[1], m[2], m[3], m[4], m[5]
    else:
        return sp
    one = O.sign(op) or ""
    X, Y, Z, W = _num(x), _num(y), _num(z), _num(w)
    boxes = [v for v in (x, y, z, w) if v == "□"]
    first_ = yes(bool(first))
    if x == "□" and y == "□" and one == "×" and Z is not None and w is None:
        root = math.isqrt(Z)  # □ × □ = 49: the same number twice, when there is one
        return (
            sp | {"a": root, "b": root, "op": one, "missing": "both", "answer_first": first_}
            if root * root == Z
            else sp
        )
    if len(boxes) != 1:
        return sp
    found = _unbox(one, X, Y, Z, W, w == "□")
    if found is None:
        return sp
    a, b, missing = found
    return sp | {"a": a, "b": b, "op": one, "missing": missing, "answer_first": first_}


def _unbox(
    one: str, x: int | None, y: int | None, z: int | None, w: int | None, remainder: bool
) -> tuple[int, int, str] | None:
    """(a, b, which is hidden) for `x one y = z [r w]` with one box, or None when no one number gives the question
    back exactly: □ × 0 = 5 has none, □ × 0 = 0 has every one, 42 ÷ □ = 5 leaves 2 over."""
    if z is None and x is not None and y is not None:
        a, b, hidden = x, y, "answer"
    elif remainder and x is not None and y is not None:
        a, b, hidden = x, y, "remainder"
    elif x is None and y and z is not None:
        a, b, hidden = (z // y if one == "×" else z * y + (w or 0)), y, "a"
    elif y is None and x is not None and z is not None and (z if one == "÷" else x):
        a, b, hidden = x, (z // x if one == "×" else (x - (w or 0)) // z), "b"
    else:
        return None
    if one == "×":
        return (a, b, hidden) if z is None or a * b == z else None
    if b <= 0:
        return None
    q, r = O.divide(a, b)
    if (
        (z is not None and q != z)
        or (w is not None and r != w)
        or (w is None and not remainder and z is not None and r)
    ):
        return None
    return a, b, hidden


def missing(t: dict[str, Any], sp: dict[str, Any]) -> dict[str, Any]:
    """Which number the box hides and how big it is, as `tags._missing_number` says it for + and −."""
    hide = sp.get("missing")
    if hide in MISSING:
        t["unknown_position"] = MISSING[hide]
        hidden = {"a": sp.get("a"), "b": sp.get("b"), "both": sp.get("a")}.get(hide)
        a, b, divides = sp.get("a"), sp.get("b"), O.sign(sp.get("op")) == "÷"
        if (
            hide in ("answer", "remainder")
            and isinstance(a, int)
            and isinstance(b, int)
            and not (divides and b == 0)
        ):
            q, r = O.divide(a, b) if divides else (a * b, 0)
            hidden = r if hide == "remainder" else q
        if isinstance(hidden, int):
            t["unknown_digits"] = len(str(hidden))
        t["answer_first"] = sp.get("answer_first", "NO")
    return t
