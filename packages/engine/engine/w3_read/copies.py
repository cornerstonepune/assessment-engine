"""N8 — the copies in one scanned file, each given to its child, then read and marked: library worksheets, and the papers
drawn for children (the paper maker's, a home paper; `READ`). A copy that is not read is said, with why.

A library worksheet carries its own code (`R8-H02`) where a child's paper carries its QR, the same on every copy,
so `sorting` can say which pages are one copy but not whose: that is the name written on its first page. A person
reads the names and says them, in the file's order — a first name, or a roll number where the name is unclear.
Every name is found in the class list before anything is read. Each copy is then cut into a file of its own
under `data/scans` (the approval screen serves an answer's photograph from that file), and read and marked as any
paper is (`legacy.import_scan`): every answer a candidate a person confirms on Marking.

What each copy is read against — the paper as it was printed — is `printed_paper`'s.
"""

import shutil
from pathlib import Path

import pymupdf

from engine.core import db, roster
from engine.w3_read import boxes, checked, legacy, marking, printed_paper, render_pdf, sorting

# Where the school's scans live, on this Mac and on the server alike (`deploy/compose.server.yml` mounts only this):
# a copy cut anywhere else can be read here but never shown on the approval screens.
CUT = Path(db.ASSESSMENTS).expanduser() / "copies"
WAS_CUT = (
    db.REPO_ROOT / "data" / "scans"
)  # where the first copies were cut, 2026-09-24; moved on their next read
SKIP = {"", "?", "-"}
# the papers read here, by their template's source: a worksheet from the library, and a paper drawn for children
# (`focus_paper.print_paper`: the paper maker's three kinds and a home paper), each read against its own template
READ = ("library", "focus")


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
        if not checked.worked_on(conn, old["id"]):
            conn.execute("update capture set superseded_by = %s where id = %s", (capture_id, old["id"]))


def _margin(conn):
    row = conn.execute("select value from threshold where key = 'read.page_margin'").fetchone()
    return float(row["value"]) if row else 1.25


def _misplaced(conn, cut, held) -> tuple[str | None, int]:
    """A live reading of this very copy with answers on questions its pages do not hold — read before a copy's
    pages were placed (`boxes.placed`) — and how many of them a person signed off or corrected. Such a reading is
    wrong at its root, a person's checks included: they were made against another question's words and key
    (2026-09-29), so it is replaced whatever was done on it (rule 4: kept, no longer read)."""
    old = conn.execute(
        "select c.id from capture c where c.path = %s and c.superseded_by is null"
        " and exists (select 1 from item_result r where r.capture_id = c.id and not (r.item_id = any(%s)))",
        (_home(cut), list(held)),
    ).fetchone()
    if not old:
        return None, 0
    conn.execute("update capture set superseded_by = id where id = %s", (old["id"],))  # pointed below
    return old["id"], checked.worked_on(conn, old["id"])


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


def _named_before(conn, scan, name, code):
    """The child a person already said a bare copy was — the live reading of the same copy of the same scan,
    cut under the same name — or None. A copy printed with no child's code is attributed once, by a person;
    reading it again never asks again."""
    r = conn.execute(
        "select si.child_id from capture c join sheet_instance si on si.id = c.sheet_instance_id"
        " join sheet_template t on t.id = si.sheet_template_id"
        " where c.superseded_by is null and (c.path = %s or c.path = %s) and coalesce(t.code, t.batch_id) = %s"
        " order by c.created_at desc limit 1",
        (_home(CUT / Path(scan).stem / name), _home(WAS_CUT / Path(scan).stem / name), code),
    ).fetchone()
    return r["child_id"] if r else None


def _not_read(copy):
    """Why a copy in the file is not read."""
    if not copy["qr"]:
        return "no code could be read on the page"
    if copy["sheet"]:
        return f"a {copy['sheet']['source']} paper, which is not read from a scan"
    return f"{copy['qr']} is not a code this school printed"


def _given(conn, qr, child):
    """A spare is the copy of the child whose name is said for it: theirs from now on, its questions seen by them. A
    copy already a child's stays theirs."""
    if not conn.execute("update sheet_instance set child_id = %s, updated_at = now() where qr_code = %s"
                        " and child_id is null", (child, qr)).rowcount:  # fmt: skip
        return
    conn.execute(
        "insert into item_exposure (tenant_id, child_id, item_id, week) select si.tenant_id, si.child_id, i, si.week"
        " from sheet_instance si join sheet_template t on t.id = si.sheet_template_id, unnest(t.item_ids) as i"
        " where si.qr_code = %s on conflict do nothing",
        (qr,),
    )


def _sorted_out(papers):
    """(the copies printed for a child, the copies no child's code is on): of the papers this reads (`READ`), a copy
    whose code names its child; and a worksheet printed bare, or a spare, which the child who takes it names."""
    ours = [p for p in papers if p["sheet"] and p["sheet"]["source"] in READ]
    own = [p for p in ours if p["sheet"]["child_id"]]
    spares = [p for p in ours if not p["sheet"]["child_id"]]
    return own, [p for p in papers if (p["worksheet"] and not p["sheet"]) or any(p is q for q in spares)]


def _said(conn, bare, section, names, actor):
    """{copy: its child, or None}: each copy no child's code is on, the name said for it, in file order. One name (or
    "?") a copy, or nothing is read."""
    if len(names) != len(bare):
        found = [
            f"copy {k}: {sorting.pages_said(p['pages'])}, {p['qr']}"
            + (f", {len(p['pages'])} of its {p['length']} pages" if len(p["pages"]) != p["length"] else "")
            + (f", no code read on page {', '.join(map(str, p['unread']))}" if p["unread"] else "")
            for k, p in enumerate(bare, 1)
        ]
        raise ValueError(
            f"the file holds {len(bare)} copies with no child's code; {len(names)} names"
            " given — one name (or ?) per copy, in this order:\n  " + "\n  ".join(found)
        )
    return dict(
        zip(
            map(id, bare),
            (None if n.strip() in SKIP else _child(conn, section, n.strip(), actor) for n in names),
        )
    )


def _owner(conn, scan, k, copy, who, named):
    """(its code, the file it is cut to, its child) of copy `k`: the child its code names, else the one said for it, else
    — nobody here to say (the inbox) — the one a person said before (`_named_before`)."""
    mine = copy["sheet"]
    code = (mine and mine["code"]) or copy["qr"]
    # a child's own paper is named by where it starts, so a file read again, sorted better, cuts it afresh
    name = f"copy{k:02d}-p{copy['pages'][0]}-{code}.pdf" if mine else f"copy{k:02d}-{code}.pdf"
    cid = (mine and mine["child_id"]) or who.get(id(copy))
    if cid is None and not mine and not named:
        cid = _named_before(conn, scan, name, code)
    return code, name, cid


def read(
    conn, scan, section, names, actor, pages_of=None, read_text=None, again=False, given=None, progress=None
):
    """Every copy in the file, in order, read for its child (`READ`): a copy printed for a child (`handout`, Make papers,
    the paper maker, a home paper) by the code on it; a copy printed bare, or a spare, by the name said for it, in file
    order ("?" leaves one unread), or — `names` None — by the child a person named for it before (`_named_before`).
    `again`: a copy read before is read afresh (a better reader), unless a person has already worked on it.
    → one dict per copy, read or not: its pages, code, child, answers read, questions a person marks — or why it was
    not read — and the file's pages in it on which no code could be read (`no_code`), said by number, never guessed:
    such a page is read only as the child a person gave it to (`given`, {page: child}; `sorting.give`).
    `progress(done, of)` is told the file's pages read so far after each copy (goals/s2-the-assessment-card.yaml)."""
    papers = sorting.give(sorting.sort_file(conn, scan, pages_of, read_text), given or {})
    tell = progress or (lambda done, of: None)
    of = sum(len(c["pages"]) for c in papers)
    own, bare = _sorted_out(papers)
    named = names is not None
    who = _said(conn, bare, section, names if named else ["?"] * len(bare), actor)
    out = []
    for k, copy in enumerate(papers, 1):  # every copy in the file has its line: read, or why not
        tell(sum(len(c["pages"]) for c in papers[: k - 1]), of)  # the pages of the copies before this one
        if not copy["qr"] or not (any(copy is p for p in own) or id(copy) in who):
            out.append({"copy": k, "pages": copy["pages"], "code": copy["qr"] or "?", "child_id": None, "answers": 0,
                        "by_code": False, "skipped": True, "why": _not_read(copy),
                        "no_code": copy["unread"]})  # fmt: skip
            continue
        code, name, cid = _owner(conn, scan, k, copy, who, named)
        row = {"copy": k, "pages": copy["pages"], "code": code, "child_id": cid, "answers": 0,
               "by_code": bool(copy["sheet"] and copy["sheet"]["child_id"]),
               "no_code": copy["unread"], "given": copy.get("given", [])}  # fmt: skip
        if cid is None:
            out.append(
                {**row, "skipped": True, "why": "printed with no child's code; say whose it is to read it"}
            )
            continue
        out.append(_read_copy(conn, scan, copy, row, name, actor, again))
    if papers:
        tell(of, of)
    return out


def _and(ns) -> str:
    ns = [str(n) for n in ns]
    return ns[0] if len(ns) == 1 else f"{', '.join(ns[:-1])} and {ns[-1]}"


def _run_placed(photos, pdf, margin, n) -> list[int] | None:
    """Which page of `pdf` each photograph of one run is: the run as one (`boxes.placed`), or — more photographs than
    the paper has pages — each by itself. None where any cannot be told apart."""
    if len(photos) <= n:
        return boxes.placed(photos, pdf, margin)
    each = [boxes.placed([ph], pdf, margin) for ph in photos]
    return None if any(not e for e in each) else [e[0] for e in each if e]


def _placing(scan, copy, cut, pdf, margin) -> tuple[list[int], list[int], list[dict]] | None:
    """(the file's pages to read, the paper's page each is, each page photographed more than once) — or None where a
    run of its pages cannot be told apart. A copy taken in one run, no longer than its paper, is placed as one
    (`boxes.placed`): it may start part-way, as a copy split across two files does. A copy whose runs lie apart in the
    file is placed run by run, and one with more photographs than its paper has pages photograph by photograph; a page
    photographed more than once is read from the last of them, the one a person took again (goals/l11)."""
    n = len(pymupdf.open(pdf))
    if len(copy["runs"]) == 1 and len(copy["pages"]) <= n:
        placed = boxes.placed(list(render_pdf.photos(cut)), pdf, margin)
        return None if placed is None else (list(copy["pages"]), placed, [])
    at: dict[int, list[int]] = {}
    for run in copy["runs"]:
        placed = _run_placed([render_pdf.photo(scan, f)[0] for f in run], pdf, margin, n)
        if placed is None:
            return None
        for f, p in zip(run, placed):
            at.setdefault(p, []).append(f)
    pages = sorted(at)
    return (
        [at[p][-1] for p in pages],
        pages,
        [{"page": p, "file_pages": at[p]} for p in pages if len(at[p]) > 1],
    )


def _lacks(pdf, placed, twice) -> tuple[list[int], list[str]]:
    """(the paper's pages not in the copy's file, what the file lacks said for the person who scanned it): each page
    not in it, and each in it more than once."""
    n = len(pymupdf.open(pdf))
    gone = [p for p in range(1, n + 1) if p not in placed]
    said = []
    if gone:
        them = "them" if len(gone) > 1 else "it"
        said.append(f"{'pages' if len(gone) > 1 else 'page'} {_and(gone)} of {n}"
                    f" {'are' if len(gone) > 1 else 'is'} not in this file: scan {them} and send {them} to be read")  # fmt: skip
    for t in twice:
        said.append(f"page {t['page']} is in the file {'twice' if len(t['file_pages']) == 2 else 'more than once'}"
                    f" (pages {_and(t['file_pages'])}): page {t['file_pages'][-1]} is read")  # fmt: skip
    return gone, said


def _read_copy(conn, scan, copy, row, name, actor, again):
    """One copy, for the child `row` names: cut to a file of its own, its pages placed, read and marked."""
    mine, code, cid = copy["sheet"], row["code"], row["child_id"]
    # cut as a copy in one run always was: the paper's layout is told from it, and a copy in one run is read from it
    cut = _cut(scan, copy["runs"][0], name)
    pdf = printed_paper.read_from(conn, code, mine, cut)
    if pdf is None:
        return {**row, "skipped": True, "why": "the paper as printed for this child is not kept here, so where its"
                " answers are cannot be told"}  # fmt: skip
    own_template = mine and mine["source"] != "library" and mine["template_id"]
    template, by_key, unread = printed_paper.paper(conn, code, pdf, own_template)
    if mine:
        template["qr"] = copy["qr"]  # the answers land on the copy printed for this child
        _given(conn, copy["qr"], cid)
    # which of the paper's pages each photographed one is: a copy split across two files starts part-way
    where = _placing(scan, copy, cut, pdf, _margin(conn))
    if where is None:
        return {**row, "skipped": True, "why": f"which pages of {code} these are could not be told apart"}
    read, placed, twice = where
    if read != copy["runs"][0]:  # named by every page it holds, never as a file an earlier sorting cut
        cut = _cut(scan, read, f"copy{row['copy']:02d}-p{'-'.join(map(str, read))}-{code}.pdf")
    template["paper_pages"] = placed
    file_page = {p: f for f, p in enumerate(placed, 1)}
    s = _imported(conn, cut, code, cid, actor, again, template, by_key, file_page)
    _replaces(conn, s["capture_id"], scan)
    _placed_on(conn, s["capture_id"], cut, by_key, file_page)
    answers = s.get("already_results") if s.get("already") else len(s["results"])
    missing, lacks = _lacks(pdf, placed, twice)
    return {**row, "answers": answers, "already": bool(s.get("already")), "unread": unread,
            "capture_id": s["capture_id"], "missing": missing, "twice": twice, "lacks": lacks,
            "notes": [n for n in s["notes"] if n]}  # fmt: skip


def _imported(conn, cut, code, cid, actor, again, template, by_key, file_page):
    """The copy read and marked (`legacy.import_scan`); a reading of it that put its answers on questions its pages do
    not hold is replaced, and only by one that was made, never by nothing."""
    held = [it["id"] for it in by_key.values() if it["spec"]["page"] in file_page]
    with conn.transaction():
        wrong, checks = _misplaced(conn, cut, held)
        s = legacy.import_scan(conn, str(cut), code, cid, actor, again=again, rows=(template, by_key))
        if wrong:
            conn.execute("update capture set superseded_by = %s where id = %s", (s["capture_id"], wrong))
            s["notes"].append(
                "an earlier reading put this copy's answers on questions its pages do not hold; replaced"
                + (
                    f", and the {checks} checks made on it no longer count: check them again"
                    if checks
                    else ""
                )
            )
    return s


def _placed_on(conn, capture_id, cut, by_key, file_page):
    """Where a reading's answers are. A copy read before it moved (`WAS_CUT`) points at where it lives. The paper's page
    each answer is on, and the page of this copy's file its photograph is — the same unless the copy starts part-way:
    a worksheet question's page is not in the bank's row (`paper`), and the approval screens show the photograph. And
    its number on this copy (`raw_read.slot`), which a person's own answers, never read over, lack too. Only where
    missing."""
    conn.execute(
        "update capture set path = %s where id = %s and path <> %s", (_home(cut), capture_id, _home(cut))
    )
    for slot, it in ((k, it) for k, it in by_key.items() if it["spec"]["page"] in file_page):
        conn.execute(
            "update item_result set raw_read = (jsonb_build_object('page', %s::int, 'file_page', %s::int,"
            " 'slot', %s::text) || raw_read::jsonb)::text where capture_id = %s and item_id = %s and rid = %s"
            " and raw_read is not null and not (raw_read::jsonb ?& array['file_page', 'slot'])",
            (it["spec"]["page"], file_page[it["spec"]["page"]], slot, capture_id, it["id"],
             marking.response_of(it).get("rid", "a")),
        )  # fmt: skip
