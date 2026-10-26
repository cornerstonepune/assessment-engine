"""N9 — whose paper is it: the proof, beside an answer's photograph, that the page belongs to the child its answer is
filed under (goals/chk_whose_paper.yaml). Nimish, 2026-10-23: "this paper is for this child. Otherwise it's very hard for
me to even understand whether you are capturing the right image."

Code decides, never a model: which copy of which scan file the page is, how many pages that copy has, the code printed on
the page, and two checks. A page whose picture is the same, byte for byte, as a page of another child's copy cut from the
same scan file is a repeated photograph; a page whose printed code is another child's copy is on the wrong child.
Either puts a notice on the answer, and a person chooses (`choose`) before it can be confirmed. Nothing is edited or
deleted: a choice is a new `page_choice` row, and the latest stands.
"""

import re
from pathlib import Path

import pymupdf

from engine.w3_read import render_pdf, same_page, sorting

COPY = re.compile(r"^copy(\d+)-")
OURS = re.compile(r"^CS[0-9A-F]{6}$")  # a code this school prints on a child's own paper
SAME = "same_picture"
WRONG = "wrong_code"


def copy_of(path: str) -> tuple[str, int | None]:
    """(the scan file's folder, the copy's number in it): `copies._cut` names a cut `copy06-p1-CS1A2B3C.pdf` inside
    a folder named for the scan."""
    p = Path(path)
    m = COPY.match(p.name)
    return str(p.parent), int(m.group(1)) if m else None


def _told(path, page_no: int) -> tuple[str, str | None] | None:
    """(the page's picture as `same_page.fingerprint` gives it, the code printed on it as `sorting.qr_of` reads it), from
    one drawing of the photograph; None where the file or page is not there. The same photograph put in two copies gives
    the same fingerprint; two photographs of one paper never do."""
    full = Path(path).expanduser()
    if not full.exists():
        return None
    with pymupdf.open(full) as doc:
        if not 1 <= page_no <= len(doc):
            return None
    img = render_pdf.photo(full, page_no)[0]
    return same_page.fingerprint(img), sorting.qr_of(img)


def pages_told(conn, wanted: list[tuple]) -> dict[tuple, tuple[str, str | None]]:
    """{(capture id, file page): (fingerprint, printed code)} for each (capture id, path, file page) wanted: read from
    `capture_page`, and a page not told yet (a file read before the rows existed) told now and kept. A page's photograph
    is drawn once in its life, never on a card (docs/notes/perf-slow-site.md: 8 seconds a click)."""
    ids = list({str(c) for c, _, _ in wanted})
    rows = conn.execute(
        "select capture_id::text, file_page, print, code from capture_page where capture_id = any(%s::uuid[])",
        (ids,),
    ).fetchall()
    told = {(r["capture_id"], r["file_page"]): (r["print"], r["code"]) for r in rows}
    for c, path, page in wanted:
        if (str(c), page) in told or (fact := _told(path, page)) is None:
            continue
        conn.execute(
            "insert into capture_page (capture_id, file_page, tenant_id, print, code)"
            " select id, %s, tenant_id, %s, %s from capture where id = %s on conflict do nothing",
            (page, *fact, c),
        )
        told[(str(c), page)] = fact
    return told


def record(conn, capture_id) -> None:
    """Every page of a capture told and kept, as it is read (`copies._read_copy`), so its first card is as quick as any."""
    cap = conn.execute("select path, pages from capture where id = %s", (capture_id,)).fetchone()
    if cap:
        pages_told(conn, [(capture_id, cap["path"], q) for q in range(1, (cap["pages"] or 0) + 1)])


def verdict(code, filed_code, same_as: list[int]) -> dict | None:
    """The problem on a page, in plain words, or None. `same_as`: the other copies (numbers) whose page has this
    picture. A code that is not one of this school's child codes (a library worksheet's) proves nothing either way."""
    if same_as:
        which = ", ".join(map(str, same_as))
        return {
            "kind": SAME,
            "text": f"This page is the same picture as a page of copy {which} in this file, which is filed under another child.",
        }
    if code and OURS.match(code) and filed_code and OURS.match(filed_code) and code != filed_code:
        return {
            "kind": WRONG,
            "text": f"The code printed on this page is {code}, which is not this child's paper ({filed_code}).",
        }
    return None


def _siblings(conn, folder: str, capture_id) -> list[dict]:
    return conn.execute(
        "select c.id, c.path, c.pages, si.child_id from capture c join sheet_instance si on si.id = c.sheet_instance_id"
        " where c.superseded_by is null and c.id <> %s and c.path like %s",
        (capture_id, folder.replace("%", r"\%").replace("_", r"\_") + "/%"),
    ).fetchall()


def proof(conn, capture_id, file_page: int) -> dict | None:
    """What a card prints beside the photograph: the scan file, the copy and its place in the file, the page of the copy,
    the code read off the page, the code the child's paper was printed with, the notice if any, and a person's latest
    choice on it. None where there is no such capture."""
    cap = conn.execute(
        "select c.path, c.pages, c.qr_read, si.qr_code, si.child_id from capture c"
        " join sheet_instance si on si.id = c.sheet_instance_id where c.id = %s",
        (capture_id,),
    ).fetchone()
    if not cap:
        return None
    folder, k = copy_of(cap["path"])
    sibs = _siblings(conn, folder, capture_id)
    nums = [n for s in sibs if (n := copy_of(s["path"])[1])] + ([k] if k else [])
    others = [s for s in sibs if s["child_id"] != cap["child_id"] and copy_of(s["path"])[1]]
    told = pages_told(conn, [(capture_id, cap["path"], file_page)])
    mine, code = told.get((str(capture_id), file_page), (None, None))
    if mine:
        told |= pages_told(
            conn, [(s["id"], s["path"], q) for s in others for q in range(1, (s["pages"] or 0) + 1)]
        )
    same_as = sorted({
        n for s in others if (n := copy_of(s["path"])[1])
        and any(told.get((str(s["id"]), q), (None,))[0] == mine for q in range(1, (s["pages"] or 0) + 1))
    }) if mine else []  # fmt: skip
    problem = verdict(code, cap["qr_code"], same_as)
    chose = conn.execute(
        "select choice, by from page_choice where capture_id = %s and file_page = %s order by created_at desc limit 1",
        (capture_id, file_page),
    ).fetchone()
    return {"scan": Path(folder).name, "copy": k, "copies": max(nums) if nums else None, "page": file_page,
            "pages": cap["pages"], "code": code, "printed_with": cap["qr_code"], "problem": problem,
            "choice": chose["choice"] if chose else None, "chosen_by": chose["by"] if chose else None}  # fmt: skip


def may_confirm(p: dict | None) -> bool:
    """A person may say Yes to an answer on this page unless it has a notice and nobody has said it is the child's."""
    return not p or not p["problem"] or p["choice"] == "theirs"


def choose(conn, capture_id, file_page: int, choice: str, by: str) -> dict:
    """A person's choice on a page with a notice, as a new row. Refused where the page has no notice."""
    if choice not in ("theirs", "not_theirs"):
        raise ValueError("the choice is 'theirs' or 'not_theirs'")
    p = proof(conn, capture_id, file_page)
    if not p or not p["problem"]:
        raise ValueError("this page has no notice to choose on")
    conn.execute(
        "insert into page_choice (tenant_id, capture_id, file_page, problem, choice, by, created_at)"
        " select tenant_id, id, %s, %s, %s, %s, clock_timestamp() from capture where id = %s",
        (file_page, p["problem"]["kind"], choice, by, capture_id),
    )
    after = proof(conn, capture_id, file_page)
    if after is None:
        raise ValueError("no such capture")
    return after
