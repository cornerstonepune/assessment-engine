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

from pathlib import Path

import pymupdf

from engine.core import db, roster
from engine.w2_print import library
from engine.w3_read import legacy, sorting

CUT = db.REPO_ROOT / "data" / "scans"
SKIP = {"", "?", "-"}
STOPS = {"working", "Answer"}  # the labels printed under a question, where its words end


def printed(path) -> tuple[dict, float]:
    """{question number: (page, its printed words)}, and the fraction of page 1 above question 1.

    A question's number is printed alone at the left margin and its words start to the right of it, down to
    the first "working" or "Answer" label, or the next question, or the footer."""
    out, n, band = {}, 1, 0.0
    for p, page in enumerate(pymupdf.open(path), 1):
        words = sorted(page.get_text("words"), key=lambda w: (w[5], w[6], w[7]))
        margin = min(w[0] for w in words)
        foot = max((w[1] for w in words if w[4] == "Cornerstone"), default=page.rect.height)
        starts = []
        for w in words:
            if w[4] == str(n) and w[0] - margin < 2 and w[1] < foot:
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


def paper(conn, code, pdf=None):
    """A library worksheet as `legacy.import_scan` reads a paper: (template, {slot: question}), and the questions
    it does not read — one asking for more than one number, which a person marks. `pdf`: the copy as it was
    printed for its child, where that file is kept; else the worksheet as the library prints it."""
    t = conn.execute(
        "select id, tenant_id, item_ids from sheet_template where source = 'library' and code = %s", (code,)
    ).fetchone()
    if not t:
        raise LookupError(f"no worksheet {code}")
    words, band = printed(pdf or library.pdf(conn, code))
    rows = {
        r["id"]: r
        for r in conn.execute(
            "select id, item_key, fmt, spec, responses from item where id = any(%s)", (t["item_ids"],)
        )
    }
    by_key, unread = {}, []
    for n, iid in enumerate(t["item_ids"], 1):
        it, (page, text) = rows[iid], words[n]
        first = it["responses"][0]
        if len(it["responses"]) > 1 or first.get("kind") != "digits":
            unread.append(n)
            continue
        spec = {**it["spec"], "kind": "bare", "question": text, "page": page, "answer": first["answer"]}
        by_key[str(n)] = {**it, "spec": spec}
    pages = max(p for p, _ in words.values())
    key = {"code": code, "fields": "boxes", "pages": [{"n": p, "mask": band if p == 1 else 0} for p in range(1, pages + 1)]}  # fmt: skip
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


def _cut(scan, pages, name):
    """The copy's pages as a file of their own — once: a second run reads the same file, so nothing is read twice."""
    out = CUT / Path(scan).stem / name
    if not out.exists():
        out.parent.mkdir(parents=True, exist_ok=True)
        src, doc = pymupdf.open(scan), pymupdf.open()
        for p in pages:
            doc.insert_pdf(src, from_page=p - 1, to_page=p - 1)
        doc.save(out, garbage=4, deflate=True, no_new_id=True)
    return out


def read(conn, scan, section, names, actor, pages_of=None):
    """Every library worksheet copy in the file, in order, read for its child: a copy printed for a child
    (`handout`, Make papers) by the code on it; a copy printed bare by the name said for it, in file order ("?"
    leaves one unread). → one dict per copy: its pages, code, child, answers read, questions a person marks."""
    papers = sorting.sort_file(conn, scan, pages_of)
    own = [p for p in papers if p["sheet"] and p["sheet"]["source"] == "library" and p["sheet"]["child_id"]]
    bare = [p for p in papers if p["worksheet"] and not p["sheet"]]
    if len(names) != len(bare):
        raise ValueError(
            f"the file holds {len(bare)} copies of library worksheets with no child's code; {len(names)} names given"
        )
    who = dict(
        zip(
            map(id, bare),
            (None if n.strip() in SKIP else _child(conn, section, n.strip(), actor) for n in names),
        )
    )
    out = []
    for k, copy in enumerate((p for p in papers if p in own or id(p) in who), 1):
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
        cut = _cut(scan, copy["pages"], f"copy{k:02d}-{code}.pdf")
        s = legacy.import_scan(conn, str(cut), code, cid, actor, rows=(template, by_key))
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
