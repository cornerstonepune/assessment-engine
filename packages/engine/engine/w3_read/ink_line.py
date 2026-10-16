"""N9 — where a pencil mark is told from the paper, measured on every answer a person settled (goals/l12a).

A box holds a digit when its marks are ink, darker than the paper around them by a line (`boxes.dark`), down enough of
its height. On 16 Oct a 6 written in faint pencil was 21% darker than its paper at its darkest, the line asked 28%, and
a right "862" waited: "2 boxes hold ink but the reader saw 862". The line is not moved on one answer: a fainter one can
count a speck in an empty box as a digit, and a blank would then wait as unclear. This measures every answer a person
settled on a copy read in its boxes: at each line, how many of its boxes hold ink, against how many digits the person
said the child wrote. Each box is found as the reader found it (`boxes.read_page`). It writes nothing. An answer is its
capture and its question, never a child's name, and no image leaves it.
"""

import re
from pathlib import Path

import cv2

from engine.assess.geometry import cells_of
from engine.w3_read import boxes, printed_paper, render_pdf
from engine.w3_read.lineup import blank, line_up, settle

LINES = (0.72, 0.76, 0.8, 0.84, 0.88)  # the reader's own line first


def inked_at(img, page_no, pdf, geometry, wanted, lines=LINES):
    """{slot: {line: how many of its boxes hold a digit}} for the answers `wanted` ({slot: (item_key, rid)}) on one
    photographed page, each box found as the reader finds it; an answer whose boxes are not found is left out. None
    when the page does not line up with the paper."""
    canon, _ = line_up(img, pdf, page_no)
    if canon is None:
        return None
    printed = blank(str(pdf), page_no)
    grey = cv2.cvtColor(canon, cv2.COLOR_BGR2GRAY)
    dark = {line: boxes.dark(canon, line) for line in lines}
    runs, _ = cells_of(geometry, page_no)
    out = {}
    for slot, key in wanted.items():
        if not runs.get(key):
            continue
        run, found = settle(grey, printed, runs[key])
        if found:
            out[slot] = {line: sum(boxes.holds_digit(d, printed, c) for c in run) for line, d in dark.items()}
    return out


def settled(conn, captures=None):
    """Every answer a person settled on a live copy read in its boxes, with how many digits the child wrote as the
    person settled it: typed by a person, or signed off as read, a blank as blank. A judgement without a typed reading
    says nothing of the digits; an answer read before the reader read boxes has no box count. Both are left out."""
    rows = conn.execute(
        "select r.id as result, c.id as capture, c.path, si.pdf_path, t.source, t.id as template_id,"
        " coalesce(t.code, t.batch_id) as code, i.item_key, r.rid, r.raw_read::jsonb as raw, k.human_read as typed"
        " from item_result r join capture c on c.id = r.capture_id"
        " join sheet_instance si on si.id = c.sheet_instance_id join sheet_template t on t.id = si.sheet_template_id"
        " join item i on i.id = r.item_id"
        " left join lateral (select id, human_read, judged from read_correction where item_result_id = r.id"
        "   order by created_at desc limit 1) k on true"
        " where c.superseded_by is null and r.raw_read is not null and r.raw_read::jsonb ? 'boxes'"
        " and (%(c)s::uuid[] is null or c.id = any(%(c)s::uuid[]))"
        " and ((k.judged is null and k.human_read is not null)"
        "   or (k.id is null and r.state = 'confirmed' and r.raw_read::jsonb ->> 'answer_state' in ('written', 'blank')))"
        " order by c.id, r.id",
        {"c": [str(c) for c in captures] if captures else None},
    ).fetchall()
    out = []
    for r in rows:
        wrote = r["typed"] if r["typed"] is not None else r["raw"].get("child_answer") or ""
        out.append({**r, "digits": len(re.sub(r"\D", "", wrote))})
    return out


def tally(measured, lines=LINES):
    """[(digits a person settled, {line: boxes holding ink})] → {line: how many answers, how many agree, lose ink the
    child wrote, gain ink the child did not write, and of the blanks how many are given ink}."""
    out = {}
    for line in lines:
        at = [(want, got[line]) for want, got in measured]
        out[line] = {
            "answers": len(at),
            "agree": sum(1 for want, got in at if got == want),
            "lose": sum(1 for want, got in at if got < want),
            "gain": sum(1 for want, got in at if got > want),
            "blank_given_ink": sum(1 for want, got in at if want == 0 and got > 0),
        }
    return out


def _page(conn, group, lines):
    """{result: {line: boxes holding ink}} for one page of one copy, or why it was not measured."""
    first = group[0]
    cut = Path(first["path"]).expanduser()
    if not cut.exists():
        return "its scan is not on this machine"
    mine = {"pdf_path": first["pdf_path"], "source": first["source"], "template_id": first["template_id"]}
    pdf = printed_paper.read_from(conn, first["code"], mine, cut)
    if pdf is None:
        return "the paper as printed is not kept"
    own = first["source"] != "library" and first["template_id"]
    template, _, _ = printed_paper.paper(conn, first["code"], pdf, own)
    if not template["key"].get("geometry"):
        return "its paper records no boxes"
    page = int(first["raw"].get("page") or 1)
    img, _ = render_pdf.photo(cut, int(first["raw"].get("file_page") or page))
    wanted = {r["result"]: (r["item_key"], r["rid"]) for r in group}
    got = inked_at(img, page, pdf, template["key"]["geometry"], wanted, lines)
    return "the page did not line up with its paper" if got is None else got


def measure(conn, lines=LINES, captures=None):
    """Every settled answer on a copy read in its boxes (`settled`), its boxes found again and counted at each line →
    {"lines": `tally`, "measured": answers measured, "unmeasured": {why: answers}, "stored": answers whose count at
    the reader's own line is the one stored with their reading, "changed": the answers a fainter line counts
    otherwise, as (capture, question, digits, {line: boxes holding ink})}."""
    pages, unmeasured, measured, stored, changed = {}, {}, [], 0, []
    for r in settled(conn, captures):
        pages.setdefault((r["capture"], r["raw"].get("page"), r["raw"].get("file_page")), []).append(r)
    for group in pages.values():
        got = _page(conn, group, lines)
        if isinstance(got, str):
            unmeasured[got] = unmeasured.get(got, 0) + len(group)
            continue
        for r in group:
            if r["result"] not in got:
                unmeasured["its boxes were not found"] = unmeasured.get("its boxes were not found", 0) + 1
                continue
            at = got[r["result"]]
            measured.append((r["digits"], at))
            stored += at[lines[0]] == r["raw"].get("inked")
            if len(set(at.values())) > 1:
                changed.append((str(r["capture"])[:8], r["item_key"], r["digits"], at))
    return {"lines": tally(measured, lines), "measured": len(measured), "unmeasured": unmeasured, "stored": stored,
            "changed": changed}  # fmt: skip


def said(report) -> list[str]:
    """The report as a person reads it: a line of counts for each line, and the answers a fainter line changes."""
    out = [f"  {report['measured']} answers a person settled, measured; {report['stored']} count as stored"
           f" at the reader's own line"]  # fmt: skip
    out += [f"  not measured: {n} — {why}" for why, n in report["unmeasured"].items()]
    out.append("  line   answers  agree  lose ink  gain ink  blanks given ink")
    for line, t in report["lines"].items():
        out.append(
            f"  {line:<5}  {t['answers']:>7}  {t['agree']:>5}  {t['lose']:>8}  {t['gain']:>8}  {t['blank_given_ink']:>16}"
        )
    if report["changed"]:
        out.append(
            "  answers a fainter line counts otherwise (copy, question, digits settled, boxes holding ink):"
        )
        out += [
            f"    {c}  {q}  {d}  " + "  ".join(f"{k}:{v}" for k, v in at.items())
            for c, q, d, at in report["changed"]
        ]
    return out
