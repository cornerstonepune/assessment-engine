"""A paper this system printed is read in its boxes (goals/s16-read-the-boxes.yaml, `w3_read/boxes.py`).

A paper is printed exactly as the engine prints one (`render_sheet`), digits are written into some of its
answer boxes and DIFFERENT digits into its working spaces, and the page is "scanned" the way a phone's scan app
hands it over on 2026-09-24: tilted, its top cut off (no corner marks), softened and JPEG-compressed. Most
tests stand a shape-matcher in for the reader, so they are about which pixels reach it — each answer's boxes as
photographed, never the working (ADR 0035) — and what code decides around it; the bent-page tests at the end
run the real reader (`adapters/digits.py`).
"""

import json
import random
import re

import cv2
import numpy as np
import pymupdf
import pytest

from engine.adapters import digits, ocr
from engine.assess import geometry, items
from engine.assess.pick import Sheet
from engine.assess.render import render_sheet
from engine.core import db
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
    monkeypatch.setattr(digits, "read", stand_in.read)
    return stand_in


def _read(paper, scan, reader, cfg=None):
    pdf, key = paper
    img, frame = render_pdf.photo(scan, 1)
    wanted = {str(n): (it["item_id"], "ans") for n, it in enumerate(key["items"], 1)}
    return boxes.read_page(img, 1, pdf, key["geometry"], wanted, cfg or ocr.settings(), frame=frame)


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
    assert tallest < (key["geometry"][0]["h"] + 2 * (boxes.AROUND + boxes.QUIET) + 2) * boxes.PPM
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

    monkeypatch.setattr(digits, "read", two_at_most)
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


def _bent(img, seed, mm=2.0):
    """A page photographed on a desk, not scanned flat: a smooth warp no one straight map undoes, moving the
    printed lines up to `mm` from where the key says they are (the 24 Sep phone photographs, 1-2 mm)."""
    rng = random.Random(seed)
    h, w = img.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    a, b = (rng.uniform(0.6, 1.0) * mm / 2**0.5 * boxes.PPM for _ in range(2))  # together at most `mm`
    f, g = rng.uniform(0.5, 1.0), rng.uniform(0.5, 1.0)  # a curl: up to one wave across the page
    p, q = rng.uniform(0, 2 * np.pi), rng.uniform(0, 2 * np.pi)
    dx = a * np.sin(2 * np.pi * f * ys / h + p)
    dy = b * np.sin(2 * np.pi * g * xs / w + q)
    return cv2.remap(img, xs + dx, ys + dy, cv2.INTER_LINEAR, borderValue=(255, 255, 255))


def _crossing(paper, answers):
    """As `_filled`, but every digit a third of a box to the right and a quarter below: over its box's printed
    lines, as a child's 8 and 3 were on 24 Sep."""
    pdf, key = paper
    img = render_pdf.render(pdf, dpi=boxes.PPM * 25.4)[0]
    for (item, _rid), run in _cells(key)[0].items():
        for cell, ch in zip(run, answers.get(item, "").rjust(len(run))):
            if ch.strip():
                over = {**cell, "x": cell["x"] + cell["w"] / 3, "y": cell["y"] + cell["h"] / 4}
                _write(img, over, ch, boxes.PPM)
    return img


def _really(paper, scan):
    """Read with the real reader at the engine's own floor."""
    return _read(paper, scan, None, {**ocr.settings(), **digits.settings(None)})


def _bent_page(paper, tmp_path, seed):
    pdf, key = paper
    ids = [it["item_id"] for it in key["items"]]
    answers = {ids[n - 1]: "" if n == 4 else _fits(key, n, seed) for n in range(1, 7)}
    working = {ids[0]: "99", ids[1]: "321", ids[4]: "13"}
    scan = _scanned(_bent(_filled(paper, answers, working), seed), tmp_path / "scan.pdf")
    return {str(n): answers[i] for n, i in enumerate(ids, 1)}, scan


@pytest.mark.parametrize("seed", range(5))
def test_a_bent_page_is_read_in_its_boxes(paper, tmp_path, reader, seed):
    """Which pixels reach the reader on a curved photograph: each answer's boxes, re-found where they printed,
    and nothing of the working — every digit read, every blank blank."""
    wrote, scan = _bent_page(paper, tmp_path, seed)
    got = _read(paper, scan, reader)
    assert got is not None
    assert {k: r["child_answer"] for k, r in got.items()} == wrote, {
        k: (r["answer_state"], r["inked"], r.get("why"), r.get("seen")) for k, r in got.items()
    }
    assert got["4"]["answer_state"] == "blank"


@pytest.mark.parametrize("seed", range(5))
def test_the_real_reader_on_a_bent_page_stands_behind_nothing_wrong(paper, tmp_path, seed, monkeypatch):
    """The real reader (ADR 0035): what it stands behind is what was written; what it is less sure of than the
    floor goes to a person with its guess — on 24 Sep 112 of 133 stood and 2 were wrong; here none may be.

    What a doubt's guess says is the reader's own: the same crop moved by less than a pixel reads differently. On
    this page "663" read "63" where it was cut, and "663" at seven of the eight one-pixel shifts around it; on the 141
    answers of 24 Sep with a gold, re-reading after a new line-up moved 19 outcomes, as many up as down (ADR 0042).
    So what is held of a doubt is what the pipeline decides: every digit written reached the reader."""
    wrote, scan = _bent_page(paper, tmp_path, seed)
    handed, real = [], digits.read

    def keeping(image_bytes, cli=None):
        handed.append(image_bytes)
        return real(image_bytes, cli)

    monkeypatch.setattr(digits, "read", keeping)
    got = _really(paper, scan)
    shapes, crops = (
        StandIn(),
        iter(handed),
    )  # an answer with ink is handed over once, in the order of its slot
    for k, r in got.items():
        crop = next(crops) if r["inked"] else None
        if r["answer_state"] == "written":
            assert r["child_answer"] == wrote[k], (k, r)
        elif r["answer_state"] == "blank":
            assert wrote[k] == "", (k, r)
        else:
            reached = "".join(w["text"] for w in shapes.read(crop)["words"]) if crop else ""
            assert r["why"] and reached == wrote[k], (k, r, reached)
    assert got["4"]["answer_state"] == "blank"
    assert sum(r["answer_state"] == "written" for r in got.values()) >= 4, got


def test_a_digit_written_over_its_box_line_reaches_the_reader_whole(paper, tmp_path):
    pdf, key = paper
    ids = [it["item_id"] for it in key["items"]]
    answers = {ids[n - 1]: _fits(key, n, 9) for n in range(1, 7)}
    scan = _scanned(_bent(_crossing(paper, answers), 3), tmp_path / "scan.pdf")
    got = _really(paper, scan)
    assert {k: r["child_answer"] for k, r in got.items()} == {
        str(n): answers[i] for n, i in enumerate(ids, 1)
    }, {k: (r["answer_state"], r["inked"], r.get("why"), r.get("seen")) for k, r in got.items()}


def _twice(real, whole=None):
    """A reader that, as Textract did on every page of 24 Sep, hands back the same pencil twice: once as one
    word over the whole strip (`whole`, or what it read) and once digit by digit underneath it."""

    def read(image_bytes, cli=None):
        page = real(image_bytes)
        ws = page["words"]
        if len(ws) < 2:
            return page
        x0, x1 = ws[0]["x"], ws[-1]["x"] + ws[-1]["w"]
        text = whole(ws) if whole else "".join(w["text"] for w in ws)
        over = {"text": text, "confidence": 95.0, "hand": False, "x": x0, "y": 0.3, "w": x1 - x0, "h": 0.5}
        return {**page, "words": [over, *ws]}

    return read


def test_two_readings_of_the_same_pencil_that_agree_stand_and_two_that_disagree_wait(
    paper, tmp_path, reader, monkeypatch
):
    pdf, key = paper
    ids = [it["item_id"] for it in key["items"]]
    wrote = {ids[n - 1]: _fits(key, n) for n in range(1, 7)}
    scan = _scanned(_filled(paper, wrote, {}), tmp_path / "scan.pdf")

    monkeypatch.setattr(digits, "read", _twice(reader.read))
    got = _read(paper, scan, reader)
    assert {k: r["child_answer"] for k, r in got.items()} == {str(n): wrote[i] for n, i in enumerate(ids, 1)}

    def one_off(ws):  # the whole-strip reading says a different first digit
        return str((int(ws[0]["text"]) + 1) % 10) + "".join(w["text"] for w in ws[1:])

    monkeypatch.setattr(digits, "read", _twice(reader.read, one_off))
    got = _read(paper, scan, reader)
    for n, i in enumerate(ids, 1):
        r = got[str(n)]
        assert r["answer_state"] == "illegible" and r["child_answer"] == ""
        assert wrote[i] in r["why"] and "disagree" in r["why"], r["why"]


@pytest.fixture(scope="module")
def two_layouts(tmp_path_factory):
    """The same six sums drawn in the layout before L3 (three boxes each, as their question set) and in today's
    (as many boxes as the answer has digits): the 23 Sep papers and the ones printed since."""
    rows = json.loads((db.REPO_ROOT / "supabase" / "seed" / "config.json").read_text(encoding="utf-8"))[
        "config"
    ]
    layouts = next(r["value"] for r in rows if r["key"] == "render.layouts")
    rng = random.Random(7)
    made = [items.bare_sum(rng, "R5", "Procedural", "+", 2, 2, [0, 1]) for _ in range(40)]
    qs = [q for q in made if len(q.responses[0].answer) == 2][:6]
    out = {}
    for name, layout in (("before L3", layouts[0]), ("today", layouts[-1])):
        d = tmp_path_factory.mktemp(name.replace(" ", ""))
        key = render_sheet(
            Sheet(CODE, "G2", "Focus", 1, "W1", qs, title="Practice"), d, "Practice", layout=layout
        )
        out[name] = (d / f"{CODE}.pdf", key)
    return out


def test_a_copy_is_read_in_the_layout_it_was_printed_in(two_layouts, tmp_path, reader):
    """Nimish: "If the answer has been in the designated place, it should be able to read the answers" — the place
    as it was printed. A 23 Sep copy printed three boxes an answer; today the same worksheet prints two."""
    pdfs = [pdf for pdf, _ in two_layouts.values()]
    assert all(len(pymupdf.open(p)) == 1 for p in pdfs)  # the page count alone does not tell them apart
    assert _boxes(two_layouts["before L3"][1], 1) == 3 and _boxes(two_layouts["today"][1], 1) == 2
    for name, paper in two_layouts.items():
        pdf, key = paper
        ids = [it["item_id"] for it in key["items"]]
        wrote = {ids[n - 1]: _fits(key, n) for n in range(1, 7)}
        scan = _scanned(_filled(paper, wrote, {}), tmp_path / f"{name}.pdf")
        img, _ = render_pdf.photo(scan, 1)

        assert boxes.as_printed([img], pdfs) == pdf, name
        got = _read(paper, scan, reader)
        assert {k: r["child_answer"] for k, r in got.items()} == {
            str(n): wrote[i] for n, i in enumerate(ids, 1)
        }


def test_an_educators_tick_in_an_empty_box_is_not_a_digit(paper, tmp_path, reader):
    """23 Sep, R8-H01 copy 05: the educator ticked each answer in the box after the child's last digit. The reader
    read 23, 26 and 27 right, and each waited — "3 boxes hold ink but the reader saw 23" — because the tick is ink.
    Measured on that page: a written digit spans 74–87% of its box's height, the tick 23%. A box holds a digit
    only when its ink is at least DIGIT_TALL of the box's height; a short stroke across its top is a mark."""
    pdf, key = paper
    ids = [it["item_id"] for it in key["items"]]
    n = next(n for n in range(1, 7) if _boxes(key, n) == 3)
    wrote = _fits(key, n)[1:]  # two digits, right-aligned: the first box stays empty
    img = _filled(paper, {ids[n - 1]: wrote}, {})
    first = geometry.cells_of(key["geometry"], 1)[0][(ids[n - 1], "ans")][0]
    ppm = boxes.PPM
    x0, y0 = (first["x"] + first["w"] * 0.35) * ppm, (first["y"] + first["h"] * 0.32) * ppm
    x1, y1 = (first["x"] + first["w"] * 0.7) * ppm, (first["y"] + first["h"] * 0.12) * ppm
    cv2.line(img, (int(x0), int(y0)), (int(x1), int(y1)), (40, 40, 40), max(2, int(0.5 * ppm)), cv2.LINE_AA)
    got = _read(paper, _scanned(img, tmp_path / "scan.pdf"), reader)[str(n)]
    assert (got["inked"], got["answer_state"], got["child_answer"]) == (2, "written", wrote), got.get("why")


def test_a_boxs_own_line_left_in_the_cell_is_not_ink():
    """23 Sep R8-H01 copy 05, question 4: the fourth box was empty but for its own left line, a hair off where it
    printed — 3 columns 97-100% dark top to bottom — and was counted as a digit. A column dark down (almost) the whole
    cell at its edge is the box's line; a stroke inside the cell, a 1 included, is not."""
    m = np.zeros((86, 70), bool)
    m[:, 0:3] = True  # the box's line, at the left edge
    assert not boxes._edge_lines_out(m).any()
    m[:, 67:70] = True  # and at the right
    assert not boxes._edge_lines_out(m).any()
    one = np.zeros((86, 70), bool)
    one[8:80, 33:37] = True  # a 1, written down the middle
    assert (boxes._edge_lines_out(one) == one).all()
    beside = one.copy()
    beside[:, 0:2] = True
    assert (boxes._edge_lines_out(beside) == one).all(), "the line goes, the 1 beside it stays"
