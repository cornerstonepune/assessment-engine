"""Stories whose template says its own numbers and its answer (goals/md4d1-times-stories.yaml; the taxonomy's A9).

A template row in `word_templates.json` that carries `numbers` and `answer` is a story of this kind: `numbers` gives
the range each number may take ([lo, hi], or one value: half as many is ÷ 2), so its numbers make sense — never 933
pencils in a box; `answer` is the formula the child works ("a*b+c", "(a+b)/c", "a/(b+1)"); `also` names each mistake by
the formula of the wrong answer it writes ("a*b": one step only); `least` is the smallest answer that asks something,
and `differ` the numbers the story must tell apart. Every division in the answer comes out exact or the
numbers are drawn again, so a story never asks for 2.5 pens. Used for times as many, the smaller and how many times,
half as many, the two-step stories with × and ÷, a number the story does not need and a price list; the older stories
keep their own makers (`words`, `divide_stories`). Deterministic given an RNG; pure: no I/O."""

import ast
import operator
import random
from collections.abc import Callable
from fractions import Fraction
from typing import Any, cast

from . import words as W
from .items import Item, Response, cells, item

UNFIT = "these numbers do not make this story; draw again"
OPS: dict[type[ast.operator], Callable[[Fraction, Fraction], Fraction]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
}


class Inexact(ValueError):
    """A division in a story's formula that does not come out exact."""


def value(formula: str, nums: dict[str, int]) -> int:
    """A template's formula worked on its numbers: + − × ÷ and brackets, every ÷ exact (`Inexact` otherwise)."""
    return int(_walk(ast.parse(formula, mode="eval").body, nums))


def _walk(node: ast.expr, nums: dict[str, int]) -> Fraction:
    if isinstance(node, ast.Name):
        return Fraction(nums[node.id])
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return Fraction(node.value)
    if isinstance(node, ast.BinOp):
        left, right = _walk(node.left, nums), _walk(node.right, nums)
        if isinstance(node.op, ast.Div):
            if right == 0 or (left / right).denominator != 1:
                raise Inexact(f"{left} ÷ {right} is not exact")
            return left / right
        return OPS[type(node.op)](left, right)
    raise ValueError(f"a story's formula is + − × ÷ of its numbers, not {ast.dump(node)}")


def _drawn(rng: random.Random, numbers: dict[str, Any]) -> dict[str, int]:
    out: dict[str, int] = {}
    for k, span in numbers.items():
        if isinstance(span, list):
            lo_hi = cast(list[int], span)
            out[k] = rng.randint(lo_hi[0], lo_hi[-1])
        else:
            out[k] = int(span)
    return out


def _mistakes(tpl: dict[str, Any], nums: dict[str, int], right: int) -> dict[str, int]:
    """Each mistake its template names, by the wrong answer it writes; one whose division is not exact, or that lands
    on the right answer, says nothing about this story's numbers and is left out."""
    out: dict[str, int] = {}
    also: dict[str, str] = tpl.get("also") or {}
    for code, formula in also.items():
        try:
            wrong = value(formula, nums)
        except Inexact:
            continue
        if wrong != right and wrong >= 0:
            out[code] = wrong
    return out


def make(rng: random.Random, rung: str, tpl: dict[str, Any]) -> Item:
    """One story of this template: its numbers drawn in their ranges, its answer worked, each division exact. Raises
    RuntimeError when this draw's numbers do not make it (the drawer draws again)."""
    nums = _drawn(rng, tpl["numbers"])
    if any(nums[x] == nums[y] for x, y in tpl.get("differ", [])):
        raise RuntimeError(
            UNFIT
        )  # two numbers the story tells apart: 2 pencils cost ₹50, what do 2 pencils cost?
    try:
        right = value(tpl["answer"], nums)
    except Inexact as e:
        raise RuntimeError(UNFIT) from e
    if right < tpl.get(
        "least", 1
    ):  # how many times, the smaller, a half: a story whose answer is 1 asks nothing
        raise RuntimeError(UNFIT)
    mis = _mistakes(tpl, nums, right)
    if not mis:
        raise RuntimeError(UNFIT)  # every question names a mistake its wrong answer shows
    n, n2 = rng.sample(W.NAMES, 2)
    stem = tpl["text"].format(**nums, n=n, n2=n2)
    widest = max([right, *nums.values()])
    r = Response("ans", "digits", str(right), cells=cells(widest), misconceptions=mis)
    lines = 4 if tpl["fmt"] == "word_2step" else 3
    kind = "WP2" if tpl["fmt"] == "word_2step" else "WP1"
    return item(
        kind, rung, "Application", tpl["fmt"], stem, W.story_spec(tpl, **nums), [r], working_lines=lines
    )


def pool(fmt: str, structure: Any, op: str | None, table: bool) -> list[dict[str, Any]]:
    """The templates of this kind a case asks for: its kind, its shape, its operation where it names one, and a price
    list only where the case reads from a table (the cost of many, with no table, is an older story)."""
    shape = structure if isinstance(structure, str) else None
    return [
        t
        for t in W.templates(fmt, structure=shape)
        if W.owns(t) and (op is None or op in t["op"]) and bool(t.get("table")) == table and shape is not None
    ]
