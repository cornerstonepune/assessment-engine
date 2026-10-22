"""L11 (goals/l11-a-scan-is-read-whole.yaml): every page of a child's paper in a scanned file is read, wherever in the
file it lies; a page photographed twice is read once, from its later photograph; and what the file lacks is said, copy
by copy, on the run a person looks at.

2026-10-16, the Grade 3 scan: roll 4's first page was photographed twice, as the file's first and ninth pages, and roll
1's first page not at all. Pages were one copy only where they lay together, so the ninth page's copy was read as a
second copy of roll 4's paper and replaced the first's reading — whole there by luck, since the later copy held both
pages — and nothing said roll 1's paper was half there.

Copies are printed for two children as the site prints them (`handout.for_children`, each child's own code on every
page), cut into pages, and scanned in the order each test needs; the reader is stood in (`test_copies`).
"""

import json

import pymupdf

from engine.w2_print import handout
from engine.w3_read import copies, inbox, sorting
from tests import test_copies
from tests.test_copies import _child, stand_in_reader
from tests.test_inbox import RUN, _Tx
from tests.test_sorting import _scanned

WEEK = "2026-W42"
conn, worksheet = test_copies.conn, test_copies.worksheet  # a worksheet as the library prints it


def test_a_childs_own_pages_are_one_copy_wherever_they_lie_and_a_worksheets_copies_stay_apart():
    got = sorting.gather(sorting.group(["CS00AAAA", "CS00BBBB", "CS00BBBB", "CS00AAAA", None]))
    assert [(p["qr"], p["pages"], p["runs"], p["unread"]) for p in got] == [
        ("CS00AAAA", [1, 4], [[1], [4]], []),
        ("CS00BBBB", [2, 3], [[2, 3]], []),
        (None, [5], [[5]], [5]),  # no code: nobody's (goals/ux9a-no-guessed-pages.yaml)
    ]
    assert [sorting.pages_said(p["pages"]) for p in got] == ["p1, p4", "p2–3", "p5"]
    # a library worksheet's code is on every child's copy of it: copies apart in the file are different children's
    two = {"R2-E12": 2}.get
    got = sorting.gather(
        sorting.group(["R2-E12", "R2-E12", "CS00AAAA", "R2-E12", "R2-E12"], lambda c: two(c, 0))
    )
    assert [(p["qr"], p["pages"]) for p in got] == [("R2-E12", [1, 2]), ("CS00AAAA", [3]), ("R2-E12", [4, 5])]


def _printed(conn, worksheet, tmp_path, rolls):
    """(the children, each printed page as a file of its own in print order, the paper's length, its questions)."""
    tenant, code, ids, pdf = worksheet
    kids = [_child(conn, tenant, r, f"Child{r}") for r in rolls]
    printed = handout.for_children(conn, code, kids, WEEK, "educator@school", tmp_path / "print")
    pages = []
    with pymupdf.open(printed) as doc:
        for i in range(len(doc)):
            one = pymupdf.open()
            one.insert_pdf(doc, from_page=i, to_page=i)
            one.save(tmp_path / f"printed-{i + 1:02d}.pdf")
            pages.append(tmp_path / f"printed-{i + 1:02d}.pdf")
    n = len(pymupdf.open(pdf))
    assert n >= 2 and len(pages) == 2 * n, "two children's copies of a paper of two pages or more"
    return kids, pages, n, ids


def _live(conn, child):
    """How many of the child's answers the live reading of their copy holds."""
    return conn.execute(
        "select count(*) as n from item_result r join capture c on c.id = r.capture_id"
        " join sheet_instance si on si.id = c.sheet_instance_id where si.child_id = %s and c.superseded_by is null",
        (child,),
    ).fetchone()["n"]


def test_a_childs_pages_apart_in_the_file_are_read_as_one_copy(conn, worksheet, tmp_path, monkeypatch):
    kids, page, n, ids = _printed(conn, worksheet, tmp_path, ["61", "62"])
    stand_in_reader(conn, ids, monkeypatch)
    # the first child's first page, the second child's whole copy, then the first child's other pages
    scan = _scanned([page[0], *page[n:], *page[1:n]], tmp_path / "apart.pdf")

    got = copies.read(conn, scan, "", [], "test")
    assert [(c["child_id"], c["pages"], c["answers"], c["missing"]) for c in got] == [
        (kids[0], [1, *range(n + 2, 2 * n + 1)], len(ids), []),
        (kids[1], list(range(2, n + 2)), len(ids), []),
    ]
    assert [_live(conn, k) for k in kids] == [len(ids)] * 2, "every answer of each paper stays read"


def test_a_page_photographed_twice_is_read_once_from_the_later_and_said(
    conn, worksheet, tmp_path, monkeypatch
):
    kids, page, n, ids = _printed(conn, worksheet, tmp_path, ["63", "64"])
    stand_in_reader(conn, ids, monkeypatch)
    # both copies whole, then the first child's first page again: read as a copy of its own, it replaced the whole one
    scan = _scanned([*page[: 2 * n], page[0]], tmp_path / "twice.pdf")

    got = copies.read(conn, scan, "", [], "test")
    first = got[0]
    assert (first["child_id"], first["answers"]) == (kids[0], len(ids))
    assert first["twice"] == [{"page": 1, "file_pages": [1, 2 * n + 1]}]
    assert (
        f"page 1 is in the file twice (pages 1 and {2 * n + 1}): page {2 * n + 1} is read" in first["lacks"]
    )
    assert [_live(conn, k) for k in kids] == [len(ids)] * 2


def test_a_page_not_in_the_file_is_said_by_its_page(conn, worksheet, tmp_path, monkeypatch):
    kids, page, n, ids = _printed(conn, worksheet, tmp_path, ["65", "66"])
    stand_in_reader(conn, ids, monkeypatch)
    scan = _scanned(
        [*page[1:n], *page[n:]], tmp_path / "short.pdf"
    )  # the first child's first page never scanned

    got = copies.read(conn, scan, "", [], "test")
    assert (got[0]["child_id"], got[0]["missing"]) == (kids[0], [1])
    assert f"page 1 of {n} is not in this file: scan it and send it to be read" in got[0]["lacks"]
    assert got[1]["missing"] == [] and _live(conn, kids[1]) == len(ids)


def test_what_a_files_reading_came_to_is_kept_on_its_run_with_no_name(tmp_path, monkeypatch):
    kept = []
    monkeypatch.setattr(inbox.db, "connect", lambda *a, **k: _Tx(kept))
    lines = [
        {"copy": 1, "pages": [2], "code": "CS6A1B49", "child_id": "c1", "answers": 9, "missing": [1], "twice": [],
         "lacks": ["page 1 of 2 is not in this file: scan it and send it to be read"], "capture_id": "k1"},
        {"copy": 2, "pages": [11], "code": "?", "child_id": None, "answers": 0, "skipped": True,
         "why": "no code could be read on the page"},
    ]  # fmt: skip
    monkeypatch.setattr(copies, "read", lambda *a, **k: lines)

    assert inbox.read(RUN, tmp_path / "2026-10-16.pdf", "achal@school") == lines
    [(sql, params)] = kept
    assert "status = 'ok'" in sql and "result" in sql
    assert json.loads(params[0]) == {"copies": lines}
