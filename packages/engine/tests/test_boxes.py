"""A paper this system printed is read in its boxes (goals/s16-read-the-boxes.yaml, `w3_read/boxes.py`).

A paper is printed exactly as the engine prints one (`render_sheet`), digits are written into some of its
answer boxes and DIFFERENT digits into its working spaces, and the page is "scanned" the way a phone's scan app
hands it over on 2026-09-24: tilted, its top cut off (no corner marks), softened and JPEG-compressed. The
reader is stood in for by a stand-in that recognises the digits it is handed by their shape alone, so the test
is about which pixels reach the reader — the boxes and nothing else — and what code decides around it.
"""

import random
import re

import cv2
import numpy as np
import pymupdf
import pytest

from engine.adapters import ocr
from engine.assess import geometry, items
from engine.assess.pick import Sheet
from engine.assess.render import render_sheet
from engine.w3_read import boxes, render_pdf, sorting

CODE = "CS00C0DE"
FONT, SCALE, THICK = cv2.FONT_HERSHEY_SIMPLEX, 2.6, 5  # a child's digit: about two-thirds of its box


@pytest.fixture(scope="module")
def paper(tmp_path_factory):
    """Six sums, their key, and the paper drawn at the frame the reader lines up in (`boxes.PPM`)."""
    rng = random.Random(7)
    made = [items.bare_sum(rng, "R5", "Procedural", "+", 2, 2, [0, 1]) for _ in range(40)]
    digits = lambda q: len(q.responses[0].answer)  # noqa: E731
    qs = [q for q in made if digits(q) == 2][:4] + [q for q in made if digits(q) == 3][
        :2
    ]  # boxes of 2 and of 3
    out = tmp_path_factory.mktemp("paper")
    key = render_sheet(Sheet(CODE, "G2", "Focus", 1, "W1", qs, title="Practice"), out, week_label="Practice")
    return out / f"{CODE}.pdf", key


def _cells(key, page=1):
    runs, works = geometry.cells_of(key["geometry"], page)
    return runs, works


def _write(img, rect_mm, text, ppm):
    """Digits typed into a recorded region, one per box or in a row, dark grey like pencil."""
    x, y, w, h = (rect_mm[k] * ppm for k in ("x", "y", "w", "h"))
    (tw, th), _ = cv2.getTextSize(text, FONT, SCALE, THICK)
    org = (int(x + (w - tw) / 2), int(y + (h + th) / 2))
    cv2.putText(img, text, org, FONT, SCALE, (45, 45, 45), THICK, cv2.LINE_AA)


def _filled(paper, answers, working):
    """The paper's first page with `answers` {item_key: digits} in its boxes (right-aligned, one digit a box)
    and `working` {item_key: digits} in its working spaces."""
    pdf, key = paper
    img = render_pdf.render(pdf, dpi=boxes.PPM * 25.4)[0]
    runs, works = _cells(key)
    for (item, _rid), run in runs.items():
        wrote = answers.get(item, "")
        for cell, ch in zip(run, wrote.rjust(len(run))):
            if ch.strip():
                _write(img, cell, ch, boxes.PPM)
    for item, text in working.items():
        for w in works[item]:
            _write(img, {**w, "h": w["h"] * 0.6, "y": w["y"] + w["h"] * 0.3}, text, boxes.PPM)
    return img


def _scanned(img, out, blur=3, quality=55, cut=0.05, tilt=1.4):
    """As a phone's scan app hands a page over: the top cut off, tilted, softened, compressed, wrapped in a PDF."""
    h, w = img.shape[:2]
    img = img[int(h * cut) :]
    h = img.shape[0]
    turn = cv2.getRotationMatrix2D((w / 2, h / 2), tilt, 0.98)
    img = cv2.warpAffine(img, turn, (w, h), borderValue=(235, 235, 235))
    img = cv2.GaussianBlur(img, (blur, blur), 0)
    ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_image(page.rect, stream=jpg.tobytes(), keep_proportion=True)
    doc.save(out)
    return out


def _glyphs():
    out = {}
    for d in "0123456789":
        (tw, th), base = cv2.getTextSize(d, FONT, SCALE, THICK)
        canvas = np.full((th + base + 8, tw + 8), 255, np.uint8)
        cv2.putText(canvas, d, (4, th + 4), FONT, SCALE, 45, THICK, cv2.LINE_AA)
        out[d] = canvas
    return out


class StandIn:
    """Reads the digits in an image by their shape, and remembers every image it was handed."""

    def __init__(self):
        self.handed, self.glyphs = [], _glyphs()

    def read(self, image_bytes, cli=None):
        img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
        self.handed.append(img)
        found = []
        for d, g in self.glyphs.items():
            if g.shape[0] > img.shape[0] or g.shape[1] > img.shape[1]:
                continue
            score = cv2.matchTemplate(img, g, cv2.TM_CCOEFF_NORMED)
            ys, xs = np.where(score > 0.6)
            for y, x in zip(ys, xs):
                found.append((float(score[y, x]), int(x), int(y), d))
        found.sort(reverse=True)
        kept = []
        for s, x, y, d in found:  # one digit per place
            if all(abs(x - kx) > self.glyphs[d].shape[1] * 0.5 for _, kx, _, _ in kept):
                kept.append((s, x, y, d))
        h, w = img.shape
        words = [
            {
                "text": d,
                "confidence": round(80 + 19 * s, 1),
                "hand": True,
                "x": x / w,
                "y": y / h,
                "w": 0.1,
                "h": 0.5,
            }
            for s, x, y, d in sorted(kept, key=lambda k: k[1])
        ]
        return {"lines": [], "words": words}


@pytest.fixture
def reader(monkeypatch):
    stand_in = StandIn()
    monkeypatch.setattr(ocr, "read", stand_in.read)
    return stand_in


def _read(paper, scan, reader, cfg=None):
    pdf, key = paper
    img, frame = render_pdf.photo(scan, 1)
    wanted = {str(n): (it["item_id"], "ans") for n, it in enumerate(key["items"], 1)}
    return boxes.read_page(img, 1, pdf, key["geometry"], wanted, None, cfg or ocr.settings(), frame=frame)


def _fits(key, n, seed=0):
    """Digits exactly as many as question `n` prints boxes for (goals/s15-answer-boxes.yaml): what a child
    writes when they fill every box. Not the right answer — the reader is not to know arithmetic."""
    item = key["items"][n - 1]["item_id"]
    run = geometry.cells_of(key["geometry"], 1)[0][(item, "ans")]
    rng = random.Random(f"{n}-{seed}")
    return "".join(str(rng.randint(1 if k == 0 else 0, 9)) for k in range(len(run)))


def _boxes(key, n):
    item = key["items"][n - 1]["item_id"]
    return len(geometry.cells_of(key["geometry"], 1)[0][(item, "ans")])


def test_every_digit_in_a_box_is_read_and_nothing_in_the_working_is(paper, tmp_path, reader):
    pdf, key = paper
    ids = [it["item_id"] for it in key["items"]]
    answers = {ids[n - 1]: "" if n == 3 else _fits(key, n) for n in range(1, 7)}
    working = {ids[0]: "99", ids[1]: "321", ids[2]: "55", ids[3]: "13"}
    scan = _scanned(_filled(paper, answers, working), tmp_path / "scan.pdf")

    got = _read(paper, scan, reader)
    assert {k: r["child_answer"] for k, r in got.items()} == {
        str(n): answers[i] for n, i in enumerate(ids, 1)
    }, {k: (r["answer_state"], r.get("why"), r.get("guess")) for k, r in got.items()}
    assert got["3"]["answer_state"] == "blank" and got["1"]["answer_state"] == "written"
    # what the reader was handed: one strip per answer with ink, and none of them tall enough to hold a
    # working space — the working digits never reach it
    assert len(reader.handed) == 5
    tallest = max(im.shape[0] for im in reader.handed)
    assert tallest < (key["geometry"][0]["h"] + 2 * boxes.MARGIN + 2) * boxes.PPM
    for k, r in got.items():
        assert r["boxes"] == _boxes(key, int(k)) and r["inked"] == len(answers[ids[int(k) - 1]])
        assert 0 <= r["box"][0] < r["box"][2] <= 1 and 0 <= r["box"][1] < r["box"][3] <= 1


def test_working_is_the_third_signal_never_the_answer(paper, tmp_path, reader):
    pdf, key = paper
    ids = [it["item_id"] for it in key["items"]]
    two = _fits(key, 2)
    scan = _scanned(_filled(paper, {ids[1]: two}, {ids[0]: "47", ids[1]: "81"}), tmp_path / "scan.pdf")
    got = _read(paper, scan, reader)
    # a blank box beside a written working: blank, with the working shown — not 47
    assert got["1"]["answer_state"] == "blank" and got["1"]["child_answer"] == ""
    assert got["1"]["working_shown"] == "partial"
    # an answer in the box beside a working: the box's digits, the working shown
    assert got["2"]["child_answer"] == two and got["2"]["working_shown"] == "partial"
    # nothing written anywhere: blank, no working
    assert got["3"]["answer_state"] == "blank" and got["3"]["working_shown"] == "none"


def test_a_reading_with_as_many_digits_as_inked_boxes_stands_and_one_without_waits(
    paper, tmp_path, reader, monkeypatch
):
    pdf, key = paper
    ids = [it["item_id"] for it in key["items"]]
    short = next(n for n in range(1, 7) if _boxes(key, n) == 2)
    long = next(n for n in range(1, 7) if _boxes(key, n) == 3)
    wrote = {ids[short - 1]: _fits(key, short), ids[long - 1]: _fits(key, long)}
    scan = _scanned(_filled(paper, wrote, {}), tmp_path / "scan.pdf")
    real = reader.read

    def two_at_most(image_bytes, cli=None):
        page = real(image_bytes)
        return {**page, "words": page["words"][:2]}  # a reader that drops the third digit of every answer

    monkeypatch.setattr(ocr, "read", two_at_most)
    got = _read(paper, scan, reader)
    s, l = got[str(short)], got[str(long)]  # noqa: E741
    assert s["answer_state"] == "written" and s["child_answer"] == wrote[ids[short - 1]]
    assert l["answer_state"] == "illegible" and l["child_answer"] == ""
    seen = wrote[ids[long - 1]][:2]
    assert re.fullmatch(rf"3 boxes hold ink but the reader saw {seen}", l["why"]) and l["guess"] == seen


def test_the_code_on_a_blurred_and_compressed_scan_is_still_read(paper, tmp_path):
    img = render_pdf.render(paper[0], dpi=boxes.PPM * 25.4)[0]
    scan = _scanned(img, tmp_path / "scan.pdf", blur=7, quality=30, cut=0.0, tilt=2.0)
    page, _ = render_pdf.photo(scan, 1)
    assert sorting.qr_of(page) == CODE
    # and read from the page's own pixels rather than a 150-dpi drawing of it: the photograph is what is kept
    assert page.shape[1] > render_pdf.render(scan)[0].shape[1]


def test_a_page_that_is_not_this_paper_does_not_line_up(paper, tmp_path, reader):
    other = np.full((2800, 2000, 3), 255, np.uint8)
    cv2.putText(other, "not a paper", (200, 1400), FONT, 4, (0, 0, 0), 8)
    scan = _scanned(other, tmp_path / "scan.pdf")
    assert _read(paper, scan, reader) is None
