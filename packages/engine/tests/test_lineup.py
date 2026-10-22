"""A photographed page is lined up with the page it was printed from (goals/s23-a-curled-photo-lines-up.yaml,
`w3_read/lineup.py`).

On 24 Sep two of Nimish's R31-H02 copies were read as old papers, nothing in their boxes: phone photographs of a page
lifting off the desk, their corner marks cut off by the scan app. Every test here prints a full page of twelve sums
the way the engine prints one, writes in its boxes, bends the page as those photographs were bent, "scans" it as the
phone did (`test_boxes._scanned`: the top cut off, tilted, softened, compressed) and reads it with a stand-in reader,
so what is tested is where each answer is looked for.
"""

import random

import cv2
import numpy as np
import pymupdf
import pytest

from engine.adapters import digits, ocr
from engine.assess import counting, geometry, items
from engine.assess.pick import Sheet
from engine.assess.render import render_sheet
from engine.w3_read import boxes, lineup, render_pdf
from tests.test_boxes import CODE, StandIn, _filled, _scanned, _write

PPM = lineup.PPM


class Stretched(StandIn):
    """The stand-in reader, for a lifted page. A lift stretches a lower row's digits as it moves them: on 24 Sep copy
    09 the print went from 2 to 6 mm off over 24 mm of page, a sixth taller, and here the last row's digits are up to a
    fifth taller. A reader of handwriting reads a digit of any height, so this one tries its shapes against the crop
    squeezed back by each amount, and keeps the reading it is surest of."""

    def read(self, image_bytes, cli=None):
        img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
        tries = []
        for taller in (1.0, 1.1, 1.2, 1.3):
            squeezed = cv2.resize(
                img, (img.shape[1], round(img.shape[0] / taller)), interpolation=cv2.INTER_AREA
            )
            words = super().read(cv2.imencode(".png", squeezed)[1].tobytes())["words"]
            tries.append((np.mean([w["confidence"] for w in words]) if words else 0.0, words))
        self.handed[-4:] = [img]  # what it was handed, once
        return {"lines": [], "words": max(tries, key=lambda t: t[0])[1]}


@pytest.fixture
def reader(monkeypatch):
    stand_in = StandIn()
    monkeypatch.setattr(digits, "read", stand_in.read)
    return stand_in


@pytest.fixture
def stretched(monkeypatch):
    stand_in = Stretched()
    monkeypatch.setattr(digits, "read", stand_in.read)
    return stand_in


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    """Twelve sums in four rows, 65 to 190 mm down the page, and their key."""
    rng = random.Random(11)
    made = [items.bare_sum(rng, "R5", "Procedural", "+", 2, 2, [0, 1]) for _ in range(80)]
    width = lambda q: len(q.responses[0].answer)  # noqa: E731
    qs = [q for q in made if width(q) == 2][:6] + [q for q in made if width(q) == 3][:6]
    out = tmp_path_factory.mktemp("page")
    key = render_sheet(Sheet(CODE, "G2", "Focus", 1, "W1", qs, title="Practice"), out, week_label="Practice")
    assert len(pymupdf.open(out / f"{CODE}.pdf")) == 1
    return out / f"{CODE}.pdf", key


def _written(page, seed):
    """Every box filled but question 7's, whose boxes stay empty: {question: digits}."""
    pdf, key = page
    rng = random.Random(seed)
    runs = geometry.cells_of(key["geometry"], 1)[0]
    out = {}
    for n, it in enumerate(key["items"], 1):
        boxes_n = len(runs[(it["item_id"], "ans")])
        out[str(n)] = (
            "" if n == 7 else "".join(str(rng.randint(1 if k == 0 else 0, 9)) for k in range(boxes_n))
        )
    return out


def _as_filled(page, wrote):
    pdf, key = page
    return _filled(page, {it["item_id"]: wrote[str(n)] for n, it in enumerate(key["items"], 1)}, {})


def _lifted(img, seed):
    """The page's lower part lifting off the desk towards the phone, as on 24 Sep copies 01 and 09: measured there, the
    bottom row of answers lay 5-6 mm below and up to 4 mm outside where the best straight map put it. Here: from 40% of
    the way down the print moves down, and out from the middle, more the lower it is — by 9-10 mm and 5-6 mm from 65%
    down. The best straight map leaves the last row of answers about 6 mm off (measured on this page: 5.8)."""
    h, w = img.shape[:2]
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    dx, dy = _lift(xs, ys, seed, (h, w))
    return cv2.remap(img, xs - dx, ys - dy, cv2.INTER_LINEAR, borderValue=(255, 255, 255))


def _lift(xs, ys, seed, shape):
    """How far the lift moves the print at (xs, ys), in pixels of the page as photographed."""
    rng = random.Random(seed)
    lift, spread = rng.uniform(9, 10) * PPM, rng.uniform(5, 6) * PPM
    h, w = shape
    t = np.clip((ys / h - 0.4) / 0.25, 0, 1) ** 2
    return spread * t * (xs - w / 2) / (w / 2), lift * t


def _in_photo(x, y, seed, shape):
    """Where a point of the printed page (pixels at PPM) is on the photograph of the lifted page as `_scanned` hands it
    over: moved by the lift, then the top 5% cut off and the rest turned 1.4° at 0.98 the size."""
    qx, qy = x, y
    for _ in range(30):  # the lift moves a point by an amount that depends on where it lands
        dx, dy = _lift(qx, qy, seed, shape)
        qx, qy = x + dx, y + dy
    h, w = shape
    cut = int(h * 0.05)
    turn = cv2.getRotationMatrix2D((w / 2, (h - cut) / 2), 1.4, 0.98)
    return turn @ np.array([qx, qy - cut, 1.0])


def _read(page, scan):
    pdf, key = page
    img, frame = render_pdf.photo(scan, 1)
    wanted = {str(n): (it["item_id"], "ans") for n, it in enumerate(key["items"], 1)}
    return boxes.read_page(img, 1, pdf, key["geometry"], wanted, ocr.settings(), frame=frame)


def _states(got):
    return {k: (r["answer_state"], r["inked"], r.get("why"), r.get("seen")) for k, r in got.items()}


@pytest.mark.parametrize("seed", range(3))
def test_a_curled_photograph_with_its_top_cut_off_is_read_in_its_boxes(page, tmp_path, stretched, seed):
    """Nimish, of R31-H02: "its in proper boxes and qr and all". Every answer is read in its own boxes on a page whose
    lower half lifts off the desk, its top and its corner marks cut off: the empty boxes blank, nothing else missed."""
    wrote = _written(page, seed)
    scan = _scanned(_lifted(_as_filled(page, wrote), seed), tmp_path / "scan.pdf")
    got = _read(page, scan)
    assert got is not None, "the page did not line up: it would be read as an old paper"
    assert {k: r["child_answer"] for k, r in got.items()} == wrote, _states(got)
    assert got["7"]["answer_state"] == "blank"


def _moved(img, rect_mm, by_mm, turn=0.0):
    """A fold: the part of the page inside `rect_mm` (x, y, w, h) moved `by_mm` (dx, dy) and turned `turn` degrees
    about its middle, the rest of the page left where it was — as a crease moved 24 Sep copy 01's question 10."""
    x, y, w, h = (round(v * PPM) for v in rect_mm)
    pad = round(max(abs(by_mm[0]), abs(by_mm[1])) * PPM) + 20
    assert pad <= min(x, y) and x + w + pad <= img.shape[1] and y + h + pad <= img.shape[0]
    part = img[y : y + h, x : x + w].copy()
    out = img.copy()
    out[y : y + h, x : x + w] = 255
    m = cv2.getRotationMatrix2D((w / 2, h / 2), turn, 1.0)
    m[:, 2] += (pad + by_mm[0] * PPM, pad + by_mm[1] * PPM)
    moved = cv2.warpAffine(part, m, (w + 2 * pad, h + 2 * pad), borderValue=(255, 255, 255))
    region = out[y - pad : y + h + pad, x - pad : x + w + pad]
    np.minimum(region, moved, out=region)
    return out


def _around(key, n):
    """Question `n`'s own part of the page, in mm: its printed words above its boxes, its boxes and its working."""
    item = key["items"][n - 1]["item_id"]
    runs, works = geometry.cells_of(key["geometry"], 1)
    run, work = runs[(item, "ans")], works[item][0]
    return (run[0]["x"] - 8, run[0]["y"] - 13, 58, work["y"] + work["h"] - run[0]["y"] + 15)


def test_an_answer_moved_by_a_fold_is_found_around_its_own_print(page, tmp_path, reader):
    """Nimish: "If the answer has been in the designated place, it should be able to read the answers." A crease moves
    one question 7 mm from where the rest of the page puts it — more than twice the reach of a run of boxes on its own,
    whose boxes repeat every 8.4 mm — and its answer is still read, found around its own printed question."""
    pdf, key = page
    wrote = _written(page, 5)
    img = _moved(_as_filled(page, wrote), _around(key, 11), (-4.5, 5.5))
    got = _read(page, _scanned(img, tmp_path / "scan.pdf"))
    assert got is not None
    assert {k: r["child_answer"] for k, r in got.items()} == wrote, _states(got)


def test_an_answer_whose_print_is_not_found_goes_to_a_person_never_read_at_a_guessed_place(
    page, tmp_path, reader
):
    """On 24 Sep copy 01 a crease turned question 10 and moved it 6 mm: where the page lined up, its boxes held the
    edges of two digits. An answer whose own print is not found near where the page puts it is not read there as
    blank or as a number: it goes to a person as the reader's `not_found` (Marking then shows the whole page), saying
    why, and every other answer on the page is read."""
    pdf, key = page
    wrote = _written(page, 6)
    img = _as_filled(page, wrote)
    x, y, w, h = (round(v * PPM) for v in _around(key, 10))
    img[y : y + h, x : x + w] = cv2.GaussianBlur(
        img[y : y + h, x : x + w], (0, 0), 3 * PPM
    )  # smeared past finding
    got = _read(page, _scanned(img, tmp_path / "scan.pdf"))
    ten = got["10"]
    assert ten["answer_state"] == "not_found" and ten["child_answer"] == "", _states(got)
    assert "not found" in ten["why"], ten["why"]
    assert {k: r["child_answer"] for k, r in got.items() if k != "10"} == {
        k: v for k, v in wrote.items() if k != "10"
    }


def test_the_part_of_the_photograph_a_person_is_shown_is_where_the_answer_was_read(page, tmp_path, stretched):
    """The approval screen crops the photograph at an answer's `box`. On a lifted page each box holds its whole run of
    boxes — every corner of it, as the lift and the scan put them on the photograph — and little more: a person is
    shown the child's answer, not a guess at where it might be."""
    pdf, key = page
    wrote = _written(page, 2)
    scan = _scanned(_lifted(_as_filled(page, wrote), 2), tmp_path / "scan.pdf")
    got = _read(page, scan)
    img, frame = render_pdf.photo(scan, 1)
    h, w = img.shape[:2]
    fx0, fy0, fx1, fy1 = frame
    runs = geometry.cells_of(key["geometry"], 1)[0]
    shape = (297 * PPM, 210 * PPM)
    for n, it in enumerate(key["items"], 1):
        run = runs[(it["item_id"], "ans")]
        x0, y0 = run[0]["x"] * PPM, run[0]["y"] * PPM
        x1, y1 = (run[-1]["x"] + run[-1]["w"]) * PPM, (run[-1]["y"] + run[-1]["h"]) * PPM
        corners = [_in_photo(x, y, 2, shape) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        left, top, right, bottom = got[str(n)]["box"]
        for px, py in corners:
            fx, fy = fx0 + (fx1 - fx0) * px / w, fy0 + (fy1 - fy0) * py / h
            assert left <= fx <= right and top <= fy <= bottom, (n, (fx, fy), got[str(n)]["box"])
        wide = (right - left) / (fx1 - fx0) * w / PPM / 0.98  # mm of the page
        assert wide <= (x1 - x0) / PPM + 2 * 2 + 3, (
            n,
            wide,
        )  # its 2 mm margin each side, and the lift's stretch


def test_a_page_is_accepted_on_the_print_found_on_it_not_on_how_many_features_matched(
    page,
    tmp_path,
    reader,
    monkeypatch,
):
    """24 Sep copy 01: 37 features matched the printed page, fewer than the 60 the reader asked for, and the whole
    copy was read as an old paper — though the map they gave put every answer of its top half in its boxes. How many
    features matched is not how well the page lines up: what is found of the printed page where the map puts it is."""
    from engine.w3_read import stencil

    real = stencil.homography
    monkeypatch.setattr(stencil, "homography", lambda a, b: (real(a, b)[0], 37))
    wrote = _written(page, 3)
    got = _read(page, _scanned(_as_filled(page, wrote), tmp_path / "scan.pdf"))
    assert got is not None, "refused on a count of matched features"
    assert {k: r["child_answer"] for k, r in got.items()} == wrote, _states(got)


def test_a_page_with_too_little_of_its_print_on_it_does_not_line_up(page, tmp_path):
    """A different paper under this one's code, or a photograph of the desk: less than half the printed page's print
    is found, and the page is read as an old paper and says so (`boxes.read_page` → None)."""
    other = np.full((2970, 2100, 3), 255, np.uint8)
    for k in range(12):
        cv2.putText(
            other,
            f"{k} not this paper {k * 7}",
            (150, 300 + 200 * k),
            cv2.FONT_HERSHEY_SIMPLEX,
            3,
            (30, 30, 30),
            6,
        )
    img, _ = render_pdf.photo(_scanned(other, tmp_path / "other.pdf"), 1)
    assert lineup.line_up(img, page[0], 1) == (None, None)


@pytest.fixture(scope="module")
def equal_groups(tmp_path_factory):
    """A Grade 1 paper of twelve "Equal groups (repeated addition)" questions, as sums and as rings of dots, over two
    pages — the paper read on 2026-10-22 — and the answer each question asks for: {page: {question: answer}}."""
    rng = random.Random(3)
    check = {"format": "equal_groups", "shape": ["SUM", "PICTURE"], "groups": [2, 3], "size": [2, 6]}
    qs = list(
        {
            q.item_id: q for q in (counting.equal_groups(rng, "R35", "Conceptual", check) for _ in range(60))
        }.values()
    )
    qs = qs[:12]  # twelve different questions: a paper never prints one twice
    out = tmp_path_factory.mktemp("g1")
    key = render_sheet(Sheet(CODE, "G1", "Focus", 1, "W1", qs, title="Equal groups"), out, week_label="W1")
    answers = {q.item_id: q.responses[0].answer for q in qs}
    on = {}
    for p in (1, 2):
        runs = geometry.cells_of(key["geometry"], p)[0]
        on[p] = {
            str(n): answers[it["item_id"]]
            for n, it in enumerate(key["items"], 1)
            if (it["item_id"], "ans") in runs
        }
    assert sorted(len(v) for v in on.values()) == [4, 8], (
        on
    )  # eight questions on page 1, four on page 2, as on live
    return out / f"{CODE}.pdf", key, on


SHARE, TALL, WIDE = 0.575, 2399, 1080


def _picture_on_a4():
    """Where the phone's picture sits on its A4 page, in points: centred, covering SHARE of it."""
    pw = (SHARE * 595 * 842 * WIDE / TALL) ** 0.5
    ph = pw * TALL / WIDE
    return pymupdf.Rect((595 - pw) / 2, (842 - ph) / 2, (595 + pw) / 2, (842 + ph) / 2)


def _on_a4(x_mm, y_mm):
    """A point of the printed page, in mm, where `_phone_on_a4` puts it: a fraction of the A4 page across and down."""
    r, paper_h = _picture_on_a4(), round(H_PX * WIDE / W_PX)
    px, py = x_mm * PPM * WIDE / W_PX, (TALL - paper_h) // 2 + y_mm * PPM * WIDE / W_PX
    return (r.x0 + px / WIDE * r.width) / 595, (r.y0 + py / TALL * r.height) / 842


W_PX, H_PX = lineup.W, lineup.H


def _phone_on_a4(img, out, share=SHARE, tall=TALL, wide=WIDE):
    """A page as the 2026-10-22 file holds it: the paper photographed by a phone in portrait — a picture 1080 x 2399,
    the paper across its width and the desk above and below it — and that picture laid on an A4 page, covering 57.5% of
    it, white around. Measured on every one of that file's 20 pages (`.github/measure/scan_vs_eye.py`)."""
    h, w = img.shape[:2]
    paper = cv2.resize(img, (wide, round(h * wide / w)), interpolation=cv2.INTER_AREA)
    top = (tall - paper.shape[0]) // 2
    photo = np.full((tall, wide, 3), 90, np.uint8)  # the desk
    photo[top : top + paper.shape[0]] = paper
    photo = cv2.GaussianBlur(photo, (3, 3), 0)
    ok, jpg = cv2.imencode(".jpg", photo, [cv2.IMWRITE_JPEG_QUALITY, 70])
    doc = pymupdf.open()
    a4 = doc.new_page(width=595, height=842)
    a4.insert_image(_picture_on_a4(), stream=jpg.tobytes())
    doc.save(out)
    return out


def _g1_scan(equal_groups, p, tmp_path):
    pdf, key, on = equal_groups
    img = render_pdf.render(pdf, dpi=PPM * 25.4)[p - 1]
    runs = geometry.cells_of(key["geometry"], p)[0]
    for n, it in enumerate(key["items"], 1):
        if str(n) in on[p]:
            run = runs[(it["item_id"], "ans")]
            for cell, ch in zip(run, on[p][str(n)].rjust(len(run))):
                if ch.strip():
                    _write(img, cell, ch, PPM)
    return _phone_on_a4(img, tmp_path / f"g1-p{p}.pdf")


@pytest.mark.parametrize("p", [1, 2])
def test_a_phone_photograph_laid_on_an_a4_page_lines_up(equal_groups, tmp_path, p):
    """2026-10-22: every page of a 20-page Grade 1 file "did not line up with the paper it printed from", and 49 of its
    120 answers came back "the printed question was not found on the page". The map from the photograph to the printed
    page was found (113 features agreed on one page) and thrown away: the check that it was sensible asked the WHOLE
    photograph to land on about one page's area, and on a picture covering 57.5% of its A4 page, the paper a third of
    it, the photograph's corners land on three pages' worth. What must be sensible is where the PAPER sits in it."""
    img, _ = render_pdf.photo(_g1_scan(equal_groups, p, tmp_path), 1)
    canon, _ = lineup.line_up(img, equal_groups[0], p)
    assert canon is not None


@pytest.mark.parametrize("p", [1, 2])
def test_every_printed_question_of_the_equal_groups_paper_is_found_in_its_own_boxes(
    equal_groups, tmp_path, reader, p
):
    """Each of the page's questions found where it printed (none `not_found`), each in boxes no other question was
    given — on live one box went to three questions. Checked against where the test itself put each question's boxes
    in the picture, not against the reader's own account: the middle of each question's run is inside the place the
    reading says it came from and no other question's is, and as many of its boxes hold ink as digits were written.
    The digits themselves are the reader's (`adapters/digits.py`): this stand-in, a shape matcher, takes a box's line
    for a 1 at a phone picture's 5 pixels a millimetre."""
    pdf, key, on = equal_groups
    img, frame = render_pdf.photo(_g1_scan(equal_groups, p, tmp_path), 1)
    wanted = {n: (key["items"][int(n) - 1]["item_id"], "ans") for n in on[p]}
    got = boxes.read_page(img, p, pdf, key["geometry"], wanted, ocr.settings(), frame=frame)
    assert got is not None, "the page did not line up"
    assert sorted(got) == sorted(on[p])
    assert [k for k, r in got.items() if r["answer_state"] == "not_found"] == []
    assert len({tuple(r["box"]) for r in got.values()}) == len(got), "two questions given one box"
    runs = geometry.cells_of(key["geometry"], p)[0]
    middle = {}
    for n in on[p]:
        run = runs[(key["items"][int(n) - 1]["item_id"], "ans")]
        x = (min(c["x"] for c in run) + max(c["x"] + c["w"] for c in run)) / 2
        y = (min(c["y"] for c in run) + max(c["y"] + c["h"] for c in run)) / 2
        middle[n] = _on_a4(x, y)
    inside = lambda b, pt: b[0] <= pt[0] <= b[2] and b[1] <= pt[1] <= b[3]  # noqa: E731
    for n, r in got.items():
        holds = [m for m, pt in middle.items() if inside(r["box"], pt)]
        assert holds == [n], f"question {n}'s reading came from where {holds} printed"
    assert {k: r["inked"] for k, r in got.items()} == {k: len(v) for k, v in on[p].items()}, _states(got)


def test_a_photograph_of_the_desk_alone_in_a_phone_picture_does_not_line_up(equal_groups, tmp_path):
    """Lowering the bar for where the paper sits must not let a picture with no paper in it through."""
    desk = np.full((2970, 2100, 3), 255, np.uint8)
    for k in range(12):
        cv2.putText(
            desk,
            f"{k} not this paper {k * 7}",
            (150, 300 + 200 * k),
            cv2.FONT_HERSHEY_SIMPLEX,
            3,
            (30, 30, 30),
            6,
        )
    img, _ = render_pdf.photo(_phone_on_a4(desk, tmp_path / "desk.pdf"), 1)
    assert lineup.line_up(img, equal_groups[0], 1) == (None, None)
