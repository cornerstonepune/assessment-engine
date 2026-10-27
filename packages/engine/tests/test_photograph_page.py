# ruff: noqa: F811, F401, E402  (fixtures are imported by name and used as arguments)
"""Which page of the paper a photograph IS comes from what it prints, never from where it sits in the file
(goals/ck2-photograph-is-its-page.yaml).

2026-10-22, Grade 1 "Equal groups", 20 pages, 10 copies: on four copies the paper's second page was photographed before
its first. A copy with as many photographs as the paper has pages was taken to be page 1, page 2 in file order with
nothing measured (`placing._placing`), so question 10 was looked for on the first page's photograph and the check screen
showed that photograph under "question 10".
"""

import cv2
import pymupdf
import pytest

from engine.w3_read import placing, render_pdf
from tests.test_boxes import _fitting, _pages
from tests.test_lineup import _g1_scan, equal_groups


def test_two_pages_photographed_in_the_opposite_order_are_placed_by_what_they_print(tmp_path, monkeypatch):
    _fitting(monkeypatch, {("a", 1): 0.1, ("a", 2): 0.8, ("b", 1): 0.7, ("b", 2): 0.1})
    assert placing.placed(["a", "b"], _pages(tmp_path, 2), 1.25) == [2, 1]


def test_two_pages_in_order_are_placed_in_order(tmp_path, monkeypatch):
    _fitting(monkeypatch, {("a", 1): 0.8, ("a", 2): 0.1, ("b", 1): 0.1, ("b", 2): 0.7})
    assert placing.placed(["a", "b"], _pages(tmp_path, 2), 1.25) == [1, 2]


def test_a_page_that_lines_up_with_neither_is_the_page_the_other_leaves(tmp_path, monkeypatch):
    """One photograph lines up with page 2 and the other with nothing: the other is page 1, by elimination."""
    _fitting(monkeypatch, {("a", 1): 0.0, ("a", 2): 0.0, ("b", 1): 0.0, ("b", 2): 0.7})
    assert placing.placed(["a", "b"], _pages(tmp_path, 2), 1.25) == [1, 2]
    _fitting(monkeypatch, {("a", 1): 0.0, ("a", 2): 0.6, ("b", 1): 0.0, ("b", 2): 0.0})
    assert placing.placed(["a", "b"], _pages(tmp_path, 2), 1.25) == [2, 1]


def test_photographs_that_fit_both_orders_alike_keep_the_files_order(tmp_path, monkeypatch):
    """Pages of one paper share a layout: with no clear margin the file's order is the only evidence there is. On CI a
    clean six-page paper was skipped as "could not be told apart" before this."""
    _fitting(monkeypatch, {("a", 1): 0.5, ("a", 2): 0.5, ("b", 1): 0.5, ("b", 2): 0.5})
    assert placing.placed(["a", "b"], _pages(tmp_path, 2), 1.25) == [1, 2]
    _fitting(monkeypatch, {("a", 1): 0.5, ("a", 2): 0.55, ("b", 1): 0.55, ("b", 2): 0.5})
    assert placing.placed(["a", "b"], _pages(tmp_path, 2), 1.25) == [1, 2], (
        "a swap that fits 10% better is no more"
    )


def test_photographs_that_line_up_with_nothing_keep_the_files_order_and_go_whole_to_a_person(
    tmp_path, monkeypatch
):
    """Nothing lines up with any page, so nothing measured says otherwise: the file's order stands, and each page that
    does not line up goes whole to a person (R2), never read by its words."""
    _fitting(monkeypatch, {(ph, p): 0.0 for ph in "ab" for p in (1, 2)})
    assert placing.placed(["a", "b"], _pages(tmp_path, 2), 1.25) == [1, 2]


def test_every_order_of_four_pages_is_found(tmp_path, monkeypatch):
    order = [3, 1, 4, 2]
    _fitting(
        monkeypatch,
        {(ph, p): (0.8 if order[i] == p else 0.05) for i, ph in enumerate("abcd") for p in range(1, 5)},
    )
    assert placing.placed(list("abcd"), _pages(tmp_path, 4), 1.25) == order


def test_a_paper_of_one_page_is_not_measured(tmp_path, monkeypatch):
    monkeypatch.setattr(
        placing, "_fits", lambda *a: pytest.fail("one photograph of a one-page paper is page 1")
    )
    assert placing.placed(["a"], _pages(tmp_path, 1), 1.25) == [1]


def _file(equal_groups, tmp_path, order):
    """The two pages of the Grade 1 paper, each as a phone's picture laid on an A4 page, in a file in `order`."""
    doc = pymupdf.open()
    for p in order:
        with pymupdf.open(_g1_scan(equal_groups, p, tmp_path)) as one:
            doc.insert_pdf(one)
    out = tmp_path / f"file-{''.join(map(str, order))}.pdf"
    doc.save(out)
    return out


@pytest.mark.parametrize("order", [(1, 2), (2, 1)])
def test_the_paper_photographed_by_a_phone_is_placed_in_either_order(equal_groups, tmp_path, order):
    """The template's own render, both pages, as a phone's picture laid on an A4 page, in the file's order or not."""
    photos = list(render_pdf.photos(_file(equal_groups, tmp_path, order)))
    assert placing.placed(photos, equal_groups[0], 1.25) == list(order)


def test_a_photograph_of_the_desk_alone_beside_a_page_is_the_page_the_other_leaves(equal_groups, tmp_path):
    desk = tmp_path / "desk.pdf"
    doc = pymupdf.open()
    doc.new_page(width=595, height=842)
    doc.save(desk)
    both = pymupdf.open()
    with pymupdf.open(_g1_scan(equal_groups, 1, tmp_path)) as one, pymupdf.open(desk) as blank:
        both.insert_pdf(blank)
        both.insert_pdf(one)
    out = tmp_path / "desk-then-1.pdf"
    both.save(out)
    photos = list(render_pdf.photos(out))
    assert placing.placed(photos, equal_groups[0], 1.25) == [2, 1]
    _ = cv2  # the photographs are numpy arrays


def test_a_copy_photographed_second_page_first_is_read_from_the_photographs_that_are_each_page(
    equal_groups,
    tmp_path,
):
    """What `copies` reads a copy from: the file's pages as they lie, and the paper page each is."""
    from engine.w3_read import copies

    scan = _file(equal_groups, tmp_path, (2, 1))
    copy = {"runs": [[1, 2]], "pages": [1, 2]}
    assert copies._placing(scan, copy, scan, equal_groups[0], 1.25) == copies.Where([1, 2], [2, 1], [], {})


# --- reading an uploaded file again ----------------------------------------------------------------------------------

from tests.test_inbox import RUN, client


def test_an_uploaded_file_is_read_again_as_a_run_of_its_own_with_again_set(client, tmp_path, monkeypatch):
    from engine.w3_read import inbox

    c, _ = client
    scan = tmp_path / "22 oct.pdf"
    doc = pymupdf.open()
    for _ in range(4):
        doc.new_page()
    doc.save(scan)
    order = []
    monkeypatch.setattr(
        inbox, "again", lambda conn, run_id: order.append(("again", run_id)) or (scan, "tenant-1")
    )
    monkeypatch.setattr(
        inbox,
        "start",
        lambda tenant, path, actor, pages=None, of_run=None: (
            order.append(("start", tenant, actor, pages, of_run)) or "new"
        ),
    )
    monkeypatch.setattr(
        inbox, "read", lambda run_id, path, actor, again=False: order.append(("read", run_id, path, again))
    )
    r = c.post(f"/read/run/{RUN}/again", json={"by": "achal@school"})
    assert r.status_code == 200, r.text
    assert r.json() == {"run_id": "new", "pages": 4}
    # the new run keeps the uploader of the run it reads again (goals/own_who_sees_answers.yaml)
    assert order == [
        ("again", RUN),
        ("start", "tenant-1", "achal@school", 4, RUN),
        ("read", "new", scan, True),
    ]


def test_a_file_still_being_read_or_no_longer_kept_is_not_read_again_and_says_why(client, monkeypatch):
    from engine.w3_read import inbox

    c, _ = client

    def refuse(conn, run_id):
        raise inbox.Refused(409, "this scan is still being read: read it again once it is read")

    monkeypatch.setattr(inbox, "again", refuse)
    r = c.post(f"/read/run/{RUN}/again", json={"by": "achal@school"})
    assert (r.status_code, "still being read" in r.json()["detail"]) == (409, True)


# --- a page photographed twice is not also the second page ------------------------------------------------------------
# 2026-10-23: on the check screen the paper's page 1 and page 2 were the same photograph. `placing._best` lays the
# photographs on DISTINCT pages whatever they fit, so the second of two photographs of page 1 was given page 2 (it
# fitted page 2 at 0.00 and page 1 at 0.81), its second page's four questions were looked for on it, and the screen drew
# it as page 2 (goals/img_page_one_and_two_same_photo.yaml).


@pytest.mark.parametrize(("order", "run", "refused"), [((1, 1), [1], {1: 1}), ((2, 2), [2], {1: 2})])
def test_a_page_photographed_twice_is_one_page_and_the_repeat_is_refused(
    equal_groups, tmp_path, order, run, refused
):
    photos = list(render_pdf.photos(_file(equal_groups, tmp_path, order)))
    assert placing.place(photos, equal_groups[0], 1.25) == placing.Placement(run, refused)


@pytest.mark.parametrize("order", [(1, 2), (2, 1)])
def test_two_different_pages_refuse_nothing(equal_groups, tmp_path, order):
    photos = list(render_pdf.photos(_file(equal_groups, tmp_path, order)))
    assert placing.place(photos, equal_groups[0], 1.25) == placing.Placement(list(order), {})


def test_the_repeat_is_the_later_photograph_whatever_the_pair_fits_alike(tmp_path, monkeypatch):
    from tests.test_boxes import _fitting, _pages

    _fitting(monkeypatch, {("a", 1): 0.1, ("a", 2): 0.8, ("b", 1): 0.1, ("b", 2): 0.7})
    got = placing.place(["a", "b"], _pages(tmp_path, 2), 1.25)
    assert got == placing.Placement([2], {1: 2}), (
        "the first photograph of a page is the page; the later is the repeat"
    )


def test_a_photograph_that_fits_every_page_alike_is_not_a_repeat(tmp_path, monkeypatch):
    """Pages of one paper share a layout: no clear identity is no evidence of a repeat (the file's order stands)."""
    from tests.test_boxes import _fitting, _pages

    _fitting(monkeypatch, {("a", 1): 0.5, ("a", 2): 0.5, ("b", 1): 0.5, ("b", 2): 0.5})
    assert placing.place(["a", "b"], _pages(tmp_path, 2), 1.25) == placing.Placement([1, 2], {})
    _fitting(monkeypatch, {("a", 1): 0.5, ("a", 2): 0.55, ("b", 1): 0.55, ("b", 2): 0.5})
    assert placing.place(["a", "b"], _pages(tmp_path, 2), 1.25) == placing.Placement([1, 2], {})


def test_a_photograph_that_fits_no_page_is_not_a_repeat(tmp_path, monkeypatch):
    """The desk beside a page is the page the other leaves, as before (`placed`)."""
    from tests.test_boxes import _fitting, _pages

    _fitting(monkeypatch, {("a", 1): 0.0, ("a", 2): 0.0, ("b", 1): 0.0, ("b", 2): 0.7})
    assert placing.place(["a", "b"], _pages(tmp_path, 2), 1.25) == placing.Placement([1, 2], {})


def test_a_repeat_among_three_pages_leaves_the_others_where_they_fit(tmp_path, monkeypatch):
    from tests.test_boxes import _fitting, _pages

    fit = {("a", 1): 0.8, ("a", 2): 0.0, ("a", 3): 0.0,
           ("b", 1): 0.8, ("b", 2): 0.0, ("b", 3): 0.0,
           ("c", 1): 0.0, ("c", 2): 0.0, ("c", 3): 0.7}  # fmt: skip
    _fitting(monkeypatch, fit)
    assert placing.place(["a", "b", "c"], _pages(tmp_path, 3), 1.25) == placing.Placement([1, 3], {1: 1})
