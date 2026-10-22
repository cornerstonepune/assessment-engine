"""N8 — which page of the paper each photograph IS (goals/ck2-photograph-is-its-page.yaml).

A photograph's page is told by what it prints, never by where it sits in the file. Each photograph is laid on every page
of the paper it could be (`_fits`: its ruled layout, times how much of the print only that page has is on it), and the
way of laying them that fits best stands if it fits clearly better than the next (`placed`). The printed pages say no
number in words and carry one QR between them, so the print is all there is to go by.
"""

import cv2
import numpy as np
import pymupdf

from engine.w3_read.boxes import _ruled, _rules, dark
from engine.w3_read.lineup import PPM, PRINTED, H, W, blank, line_up

# Telling one page of a worksheet from another (`_fits`): each page's own print is its words that no other page
# prints within APART mm, looked for on the photograph within OWN_GROW mm, at PPM / FINE — 5 px a mm, a digit's
# strokes apart. On the 2026-09-29 photographs this put all eight on their own page; the ruled lines alone, five.
FINE = 2
APART = 1.0
OWN_GROW = 0.5


def _fine(mask):
    return cv2.resize(mask.astype(np.uint8), (W // FINE, H // FINE), interpolation=cv2.INTER_AREA) > 0


def _grown(mask, mm):
    k = np.ones((2 * max(1, int(mm * PPM / FINE)) + 1,) * 2, np.uint8)
    return cv2.dilate(mask.astype(np.uint8), k).astype(bool)


def _own_print(pdf):
    """{page: its own print}: the words and numbers a page prints that no other page of `pdf` prints within APART mm
    of the same place — its questions, not the labels, boxes and footer every page shares."""
    with pymupdf.open(pdf) as doc:
        n = len(doc)
    words = {}
    for p in range(1, n + 1):
        pr = blank(str(pdf), p) < PRINTED
        words[p] = _fine(pr & ~(_rules(pr) > 0))
    near = {p: _grown(words[p], APART) for p in words}
    return {p: words[p] & ~np.logical_or.reduce([near[q] for q in words if q != p] or [np.zeros_like(words[p])])
            for p in words}  # fmt: skip


def _fits(img, pdf, page_no, own):
    """How surely a photographed page is `pdf`'s page `page_no`: its layout (`_ruled`), times how much of the print
    only that page has is on the photograph. Pages of one worksheet share a layout — on 2026-09-29 the ruled lines
    alone took R8-H03's page 4 for its page 2 — and differ in their questions."""
    canon, _ = line_up(img, pdf, page_no)
    if canon is None:
        return 0.0
    mine = own[page_no]
    if not mine.any():
        return _ruled(canon, pdf, page_no)
    found = (mine & _grown(_fine(dark(canon)), OWN_GROW)).sum() / mine.sum()
    return _ruled(canon, pdf, page_no) * float(found)


def _placing(pages, pdf):
    """(how well, which printed page each photograph is, how well the next best did): the way of laying the
    photographs on distinct pages of `pdf` that they fit (`_fits`) most. Not "in order": on 2026-10-22 four of ten
    copies of a two-page paper were photographed second page first, and a copy with as many photographs as the paper
    has pages, taken as 1…n unmeasured, had its second page's questions looked for on its first page's photograph.
    A copy may also start part-way: on 2026-09-29 one child's copy was photographed across two files, and the second
    file's two pages — the paper's third and fourth — were read as its first and second, against questions 1–6.
    Nothing is measured only where nothing can differ: one page, or a photograph over for every page (more
    photographs than the paper has pages — `copies._run_placed` places those one by one). Where no photograph lines
    up with any page, nothing measured says otherwise: the file's order stands, and each page that does not line up
    goes whole to a person."""
    n, k = len(pymupdf.open(pdf)), len(pages)
    if k > n or n == 1:
        return None, list(range(1, k + 1)), None
    runs = _runs(pages, pdf)
    if k == n and runs[0][0] <= 0:
        return None, list(range(1, k + 1)), None
    return runs[0][0], runs[0][1], runs[1][0] if len(runs) > 1 else 0.0


def _best(fit, k, n, banned=()):
    """(the most the photographs fit, which page each is): each of `k` photographs on a page of 1…`n` of its own,
    `banned` (photograph, page) pairs left out. Dynamic over the pages used, so a long paper costs 2**n, not n!."""
    states = {0: (0.0, [])}
    for i in range(k):
        step = {}
        for used, (score, run) in states.items():
            for p in range(1, n + 1):
                if used >> p & 1 or (i, p) in banned:
                    continue
                at = used | 1 << p
                if at not in step or score + fit(i, p) > step[at][0]:
                    step[at] = (score + fit(i, p), run + [p])
        states = step
    return max(states.values(), default=(float("-inf"), []))


def _runs(pages, pdf):
    """The best and the next best way of laying `pdf`'s pages under the photographs, with how well they fit (`_fits`):
    [(score, pages)], best first. The next best is the best that differs from it in at least one photograph's page.
    Every photograph is measured against every page it could be."""
    n, k, own, fit = len(pymupdf.open(pdf)), len(pages), _own_print(pdf), {}

    def at(i, p):
        if (i, p) not in fit:
            fit[i, p] = _fits(pages[i], pdf, p, own)
        return fit[i, p]

    best = _best(at, k, n)
    others = [_best(at, k, n, {(i, p)}) for i, p in enumerate(best[1])]
    return [best, *sorted((o for o in others if o[1]), reverse=True)[:1]]


def placed(pages, pdf, margin) -> list[int] | None:
    """Which page of `pdf` each photographed page of a copy is, in order (`_placing`) — or None when no way of laying
    them fits `margin` times better than the next: its answers are then not read against a key nobody can be sure of,
    and a person places the pages."""
    best, run, second = _placing(pages, pdf)
    if best is None:
        return run
    return run if best > 0 and best >= margin * second else None


def as_printed(pages, pdfs):
    """Of the PDFs one worksheet has printed as (one per `render.layouts` row, goals/s18-read-as-printed.yaml), the
    one a copy was printed from: of those long enough to hold its photographs, the one whose run of pages they fit
    most (`_runs`), every layout measured alike. `pages`: the copy's pages as photographed, in order — all of them, or
    a run of them. Its page count does not tell its layout: on 2026-10-15 a copy photographed from its second page on
    held as many pages as the layout before L3 draws its worksheet in, was read in that layout unmeasured, and its
    answers landed on questions 1 to 8 (test_copies)."""
    held = [pdf for pdf in pdfs if len(pymupdf.open(pdf)) >= len(pages)] or list(pdfs)
    if len(held) == 1:
        return held[0]
    # the whole page's ruled lines (`_ruled`), not only those near the answers: held to the answer boxes alone, a copy
    # printed in the 21 Sep layout agreed with 24 Sep's more (0.576) than its own (0.503); over the page, its own 0.875
    # against 0.607 (2026-09-29, test_copies on a database built from the seed)
    return max(held, key=lambda pdf: (_runs(pages, pdf) or [(0.0, [])])[0][0])
