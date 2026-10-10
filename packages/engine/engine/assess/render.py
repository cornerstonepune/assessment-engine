"""Render a Sheet to a camera-ready A4 PDF and a geometry manifest.

Design rules (spec §06): no level printed anywhere; sheet_id as QR + short code; four fiducial
squares; one digit per cell; working box separate from answer cells; positions of every
response cell recorded in millimetres from the page origin so the marker can crop by lookup.
"""

import base64
import dataclasses
import functools
import html
import io
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import segno
from playwright.sync_api import sync_playwright

from engine.assess import answer_space, pictures
from engine.assess import operations as O
from engine.assess.answer_space import op_sign, textbox, ticks, working
from engine.assess.geometry import GEOM_JS
from engine.assess.items import Response
from engine.assess.page_css import CSS, overrides

MM = 25.4 / 96.0  # CSS px -> mm


def render_item(sheet, it, n, layout: dict[str, Any] | None = None):
    # the answer boxes as the layout draws them (`render.layouts`): today's unless a paper printed in another
    _cells = functools.partial(answer_space.cells, boxes=(layout or {}).get("boxes", "digits"))
    _grid = functools.partial(
        answer_space.grid,
        boxes=(layout or {}).get("boxes", "digits"),
        long_rows=layout is None or layout.get("long_rows", False),
    )
    sid, iid, sp, R = sheet.sheet_id, it.item_id, it.spec, {r.rid: r for r in it.responses}
    big = sheet.grade == "G1"
    stem = html.escape(it.stem)
    body = ""
    f = it.fmt
    if f in ("bare_sum", "column_grid"):
        stem, body = _straight(sid, it, R, functools.partial(_cells, sid, iid), _grid, big)
    elif f == "missing_number":
        stem = f'<span class="eq">{html.escape(sp["text"]).replace("□", "&#9633;")}</span>'
        body = (
            '<span class="lab">&#9633; =</span>' + _cells(sid, iid, R["ans"], big) + working(it.working_lines)
        )
    elif f in pictures.DRAW:  # a balance, a number line, a tally, equal groups: drawn in one place
        body = pictures.DRAW[f](sp, R, functools.partial(_cells, sid, iid), big)
    elif f == "number_wall":
        b = sp["base"]
        # Every brick as wide as the widest answer's boxes (8.4 mm each), so no box spills out of its
        # brick and the wall stays a pyramid: 24 mm bricks drew 106's four boxes over their neighbours.
        brick = max(24, 8.4 * max(R[k].cells for k in ("top", "m1", "m2")) + 4)
        body = f"""<div class="wall" style="--brick:{brick:.1f}mm"><div class="r"><div class="b">{_cells(sid, iid, R["top"])}</div></div>
<div class="r"><div class="b">{_cells(sid, iid, R["m1"])}</div><div class="b">{_cells(sid, iid, R["m2"])}</div></div>
<div class="r"><div class="b">{b[0]}</div><div class="b">{b[1]}</div><div class="b">{b[2]}</div></div></div>"""
    elif f == "partition_scaffold":
        a, b = sp["a"], sp["b"]
        body = f"""<div class="row" style="margin-bottom:2mm"><span class="eq">{a} = {sp["a_h"]} +</span>{_cells(sid, iid, R["a_t"])}<span class="eq">+</span>{_cells(sid, iid, R["a_o"])}</div>
<div class="row" style="margin-bottom:2mm"><span class="eq">{b} =</span>{_cells(sid, iid, R["b_h"])}<span class="eq">+</span>{_cells(sid, iid, R["b_t"])}<span class="eq">+</span>{_cells(sid, iid, R["b_o"])}</div>
<div class="row"><span class="eq">total =</span>{_cells(sid, iid, R["hund"])}<span class="eq">+</span>{_cells(sid, iid, R["tens"])}<span class="eq">+</span>{_cells(sid, iid, R["ones"])}<span class="eq">=</span>{_cells(sid, iid, R["ans"])}</div>"""
    elif f == "estimate_then_calc":
        body = _estimate(sid, iid, sp, R, functools.partial(_cells, sid, iid))
    elif f == "missing_digit":
        body = _missing_digit(sid, iid, it, R, big, functools.partial(_cells, sid, iid))
    elif f == "equation":
        stem = (
            html.escape(it.stem)
            + f'<br><span class="eq">{html.escape(sp["text"]).replace("□", "&#9633;")}</span>'
        )
        body = "".join(
            ticks(sid, iid, r)
            if r.kind == "tick"
            else f'<span class="lab">&#9633; =</span>{_cells(sid, iid, r, big)}'
            for r in it.responses
        )
    elif f in ("fact_family", "break_apart") or (f == "inverse_check" and "right" not in R):
        # each sentence a row and its box (the table backwards: the division, then its fact)
        body = "".join(
            f'<div class="row" style="margin-bottom:2mm"><span class="eq">{html.escape(r.label).replace("□", "&#9633;")}</span>{_cells(sid, iid, r)}</div>'
            for r in it.responses
        )
    elif f == "inverse_check":
        chk, ok = R["check"], R["right"]
        body = (
            f'<div class="row"><span class="eq">{html.escape(chk.label).replace("□", "&#9633;")}</span>{_cells(sid, iid, chk)}</div>'
            f'<div class="row" style="margin-top:2mm"><span class="lab">{html.escape(ok.label)}</span>{ticks(sid, iid, ok)}</div>'
            + working(it.working_lines)
        )
    elif f in ("choose_estimate", "possible_answer", "odd_even"):
        body = "".join(ticks(sid, iid, r) for r in it.responses) + working(it.working_lines)
    elif f == "digit_cards":
        cards = "".join(f'<div class="card">{c}</div>' for c in sp["cards"])
        body = (
            f'<div class="cards">{cards}</div><div class="row"><span class="lab">largest total =</span>{_cells(sid, iid, R["largest"])}</div>'
            + textbox(sid, iid, R["how"], 13)
        )
    elif f == "efficient_method":
        body = _efficient(sid, iid, R, functools.partial(_cells, sid, iid))
    elif f == "partial_worked":
        a, b, bp = sp["a"], sp["b"], sp["b_parts"]
        body = f"""<div class="row" style="margin-bottom:2mm"><span class="eq">{a} = {sp["p1"]} +</span>{_cells(sid, iid, R["p2"])}<span class="eq">+</span>{_cells(sid, iid, R["p3"])}</div>
<div class="row" style="margin-bottom:2mm"><span class="eq">&minus; {b} = {bp[0]} + {bp[1]} + {bp[2]}</span></div>
<div class="row"><span class="eq">{a} &minus; {b} =</span>{_cells(sid, iid, R["ans"])}</div>"""
    elif f == "explain_claim":
        body = ticks(sid, iid, R["tick"], {"yes": "Yes, correct", "no": "No, not correct"}) + textbox(
            sid, iid, R["why"], 15
        )
    elif f == "find_mistake":
        where = (
            f'<div class="row"><span class="lab">{html.escape(R["where"].label or "The mistake is in the")}</span>{ticks(sid, iid, R["where"])}</div>'
            if "where" in R
            else ""
        )
        body = (
            where
            + f'<div class="row" style="margin-top:2mm"><span class="lab">The correct answer is</span>{_cells(sid, iid, R["ans"])}</div>'
            + textbox(sid, iid, R["why"], 14)
        )
    elif f in ("word_1step", "word_2step"):
        table = ""
        if sp.get("table"):
            rows = "".join(f"<tr><td>{html.escape(str(k))}</td><td>{v}</td></tr>" for k, v in sp["table"])
            table = f'<table class="sort">{rows}</table>'
        body = (
            table
            + working(it.working_lines)
            + f'<div class="row" style="margin-top:2mm"><span class="lab">Answer</span>{_cells(sid, iid, R["ans"], big)}</div>'
        )
    else:
        body = "".join(_cells(sid, iid, r) for r in it.responses if r.kind == "digits")
    compact = (
        " compact"
        if f in ("column_grid", "bare_sum", "missing_number", "estimate_then_calc")
        and sheet.grade != "G1"
        or (f in ("bare_sum", "missing_number") and sheet.grade == "G1")
        else ""
    )
    return f'<div class="item{compact}" data-item="{iid}" data-rung="{it.rung}"><div class="q"><span class="n">{n}</span><span class="stem">{stem}</span></div><div class="body">{body}</div></div>'


def _straight(
    sid: str, it: Any, R: dict[str, Response], cells: Callable[..., str], grid: Callable[..., str], big: bool
) -> tuple[str, str]:
    """A straight calculation's question and its boxes: in a line ("85 ÷ 4 = □ r □", a remainder's box after "r"
    where there is one), in columns, or in the division layout (`answer_space.divided`); a division asked in words
    prints its sentence alone ("How many 6s make 42?")."""
    sp, rem = it.spec, R.get("rem")
    tail = f'<span class="eq rem">r</span>{cells(rem, big)}' if rem else ""
    if it.fmt == "column_grid" and O.sign(sp["op"]) == "÷":
        layout = answer_space.divided(sid, it.item_id, sp["a"], sp["b"], R["ans"], tail)
        return "Complete the calculation.", layout + (working(1) if len(str(sp["a"])) >= 3 else "")
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


def _missing_digit(
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


def _estimate(
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
    rem = R.get(
        "rem"
    )  # a division that leaves a remainder: "r" and its box after the quotient's, one answer that
    if rem:  # wraps whole (alone, the remainder's box fell to the next line, away from its "r")
        exact = f'<span class="quotient">{exact}<span class="eq rem">r</span>{cells(rem)}</span>'
    body = f"""<div class="row"><span class="lab">{first}</span>{cells(R["est"])}</div>
<div class="row" style="margin-top:2mm"><span class="lab">exact: {sp["a"]} {op_sign(sp["op"])} {sp["b"]} =</span>{exact}</div>""" + working(
        2
    )
    if "sense" in R:
        body += f'<div class="row" style="margin-top:2mm"><span class="lab">{html.escape(R["sense"].label)}</span>{ticks(sid, iid, R["sense"])}</div>'
    return body


def _efficient(sid: str, iid: str, R: dict[str, Response], cells: Callable[[Response], str]) -> str:
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


def _grade(band):
    """A band in words: "G3" is "Grade 3", and a reasoning rung's "G2+" is "Grade 2+"."""
    return f"Grade {band[1:]}" if band.startswith("G") else band


def _literal(text):
    """Text safe inside the page's HTML and inside the JavaScript template literal that lays it out:
    a name holding a backtick or `${` must print as itself, not end the literal."""
    return html.escape(text).replace("`", "&#96;").replace("$", "&#36;")


def sheet_html(sheet, week_label="Week __", layout=None):
    # the most error correction there is: a phone's scan smears the code's squares, and a child writes the
    # date across it (2026-09-24) — a 30% loss still reads, and an eight-character code fits in the smallest QR either way
    qr = segno.make(sheet.sheet_id, error=(layout or {}).get("qr_error", "h"), micro=False)
    buf = io.BytesIO()
    qr.save(buf, kind="svg", scale=4, border=1)
    svg = base64.b64encode(buf.getvalue()).decode()
    rendered = [render_item(sheet, it, n + 1, layout) for n, it in enumerate(sheet.items)]
    per_row = 3 if sheet.grade != "G1" else 2
    groups, cur = [], []

    def flush():
        nonlocal cur
        if cur:
            groups.append('<div class="rowgroup">' + "".join(cur) + "</div>" if len(cur) > 1 else cur[0])
            cur = []

    for r_html in rendered:
        if 'class="item compact"' in r_html:
            cur.append(r_html)
            if len(cur) == per_row:
                flush()
        else:
            flush()
            groups.append(r_html)
    flush()
    items = "\n".join(groups)
    # What the paper practises comes from data — the skill set's own name — never a subject in code.
    # It heads page 1 and every "continued" line; the footer keeps to school and grade, so a long
    # name never wraps the page number onto a second line.
    grade = _grade(sheet.grade)
    heading = " · ".join(filter(None, [grade, _literal(sheet.title)]))
    instr = "Work carefully and show how you found each answer. Write one digit in each box."
    if sheet.grade == "G1":
        instr = "Write one number in each box. You may draw a picture to help you."
    head = f"""<div class="head"><div class="school">Cornerstone School</div><div class="title">{heading}</div><div class="sub">{_literal(week_label)}</div>
<div class="nameline"><span>Name:</span><span class="short">Class:</span><span class="short">Date:</span></div></div><div class="instr">{instr}</div>"""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}{overrides(layout)}</style></head><body>
<div id="src" style="position:absolute;left:-9999px;top:0;width:178mm">{items}</div>
<template id="pageT"><div class="page"><div class="fid tl"></div><div class="fid tr"></div><div class="fid bl"></div><div class="fid br"></div>
<div class="qr"><img src="data:image/svg+xml;base64,{svg}"></div><div class="code">{sheet.sheet_id}</div><div class="content"></div>
<div class="foot"><span>Cornerstone School · {grade}</span><span>Show your working in the space provided · {sheet.sheet_id} · p<span class="pn"></span></span></div></div></template>
<script>
(function(){{
  const src=document.getElementById('src'); const T=document.getElementById('pageT');
  const items=[...src.children]; let pages=[];
  function newPage(first){{ const p=T.content.firstElementChild.cloneNode(true); const c=p.querySelector('.content');
    c.innerHTML = first ? `{head}` : `<div class="slim">Cornerstone School · {heading} · continued</div>`;
    if(!first) c.style.top='36mm';
    document.body.appendChild(p); pages.push(p); return p; }}
  let p=newPage(true); let c=p.querySelector('.content');
  const limit=()=> c.clientHeight - 6*96/25.4;   // leave 6mm above the footer
  const bottom=(el)=>{{ const cr=c.getBoundingClientRect(); const r=el.getBoundingClientRect(); return r.bottom-cr.top; }};
  for(const it of items){{ c.appendChild(it); if(bottom(it)>limit()){{ p=newPage(false); c=p.querySelector('.content'); c.appendChild(it); }} }}
  pages.forEach((pg,i)=>pg.querySelector('.pn').textContent=(i+1)+'/'+pages.length);
  src.remove();
}})();
</script></body></html>"""


def _browser(pw):
    """The one browser a batch's Playwright renders every paper in: launched on its first paper, closed when the
    batch's Playwright stops. A browser per paper made a class-sized batch outlive the website's wait (2026-09-30)."""
    browser = getattr(pw, "_one_browser", None)
    if browser is None or not browser.is_connected():
        browser = pw._one_browser = pw.chromium.launch()
    return browser


def render_sheet(sheet, outdir, week_label="Week __", pw=None, layout=None):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    htmlpath = outdir / f"{sheet.sheet_id}.html"
    htmlpath.write_text(sheet_html(sheet, week_label, layout), encoding="utf-8")
    own = pw is None
    if own:
        pw = sync_playwright().start()
    browser = pw.chromium.launch() if own else _browser(pw)
    page = browser.new_page(viewport={"width": 794, "height": 1123})
    page.goto(htmlpath.resolve().as_uri())
    page.wait_for_timeout(50)
    geom = page.evaluate(GEOM_JS)
    page.pdf(
        path=str(outdir / f"{sheet.sheet_id}.pdf"),
        format="A4",
        print_background=True,
        margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        prefer_css_page_size=True,
    )
    page.close()
    if own:
        browser.close()
        pw.stop()
    key = dict(
        sheet_id=sheet.sheet_id,
        grade=sheet.grade,
        level=sheet.level,
        variant=sheet.variant,
        week=sheet.week,
        pages=geom["pages"],
        n_responses=sheet.n_responses(),
        items=[
            dict(
                item_id=i.item_id,
                n=n + 1,
                template=i.template,
                rung=i.rung,
                skills=i.skills,
                signal=i.signal,
                fmt=i.fmt,
                scaffolded=i.scaffolded,
                stem=i.stem,
                spec={k: v for k, v in i.spec.items()},
                responses=[
                    dict(
                        rid=r.rid,
                        kind=r.kind,
                        answer=r.answer,
                        cells=r.cells,
                        options=r.options,
                        misconceptions=r.misconceptions,
                        tolerance=r.tolerance,
                        rubric=r.rubric,
                        label=r.label,
                    )
                    for r in i.responses
                ],
            )
            for n, i in enumerate(sheet.items)
        ],
        geometry=geom["cells"],
    )
    (outdir / f"{sheet.sheet_id}.key.json").write_text(
        json.dumps(key, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    return key
