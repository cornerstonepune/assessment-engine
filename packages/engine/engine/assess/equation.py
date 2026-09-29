"""The equation a group of answer boxes completes, held by code (goals/s24-a-split-that-holds-is-right.yaml).

"638 = 600 + [ ] + [ ]" is right for 30 and 8, and for 19 and 19: 600 + 19 + 19 is 638 (Nimish, 2026-09-29). A paper
names the equation once, each box by its question and part — `638 = 600 + {5a} + {5b}` — and a box is right when the
side it is written on comes out at the equation's total with what the child wrote there. The total is the side of the
question's own numbers, so each other side is its own claim: in "638 + 475 = {5f} + {5g} + {5h} = {5i}", 1100 + 0 + 13
is a right split beside a total of 1112, which is not. Whole numbers, + and − only: an equation code cannot read, or
that the paper's own key does not make true, is refused when the paper is entered, never guessed at when it is marked.
"""

import re

_TERM = re.compile(r"\d+|\{\w+\}")
_SIGN = {"+": 1, "-": -1, "−": -1}


def refs(expr):
    return re.findall(r"\{(\w+)\}", expr)


def _side(text, expr):
    tokens = re.findall(r"\{\w+\}|\d+|\S", text)
    if len(tokens) % 2 == 0:
        raise ValueError(f"{expr!r}: {text.strip() or 'an empty side'!r} is not a sum code can read")
    out, sign = [], 1
    for i, t in enumerate(tokens):
        if i % 2 == 0 and not _TERM.fullmatch(t) or i % 2 == 1 and t not in _SIGN:
            raise ValueError(f"{expr!r}: {t!r} is not a number, a box or + and −")
        if i % 2 == 0:
            out.append((sign, int(t) if t.isdigit() else t[1:-1]))
        else:
            sign = _SIGN[t]
    return out


def _boxes(side):
    return [term for _, term in side if isinstance(term, str)]


def _sum(side, values):
    return sum(sign * (values[term] if isinstance(term, str) else term) for sign, term in side)


def check(expr):
    """The equation, read → (its total, [[(sign, number or box)] for each side with a box]). ValueError when code
    cannot read it, or when no side is numbers only (nothing says what the boxes must come to), or two such disagree."""
    sides = expr.split("=")
    if len(sides) < 2:
        raise ValueError(f"{expr!r} is not an equation")
    read = [_side(s, expr) for s in sides]
    totals = {_sum(s, {}) for s in read if not _boxes(s)}
    if len(totals) != 1:
        raise ValueError(
            f"{expr!r}: {'its sides of numbers disagree' if totals else 'no side is numbers only'}"
        )
    return totals.pop(), [s for s in read if _boxes(s)]


def right(expr, values):
    """{box: True when the side it is on comes out at the total with `values` put in, False when it does not, None
    while a box of that side is not known}. `values`: {box: what the child wrote}; anything not a whole number is
    not known."""
    total, sides = check(expr)
    known = {b: int(v) for b, v in values.items() if re.fullmatch(r"-?\d+", str(v))}
    out = {}
    for side in sides:
        boxes = _boxes(side)
        out |= dict.fromkeys(boxes, _sum(side, known) == total if set(boxes) <= set(known) else None)
    return out


def of(item, paper):
    """A paper's printed question → {"holds": its equation}, or {} when it names none. Refused unless code can read it,
    it names the question's own box and only the paper's, and the paper's own key makes every box right."""
    expr = item.get("holds")
    if not expr:
        return {}
    key = {f"{it['n']}{it.get('part', '')}": it.get("answer") for it in paper["items"]}
    boxes = refs(expr)
    if f"{item['n']}{item.get('part', '')}" not in boxes or not set(boxes) <= set(key):
        raise ValueError(f"{expr!r} must name its own question's box, and only boxes of this paper")
    if not all(right(expr, {b: key[b] for b in boxes}).values()):
        raise ValueError(f"{expr!r} is not made true by the paper's own key { ({b: key[b] for b in boxes}) }")
    return {"holds": expr}
