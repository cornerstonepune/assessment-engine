# ruff: noqa: F811, F401, E402  (fixtures are imported by name and used as arguments)
"""A page of a paper that is another page again is never shown as its second page
(goals/img_page_one_and_two_same_photo.yaml).

2026-10-23: the check screen drew a copy's page 1 and page 2 as the same photograph. The engine laid a second photograph
of page 1 on the page the paper had left (`placing.place` refuses it now), and the image server answered a page the file
does not have with the file's last page, so a reading made before is told by its pixels (`same_page`).
"""

import cv2
import numpy as np
import pymupdf
import pytest

from engine.w3_read import copies, placing, same_page
from tests.test_copies import SECTION, _child, conn, stand_in_reader, worksheet
from tests.test_lineup import equal_groups
from tests.test_photograph_page import _file
from tests.test_sorting import _scanned


def test_a_page_is_its_bytes_two_pages_with_the_same_bytes_are_one_photograph():
    page = np.zeros((20, 10, 3), np.uint8)
    other = page.copy()
    other[3, 3] = 1  # one pixel
    assert same_page.fingerprint(page) == same_page.fingerprint(page.copy())
    assert same_page.fingerprint(page) != same_page.fingerprint(other)
    assert same_page.fingerprint(page) != same_page.fingerprint(np.zeros((10, 20, 3), np.uint8)), (
        "same bytes, new shape"
    )


def test_the_later_page_is_the_repeat_of_the_earliest():
    assert same_page.repeats({1: "a", 2: "b", 3: "a", 4: "a"}) == {3: 1, 4: 1}
    assert same_page.repeats({1: "a", 2: "b"}) == {}


def test_the_words_name_the_page_and_the_page_it_is_again():
    assert same_page.words(2, 1) == "page 2 not found: the photograph in its place is page 1 again"
    assert same_page.words(2) == "page 2 not found: no photograph of it is in the file"
    assert same_page.sentence(2, 1) == "Page 2 not found. The photograph in its place is page 1 again."


def test_the_two_pages_of_the_grade_1_paper_are_two_photographs(equal_groups, tmp_path):
    same = _file(equal_groups, tmp_path, (1, 1))
    two = _file(equal_groups, tmp_path, (1, 2))
    one = _file(equal_groups, tmp_path, (1,))
    assert same_page.repeats(same_page._prints(same, {1: 1, 2: 2})) == {2: 1}, "page 1 photographed twice"
    assert same_page.repeats(same_page._prints(two, {1: 1, 2: 2})) == {}
    assert same_page.repeats(same_page._prints(one, {1: 1, 2: 2})) == {2: 1}, (
        "a file with no second page: page 1 again"
    )


def _two_pages_of(pdf, tmp_path, order, name):
    with pymupdf.open(pdf) as doc:
        out = pymupdf.open()
        for i in order:
            out.insert_pdf(doc, from_page=i, to_page=i)
        out.save(tmp_path / name)
    return tmp_path / name


def test_a_copy_whose_second_photograph_is_page_1_again_has_no_second_page_and_says_so(
    conn, worksheet, tmp_path, monkeypatch
):
    """The 23 Oct report, end to end on a seeded copy: pages (1, 1) of a two-page paper. Page 2's answers are read by
    nobody and wait for a person with the reason in words; the stored file holds the page once; no row points at a
    photograph of page 2, and the screen's page list says page 2 is not found."""
    tenant, code, ids, pdf = worksheet
    again = _two_pages_of(pdf, tmp_path, [0, 0], "again.pdf")
    _child(conn, tenant, "45", "Esha")
    stand_in_reader(conn, ids, monkeypatch)
    scan = _scanned([again], tmp_path / "again-file.pdf")

    got = copies.read(conn, scan, SECTION, ["Esha"], "test", pages_of=lambda c: 2)[0]
    assert got["missing"][0] == 2 and any("page 2 of the file is page 1 again" in x for x in got["lacks"]), (
        got["lacks"]
    )
    rows = conn.execute(
        "select r.raw_read::jsonb as raw, r.status from item_result r where r.capture_id = %s",
        (got["capture_id"],),
    ).fetchall()
    lost = [r for r in rows if r["raw"].get("page") == 2]
    assert lost and all(r["raw"]["page_found"] is False for r in lost), "page 2's answers wait for a person"
    assert all(r["raw"]["answer_state"] == "not_found" and r["raw"]["child_answer"] == "" for r in lost)
    assert all(r["raw"]["why"].startswith("page 2 not found") for r in lost)
    assert not [r for r in rows if r["raw"].get("page") == 1 and r["raw"].get("page_found") is False]
    path = conn.execute("select path from capture where id = %s", (got["capture_id"],)).fetchone()["path"]
    with pymupdf.open(path.replace("~", __import__("os").path.expanduser("~"))) as stored:
        assert len(stored) == 1, "the repeat is not stored as a page of the copy"
    found = {p["page"]: p for p in same_page.pages_of(conn, got["capture_id"])}
    assert found[1]["found"] and not found[2]["found"] and found[2]["why"].startswith("page 2 not found")
    assert found[2]["file_page"] is None, "no photograph is drawn for it"


def test_a_reading_made_before_is_told_by_its_pixels(conn, worksheet, tmp_path, monkeypatch):
    """What is on live: the same pair of photographs read as page 1 and page 2 (the placing then laid the repeat on the
    page the paper had left). Nothing is re-read: the screen's page list compares what was stored."""
    tenant, code, ids, pdf = worksheet
    again = _two_pages_of(pdf, tmp_path, [0, 0], "again.pdf")
    _child(conn, tenant, "45", "Esha")
    stand_in_reader(conn, ids, monkeypatch)
    # the placing of a two-page copy before it could refuse a repeat: its photographs were pages 1 and 2, in file order
    monkeypatch.setattr(placing, "place", lambda pages, p, m: placing.Placement([1, 2], {}))
    scan = _scanned([again], tmp_path / "again-file.pdf")

    got = copies.read(conn, scan, SECTION, ["Esha"], "test", pages_of=lambda c: 2)[0]
    assert 2 not in got["missing"], (
        "read as it was read before: page 2 has its photograph, the same as page 1's"
    )
    found = {p["page"]: p for p in same_page.pages_of(conn, got["capture_id"])}
    assert found[1]["found"] and not found[2]["found"]
    assert found[2]["why"] == "page 2 not found: the photograph in its place is page 1 again"


def test_a_copy_of_two_different_pages_is_found_whole(conn, worksheet, tmp_path, monkeypatch):
    tenant, code, ids, pdf = worksheet
    both = _two_pages_of(pdf, tmp_path, [0, 1], "both.pdf")
    _child(conn, tenant, "45", "Esha")
    stand_in_reader(conn, ids, monkeypatch)
    scan = _scanned([both], tmp_path / "both-file.pdf")

    got = copies.read(conn, scan, SECTION, ["Esha"], "test", pages_of=lambda c: 2)[0]
    assert got["missing"] == [3, 4], (
        "pages 3 and 4 were never photographed, as before: no answers, said in `lacks`"
    )
    assert [(p["page"], p["found"]) for p in same_page.pages_of(conn, got["capture_id"])] == [
        (1, True),
        (2, True),
    ]
