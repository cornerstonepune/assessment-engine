"""N8 — the copies of library worksheets in one scanned file, each given to its child, then read and marked.

A library worksheet carries its own code (`R8-H02`) where a child's paper carries its QR, the same on every copy,
so `sorting` can say which pages are one copy but not whose: that is the name written on its first page. A person
reads the names and says them, in the file's order — a first name, or a roll number where the name is unclear.
Every name is found in the class list before anything is read. Each copy is then cut into a file of its own
under `data/scans` (the approval screen serves an answer's photograph from that file), and read and marked as any
paper is (`legacy.import_scan`): every answer a candidate a person confirms on Marking.

The worksheet is entered from the page it prints (`library.pdf`): each question's printed words and the page it
is on, and the band of page 1 above question 1 — the name — which the reader never sees.
"""

import json
import shutil
from pathlib import Path

import pymupdf

from engine.core import db, roster
from engine.w2_print import library
from engine.w3_read import legacy, read_eval, sorting

# Where the school's scans live, on this Mac and on the server alike (`deploy/compose.server.yml` mounts only this):
# a copy cut anywhere else can be read here but never shown on the approval screens.
CUT = Path(read_eval.ASSESSMENTS).expanduser() / "copies"
WAS_CUT = (
    db.REPO_ROOT / "data" / "scans"
)  # where the first copies were cut, 2026-09-24; moved on their next read
SKIP = {"", "?", "-"}
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
    for p, page in enumerate(pymupdf.open(path), 1):
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


def _geometry(pdf) -> list:
    """Where every box prints, from the key the renderer wrote beside the PDF; [] where there is none."""
    key = Path(pdf).with_suffix(".key.json")
    if not key.exists():
        return []
    return json.loads(key.read_text(encoding="utf-8")).get("geometry", [])


def _pages_in_key(pdf) -> dict:
    """{item_key: the page its answer boxes print on}, from the key the renderer wrote beside the PDF — the page
    as it was drawn, not as it is read back."""
    pages = {}
    for cell in _geometry(pdf):
        pages[cell["item"]] = min(pages.get(cell["item"], cell["page"]), cell["page"])
    return pages


def _words(it) -> str:
    """A question's own words, where its printed ones were not found: the story, or the sum."""
    sp = it["spec"] or {}
    if it["stem"]:
        return it["stem"]
    return f"{sp['a']} {sp['op']} {sp['b']}" if {"a", "b", "op"} <= set(sp) else ""


def paper(conn, code, pdf=None):
    """A library worksheet as `legacy.import_scan` reads a paper: (template, {slot: question}), and the questions
    it does not read — one asking for more than one number, or one whose page is not known, which a person marks.
    `pdf`: the copy as it was printed for its child, where that file is kept; else the worksheet as the library
    prints it."""
    t = conn.execute(
        "select id, tenant_id, item_ids from sheet_template where source = 'library' and code = %s", (code,)
    ).fetchone()
    if not t:
        raise LookupError(f"no worksheet {code}")
    pdf = pdf or library.pdf(conn, code)
    words, band = printed(pdf)
    band = band or NAME_BAND  # question 1 not found: still never show the reader the name
    drawn = _pages_in_key(pdf)
    rows = {
        r["id"]: r
        for r in conn.execute(
            "select id, item_key, fmt, stem, spec, responses from item where id = any(%s)", (t["item_ids"],)
        )
    }
    by_key, unread = {}, []
    for n, iid in enumerate(t["item_ids"], 1):
        it = rows[iid]
        found_page, text = words.get(n, (None, ""))
        page, first = drawn.get(it["item_key"], found_page), it["responses"][0]
        if len(it["responses"]) > 1 or first.get("kind") != "digits" or page is None:
            unread.append(n)
            continue
        spec = {
            **it["spec"],
            "kind": "bare",
            "question": text or _words(it),
            "page": page,
            "answer": first["answer"],
        }
        by_key[str(n)] = {**it, "spec": spec}
    pages = max([p for p, _ in words.values()] + list(drawn.values()) + [len(pymupdf.open(pdf))])
    key = {"code": code, "fields": "boxes", "pages": [{"n": p, "mask": band if p == 1 else 0} for p in range(1, pages + 1)]}  # fmt: skip
    geometry = _geometry(pdf)
    if geometry:
        # the renderer's own record of where each box is: the scan is read in those boxes (`boxes.read_page`)
        key |= {"fields": "cells", "geometry": geometry, "printed": str(pdf)}
    return {"id": t["id"], "tenant_id": t["tenant_id"], "key": key}, by_key, unread


def _child(conn, section, who, actor):
    """A first name, or a roll number where the name on the page is unclear."""
    if not who.isdigit():
        return roster.find(conn, section, who, actor)
    r = conn.execute(
        "select id from child where section = %s and roll_no = %s and active", (section, who)
    ).fetchone()
    if not r:
        raise ValueError(f"no roll {who} in {section}")
    return r["id"]


def _home(path) -> str:
    """A path as `capture.path` records one: from the home folder, so it resolves on the server as on this Mac."""
    return str(Path(path).resolve()).replace(str(Path.home()), "~")


def _replaces(conn, capture_id, scan):
    """A copy read afresh from the same scan — cut again after better sorting — stands in for the reading of the
    same paper made from it before: that one is superseded (rule 4: kept, no longer read), unless a person has
    already worked on it, which stays as they left it."""
    stem = Path(scan).stem
    for old in conn.execute(
        "select c.id from capture c where c.sheet_instance_id = (select sheet_instance_id from capture where id = %s)"
        " and c.id <> %s and c.superseded_by is null and (c.path like %s or c.path like %s)",
        (capture_id, capture_id, _home(CUT / stem) + "/%", _home(WAS_CUT / stem) + "/%"),
    ).fetchall():
        if not legacy.worked_on(conn, old["id"]):
            conn.execute("update capture set superseded_by = %s where id = %s", (capture_id, old["id"]))


def _cut(scan, pages, name):
    """The copy's pages as a file of their own — once: a second run reads the same file, so nothing is read twice."""
    out = CUT / Path(scan).stem / name
    was = WAS_CUT / Path(scan).stem / name
    if was.exists() and not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(was, out)
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        src, doc = pymupdf.open(scan), pymupdf.open()
        for p in pages:
            doc.insert_pdf(src, from_page=p - 1, to_page=p - 1)
        doc.save(out, garbage=4, deflate=True, no_new_id=True)
    return out


def read(conn, scan, section, names, actor, pages_of=None, read_text=None):
    """Every library worksheet copy in the file, in order, read for its child: a copy printed for a child
    (`handout`, Make papers) by the code on it; a copy printed bare by the name said for it, in file order ("?"
    leaves one unread). → one dict per copy: its pages, code, child, answers read, questions a person marks."""
    papers = sorting.sort_file(conn, scan, pages_of, read_text)
    own = [p for p in papers if p["sheet"] and p["sheet"]["source"] == "library" and p["sheet"]["child_id"]]
    bare = [p for p in papers if p["worksheet"] and not p["sheet"]]
    if len(names) != len(bare):
        found = [
            f"copy {k}: pages {p['pages'][0]}–{p['pages'][-1]}, {p['qr']}"
            + (f", {len(p['pages'])} of its {p['length']} pages" if len(p["pages"]) != p["length"] else "")
            + (f", no code read on page {', '.join(map(str, p['unread']))}" if p["unread"] else "")
            for k, p in enumerate(bare, 1)
        ]
        raise ValueError(
            f"the file holds {len(bare)} copies of library worksheets with no child's code; {len(names)} names"
            " given — one name (or ?) per copy, in this order:\n  " + "\n  ".join(found)
        )
    who = dict(
        zip(
            map(id, bare),
            (None if n.strip() in SKIP else _child(conn, section, n.strip(), actor) for n in names),
        )
    )
    out = []
    lost = [p for p in papers if not p["qr"]]  # no code on the page, QR or print: whose it is cannot be said
    for k, copy in enumerate((p for p in papers if p in own or id(p) in who or p in lost), 1):
        if not copy["qr"]:
            out.append({"copy": k, "pages": copy["pages"], "code": "?", "child_id": None, "answers": 0,
                        "by_code": False, "skipped": True, "why": "no code could be read on the page"})  # fmt: skip
            continue
        mine = copy["sheet"]
        cid = mine["child_id"] if mine else who[id(copy)]
        code = mine["code"] if mine else copy["qr"]
        row = {
            "copy": k,
            "pages": copy["pages"],
            "code": code,
            "child_id": cid,
            "answers": 0,
            "by_code": bool(mine),
        }
        if cid is None:
            out.append({**row, "skipped": True})
            continue
        kept = mine and mine["pdf_path"] and Path(mine["pdf_path"]).exists()
        template, by_key, unread = paper(conn, code, mine["pdf_path"] if kept else None)
        if mine:
            template["qr"] = copy["qr"]  # the answers land on the copy printed for this child
        # a child's own paper is named by where it starts, so a file read again, sorted better, cuts it afresh
        name = f"copy{k:02d}-p{copy['pages'][0]}-{code}.pdf" if mine else f"copy{k:02d}-{code}.pdf"
        cut = _cut(scan, copy["pages"], name)
        s = legacy.import_scan(conn, str(cut), code, cid, actor, rows=(template, by_key))
        _replaces(conn, s["capture_id"], scan)
        # a copy read before it moved (`WAS_CUT`): its reading now points at where it lives
        conn.execute(
            "update capture set path = %s where id = %s and path <> %s",
            (_home(cut), s["capture_id"], _home(cut)),
        )
        # The page each answer was read on, kept with its reading: a worksheet question's page is not in the
        # bank's row (`paper`), and the approval screens show the photograph of that page. Only where missing.
        for it in by_key.values():
            conn.execute(
                "update item_result set raw_read = (raw_read::jsonb || jsonb_build_object('page', %s::int))::text"
                " where capture_id = %s and item_id = %s and raw_read is not null and not (raw_read::jsonb ? 'page')",
                (it["spec"]["page"], s["capture_id"], it["id"]),
            )
        answers = s.get("already_results") if s.get("already") else len(s["results"])
        out.append({**row, "answers": answers, "already": bool(s.get("already")), "unread": unread,
                    "capture_id": s["capture_id"], "notes": [n for n in s["notes"] if n]})  # fmt: skip
    return out


def tally(conn, capture_id) -> dict:
    """What the engine made of one copy's answers: settled right, and waiting for a person as read right,
    read wrong, read blank or not read at all — the reason each waits is its own (`marking.mark_read`)."""
    return conn.execute(
        "select count(*) filter (where status = 'correct') as right,"
        " count(*) filter (where status <> 'correct' and raw_read::jsonb ->> 'why' like 'read as a right%%')"
        "   as right_waiting,"
        " count(*) filter (where raw_read::jsonb ->> 'why' like 'read as a wrong%%') as wrong,"
        " count(*) filter (where raw_read::jsonb ->> 'why' like 'read as blank%%') as blank,"
        " count(*) filter (where status <> 'correct') as waiting"
        " from item_result where capture_id = %s",
        (capture_id,),
    ).fetchone()
