"""The equation a group of answer boxes completes, held by code (goals/s24-a-split-that-holds-is-right.yaml).

"638 = 600 + [ ] + [ ]" is right for 30 and 8, and for 19 and 19: 600 + 19 + 19 is 638 (Nimish, 2026-09-29). A paper
names the equation once, each box by its question and part — `638 = 600 + {5a} + {5b}` — and a box is right when the
side it is written on comes out at the equation's total with what the child wrote there. The total is the side of the
question's own numbers, so each other side is its own claim: in "638 + 475 = {5f} + {5g} + {5h} = {5i}", 1100 + 0 + 13
is a right split beside a total of 1112, which is not. Whole numbers and the four printed signs, × and ÷ before + and
−, left to right, as a child is taught (goals/md0b-division-is-an-operation.yaml); a side is worked exactly, so
"{a} ÷ 4 = 21" is not right for 85. An equation code cannot read, or that the paper's own key does not make true, is
refused when the paper is entered, never guessed at when it is marked.
"""

import re
from fractions import Fraction
from typing import Any

from . import operations as O

_TERM = re.compile(r"\d+|\{\w+\}")
Atom = int | str  # a number, or a box's name
Side = list[tuple[int, list[tuple[str, Atom]]]]  # its terms: + or −, then a run of × and ÷ factors


def refs(expr: str) -> list[str]:
    return re.findall(r"\{(\w+)\}", expr)


def _side(text: str, expr: str) -> Side:
    """A side → [(+1 or −1, [(× or ÷, number or box), …])]: its terms, each a run of factors."""
    tokens: list[str] = re.findall(r"\{\w+\}|\d+|\S", text)
    if len(tokens) % 2 == 0:
        raise ValueError(f"{expr!r}: {text.strip() or 'an empty side'!r} is not a sum code can read")
    out: Side = []
    sign, op = 1, "×"
    for i, t in enumerate(tokens):
        if i % 2 == 0 and not _TERM.fullmatch(t) or i % 2 == 1 and t not in O.PRINTED_SIGNS:
            raise ValueError(f"{expr!r}: {t!r} is not a number, a box or a printed sign")
        if i % 2 == 0:
            atom: Atom = int(t) if t.isdigit() else t[1:-1]
            if op in ("+", "-"):
                out.append((sign, [("×", atom)]))
            elif out:
                out[-1][1].append((op, atom))
            else:
                out.append((1, [("×", atom)]))
        else:
            op = O.sign(t) or ""
            sign = {"+": 1, "-": -1}.get(op, sign)
    return out


def _boxes(side: Side) -> list[str]:
    return [atom for _, factors in side for _, atom in factors if isinstance(atom, str)]


def _value(side: Side, values: dict[str, int]) -> Fraction | None:
    """What a side comes to, exactly; None where it divides by 0."""
    total = Fraction(0)
    for sign, factors in side:
        term = Fraction(1)
        for op, atom in factors:
            n = Fraction(values[atom] if isinstance(atom, str) else atom)
            if op == "÷" and n == 0:
                return None
            term = term / n if op == "÷" else term * n
        total += sign * term
    return total


def check(expr: str) -> tuple[int, list[Side]]:
    """The equation, read → (its total, [side for each side with a box]). ValueError when code cannot read it, when no
    side is numbers only (nothing says what the boxes must come to), when two such disagree, or when the total is not a
    whole number."""
    sides = expr.split("=")
    if len(sides) < 2:
        raise ValueError(f"{expr!r} is not an equation")
    read = [_side(s, expr) for s in sides]
    totals = {_value(s, {}) for s in read if not _boxes(s)}
    if len(totals) != 1:
        raise ValueError(
            f"{expr!r}: {'its sides of numbers disagree' if totals else 'no side is numbers only'}"
        )
    total = totals.pop()
    if total is None:
        raise ValueError(f"{expr!r}: its total divides by 0")
    if total.denominator != 1:
        raise ValueError(f"{expr!r}: its total is not a whole number")
    return int(total), [s for s in read if _boxes(s)]


def right(expr: str, values: dict[str, Any]) -> dict[str, bool | None]:
    """{box: True when the side it is on comes out at the total with `values` put in, False when it does not, None
    while a box of that side is not known}. `values`: {box: what the child wrote}; anything not a whole number is
    not known."""
    total, sides = check(expr)
    known = {b: int(v) for b, v in values.items() if re.fullmatch(r"-?\d+", str(v))}
    out: dict[str, bool | None] = {}
    for side in sides:
        boxes = _boxes(side)
        out |= dict.fromkeys(boxes, _value(side, known) == total if set(boxes) <= set(known) else None)
    return out


def of(item: dict[str, Any], paper: dict[str, Any]) -> dict[str, str]:
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
