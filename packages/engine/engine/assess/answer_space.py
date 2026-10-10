"""Where a child writes on a printed paper: the answer boxes, the ticks, the working space and the column grid.
Pure: HTML fragments, read back by the key's geometry (`render.render_sheet`) and the marker.

As many boxes as the right answer has digits (goals/s15-answer-boxes.yaml); in columns the numbers still line up
by their ones, and only the answer's own columns have boxes.
"""

import html
from typing import TYPE_CHECKING, Any

from engine.assess import operations as O

if TYPE_CHECKING:
    from engine.assess.items import Response


def _boxes(r: "Response", rule: str = "digits") -> int:
    """As many boxes as the right answer has digits (Nimish, 2026-09-23: four boxes for a one- or two-digit answer
    confused the children). A response with no written number keeps the room its question set — as every answer
    did in the layout before L3 (`rule` "cells", a `render.layouts` row: goals/s18-read-as-printed.yaml)."""
    ans = str(r.answer or "")
    return len(ans) if rule == "digits" and r.kind == "digits" and ans.isdigit() else max(1, r.cells)


def cells(
    sheet_id: str, item_id: str, r: "Response", big: bool = False, cls: str = "", boxes: str = "digits"
) -> str:
    n = _boxes(r, boxes)
    s = "".join(
        f'<span class="cell {cls}" data-s="{sheet_id}" data-i="{item_id}" data-r="{r.rid}" data-k="{k}"></span>'
        for k in range(n)
    )
    return f'<span class="cells{" big" if big else ""}" data-resp="{item_id}|{r.rid}">{s}</span>'


def ticks(sheet_id, item_id, r, labels=None):
    out = []
    for j, o in enumerate(r.options):
        lab = (labels or {}).get(o, o)
        out.append(
            f'<span class="tickopt"><span class="tick" data-s="{sheet_id}" data-i="{item_id}" data-r="{r.rid}" data-k="{j}" data-opt="{html.escape(o)}"></span>{html.escape(lab)}</span>'
        )
    return f'<span data-resp="{item_id}|{r.rid}">{"".join(out)}</span>'


def textbox(sheet_id, item_id, r, h=16):
    return f'<div class="textbox" data-resp="{item_id}|{r.rid}" data-s="{sheet_id}" data-i="{item_id}" data-r="{r.rid}" data-k="0" style="min-height:{h}mm"></div>'


def working(lines):
    if not lines:
        return ""
    return f'<div class="work h{min(lines, 4)}">working</div>'


def grid(
    sheet_id: str,
    item_id: str,
    rows: list[int],
    op: str,
    ans_resp: Any,
    carry: bool = True,
    boxes: str = "digits",
    long_rows: bool = True,
) -> str:
    """rows: list of ints (addends or minuend/subtrahend), lined up by the ones under as many columns as the widest
    number or the answer needs; the answer row has a box only under the answer's own digits."""
    count = _boxes(ans_resp, boxes)
    worked = _rows_worked(rows, op) if long_rows else []  # a layout before 2026-10-09 printed none
    w = max([count, *(len(str(x)) for x in (*rows, *worked))])
    out = ['<div class="grid" style="grid-template-columns: 8.4mm repeat(%d, 8.4mm)">' % w]
    if carry:
        out.append('<div class="g blank"></div>' + "".join('<div class="g carry"></div>' for _ in range(w)))
    for idx, n in enumerate(rows):
        s = str(n).rjust(w)
        opch = "" if idx == 0 else op_sign(op)
        out.append(
            f'<div class="g op">{opch if idx == len(rows) - 1 else ""}</div>'
            + "".join(f'<div class="g">{c.strip() or ""}</div>' for c in s)
        )
    for k in range(len(worked)):  # the rows of a long multiplication, the last added with its +
        out.append(
            f'<div class="g op">{"+" if k == len(worked) - 1 else ""}</div>'
            + '<div class="g worked"></div>' * w
        )
    out.append(
        '<div class="g blank"></div>'
        + '<div class="g blank"></div>' * (w - count)
        + "".join(
            f'<div class="g ans cell" data-s="{sheet_id}" data-i="{item_id}" data-r="{ans_resp.rid}" data-k="{k}"></div>'
            for k in range(count)
        )
    )
    out.append("</div>")
    return f'<span data-resp="{item_id}|{ans_resp.rid}">{"".join(out)}</span>'


def divided(sheet_id: str, item_id: str, a: int, b: int, ans: Any, tail: str = "") -> str:
    """The division layout as the school writes it (D01, 84 ÷ 4): the quotient's boxes on top, one over each digit of
    the number divided, so 156 ÷ 4 = 39 is written over the 5 and the 6 and the box over the 1 stays empty; then the
    divisor and the number divided under its bar; `tail`, "r" and the remainder's boxes as the paper's layout draws
    them, beside the quotient where there is a remainder (ADR 0056)."""
    w = len(str(a))
    top = "".join(
        f'<div class="g ans cell" data-s="{sheet_id}" data-i="{item_id}" data-r="{ans.rid}" data-k="{k}"></div>'
        for k in range(w)
    )
    under = f'<div class="g dv">{b}</div>' + "".join(f'<div class="g dd">{d}</div>' for d in str(a))
    grid = f'<div class="grid" style="grid-template-columns: auto repeat({w}, 8.4mm)"><div class="g blank"></div>{top}{under}</div>'
    return f'<span class="divide"><span data-resp="{item_id}|{ans.rid}">{grid}</span>{tail}</span>'


def _rows_worked(rows: list[int], op: str) -> list[int]:
    """A long multiplication's rows, one for each digit of its multiplier (68 × 17 is 476 and 680), where it has two or
    more; nothing for any other sum. Their room is drawn, never their numbers: the child writes them."""
    if O.sign(op) != "×" or len(rows) != 2 or min(len(str(n)) for n in rows) < 2 or max(rows) <= 12:
        return []  # a table fact in columns (11 × 12) is recalled, not worked in rows
    top, multiplier = (rows[1], rows[0]) if len(str(rows[0])) < len(str(rows[1])) else (rows[0], rows[1])
    worked = O.rows(top, multiplier)
    return worked if len(worked) >= 2 else []


def op_sign(o: str) -> str:
    return "−" if o == "-" else o
