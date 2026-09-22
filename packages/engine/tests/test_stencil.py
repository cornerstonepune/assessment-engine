"""The stencil: a paper's blank rebuilt from its copies, and the one rule it applies to a child's page."""

import cv2
import numpy as np

from engine.w3_read import stencil


def _page(marks=()):
    """A printed page — a heading and three rules — with a child's marks drawn where asked."""
    img = np.full((1400, 1000), 255, np.uint8)
    cv2.putText(img, "Grade 3 Mathematics Assessment", (80, 120), cv2.FONT_HERSHEY_SIMPLEX, 1.4, 0, 3)
    for i, y in enumerate((300, 600, 900)):
        cv2.putText(img, f"{i + 1}. 45 + 38 =", (80, y), cv2.FONT_HERSHEY_SIMPLEX, 1.3, 0, 3)
        cv2.rectangle(img, (520, y - 60), (760, y + 30), 0, 3)
        cv2.line(img, (80, y + 90), (900, y + 90), 0, 2)
    for text, (x, y) in marks:
        cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SCRIPT_SIMPLEX, 2.2, 0, 4)
    return cv2.imencode(".jpg", img)[1].tobytes()


def test_a_mark_on_one_copy_of_three_is_voted_away_and_the_print_survives():
    copies = [_page([("83", (560, 300))]), _page([("71", (560, 600))]), _page([("12", (560, 900))])]
    blank, used, _ = stencil.build(copies)
    assert used == 3
    empty = stencil.grey(_page())
    clean = cv2.resize(blank, (empty.shape[1], empty.shape[0]))
    # inside each box the blank is as white as the unmarked page, and the printed rule is still dark
    for y in (300, 600, 900):
        box = (
            slice(int((y - 50) * 2000 / 1400), int((y + 20) * 2000 / 1400)),
            slice(int(540 * 2000 / 1400), int(740 * 2000 / 1400)),
        )
        assert clean[box].mean() > 240
    assert clean[int(390 * 2000 / 1400), int(400 * 2000 / 1400)] < 128


def _w(text, x, y, hand, w=0.05, h=0.02):
    return {"text": text, "x": x, "y": y, "w": w, "h": h, "hand": hand, "confidence": 99.0}


def test_a_childs_number_taken_for_print_is_given_back_only_where_the_blank_is_empty():
    """Nine answers in nine boxes came back as one: 30, 8, 70, 100, 13 and 1113 were tagged PRINT at
    98-99%. Where the blank is empty they are the child's. Where the paper prints ink, where the
    number is one the page prints, and whenever the word is already handwriting, nothing changes."""
    g = np.full((1000, 1000), 255, np.uint8)
    cv2.putText(g, "638 = 600 +", (100, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.5, 0, 4)
    blank = {"grey": g}
    cfg = {"stencil_empty": 0.03}
    got = stencil.promote(
        [
            _w("30", 0.60, 0.19, False),  # print-tagged, the blank is white there -> the child's
            _w("600", 0.26, 0.19, False),  # the paper's own ink under it -> stays the paper's
            _w("475", 0.60, 0.50, False),  # white there, but the page prints 475 -> never given away
            _w("15", 0.10, 0.19, True),  # handwriting stays handwriting, whatever the blank holds
        ],
        blank,
        np.eye(3),
        {"638", "600", "475"},
        cfg,
    )
    assert [w["hand"] for w in got] == [True, False, False, True]


def test_a_page_too_bare_to_line_up_is_read_as_it_was_not_forced_onto_a_blank():
    blank = stencil.grey(_page())
    H, n = stencil.homography(np.full((2000, 1400), 255, np.uint8), blank)
    assert H is None or n < 50


def test_a_printed_question_number_is_never_given_to_the_child(monkeypatch):
    """Kabir left "9 x 6 =" blank. "10." printed beside it landed on white in a photograph that lines
    up with its blank to a percent or two, was given to the child, and he was recorded as answering
    10. Question numbers are print, whatever the blank says."""
    white = np.full((1000, 1000), 255, np.uint8)
    monkeypatch.setattr(stencil, "load", lambda form, page: {"grey": white, "read": {"words": []}})
    monkeypatch.setattr(stencil, "grey", lambda jpeg: white)
    monkeypatch.setattr(stencil, "homography", lambda a, b: (np.eye(3), 500))
    monkeypatch.setattr(stencil, "plausible", lambda *a: True)
    q = _w("9 x 6 =", 0.10, 0.30, False, w=0.2)
    monkeypatch.setattr(
        stencil.ocr, "read", lambda jpeg, cli: {"lines": [q], "words": [_w("10.", 0.04, 0.30, False), q]}
    )
    cfg = {**stencil.ocr.DEFAULTS}
    out = stencil.read_page(b"", {"10": "9 x 6 ="}, cfg, None, form="QUIZ", page_no=2)
    assert out["10"]["child_answer"] != "10"
