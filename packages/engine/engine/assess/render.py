"""Render a Sheet to a camera-ready A4 PDF and a geometry manifest.

Design rules (spec §06): no level printed anywhere; sheet_id as QR + short code; four fiducial
squares; one digit per cell; working box separate from answer cells; positions of every
response cell recorded in millimetres from the page origin so the marker can crop by lookup.
"""

import base64
import html
import io
import json
from pathlib import Path

import segno
from playwright.sync_api import sync_playwright

MM = 25.4 / 96.0  # CSS px -> mm

CSS = """
@page { size: A4; margin: 0; }
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; background: #fff; color: #111; font-family: "DejaVu Sans", Arial, sans-serif; font-size: 11.5pt; line-height: 1.35; -webkit-print-color-adjust: exact; }
.page { position: relative; width: 210mm; height: 297mm; overflow: hidden; page-break-after: always; }
.page:last-child { page-break-after: auto; }
.fid { position: absolute; width: 7mm; height: 7mm; background: #000; }
.fid.tl { left: 6mm; top: 6mm; } .fid.tr { right: 6mm; top: 6mm; } .fid.bl { left: 6mm; bottom: 6mm; } .fid.br { right: 6mm; bottom: 6mm; }
.qr { position: absolute; right: 16mm; top: 15mm; width: 17mm; height: 17mm; }
.qr img { width: 100%; height: 100%; display: block; }
.code { position: absolute; right: 16mm; top: 32.5mm; width: 17mm; text-align: center; font-family: "DejaVu Sans Mono", monospace; font-size: 7.5pt; letter-spacing: .04em; }
.content { position: absolute; left: 16mm; right: 16mm; top: 15mm; bottom: 15mm; }
.head { padding-right: 22mm; border-bottom: 1.2px solid #111; padding-bottom: 2.5mm; margin-bottom: 3.5mm; }
.school { font-size: 8pt; letter-spacing: .14em; text-transform: uppercase; color: #333; }
.title { font-size: 15pt; font-weight: bold; margin-top: 1mm; }
.sub { font-size: 9.5pt; color: #333; }
.nameline { display: flex; gap: 8mm; margin-top: 3mm; font-size: 10pt; }
.nameline span { flex: 1; border-bottom: 1px solid #111; padding-bottom: 1mm; white-space: nowrap; }
.nameline span.short { flex: 0 0 34mm; }
.instr { font-size: 9pt; background: #f1f1f1; padding: 1.5mm 2.5mm; margin-bottom: 3.5mm; }
.slim { font-size: 8.5pt; color: #333; border-bottom: 1px solid #111; padding-bottom: 1.5mm; margin-bottom: 3mm; padding-right: 22mm; }
.foot { position: absolute; left: 16mm; right: 16mm; bottom: 8mm; font-size: 8pt; color: #444; display: flex; justify-content: space-between; }
.item { break-inside: avoid; margin-bottom: 4.2mm; }
.rowgroup { display: flex; gap: 4mm; align-items: flex-start; margin-bottom: 2mm; }
.rowgroup .item { flex: 1 1 0; min-width: 0; }
.rowgroup .item .work { min-height: 9mm; }
.item .q { display: flex; gap: 2.5mm; align-items: baseline; }
.item .n { font-weight: bold; width: 6mm; flex: none; }
.item .stem { font-weight: 600; }
.item .body { margin-left: 8.5mm; margin-top: 1.5mm; }
.cells { display: inline-flex; gap: 0; vertical-align: middle; }
.cell { display: inline-block; width: 8.4mm; height: 10mm; border: 1px solid #111; margin-right: -1px; background: #fff; }
.cell.sm { width: 5.4mm; height: 6.4mm; border-color: #666; }
.cells.big .cell { width: 11mm; height: 13mm; }
.work { border: 1px dashed #888; border-radius: 1.5mm; min-height: 11mm; margin-top: 1.5mm; padding: 1mm 2mm; font-size: 8pt; color: #888; }
.work.h2 { min-height: 15mm; } .work.h3 { min-height: 20mm; } .work.h4 { min-height: 26mm; }
.row { display: flex; gap: 8mm; align-items: flex-end; flex-wrap: wrap; }
.lab { font-size: 9pt; color: #333; margin-right: 2mm; }
.eq { font-size: 13pt; }
.textbox { border: 1px solid #999; border-radius: 1mm; min-height: 16mm; margin-top: 1.5mm; background: repeating-linear-gradient(#fff 0 7.5mm, #ddd 7.5mm 7.6mm); }
.tick { display: inline-block; width: 6mm; height: 6mm; border: 1px solid #111; vertical-align: middle; margin-right: 2mm; }
.tickopt { display: inline-flex; align-items: center; margin-right: 8mm; font-size: 10pt; }
/* column grid */
.grid { display: inline-grid; grid-auto-rows: 10mm; gap: 0; border-collapse: collapse; }
.grid .g { width: 8.4mm; height: 10mm; border: 1px solid #bbb; display: flex; align-items: center; justify-content: center; font-size: 14pt; margin: -0.5px; }
.grid .g.op { border: none; font-size: 14pt; }
.grid .g.carry { height: 5.5mm; border: 1px dashed #999; font-size: 8pt; }
.grid .g.ans { border: 1px solid #111; border-top: 2px solid #111; background: #fff; }
.grid .g.line { border: none; border-top: 1.5px solid #111; height: 0; }
.grid .g.res { border-top: 2px solid #111; }
.grid .g.blank { border: none; }
table.sort { border-collapse: collapse; font-size: 10.5pt; }
table.sort th, table.sort td { border: 1px solid #333; padding: 1.2mm 3mm; text-align: center; }
table.sort td:first-child { text-align: left; font-family: "DejaVu Sans Mono", monospace; }
.wall { display: flex; flex-direction: column; align-items: center; gap: 0; }
.wall .r { display: flex; }
.wall .b { width: var(--brick, 24mm); height: 11mm; border: 1px solid #111; display: flex; align-items: center; justify-content: center; font-size: 12pt; margin: -0.5px; }
.cards { display: inline-flex; gap: 3mm; margin: 1.5mm 0; }
.card { width: 10mm; height: 13mm; border: 1.5px solid #111; border-radius: 1mm; display: flex; align-items: center; justify-content: center; font-size: 15pt; font-weight: bold; background: #f4f4f4; }
svg text { font-family: "DejaVu Sans", Arial, sans-serif; }
"""


def _cells(sheet_id, item_id, r, big=False, cls=""):
    n = max(1, r.cells)
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
    """rows: list of ints (addends or minuend/subtrahend); answer cells = ans_resp.cells"""
    w = ans_resp.cells
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
        + "".join(
            f'<div class="g ans cell" data-s="{sheet_id}" data-i="{item_id}" data-r="{ans_resp.rid}" data-k="{k}"></div>'
            for k in range(w)
        )
    )
    out.append("</div>")
    return f'<span data-resp="{item_id}|{ans_resp.rid}">{"".join(out)}</span>'


def _op(o):
    return "−" if o == "-" else o


def render_item(sheet, it, n):
    sid, iid, sp, R = sheet.sheet_id, it.item_id, it.spec, {r.rid: r for r in it.responses}
    big = sheet.grade == "G1"
    stem = html.escape(it.stem)
    body = ""
    f = it.fmt
    if f == "bare_sum":
        stem = f'<span class="eq">{sp["a"]} {_op(sp["op"])} {sp["b"]} =</span>'
        body = _cells(sid, iid, R["ans"], big) + _work(it.working_lines)
    elif f == "column_grid":
        rows = sp.get("addends") or [sp["a"], sp["b"]]
        stem = "Complete the calculation." if not sp.get("_slot", "").startswith("probe") else "Try this one."
        body = _grid(sid, iid, rows, sp["op"], R["ans"]) + (_work(1) if len(str(rows[0])) >= 3 else "")
    elif f == "missing_number":
        stem = f'<span class="eq">{html.escape(sp["text"]).replace("□", "&#9633;")}</span>'
        body = (
            '<span class="lab">&#9633; =</span>' + _cells(sid, iid, R["ans"], big) + _work(it.working_lines)
        )
    elif f == "balance_scale":
        L, Rr = sp["left"], sp["right"]
        body = f"""<svg width="120mm" height="26mm" viewBox="0 0 240 52"><rect x="8" y="6" width="34" height="18" fill="none" stroke="#111"/><text x="25" y="19" text-anchor="middle" font-size="11">{L[0]}</text>
<rect x="42" y="6" width="34" height="18" fill="none" stroke="#111"/><text x="59" y="19" text-anchor="middle" font-size="11">{L[1]}</text>
<rect x="164" y="6" width="34" height="18" fill="none" stroke="#111" stroke-dasharray="3 2"/><text x="181" y="19" text-anchor="middle" font-size="14">?</text>
<rect x="198" y="6" width="34" height="18" fill="none" stroke="#111"/><text x="215" y="19" text-anchor="middle" font-size="11">{Rr[1]}</text>
<line x1="4" y1="26" x2="236" y2="26" stroke="#111" stroke-width="2"/><polygon points="120,26 108,46 132,46" fill="#999"/></svg>
<div class="row"><span class="lab">? =</span>{_cells(sid, iid, R["ans"])}</div>"""
    elif f == "number_wall":
        b = sp["base"]
        # Every brick as wide as the widest answer's boxes (8.4 mm each), so no box spills out of its
        # brick and the wall stays a pyramid: 24 mm bricks drew 106's four boxes over their neighbours.
        brick = max(24, 8.4 * max(R[k].cells for k in ("top", "m1", "m2")) + 4)
        body = f"""<div class="wall" style="--brick:{brick:.1f}mm"><div class="r"><div class="b">{_cells(sid, iid, R["top"])}</div></div>
<div class="r"><div class="b">{_cells(sid, iid, R["m1"])}</div><div class="b">{_cells(sid, iid, R["m2"])}</div></div>
<div class="r"><div class="b">{b[0]}</div><div class="b">{b[1]}</div><div class="b">{b[2]}</div></div></div>"""
    elif f == "number_line_jumps":
        a, op, tens, ones = sp["a"], sp["op"], sp["tens"], sp["ones"]
        d = 1 if op == "+" else -1
        body = f'''<div class="row"><span class="eq">{a} {_op(op)} {sp["b"]} =</span>{_cells(sid, iid, R["ans"])}</div>
<svg width="150mm" height="24mm" viewBox="0 0 300 48"><line x1="10" y1="34" x2="290" y2="34" stroke="#111" stroke-width="1.5"/><polygon points="290,34 283,30 283,38" fill="#111"/>
<path d="M{40 if d > 0 else 260} 34 Q {(40 + 150) / 2 if d > 0 else (260 + 150) / 2} 2 150 34" fill="none" stroke="#111" stroke-width="1.2"/><text x="{95 if d > 0 else 205}" y="12" text-anchor="middle" font-size="10">{_op(op)}{tens}</text>
<path d="M150 34 Q {(150 + 215) / 2 if d > 0 else (150 + 85) / 2} 12 {215 if d > 0 else 85} 34" fill="none" stroke="#111" stroke-width="1.2"/><text x="{182 if d > 0 else 118}" y="20" text-anchor="middle" font-size="10">{_op(op)}{ones}</text>
<line x1="{40 if d > 0 else 260}" y1="30" x2="{40 if d > 0 else 260}" y2="38" stroke="#111"/><text x="{40 if d > 0 else 260}" y="47" text-anchor="middle" font-size="10">{a}</text>
<line x1="150" y1="30" x2="150" y2="38" stroke="#111"/><line x1="{215 if d > 0 else 85}" y1="30" x2="{215 if d > 0 else 85}" y2="38" stroke="#111"/></svg>
<div class="row" style="margin-left:{"58mm" if d > 0 else "30mm"}"><span class="lab">lands on</span>{_cells(sid, iid, R["land1"])}</div>'''
    elif f == "partition_scaffold":
        a, b = sp["a"], sp["b"]
        body = f"""<div class="row" style="margin-bottom:2mm"><span class="eq">{a} = {sp["a_h"]} +</span>{_cells(sid, iid, R["a_t"])}<span class="eq">+</span>{_cells(sid, iid, R["a_o"])}</div>
<div class="row" style="margin-bottom:2mm"><span class="eq">{b} =</span>{_cells(sid, iid, R["b_h"])}<span class="eq">+</span>{_cells(sid, iid, R["b_t"])}<span class="eq">+</span>{_cells(sid, iid, R["b_o"])}</div>
<div class="row"><span class="eq">total =</span>{_cells(sid, iid, R["hund"])}<span class="eq">+</span>{_cells(sid, iid, R["tens"])}<span class="eq">+</span>{_cells(sid, iid, R["ones"])}<span class="eq">=</span>{_cells(sid, iid, R["ans"])}</div>"""
    elif f == "sort_into_table":
        rows = ""
        for r in it.responses:
            t0 = f'<span class="tick" data-s="{sid}" data-i="{iid}" data-r="{r.rid}" data-k="0" data-opt="regroup"></span>'
            t1 = f'<span class="tick" data-s="{sid}" data-i="{iid}" data-r="{r.rid}" data-k="1" data-opt="none"></span>'
            rows += f'<tr data-resp="{iid}|{r.rid}"><td>{html.escape(r.label)}</td><td>{t0}</td><td>{t1}</td></tr>'
        body = f'<table class="sort"><tr><th></th><th>{html.escape(sp["col_a"])}</th><th>{html.escape(sp["col_b"])}</th></tr>{rows}</table>'
    elif f == "estimate_then_calc":
        body = f"""<div class="row"><span class="lab">estimate: {sp["ra"]} {_op(sp["op"])} {sp["rb"]} =</span>{_cells(sid, iid, R["est"])}</div>
<div class="row" style="margin-top:2mm"><span class="lab">exact: {sp["a"]} {_op(sp["op"])} {sp["b"]} =</span>{_cells(sid, iid, R["ans"])}</div>""" + _work(
            2
        )
    elif f == "missing_digit":
        a, b, c, op = sp["a"], sp["b"], sp["c"], sp["op"]
        w = max(len(a), len(b), len(c))

        def rowhtml(s, rid, opch=""):
            s = s.rjust(w)
            cells = ""
            for ch in s:
                if ch == "□":
                    cells += f'<div class="g ans cell" data-s="{sid}" data-i="{iid}" data-r="{rid}" data-k="0"></div>'
                else:
                    cells += f'<div class="g">{ch.strip()}</div>'
            return f'<div class="g op">{opch}</div>' + cells

        body = (
            f"""<div class="grid" style="grid-template-columns: 8.4mm repeat({w}, 8.4mm)">{rowhtml(a, "da")}{rowhtml(b, "db", _op(op))}{rowhtml(c, "none").replace('class="g"', 'class="g res"')}</div>"""
            + _work(2)
        )
    elif f == "digit_cards":
        cards = "".join(f'<div class="card">{c}</div>' for c in sp["cards"])
        body = (
            f'<div class="cards">{cards}</div><div class="row"><span class="lab">largest total =</span>{_cells(sid, iid, R["largest"])}</div>'
            + _text(sid, iid, R["how"], 13)
        )
    elif f == "efficient_method":
        body = (
            f'<div class="row"><span class="lab">answer =</span>{_cells(sid, iid, R["ans"])}</div>'
            + _text(sid, iid, R["method"], 13)
        )
    elif f == "partial_worked":
        a, b, bp = sp["a"], sp["b"], sp["b_parts"]
        body = f"""<div class="row" style="margin-bottom:2mm"><span class="eq">{a} = {sp["p1"]} +</span>{_cells(sid, iid, R["p2"])}<span class="eq">+</span>{_cells(sid, iid, R["p3"])}</div>
<div class="row" style="margin-bottom:2mm"><span class="eq">&minus; {b} = {bp[0]} + {bp[1]} + {bp[2]}</span></div>
<div class="row"><span class="eq">{a} &minus; {b} =</span>{_cells(sid, iid, R["ans"])}</div>"""
    elif f == "explain_claim":
        body = _ticks(sid, iid, R["tick"], {"yes": "Yes, correct", "no": "No, not correct"}) + _text(
            sid, iid, R["why"], 15
        )
    elif f == "find_mistake":
        body = (
            f'<div class="row"><span class="lab">The mistake is in the</span>{_ticks(sid, iid, R["where"])}</div><div class="row" style="margin-top:2mm"><span class="lab">The correct answer is</span>{_cells(sid, iid, R["ans"])}</div>'
            + _text(sid, iid, R["why"], 14)
        )
    elif f in ("word_1step", "word_2step"):
        body = (
            _work(it.working_lines)
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


def _grade(band):
    """A band in words: "G3" is "Grade 3", and a reasoning rung's "G2+" is "Grade 2+"."""
    return f"Grade {band[1:]}" if band.startswith("G") else band


def _literal(text):
    """Text safe inside the page's HTML and inside the JavaScript template literal that lays it out:
    a name holding a backtick or `${` must print as itself, not end the literal."""
    return html.escape(text).replace("`", "&#96;").replace("$", "&#36;")


def sheet_html(sheet, week_label="Week __"):
    qr = segno.make(sheet.sheet_id, error="m", micro=False)
    buf = io.BytesIO()
    qr.save(buf, kind="svg", scale=4, border=1)
    svg = base64.b64encode(buf.getvalue()).decode()
    rendered = [render_item(sheet, it, n + 1) for n, it in enumerate(sheet.items)]
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
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
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


GEOM_JS = """
() => {
  const mm = 25.4/96;
  const pages=[...document.querySelectorAll('.page')]; const out=[];
  pages.forEach((pg,pi)=>{
    const pr=pg.getBoundingClientRect();
    pg.querySelectorAll('[data-r]').forEach(el=>{
      const r=el.getBoundingClientRect();
      out.push({page:pi+1, item:el.dataset.i, resp:el.dataset.r, k:+el.dataset.k, opt:el.dataset.opt||null,
        kind: el.classList.contains('tick')?'tick':(el.classList.contains('textbox')?'text':'digit'),
        x:(r.left-pr.left)*mm, y:(r.top-pr.top)*mm, w:r.width*mm, h:r.height*mm});
    });
  });
  return {pages: pages.length, cells: out};
}
"""


def render_sheet(sheet, outdir, week_label="Week __", pw=None):
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    htmlpath = outdir / f"{sheet.sheet_id}.html"
    htmlpath.write_text(sheet_html(sheet, week_label), encoding="utf-8")
    own = pw is None
    if own:
        pw = sync_playwright().start()
    browser = pw.chromium.launch()
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
    browser.close()
    if own:
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
