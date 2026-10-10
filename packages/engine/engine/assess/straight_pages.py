"""A calculation's question and its boxes on the page, and the kinds made of one (`render.render_item`): a sum in a
line or in columns, a division in its layout with its exchanges; a missing digit; an estimate, then the calculation; the
quickest method. Pure: HTML fragments, read back by the key's geometry (`render.render_sheet`)."""

import dataclasses
import html
from collections.abc import Callable
from typing import Any

from engine.assess import answer_space
from engine.assess import operations as O
from engine.assess.answer_space import op_sign, textbox, ticks, working
from engine.assess.items import Response


def straight(
    sid: str,
    it: Any,
    R: dict[str, Response],
    cells: Callable[..., str],
    grid: Callable[..., str],
    big: bool,
    layout: dict[str, Any] | None = None,
) -> tuple[str, str]:
    """A straight calculation's question and its boxes: in a line ("85 ÷ 4 = □ r □", a remainder's box after "r"
    where there is one), in columns, or in the division layout (`answer_space.divided`), each exchange in a small box
    where the paper's layout writes them (`exchanges`, a `render.layouts` row); a division asked in words prints its
    sentence alone ("How many 6s make 42?")."""
    sp, rem = it.spec, R.get("rem")
    tail = f'<span class="eq rem">r</span>{cells(rem, big)}' if rem else ""
    if it.fmt == "column_grid" and O.sign(sp["op"]) == "÷":
        small = layout is None or layout.get("exchanges", False)
        boxes = [R[f"x{k}"] for k in range(1, len(sp.get("exchanged", [])) + 1)]
        written = dict(zip(sp.get("exchanged", []), boxes, strict=True))
        drawn = answer_space.divided(
            sid, it.item_id, sp["a"], sp["b"], R["ans"], tail, written if small else None
        )
        return "Complete the calculation.", drawn + (working(1) if len(str(sp["a"])) >= 3 else "")
    if it.fmt == "column_grid":
        rows = sp.get("addends") or [sp["a"], sp["b"]]
        stem = "Complete the calculation." if not sp.get("_slot", "").startswith("probe") else "Try this one."
        return stem, grid(sid, it.item_id, rows, sp["op"], R["ans"]) + (
            working(1) if len(str(rows[0])) >= 3 else ""
        )
    sign = f" {op_sign(sp['op'])} "
    line = sign.join(map(str, sp["addends"])) if sp.get("addends") else f"{sp['a']}{sign}{sp['b']}"
    # asked in words, the sentence alone; an instruction beside the numbers (a stem) prints them too
    if sp.get("text"):
        stem = html.escape(sp["text"])
    else:
        stem = (html.escape(it.stem) + "<br>" if it.stem else "") + f'<span class="eq">{line} =</span>'
    return stem, cells(R["ans"], big) + tail + working(it.working_lines)


def missing_digit(
    sid: str, iid: str, it: Any, R: dict[str, Response], big: bool, cells: Callable[..., str]
) -> str:
    """A missing digit's boxes: how many digits fit, for an inequality; a division as its sentence (7□ ÷ 4 = 18), never a
    column, the digit's box after it as a missing number's; any other operation in columns, each box in its place,
    and a letter's own box."""
    sp = it.spec
    if sp.get("shape") == "INEQUALITY":
        return (
            f'<div class="row"><span class="lab">how many digits:</span>{cells(R["count"])}</div>'
            + working(2)
        )
    if O.sign(sp.get("op")) == "÷":
        return '<span class="lab">&#9633; =</span>' + cells(R["d1"], big) + working(2)
    rows = [sp["a"], sp["b"], sp["c"]]
    w = max(len(r) for r in rows)
    boxes = iter([r for r in it.responses if r.kind == "digits" and r.rid != "A"])

    def rowhtml(text: str, opch: str = "", res: bool = False) -> str:
        out = ""
        for ch in text.rjust(w):
            if ch == "□":
                r = next(boxes)
                out += f'<div class="g ans cell" data-s="{sid}" data-i="{iid}" data-r="{r.rid}" data-k="0"></div>'
            else:
                out += f'<div class="g{" res" if res else ""}">{ch.strip()}</div>'
        return f'<div class="g op">{opch}</div>' + out

    grid = f"""<div class="grid" style="grid-template-columns: 8.4mm repeat({w}, 8.4mm)">{rowhtml(rows[0])}{rowhtml(rows[1], op_sign(sp["op"]))}{rowhtml(rows[2], res=True)}</div>"""
    letter = f'<div class="row"><span class="lab">A =</span>{cells(R["A"])}</div>' if "A" in R else ""
    return grid + letter + working(2)


def estimate(
    sid: str, iid: str, sp: dict[str, Any], R: dict[str, Response], cells: Callable[[Response], str]
) -> str:
    """An estimate, then the exact answer: the rounded numbers, or a × judgement named by its label (how many
    digits, the digit it ends in); on a judged level, whether someone's answer is close to it."""
    first = (
        html.escape(R["est"].label) + ":"
        if sp.get("shape") in ("ANSWER_DIGITS", "LAST_DIGIT")
        else f"estimate: {sp['ra']} {op_sign(sp['op'])} {sp['rb']} ="
    )
    exact = cells(R["ans"])
    if sp.get("shape") == "ANSWER_DIGITS":
        # how many digits it has is the question, so its exact answer has the room the longest such answer needs
        # (84 × 18 in 4 boxes answered it): a product's two numbers' digits, a quotient's the number divided's
        room = len(str(sp["a"])) + (len(str(sp["b"])) if op_sign(sp["op"]) == "×" else 0)
        exact = answer_space.cells(sid, iid, dataclasses.replace(R["ans"], cells=room), boxes="cells")
    rem = R.get("rem")  # a division that leaves a remainder: its "r" and box kept with the quotient's
    exact = answer_space.with_remainder(exact, cells(rem) if rem else None)
    body = f"""<div class="row"><span class="lab">{first}</span>{cells(R["est"])}</div>
<div class="row" style="margin-top:2mm"><span class="lab">exact: {sp["a"]} {op_sign(sp["op"])} {sp["b"]} =</span>{exact}</div>""" + working(
        2
    )
    if "sense" in R:
        body += f'<div class="row" style="margin-top:2mm"><span class="lab">{html.escape(R["sense"].label)}</span>{ticks(sid, iid, R["sense"])}</div>'
    return body


def efficient(sid: str, iid: str, R: dict[str, Response], cells: Callable[[Response], str]) -> str:
    """A shortcut: each box after its sentence (46 × 10, then 46 × 5; a fact from the one above it; a fact scaled by ten,
    once and again); or the answer and the method in words."""
    if "method" not in R:
        rows = (
            f'<div class="row" style="margin-bottom:2mm"><span class="lab">{html.escape(r.label or "")}</span>{cells(r)}</div>'
            for r in R.values()
        )
        return "".join(rows) + working(2)
    return f'<div class="row"><span class="lab">answer =</span>{cells(R["ans"])}</div>' + textbox(
        sid, iid, R["method"], 13
    )
