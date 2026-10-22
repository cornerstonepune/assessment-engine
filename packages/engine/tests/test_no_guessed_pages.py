"""UX9a (goals/ux9a-no-guessed-pages.yaml): a page on which no code can be read is never guessed onto a child.

Nimish, 2026-10-22, on PR #252's question (a page with no code inside a child's copy short of a page was read as that
copy's next page): "yes, stop guessing." Such a page stays unread, is listed on Marking by its page number, and is read
only once a person has said whose it is.

Copies are printed for two children as the site prints them (`handout.for_children`), and one child's last page has its
code covered, as a thumb or a fold covers it; the reader is stood in (`test_copies`).
"""

import json
import uuid

import pymupdf
import pytest

from engine.w3_read import copies, inbox, sorting
from tests import test_copies
from tests.test_a_scan_read_whole import _live, _printed
from tests.test_copies import stand_in_reader
from tests.test_sorting import _scanned

conn, worksheet = test_copies.conn, test_copies.worksheet


def test_a_page_with_no_code_is_never_joined_to_the_paper_before_it():
    alone = lambda n: {"qr": None, "pages": [n], "unread": [n]}  # noqa: E731
    assert sorting.group(["CS00AAAA", None, "CS00BBBB", None]) == [
        {"qr": "CS00AAAA", "pages": [1], "unread": []},
        alone(2),
        {"qr": "CS00BBBB", "pages": [3], "unread": []},
        alone(4),
    ]
    # a library worksheet's copies are no different: a page with no code joins no copy, before it or after it
    two = {"R2-E12": 2, "R5-H14": 2}.get
    got = sorting.group(["R2-E12", None, "R2-E12", "R2-E12", None, "R5-H14"], lambda c: two(c, 0))
    assert [(p["qr"], p["pages"]) for p in got] == [
        ("R2-E12", [1]),
        (None, [2]),
        ("R2-E12", [3, 4]),
        (None, [5]),
        ("R5-H14", [6]),
    ]


def _covered(page, out):
    """The printed page with its code covered: the QR's corner and the code printed in words under it."""
    doc = pymupdf.open(page)
    p = doc[0]
    r = p.rect
    p.draw_rect(pymupdf.Rect(r.width * 0.5, 0, r.width, r.height * 0.22), color=(1, 1, 1), fill=(1, 1, 1))
    for hit in p.search_for("CS"):
        p.draw_rect(hit + (-4, -4, 80, 4), color=(1, 1, 1), fill=(1, 1, 1))
    doc.save(out)
    return out


def _first_page_hidden(conn, worksheet, tmp_path, monkeypatch, rolls):
    """The first child's copy, its first page's code covered, then the second child's whole copy. Until 2026-10-22 the
    page was read as the first child's, as the page their copy was short of (`sorting.group`)."""
    kids, page, n, ids = _printed(conn, worksheet, tmp_path, rolls)
    stand_in_reader(conn, ids, monkeypatch)
    hidden = _covered(page[0], tmp_path / "covered.pdf")
    scan = _scanned([hidden, *page[1 : 2 * n]], tmp_path / f"hidden-{rolls[0]}.pdf")
    return kids, n, ids, scan


def test_a_page_with_no_code_beside_a_childs_short_paper_lands_on_no_child(
    conn, worksheet, tmp_path, monkeypatch
):
    kids, n, ids, scan = _first_page_hidden(conn, worksheet, tmp_path, monkeypatch, ["81", "82"])

    got = copies.read(conn, scan, "", None, "test")
    alone, first = got[0], got[1]
    assert (alone["child_id"], alone["pages"], alone["no_code"], alone["skipped"]) == (None, [1], [1], True)
    assert (first["child_id"], first["pages"], first["missing"]) == (kids[0], list(range(2, n + 1)), [1])
    assert _live(conn, kids[0]) < len(ids), (
        "no answer from the page lands on the child it would have been guessed for"
    )
    assert _live(conn, kids[1]) == len(ids)


def test_a_page_a_person_gives_to_a_child_is_read_as_theirs(conn, worksheet, tmp_path, monkeypatch):
    kids, n, ids, scan = _first_page_hidden(conn, worksheet, tmp_path, monkeypatch, ["83", "84"])

    got = copies.read(conn, scan, "", None, "test", given={1: kids[0]})
    first = got[0]
    assert (first["child_id"], first["pages"], first["missing"], first["given"]) == (
        kids[0],
        list(range(1, n + 1)),
        [],
        [1],
    )
    assert all(not c["no_code"] for c in got) and len(got) == 2, "the page is no longer waiting"
    assert _live(conn, kids[0]) == len(ids), "every answer of the paper read, the given page's too"


def _run(conn, copies_, status="ok", file="u9a.pdf"):
    tenant = conn.execute("select id from tenant limit 1").fetchone()["id"]
    return str(
        conn.execute(
            "insert into flow_run (tenant_id, flow, trigger, status, result) values (%s, 'read-scan', %s, %s, %s)"
            " returning id",
            (
                tenant,
                f"educator@school: {file}",
                status,
                json.dumps({"pages": 5, "file": file, "copies": copies_}),
            ),
        ).fetchone()["id"]
    )


def test_a_page_is_given_only_to_a_child_whose_paper_is_in_the_file_and_only_while_it_waits(
    conn, tmp_path, monkeypatch
):
    monkeypatch.setattr(inbox, "INBOX", tmp_path)
    (tmp_path / "u9a.pdf").write_bytes(b"%PDF-1.4")
    mine, other = str(uuid.uuid4()), str(uuid.uuid4())
    lines = [
        {"copy": 1, "pages": [1, 2], "code": "CS9A0001", "child_id": mine, "by_code": True, "answers": 4,
         "missing": [3], "no_code": []},
        {"copy": 2, "pages": [3], "code": "?", "child_id": None, "answers": 0, "skipped": True,
         "why": "no code could be read on the page", "no_code": [3]},
    ]  # fmt: skip
    run = _run(conn, lines)

    with pytest.raises(inbox.Refused, match="page 2 of this file is not one waiting"):
        inbox.give(conn, run, 2, mine, "educator@school")
    with pytest.raises(inbox.Refused, match="no paper of that child is in this file"):
        inbox.give(conn, run, 3, other, "educator@school")
    assert inbox.give(conn, run, 3, mine, "educator@school") == tmp_path / "u9a.pdf"
    row = conn.execute("select status, result from flow_run where id = %s", (run,)).fetchone()
    assert row["status"] == "running", "read again now, with the page as the child's"
    assert [(g["page"], g["child_id"], g["by"]) for g in row["result"]["given"]] == [
        (3, mine, "educator@school")
    ]
    with pytest.raises(inbox.Refused, match="still being read"):
        inbox.give(conn, _run(conn, lines, status="running"), 3, mine, "educator@school")


def test_the_reading_reads_each_page_as_the_child_a_person_gave_it_to(conn, monkeypatch):
    mine = str(uuid.uuid4())
    run = _run(conn, [], file="u9a-given.pdf")
    conn.execute(
        "update flow_run set result = result || %s where id = %s",
        (json.dumps({"given": [{"page": 3, "child_id": mine, "by": "educator@school"}]}), run),
    )
    assert inbox.given(conn, "u9a-given.pdf") == {3: mine}
