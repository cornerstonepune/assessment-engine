"""Every number a model writes is recomputed here before an item exists (ADR 0005).

`problems` returns the reasons a candidate fails, empty when it passes. `to_item` turns an
accepted candidate into the same `Item` the deterministic generators build, so the renderer, the
marker and the tag deriver cannot tell the two apart — and the same operands produce the same
item_key from either path, which is what stops the bank holding one sum twice.
"""

from typing import Any, cast

from . import divide_kinds as DK
from . import division as DV
from . import facts_kinds as FK
from . import misconceptions as M
from . import operations as O
from . import taxonomy
from . import words as W
from . import written_methods as WM
from .items import Item, Response, cells, item, regroup_count_add, regroup_count_sub

FORBIDDEN_WORDS = ("borrow",)
# fmt -> (signal, working_lines, needs_stem); mirrors what items.py gives each format
FORMATS = {
    "column_grid": ("Procedural", 0, False),
    "bare_sum": ("Procedural", 3, False),
    "missing_number": ("Conceptual", 1, True),
    "word_1step": ("Application", 3, True),
}
REGROUPS = {"+": regroup_count_add, "-": regroup_count_sub}
SYMMETRIC = {
    "M_FACT_PM1": 1,
    "M_FACT_PM10": 10,
    "M_FACT_PM100": 100,
}  # "plus or minus": either direction is the mistake


def normalise(c: dict[str, Any]) -> dict[str, Any]:
    """The model's symbol for an operation, folded to the one the rules use (`operations.sign`). Nothing else changes."""
    return c | {"op": O.sign(c.get("op")) or c.get("op")}


def _unworkable(op: str | None, a: Any, b: Any, answer: Any) -> str | None:
    """Why a candidate's arithmetic cannot be checked at all; None when it can. A division that leaves a remainder has
    two answers, and these formats ask for one."""
    if not all(isinstance(x, int) for x in (a, b, answer)):
        return "operands and answer must be integers"
    try:
        M.compute(op, a, b)
    except ValueError as e:
        return str(e)
    return None


def problems(c: dict[str, Any], check: dict[str, Any]) -> list[str]:
    fmt = c.get("format")
    if fmt not in FORMATS:
        return [f"format {fmt!r} is not one the bank can render"]
    op, a, b, answer = c.get("op"), c.get("a"), c.get("b"), c.get("answer")
    allowed_ops = check["op"] if isinstance(check["op"], list) else [check["op"]]
    if op not in allowed_ops:
        return [f"op {op!r} is not one of the rule's {allowed_ops!r}"]
    unworkable = _unworkable(op, a, b, answer)
    if unworkable:
        return [unworkable]

    out: list[str] = []
    correct = M.compute(op, cast(int, a), cast(int, b))  # whole numbers, `_unworkable` said
    if answer != correct:
        out.append(f"answer {answer} != {correct}")
    da, db = check["digits"]
    if (len(str(a)), len(str(b))) != (da, db):
        out.append(f"digits {len(str(a))},{len(str(b))} != {da},{db}")
    if op in REGROUPS and REGROUPS[op](a, b) not in check["regroups"]:
        out.append(f"regroups {REGROUPS[op](a, b)} not in {check['regroups']}")
    if check.get("no_zero_top") and "0" in str(a):
        out.append("zero in the top number")
    if "across_zero" in check and bool(check["across_zero"]) != ("0" in str(a)[:-1]):
        out.append(
            "across-zero rule: "
            + (
                "needs a zero in a lender column"
                if check["across_zero"]
                else "must not have a zero in a lender column"
            )
        )
    if correct < check.get("min_answer", 1 if op == "-" else 0):
        out.append(f"answer {correct} below the minimum")
    if check.get("max_total") and correct > check["max_total"]:
        out.append(f"answer {correct} above max_total {check['max_total']}")

    truth, table = M.predict(cast(str, op), cast(int, a), cast(int, b)), M.TABLES.get(op or "", {})
    for mc in c.get("misconceptions", []):
        code, wrong = mc.get("code"), mc.get("wrong_answer")
        if code not in table or code not in truth:
            continue  # nothing to check it against: the claim is dropped by to_item, the item survives
        delta = SYMMETRIC.get(code)
        agrees = abs(wrong - correct) == delta if delta else truth[code] == wrong
        if not agrees:
            out.append(f"{code} claims {wrong}, predictor says {truth[code]}")

    stem = (c.get("stem") or "").strip()
    needs_stem = FORMATS[fmt][2]
    if needs_stem and not stem:
        out.append("stem required for this format")
    if not needs_stem and stem:
        out.append("stem must be empty for this format")
    for w in FORBIDDEN_WORDS:
        if w in stem.lower():
            out.append(f"forbidden word {w!r} in stem")
    if fmt == "word_1step" and not (str(a) in stem and str(b) in stem):
        out.append("stem must contain both numbers")
    if fmt == "missing_number" and c.get("missing") not in ("a", "b", "answer", "both", "remainder"):
        out.append("missing must be a, b, answer, both or remainder")
    return out


# What a band's `check.format` implies in the dimension vocabulary tags.derive measures. Only the
# keys a given item's tags actually carry are compared, so a native format whose tags stop at
# the format level is judged on the format level and nothing is invented for it.
FORMAT_DIMENSIONS = {
    "bare_sum": {"presentation": "HORIZONTAL", "unknown_type": "NONE", "context": "BARE_NUMBER"},
    "column_grid": {"presentation": "VERTICAL", "unknown_type": "NONE"},
    "missing_number": {"unknown_type": "WHOLE_NUMBER"},
    "word_1step": {"context": "WORD_PROBLEM"},
    "word_2step": {"context": "WORD_PROBLEM"},
    "balance_scale": {"reasoning_type": "BALANCE"},
    "find_mistake": {"reasoning_type": "ERROR_DIAGNOSIS"},
    "explain_claim": {"reasoning_type": "ERROR_DIAGNOSIS"},
    "estimate_then_calc": {"reasoning_type": "DIRECT"},
}


def dimension_problems(tags, check, fmt=None, case_matches=None):
    """The item as measured, against the band as declared (BUILD-ORDER gate 4, amended).

    Difficulty is a region in dimension space, not a label: a band says digits, regroups, zeros
    and shape, and an item's tags say what it actually is. This is the check that makes two bands
    with different rules produce different items — the one that would have caught R1's Hard band
    quietly holding the same sums as its Medium band. Dimensions the tags do not carry are not
    judged; that is stated here, not hidden.

    A level that lists taxonomy cases (step 8f) is exactly the union of its cases: an item is inside it
    when it is one of them. With no case rows to read, there is nothing to judge it against."""
    if check.get("cases"):
        if case_matches is None:
            return []
        shape = check.get(
            "within"
        )  # a skill of one operation and digit shape holds its cases on its own numbers
        if any(
            taxonomy.matches(taxonomy.within(case_matches[c], shape), fmt, tags)
            for c in check["cases"]
            if c in case_matches
        ):
            return []
        return ["dimension outside every case the level holds"]
    out = []
    if "digits" in check and "operand_1_digits" in tags:
        want = tuple(check["digits"])
        got = (tags["operand_1_digits"], tags["operand_2_digits"])
        if got != want:
            out.append(f"dimension digits {got[0]},{got[1]} outside {want[0]},{want[1]}")
    if "regroups" in check and "regroup_columns" in tags:
        n = len(tags["regroup_columns"])
        if n not in check["regroups"]:
            out.append(f"dimension regroups {n} outside {list(check['regroups'])}")
    if (
        check.get("across_zero")
        and "zero_pattern" in tags
        and tags["zero_pattern"] not in ("INTERNAL", "MULTIPLE")
    ):
        out.append("dimension zeros: band needs an exchange across a zero, item has none")
    if check.get("format") == "word_budget" and "num_costs" in tags:
        # a budget level says how many costs, how big a budget, and whether one cost is a product
        if tags["num_costs"] != check.get("n_costs", 3):
            out.append(f"dimension costs {tags['num_costs']} not the level's {check.get('n_costs', 3)}")
        lo, hi = check.get("budget_range", (0, 10**9))
        if not lo <= tags["budget"] <= hi:
            out.append(f"dimension budget {tags['budget']} outside {lo}–{hi}")
        if (tags["cost_is_a_product"] == "YES") != bool(check.get("one_cost_is_a_product")):
            out.append("dimension a cost that is a product, against the level's rule")
    want_shape = FORMAT_DIMENSIONS.get(check.get("format"), {})
    for dim, value in want_shape.items():
        if dim in tags and tags[dim] != value:
            out.append(f"dimension {dim} {tags[dim]} outside the band's {check['format']} ({value})")
    return out


def _template(op, a, b):
    shape = f"{O.NAMES[op]}.{len(str(a))}D{len(str(b))}D"
    return f"{shape}.REG{REGROUPS[op](a, b)}" if op in REGROUPS else shape


def _missing_distractors(op: str, a: int, b: int, ans: int, hidden_key: str, hidden: int) -> dict[str, int]:
    """Mirrors items.missing_number: the wrong answers are about the hidden number, not a op b."""
    if hidden_key == "answer":
        return M.predict(op, a, b)
    if hidden_key == "remainder":  # 85 ÷ 4 = 21 r □: found by taking away (`divide_kinds`, ADR 0058)
        return DK.remainder_mistakes(a, b)
    if O.sign(op) in ("×", "÷"):  # × read as +, ÷ as −, the table one row out, a zero too few (`facts_kinds`)
        return FK.missing_mistakes(O.sign(op) or op, a, b, hidden_key)
    known = b if hidden_key == "a" else a
    if op not in REGROUPS:
        return {}
    if op == "-" and hidden_key == "a":
        mis = {"M_SUB_INSTEAD": abs(ans - b), "M_FACT_PM1": hidden - 1}
    elif op == "-":
        mis = {"M_ADD_INSTEAD": a + ans, "M_FACT_PM1": hidden + 1}
    else:
        mis = {"M_ADD_INSTEAD": known + ans, "M_FACT_PM1": hidden + 1}
    return {k: v for k, v in mis.items() if v != hidden and v >= 0}


def division(
    a: int,
    b: int,
    rung: str,
    layout: str = "horizontal",
    shape: str | None = None,
    skills: list[str] | None = None,
) -> Item:
    """a ÷ b as a child answers it: the quotient's box, and the remainder's after "r" where there is one (ADR 0056),
    each keyed by the mistakes predicted for it (`division.boxes`). In a line, in the division layout (`layout`
    "column"), or asked in words, its sentence a row (`shape`: "How many 6s make 42?")."""
    fmt = "column_grid" if layout == "column" else "bare_sum"
    stem = W.templates(fmt, "÷", shape)[0]["text"].format(a=a, b=b) if shape else ""
    # asked in words, the sentence is what is printed (`text`, as a missing number's line is), never the line too
    spec: dict[str, Any] = dict(a=a, b=b, op="÷", layout=layout) | (
        {"shape": shape, "text": stem} if shape else {}
    )
    signal, lines, _ = FORMATS[fmt]
    return item(
        _template("÷", a, b),
        rung,
        signal,
        fmt,
        stem,
        spec,
        DV.boxes(a, b),
        working_lines=lines,
        skills=skills,
    )


def to_item(c: dict[str, Any], rung: str, skills: list[str] | None = None):
    fmt, op, a, b = c["format"], c["op"], c["a"], c["b"]
    if fmt in ("bare_sum", "column_grid") and O.sign(op) == "÷":  # a division's own boxes (ADR 0056)
        return division(a, b, rung, "column" if fmt == "column_grid" else "horizontal", skills=skills)
    signal, lines, _ = FORMATS[fmt]
    stem = (c.get("stem") or "").strip()

    if fmt == "missing_number":
        # 85 ÷ □ = 21 r 1 and 85 ÷ 4 = 21 r □ leave a remainder; every other missing number is exact
        ans, rem = O.divide(a, b) if O.sign(op) == "÷" else (M.compute(op, a, b), 0)
        hidden = {"a": a, "b": b, "answer": ans, "both": a, "remainder": rem}[c["missing"]]
        mis = _missing_distractors(op, a, b, ans, c["missing"], hidden)
        r = Response("ans", "digits", str(hidden), cells=cells(max(a, b, ans)), misconceptions=mis)
        # The renderer reads only `text`; a, b, op, missing are kept so recheck and the tag
        # deriver can see the arithmetic behind the box, and a box written first says so.
        spec = dict(text=stem, a=a, b=b, op=op, missing=c["missing"])
        return item(
            "MISSING.NUM",
            rung,
            signal,
            fmt,
            stem,
            spec | ({"answer_first": "YES"} if c.get("answer_first") else {}),
            [r],
            working_lines=lines,
            skills=skills,
        )

    ans = M.compute(op, a, b)
    mis = M.predict(op, a, b)
    table = M.TABLES.get(op, {})
    mis |= {m["code"]: m["wrong_answer"] for m in c.get("misconceptions", []) if m["code"] not in table}
    if fmt == "word_1step":
        mis["M_WRONG_OP"] = abs(a - b) if op == "+" else a + b
        # keyed as the drawer keys it when a template wrote its words (the sampler's do); a model's sentence names no
        # shape, so it is keyed by its numbers, as it always was (ADR 0053)
        found = W.template_of(stem)
        tpl = found if found and found["op"] == op else None
        return item(
            "WP1",
            rung,
            signal,
            fmt,
            stem,
            W.story_spec(tpl, a=a, b=b) if tpl else dict(a=a, b=b, op=op),
            [
                Response(
                    "ans",
                    "digits",
                    str(ans),
                    cells=cells(max(ans, a + b)),
                    misconceptions=W.added_as(tpl, mis),
                )
            ],
            working_lines=lines,
            skills=skills,
        )
    layout = "column" if fmt == "column_grid" else "horizontal"
    if (
        fmt == "column_grid" and op == "×"
    ):  # a long multiplication's rows added without a carry (A11, ADR 0055)
        mis |= {c: v for c, v in WM.rows_added(a, b).items() if v not in mis.values()}
    r = Response("ans", "digits", str(ans), cells=cells(max(ans, a)), misconceptions=mis)
    return item(
        _template(op, a, b),
        rung,
        signal,
        fmt,
        "",
        dict(a=a, b=b, op=op, layout=layout),
        [r],
        working_lines=lines,
        skills=skills,
    )
