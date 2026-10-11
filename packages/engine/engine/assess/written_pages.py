"""The written methods as the child meets them on the page (`written_methods`, ADR 0055): every step a box where it is
worked, set out as the school sets the method out. Pure: HTML fragments, read back by the key's geometry
(`render.render_sheet`), so the reader finds every box and marking marks each by itself.

Partitioning a line for each part, then the total, a division's remainder after "r" beside its part and its total;
expanded columns the numbers in columns and a row of boxes for each product, its sum written beside it; a grid headed by
its parts, a box in every cell; a lattice a cell for every pair of digits, its two boxes either side of the diagonal,
the tens above."""

import html
from collections.abc import Callable
from typing import Any

from engine.assess import written_methods as WM
from engine.assess.answer_space import with_remainder
from engine.assess.items import Response

Boxes = Callable[[Response, bool], str]


def _rest(rid: str, R: dict[str, Response]) -> Response | None:
    """A division's remainder, printed after "r" beside the box it belongs to: the total's `rem`, a part's `s2r`."""
    return R.get("rem" if rid == "ans" else f"{rid}r")


def _steps(R: dict[str, Response]) -> list[Response]:
    """Every step's box, a remainder's left to the line of the box it belongs to."""
    rests = {"rem", *(f"{rid}r" for rid in R)}
    return [r for rid, r in R.items() if rid != "ans" and rid not in rests]


def _line(r: Response, box: Boxes, big: bool, R: dict[str, Response] | None = None) -> str:
    rest = _rest(r.rid, R or {})
    boxes = with_remainder(box(r, big), box(rest, big) if rest else None)
    return f'<div class="row step"><span class="eq">{html.escape(r.label)}</span>{boxes}</div>'


def partitioning(sp: dict[str, Any], R: dict[str, Response], box: Boxes, big: bool) -> str:
    lines = "".join(_line(r, box, big, R) for r in _steps(R))
    return f'<div class="method">{lines}{_line(R["ans"], box, big, R)}</div>'


def digits(n: int | str, width: int) -> str:
    """A number's digits, one to a column, right-aligned in `width` columns."""
    return "".join(f'<span class="xd">{c.strip()}</span>' for c in str(n).rjust(width))


def expanded_columns(sp: dict[str, Any], R: dict[str, Response], box: Boxes, big: bool) -> str:
    """34 × 6 in columns, then 4 × 6 and 30 × 6 each in a row of its own, then the total: every row right-aligned by its
    ones, so a product's place is where the child writes it."""
    a, b = sp["a"], sp["b"]
    width = max(len(str(a)), len(str(b)) + 1, *(len(r.answer) for r in R.values()))
    top = f'<span></span><span class="xn">{digits(a, width)}</span>'
    times = f'<span class="xop">×</span><span class="xn">{digits(b, width)}</span>'
    rows = "".join(
        f'<span class="lab">{html.escape(r.label.rstrip(" ="))}</span><span class="xn">{box(r, big)}</span>'
        for r in _steps(R)
    )
    total = f'<span class="lab">total</span><span class="xn sum">{box(R["ans"], big)}</span>'
    return f'<div class="expanded" style="--w:{width}">{top}{times}{rows}{total}</div>'


def grid_method(sp: dict[str, Any], R: dict[str, Response], box: Boxes, big: bool) -> str:
    """The parts of the number with more across the top, the other's down the side, a box in every cell (the cells
    in `written_methods._grid`'s order, a row at a time), then the cells added."""
    top, side, _ = WM.grid_axes(sp["a"], sp["b"])
    cells = iter(_steps(R))
    head = "".join(f"<th>{t}</th>" for t in top)
    body = "".join(
        f"<tr><th>{s}</th>" + "".join(f"<td>{box(next(cells), big)}</td>" for _ in top) + "</tr>"
        for s in side
    )
    return f'<table class="gridm"><tr><th>×</th>{head}</tr>{body}</table>{_line(R["ans"], box, big)}'


def lattice(sp: dict[str, Any], R: dict[str, Response], box: Boxes, big: bool) -> str:
    """The digits of one number across the top, the other's down the right side, a cell for every pair: its product's
    tens above the diagonal and its ones below (`written_methods._lattice`, a row at a time), then the answer."""
    a, b = str(sp["a"]), str(sp["b"])
    cells = iter(_steps(R))
    head = "".join(f"<th>{d}</th>" for d in a)
    body = "".join(
        "<tr>" + "".join(f'<td class="lat">{box(next(cells), big)}</td>' for _ in a) + f"<th>{d}</th></tr>"
        for d in b
    )
    return f'<table class="lattice"><tr>{head}<th></th></tr>{body}</table>{_line(R["ans"], box, big)}'


DRAW: dict[str, Callable[[dict[str, Any], dict[str, Response], Boxes, bool], str]] = {
    "partitioning": partitioning,
    "expanded_columns": expanded_columns,
    "grid_method": grid_method,
    "lattice": lattice,
}
