"""What a copy is read against: the paper as it was printed (N8). Each question's printed words and the page it is on,
the band of page 1 above question 1 — the name, which the reader never sees — where every answer box prints (the key
the renderer wrote beside the PDF), and which PDF that is: the one printed for the child where it is kept, else the
layout of a library worksheet the page matches. Whose a copy is, and reading it, are `copies`'.
"""

import json
from pathlib import Path

import pymupdf

from engine.w2_print import library
from engine.w3_read import boxes, render_pdf

STOPS = {"working", "Answer"}  # the labels printed under a question, where its words end
NAME_BAND = (
    0.17  # the library page's name line ends at 13% of the page (`render.py`, the header); a margin over it
)


def printed(path) -> tuple[dict, float]:
    """{question number: (page, its printed words)}, and the fraction of page 1 above question 1.

    A question's number is printed alone at the left margin and its words start to the right of it, down to
    the first "working" or "Answer" label, or the next question, or the footer. Numbers are found top to bottom
    as they sit on the page, not in the order the PDF happens to store its text."""
    out, n, band = {}, 1, 0.0
    for p, page in enumerate(pymupdf.open(path).pages(), 1):
        words = sorted(page.get_text("words"), key=lambda w: (w[5], w[6], w[7]))
        if not words:
            continue
        margin = min(w[0] for w in words)
        foot = max((w[1] for w in words if w[4] == "Cornerstone"), default=page.rect.height)
        starts = []
        for w in sorted(words, key=lambda w: (round(w[1]), w[0])):
            if w[4].rstrip(".") == str(n) and w[0] - margin < 2 and w[1] < foot:
                starts.append((n, w))
                n += 1
        for k, (q, w) in enumerate(starts):
            end = starts[k + 1][1][1] if k + 1 < len(starts) else foot
            stop = min((x[1] for x in words if x[4] in STOPS and w[1] <= x[1] < end), default=end)
            text = [x[4] for x in words if w[1] - 1 <= x[1] < stop and x[0] > w[2]]
            out[q] = (p, " ".join(text))
        if p == 1 and starts:
            band = (starts[0][1][1] - 4) / page.rect.height
    return out, round(band, 3)


def boxes_drawn(pdf) -> list:
    """Where every box prints, from the key the renderer wrote beside the PDF; [] where there is none."""
    key = Path(pdf).with_suffix(".key.json")
    if not key.exists():
        return []
    return json.loads(key.read_text(encoding="utf-8")).get("geometry", [])


def pages_in_key(pdf, geometry=None) -> dict:
    """{item_key: the page its answer boxes print on}, from the key the renderer wrote beside the PDF — the page
    as it was drawn, not as it is read back. `geometry`: that key's boxes, already read (`_named_now`)."""
    pages = {}
    for cell in boxes_drawn(pdf) if geometry is None else geometry:
        pages[cell["item"]] = min(pages.get(cell["item"], cell["page"]), cell["page"])
    return pages


def _named_now(conn, geometry) -> list:
    """Each box named by its question's key now. A copy printed before a story was keyed again names the key it had
    (`bank rekey`, ADR 0053), and `current_item_key` leads that to the question, so the copy reads as it did."""
    keys = sorted({cell["item"] for cell in geometry})
    now = {
        r["k"]: r["now"]
        for r in conn.execute(
            "select k, public.current_item_key(k) as now from unnest(%s::text[]) k", (keys,)
        )
    }
    return [{**cell, "item": now.get(cell["item"], cell["item"])} for cell in geometry]


def _words(it) -> str:
    """A question's own words, where its printed ones were not found: the story, or the sum."""
    sp = it["spec"] or {}
    if it["stem"]:
        return it["stem"]
    return f"{sp['a']} {sp['op']} {sp['b']}" if {"a", "b", "op"} <= set(sp) else ""


def _slots(n, it, page, text, boxed) -> dict:
    """Question `n`'s answers, each a slot read and marked against its own key (`marking.response_of`): `n` its first,
    `n.rid` each after it. A copy whose boxes the renderer recorded is read in them, every answer of every kind — a
    tick or a sentence comes back for a person (`boxes.read_page`); one that did not is read by its words, and only a
    question that asks for one number. Nothing where the question's page is not known."""
    rs = it["responses"]
    if not boxed:
        rs = rs if len(rs) == 1 and rs[0].get("kind") == "digits" else []
    if page is None:
        return {}
    spec = {**it["spec"], "kind": "bare", "question": text or _words(it), "page": page}
    return {
        str(n) if k == 0 else f"{n}.{r['rid']}": {
            **it,
            "response": r,
            "spec": {**spec, "answer": r.get("answer")},
        }
        for k, r in enumerate(rs)
    }


def paper(conn, code, pdf=None, template_id=None):
    """A library worksheet as `legacy.import_scan` reads a paper: (template, {slot: answer}), a slot for every answer
    it reads (`_slots`), and the questions it reads nothing of — one whose page is not known, or, on a copy printed
    before the renderer recorded its boxes, one asking for more than a number — named for the person reading it in.
    `pdf`: the copy as it was printed for its child, where that file is kept; else the worksheet as the library
    prints it. `template_id`: a copy's own template, which a paper drawn for children is read against (it has no code)."""
    t = conn.execute(
        "select id, tenant_id, item_ids from sheet_template where id = %s" if template_id else
        "select id, tenant_id, item_ids from sheet_template where source = 'library' and code = %s",
        (template_id or code,),
    ).fetchone()  # fmt: skip
    if not t:
        raise LookupError(f"no worksheet {code}")
    pdf = pdf or library.pdf(conn, code)
    words, band = printed(pdf)
    band = band or NAME_BAND  # question 1 not found: still never show the reader the name
    geometry = _named_now(conn, boxes_drawn(pdf))
    drawn = pages_in_key(pdf, geometry)
    rows = {
        r["id"]: r
        for r in conn.execute(
            "select id, item_key, fmt, stem, spec, responses from item where id = any(%s)", (t["item_ids"],)
        )
    }
    by_key, unread = {}, []
    for n, iid in enumerate(t["item_ids"], 1):
        found_page, text = words.get(n, (None, ""))
        slots = _slots(n, rows[iid], drawn.get(rows[iid]["item_key"], found_page), text, bool(geometry))
        by_key |= slots
        if not slots:
            unread.append(n)
    pages = max([p for p, _ in words.values()] + list(drawn.values()) + [len(pymupdf.open(pdf))])
    key = {"code": code, "fields": "boxes", "pages": [{"n": p, "mask": band if p == 1 else 0} for p in range(1, pages + 1)]}  # fmt: skip
    if geometry:
        # the renderer's own record of where each box is: the scan is read in those boxes (`boxes.read_page`)
        key |= {"fields": "cells", "geometry": geometry, "printed": str(pdf)}
    return {"id": t["id"], "tenant_id": t["tenant_id"], "key": key}, by_key, unread


def _as_printed(conn, code, cut):
    """The worksheet as this copy was printed, where no PDF of it was kept: of the layouts the worksheet has
    printed in (`library.printed`), the one the copy's pages match (`boxes.as_printed`, goals/s18). On 23 Sep a
    copy printed four boxes an answer; the worksheet prints two today."""
    drawn = list(library.printed(conn, code).values())
    if len(drawn) == 1:
        return drawn[0]
    return boxes.as_printed(list(render_pdf.photos(cut)), drawn)


def read_from(conn, code, mine, cut):
    """The PDF a copy is read against: the one printed for its child, where that file is kept and records where its
    boxes are; else the layout its pages match (`_as_printed`). A child's PDF drawn before the renderer recorded its
    boxes (23 Sep) would have the copy read as an old paper, numbers taken from the working. None: a paper drawn for
    children whose printed PDF is not kept — it has no layout but its own."""
    kept = mine and mine["pdf_path"] and Path(mine["pdf_path"]).exists() and boxes_drawn(mine["pdf_path"])
    if kept:
        return mine["pdf_path"]
    return None if mine and mine["source"] != "library" else _as_printed(conn, code, cut)
