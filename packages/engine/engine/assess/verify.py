"""Every number a model writes is recomputed here before an item exists (ADR 0005).

`problems` returns the reasons a candidate fails, empty when it passes. `to_item` turns an
accepted candidate into the same `Item` the deterministic generators build, so the renderer, the
marker and the tag deriver cannot tell the two apart — and the same operands produce the same
item_key from either path, which is what stops the bank holding one sum twice.
"""
from . import misconceptions as M
from .items import Response, _cells, _item, _regroup_count_add, _regroup_count_sub

FORBIDDEN_WORDS = ("borrow",)
# fmt -> (signal, working_lines, needs_stem); mirrors what items.py gives each format
FORMATS = {
    "column_grid":    ("Procedural",  0, False),
    "bare_sum":       ("Procedural",  3, False),
    "missing_number": ("Conceptual",  1, True),
    "word_1step":     ("Application", 3, True),
}
REGROUPS = {"+": _regroup_count_add, "-": _regroup_count_sub}
OPS = {"−": "-", "–": "-", "x": "×", "X": "×", "*": "×"}  # symbols a model writes for the same operation


def normalise(c):
    """The model's symbol for an operation, folded to the one the rules use. Nothing else changes."""
    return c | {"op": OPS.get(c.get("op"), c.get("op"))}


def problems(c, check):
    fmt = c.get("format")
    if fmt not in FORMATS:
        return [f"format {fmt!r} is not one the bank can render"]
    op, a, b, answer = c.get("op"), c.get("a"), c.get("b"), c.get("answer")
    if op != check["op"]:
        return [f"op {op!r} is not the rule's {check['op']!r}"]
    if not all(isinstance(x, int) for x in (a, b, answer)):
        return ["operands and answer must be integers"]

    out = []
    correct = M.compute(op, a, b)
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
        out.append("across-zero rule: " + ("needs a zero in a lender column" if check["across_zero"]
                                           else "must not have a zero in a lender column"))
    if correct < check.get("min_answer", 1 if op == "-" else 0):
        out.append(f"answer {correct} below the minimum")
    if check.get("max_total") and correct > check["max_total"]:
        out.append(f"answer {correct} above max_total {check['max_total']}")

    truth, table = M.predict(op, a, b), M.TABLES.get(op, {})
    for mc in c.get("misconceptions", []):
        code, wrong = mc.get("code"), mc.get("wrong_answer")
        if code not in table:
            continue  # no predictor: the claim is accepted as the model's (ADR 0005)
        if code not in truth:
            out.append(f"{code} cannot occur on {a} {op} {b}")
        elif truth[code] != wrong:
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
    if fmt == "missing_number" and c.get("missing") not in ("a", "b", "answer"):
        out.append("missing must be a, b or answer")
    return out


def _template(op, a, b):
    if op in REGROUPS:
        return f"{'ADD' if op == '+' else 'SUB'}.{len(str(a))}D{len(str(b))}D.REG{REGROUPS[op](a, b)}"
    return f"MUL.{len(str(a))}D{len(str(b))}D"


def _missing_distractors(op, a, b, ans, hidden_key, hidden):
    """Mirrors items.missing_number: the wrong answers are about the hidden number, not a op b."""
    if hidden_key == "answer":
        return M.predict(op, a, b)
    known = b if hidden_key == "a" else a
    if op == "-" and hidden_key == "a":
        mis = {"M_SUB_INSTEAD": abs(ans - b), "M_FACT_PM1": hidden - 1}
    elif op == "-":
        mis = {"M_ADD_INSTEAD": a + ans, "M_FACT_PM1": hidden + 1}
    else:
        mis = {"M_ADD_INSTEAD": known + ans, "M_FACT_PM1": hidden + 1}
    return {k: v for k, v in mis.items() if v != hidden and v >= 0}


def to_item(c, rung, skills=None):
    fmt, op, a, b = c["format"], c["op"], c["a"], c["b"]
    signal, lines, _ = FORMATS[fmt]
    ans = M.compute(op, a, b)
    stem = (c.get("stem") or "").strip()

    if fmt == "missing_number":
        hidden = {"a": a, "b": b, "answer": ans}[c["missing"]]
        mis = _missing_distractors(op, a, b, ans, c["missing"], hidden)
        r = Response("ans", "digits", str(hidden), cells=_cells(max(a, b, ans)), misconceptions=mis)
        # The renderer reads only `text`; a, b, op, missing are kept so recheck and the tag
        # deriver can see the arithmetic behind the box.
        return _item("MISSING.NUM", rung, signal, fmt, stem, dict(text=stem, a=a, b=b, op=op, missing=c["missing"]),
                     [r], working_lines=lines, skills=skills)

    mis = M.predict(op, a, b)
    table = M.TABLES.get(op, {})
    mis |= {m["code"]: m["wrong_answer"] for m in c.get("misconceptions", []) if m["code"] not in table}
    if fmt == "word_1step":
        mis["M_WRONG_OP"] = abs(a - b) if op == "+" else a + b
        return _item("WP1", rung, signal, fmt, stem, dict(a=a, b=b, op=op),
                     [Response("ans", "digits", str(ans), cells=_cells(max(ans, a + b)), misconceptions=mis)],
                     working_lines=lines, skills=skills)
    layout = "column" if fmt == "column_grid" else "horizontal"
    r = Response("ans", "digits", str(ans), cells=_cells(max(ans, a)), misconceptions=mis)
    return _item(_template(op, a, b), rung, signal, fmt, "", dict(a=a, b=b, op=op, layout=layout), [r],
                 working_lines=lines, skills=skills)
