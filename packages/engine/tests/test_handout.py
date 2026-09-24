"""A library worksheet printed for the children an educator picks: one copy each, each with its own code, recorded
for its child — and a scan of those copies reads itself onto each child with no name said (`engine read file`)."""

import pymupdf

from engine.w2_print import handout
from engine.w3_read import copies
from tests import test_copies
from tests.test_copies import _child, stand_in_reader
from tests.test_sorting import _scanned

WEEK = "2026-W39"
conn, worksheet = (
    test_copies.conn,
    test_copies.worksheet,
)  # the same fixtures: a worksheet as the library prints it


def test_each_child_gets_a_copy_with_its_own_code_printed_in_the_educators_name_and_a_reprint_is_the_same_copy(
    conn, worksheet, tmp_path
):
    tenant, code, ids, pdf = worksheet
    kids = [_child(conn, tenant, "51", "Esha"), _child(conn, tenant, "52", "Farah")]
    out = handout.for_children(conn, code, kids, WEEK, "educator@school", tmp_path / "print")
    rows = conn.execute(
        "select si.qr_code, si.child_id, si.print_status, si.approved_by, si.kind, t.code from sheet_instance si"
        " join sheet_template t on t.id = si.sheet_template_id where si.child_id = any(%s) order by si.qr_code",
        (kids,),
    ).fetchall()
    assert {r["child_id"] for r in rows} == set(kids) and len(rows) == 2
    assert all(r["qr_code"].startswith("CS") and r["code"] == code for r in rows)
    assert {(r["print_status"], r["approved_by"], r["kind"]) for r in rows} == {
        ("printed", "educator@school", "custom")
    }
    assert len(pymupdf.open(out)) == 2 * len(pymupdf.open(pdf))
    seen = conn.execute(
        "select count(*) as n from item_exposure where child_id = any(%s)", (kids,)
    ).fetchone()["n"]
    assert seen == 2 * len(ids), "what each child was shown is recorded"

    handout.for_children(conn, code, kids, WEEK, "educator@school", tmp_path / "again")
    n = conn.execute("select count(*) as n from sheet_instance where child_id = any(%s)", (kids,)).fetchone()[
        "n"
    ]
    assert n == 2, "the same worksheet for the same child this week is the same copy"


def test_a_scan_of_copies_printed_for_children_reads_each_onto_its_child_with_no_name_said(
    conn, worksheet, tmp_path, monkeypatch
):
    tenant, code, ids, _ = worksheet
    kids = [_child(conn, tenant, "53", "Gita"), _child(conn, tenant, "54", "Hema")]
    printed = handout.for_children(conn, code, kids, WEEK, "educator@school", tmp_path / "print")
    stand_in_reader(conn, ids, monkeypatch)
    scan = _scanned([printed], tmp_path / "class.pdf")
    got = copies.read(conn, scan, "", [], "test")
    assert [(c["child_id"], c["by_code"], c["answers"]) for c in got] == [
        (kids[0], True, 12),
        (kids[1], True, 12),
    ]
    landed = conn.execute(
        "select si.child_id, si.qr_code from capture c join sheet_instance si on si.id = c.sheet_instance_id"
        " where si.child_id = any(%s) and c.superseded_by is null",
        (kids,),
    ).fetchall()
    assert {r["child_id"] for r in landed} == set(kids)
    assert all(r["qr_code"].startswith("CS") for r in landed), (
        "the answers are on the copy printed for the child"
    )


def test_a_paper_whose_qr_will_not_scan_is_read_by_the_code_printed_beside_it_and_a_second_read_replaces_the_first(
    conn, worksheet, tmp_path, monkeypatch
):
    """2026-09-24: the QR scanned on 3 of 16 one-page papers, and each unread page was joined to the paper before
    it. The code printed in words beside the QR finds each paper its child; reading the file again stands in for
    the earlier reading of the same paper, never beside it."""
    from engine.w3_read import sorting

    tenant, code, ids, _ = worksheet
    kids = [_child(conn, tenant, "55", "Ira"), _child(conn, tenant, "56", "Jaya")]
    printed = handout.for_children(conn, code, kids, WEEK, "educator@school", tmp_path / "print")
    stand_in_reader(conn, ids, monkeypatch)
    scan = _scanned([printed], tmp_path / "class.pdf")
    real = sorting.qr_of
    pages = len(pymupdf.open(printed)) // 2
    seen = iter(range(10_000))
    # the second child's QR is spoiled on every page; their code still reads in words
    monkeypatch.setattr(
        sorting, "qr_of", lambda img: None if next(seen) % (2 * pages) >= pages else real(img)
    )
    second = [real(img) for img in sorting.render_pdf.render(printed)][pages]
    words = lambda img: [f"Show your working · {second}"]  # noqa: E731
    first = copies.read(conn, scan, "", [], "test", read_text=words)
    assert {c["child_id"] for c in first if not c.get("skipped")} == set(kids)
    assert all(c["by_code"] for c in first if not c.get("skipped"))
    copies.read(conn, scan, "", [], "test", read_text=words)  # read again: nothing added beside it
    live = conn.execute(
        "select si.child_id, count(*) as n from capture c join sheet_instance si on si.id = c.sheet_instance_id"
        " where si.child_id = any(%s) and c.superseded_by is null group by 1",
        (kids,),
    ).fetchall()
    assert sorted(r["n"] for r in live) == [1, 1], "each child's paper read once"
