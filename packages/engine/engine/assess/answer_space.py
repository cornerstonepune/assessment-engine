"""Where a child writes on a printed paper: the answer boxes, the ticks, the working space and the column grid.
Pure: HTML fragments, read back by the key's geometry (`render.render_sheet`) and the marker.

As many boxes as the right answer has digits (goals/s15-answer-boxes.yaml); in columns the numbers still line up
by their ones, and only the answer's own columns have boxes.
"""

import html


def _boxes(r):
    """As many boxes as the right answer has digits (Nimish, 2026-09-23: four boxes for a one- or two-digit answer
    confused the children). A response with no written number keeps the room its question set."""
    ans = str(r.answer or "")
    return len(ans) if r.kind == "digits" and ans.isdigit() else max(1, r.cells)


def _cells(sheet_id, item_id, r, big=False, cls=""):
    n = _boxes(r)
    s = "".join(
        f'<span class="cell {cls}" data-s="{sheet_id}" data-i="{item_id}" data-r="{r.rid}" data-k="{k}"></span>'
        for k in range(n)
    )
    return f'<span class="cells{" big" if big else ""}" data-resp="{item_id}|{r.rid}">{s}</span>'


def _ticks(sheet_id, item_id, r, labels=None):
    out = []
    for j, o in enumerate(r.options):
        lab = (labels or {}).get(o, o)
        out.append(
            f'<span class="tickopt"><span class="tick" data-s="{sheet_id}" data-i="{item_id}" data-r="{r.rid}" data-k="{j}" data-opt="{html.escape(o)}"></span>{html.escape(lab)}</span>'
        )
    return f'<span data-resp="{item_id}|{r.rid}">{"".join(out)}</span>'


def _text(sheet_id, item_id, r, h=16):
    return f'<div class="textbox" data-resp="{item_id}|{r.rid}" data-s="{sheet_id}" data-i="{item_id}" data-r="{r.rid}" data-k="0" style="min-height:{h}mm"></div>'


def _work(lines):
    if not lines:
        return ""
    return f'<div class="work h{min(lines, 4)}">working</div>'


def _grid(sheet_id, item_id, rows, op, ans_resp, carry=True):
    """rows: list of ints (addends or minuend/subtrahend), lined up by the ones under as many columns as the widest
    number or the answer needs; the answer row has a box only under the answer's own digits."""
    boxes = _boxes(ans_resp)
    w = max([boxes, *(len(str(n)) for n in rows)])
    out = ['<div class="grid" style="grid-template-columns: 8.4mm repeat(%d, 8.4mm)">' % w]
    if carry:
        out.append('<div class="g blank"></div>' + "".join('<div class="g carry"></div>' for _ in range(w)))
    for idx, n in enumerate(rows):
        s = str(n).rjust(w)
        opch = "" if idx == 0 else _op(op)
        out.append(
            f'<div class="g op">{opch if idx == len(rows) - 1 else ""}</div>'
            + "".join(f'<div class="g">{c.strip() or ""}</div>' for c in s)
        )
    out.append(
        '<div class="g blank"></div>'
        + '<div class="g blank"></div>' * (w - boxes)
        + "".join(
            f'<div class="g ans cell" data-s="{sheet_id}" data-i="{item_id}" data-r="{ans_resp.rid}" data-k="{k}"></div>'
            for k in range(boxes)
        )
    )
    out.append("</div>")
    return f'<span data-resp="{item_id}|{ans_resp.rid}">{"".join(out)}</span>'


def _op(o):
    return "−" if o == "-" else o
