"""A paper this system printed is read where it printed (goals/s16-read-the-boxes.yaml).

The renderer records where every answer box sits, to the tenth of a millimetre, in the key it writes beside
each PDF (`render.GEOM_JS`). So a scan of that paper needs no searching: the page is lined up with the page
it was printed from, each box is cut out at its recorded place, and only what is inside the boxes is handed to
the reader. This is what a form reader does, and what the old-paper reader (`ocr.answers_for`) could not do,
because nobody knew where those papers' answers lived: it took the handwritten number nearest the printed
question, which on 2026-09-24 was the child's working.

What code decides here, and the reader is never asked: whether a box is blank (a count of dark pixels, the
paper's own print taken out), how many boxes hold a digit (ink down the box, not a tick across it), whether the working space was written in
(the third signal, rule 5). The reader (`adapters/digits.py`, ADR 0035) is asked one thing — which digits are
in this run of boxes, handed to it as photographed, print and all — and its answer stands only when it has
exactly as many digits as boxes hold ink and it is at least as sure as the floor.

Lining up is by the printed page's own features (ORB, RANSAC; `stencil.homography`), not by the corner marks:
a phone's "scan" app crops the page tight and the marks are the first thing it cuts off (every page of the
2026-09-24 file). A page that will not line up is read as an old paper, and says so.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
import pymupdf

from engine.adapters import digits
from engine.assess.geometry import cells_of
from engine.w3_read import stencil

PPM = 10  # pixels per mm the scan is drawn at in the printed page's frame: 254 dpi, a phone scan's own
W, H = 210 * PPM, 297 * PPM
EDGE = 0.8  # mm each printed pixel is grown by before it is removed: the line, its blur and its JPEG halo
SEEK = 3.0  # mm a run of boxes is looked for around its recorded place: a curved phone photo moves it 1-2 mm
PRINTED = 140  # grey under this on the blank page is the paper's own print
INSIDE = 0.7  # mm inside its printed line a cell is measured for ink, so the line itself never counts
# A pencil digit fills 3-15% of its cell; JPEG noise and a shadow on white, measured under 0.3%.
INK = 0.012
# A digit is written down its box; an educator's tick or a stray stroke lies across it. Measured on 23 Sep R8-H01 copy
# 05: digits span 74–87% of their box's height, the tick in the box after them 23%, an empty box's specks 6%.
DIGIT_TALL = 0.45
EDGE_LINE = 0.9  # a column this much dark, top to bottom, at a cell's edge is the box's line
WORK_INK = 0.004  # this much of the working space written on is the third signal (rule 5)
WORK_INSIDE = 1.5  # mm: the working box's dashed border and its printed label stay outside the measure
AROUND = 2  # mm of the photograph around a run of boxes handed to the reader, as ADR 0035 measured it
QUIET = 1  # mm of that crop's own edge repeated around it: the reader's detector wants still space about a
# number, and on 24 Sep this took 115 of 133 answers read exactly to 125, with the same two wrong (ADR 0035)
MIN_INLIERS = 60  # fewer matched features than this and the page is not the one it claims to be
SIDE = 2000  # the long side features are matched at, as `stencil` does
COARSE = 5  # a page's print and marks are compared at PPM / COARSE: 2 px a mm, a box line still one pixel
RULE = 6  # mm: a box's edge is 5.4–13 mm, a run of them longer; a pencil stroke across a box is shorter
GROW = 1.5  # mm a mark and a printed line may sit apart and still be the same line: a curved photograph


def _grey(img, side):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    s = side / max(g.shape[:2])
    return cv2.resize(g, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), s


@lru_cache(maxsize=8)
def blank(pdf, page_no):
    """The printed page, drawn at PPM, grey: the frame every box position is recorded in."""
    with pymupdf.open(pdf) as doc:
        pix = doc[page_no - 1].get_pixmap(
            matrix=pymupdf.Matrix(PPM * 25.4 / 72, PPM * 25.4 / 72), colorspace=pymupdf.csGRAY
        )
        g = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    return cv2.resize(g, (W, H), interpolation=cv2.INTER_AREA)


def _scale(s):
    return np.array([[s, 0, 0], [0, s, 0], [0, 0, 1]], dtype=np.float64)


def line_up(img, pdf, page_no):
    """→ (the scan drawn in the printed page's frame, the 3x3 map from the scan's pixels to that frame), or
    (None, None) when the page does not match the paper it was said to come from."""
    ref = blank(str(pdf), page_no)
    small, s_child = _grey(img, SIDE)
    ref_small, s_ref = _grey(ref, SIDE)
    Hm, n = stencil.homography(small, ref_small)
    if Hm is None or n < MIN_INLIERS or not stencil.plausible(Hm, small.shape, ref_small.shape):
        return None, None
    M = _scale(1 / s_ref) @ Hm @ _scale(s_child)
    canon = cv2.warpPerspective(img, M, (W, H), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))
    return canon, M


def dark(canon):
    """Where the page is marked: darker than its own surroundings, so a shadow across a photograph is not ink
    and a faint pencil on a bright page is. The paper's own print is taken out per answer, where it settled
    (`_theirs`), never at the key's place: on a bent page that is a millimetre or two off."""
    g = cv2.cvtColor(canon, cv2.COLOR_BGR2GRAY)
    background = cv2.blur(g, (8 * PPM, 8 * PPM))
    return g < background * 0.72


def agreement(img, pdf, page_no, where=None):
    """How closely a photographed page's ruled lines (`_rules`) follow those `pdf` printed on that page, 0–1: of the
    printed lines, how much is on the photograph, and of the photograph's, how much the print explains (their
    harmonic mean), each within GROW mm, counted only `where` (a mask at PPM / COARSE; the whole page when None). A layout the page was
    not printed in leaves boxes unexplained or missing. 0: the page does not line up with `pdf`."""
    canon, _ = line_up(img, pdf, page_no)
    if canon is None:
        return 0.0
    size = (W // COARSE, H // COARSE)
    printed = cv2.resize(_rules(blank(str(pdf), page_no) < PRINTED), size, interpolation=cv2.INTER_AREA)
    marked = cv2.resize(_rules(dark(canon)), size, interpolation=cv2.INTER_AREA)
    if where is not None:
        printed, marked = printed & where, marked & where
    grow = np.ones((2 * int(GROW * PPM / COARSE) + 1,) * 2, np.uint8)
    found = (printed & cv2.dilate(marked, grow)).sum() / max(1, printed.sum())
    explained = (marked & cv2.dilate(printed, grow)).sum() / max(1, marked.sum())
    return 0.0 if found + explained == 0 else float(2 * found * explained / (found + explained))


def _rules(mask):
    """The straight horizontal lines of a page, RULE mm or longer — the tops and bottoms of its answer boxes, its
    rules — without its words or a child's pencil, whose strokes are shorter."""
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (int(RULE * PPM), 1))
    return cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, kernel)


def _answer_places(pdfs, page_no):
    """Where any of `pdfs` prints an answer box on a page, grown by SEEK, as a mask at PPM / COARSE: the part of a
    page layouts differ in. The text around them is the same in every layout, and only dilutes the difference."""
    where = np.zeros((H // COARSE, W // COARSE), np.uint8)
    pad = SEEK * PPM / COARSE
    for pdf in pdfs:
        key = Path(pdf).with_suffix(".key.json")
        for c in json.loads(key.read_text(encoding="utf-8")).get("geometry", []) if key.exists() else []:
            if c["page"] == page_no and c.get("kind") != "work":
                x0, y0 = int(c["x"] * PPM / COARSE - pad), int(c["y"] * PPM / COARSE - pad)
                x1, y1 = (
                    int((c["x"] + c["w"]) * PPM / COARSE + pad),
                    int((c["y"] + c["h"]) * PPM / COARSE + pad),
                )
                where[max(0, y0) : y1, max(0, x0) : x1] = 1
    return where if where.any() else None


def as_printed(pages, pdfs):
    """Of the PDFs one worksheet has printed as (one per `render.layouts` row, goals/s18-read-as-printed.yaml), the
    one a copy was printed from: among those with as many pages as the copy, the one its answer boxes agree with
    most. `pages`: the copy's pages as photographed, in order."""
    counted = {pdf: len(pymupdf.open(pdf)) for pdf in pdfs}
    same = [pdf for pdf in pdfs if counted[pdf] == len(pages)] or list(pdfs)
    if len(same) == 1:
        return same[0]
    where = {n: _answer_places(same, n) for n in range(1, len(pages) + 1)}
    return max(
        same,
        key=lambda pdf: sum(
            agreement(img, pdf, n, where[n]) for n, img in enumerate(pages[: counted[pdf]], 1)
        ),
    )


def _shift(c, d):
    return {**c, "x": c["x"] + d[0] / PPM, "y": c["y"] + d[1] / PPM}


def _find(grey, printed, cells, seek):
    """→ (dx, dy) pixels: where the printed `cells` sit on the scan, found by matching the blank page's print
    around them against the scan within `seek` mm. No print to match (a flat patch): (0, 0)."""
    pad, s = int(1.5 * PPM), int(seek * PPM)
    x0 = min(_px(c)[0] for c in cells) - pad
    y0 = min(_px(c)[1] for c in cells) - pad
    x1 = max(_px(c)[2] for c in cells) + pad
    y1 = max(_px(c)[3] for c in cells) + pad
    if x0 - s < 0 or y0 - s < 0 or x1 + s > W or y1 + s > H:
        return 0, 0
    tpl = printed[y0:y1, x0:x1]
    if tpl.std() < 5:
        return 0, 0
    score = cv2.matchTemplate(grey[y0 - s : y1 + s, x0 - s : x1 + s], tpl, cv2.TM_CCOEFF_NORMED)
    _, _, _, (bx, by) = cv2.minMaxLoc(score)
    return bx - s, by - s


def settle(grey, printed, cells):
    """The recorded cells moved together to where their run printed on this scan (it may sit a few mm off on a
    curved photograph). Not box by box: one printed square is too little to match on, and jumps."""
    d = _find(grey, printed, cells, SEEK)
    return [{**_shift(c, d), "from": (c["x"], c["y"])} for c in cells]


def _theirs(printed, cells, box):
    """The paper's own print around settled `cells`, grown by EDGE, in the frame of `box` (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = box
    mask = np.zeros((y1 - y0, x1 - x0), np.uint8)
    pad = int(1.5 * PPM)
    for c in cells:
        fx, fy = c["from"]
        dx, dy = round((c["x"] - fx) * PPM), round((c["y"] - fy) * PPM)
        a0, b0, a1, b1 = _px(c)
        a0, b0, a1, b1 = max(a0 - pad, x0), max(b0 - pad, y0), min(a1 + pad, x1), min(b1 + pad, y1)
        src = printed[max(0, b0 - dy) : max(0, b1 - dy), max(0, a0 - dx) : max(0, a1 - dx)] < PRINTED
        h, w = src.shape
        mask[b0 - y0 : b0 - y0 + h, a0 - x0 : a0 - x0 + w] |= src.astype(np.uint8)
    e = 2 * max(1, int(EDGE * PPM)) + 1
    return cv2.dilate(mask, np.ones((e, e), np.uint8)) > 0


def _px(g, inside=0.0):
    """A recorded cell, in canonical pixels, shrunk `inside` mm on every side."""
    x0, y0 = int((g["x"] + inside) * PPM), int((g["y"] + inside) * PPM)
    x1, y1 = int((g["x"] + g["w"] - inside) * PPM), int((g["y"] + g["h"] - inside) * PPM)
    return max(0, x0), max(0, y0), min(W, max(x0 + 1, x1)), min(H, max(y0 + 1, y1))


def marks(is_dark, printed, g, inside=INSIDE):
    """What is marked in a settled cell, `inside` mm in from its line, by anything but the paper: the paper's print
    taken out where it settled (`_theirs`), and then the box's own line where it still shows — a column dark from
    top to bottom at the cell's edge. On 23 Sep R8-H01 copy 05 an empty box's left line, a hair off where it printed,
    was 3 columns 97-100% dark and nothing else: counted as a digit, "3 boxes hold ink but the reader saw 23"."""
    x0, y0, x1, y1 = box = _px(g, inside)
    m = is_dark[y0:y1, x0:x1] & ~_theirs(printed, [g], box)
    return _edge_lines_out(m)


def _edge_lines_out(m):
    """`m` without the columns at its left and right edges that run (almost) its whole height: a box's line."""
    full = m.mean(axis=0) >= EDGE_LINE if m.size else np.zeros(0, bool)
    out = m.copy()
    for cols in (range(len(full)), range(len(full) - 1, -1, -1)):
        for c in cols:
            if not full[c]:
                break
            out[:, c] = False
    return out


def ink(is_dark, printed, g, inside=INSIDE):
    """How much of a settled cell, `inside` mm in from its line, is marked by anything but the paper."""
    m = marks(is_dark, printed, g, inside)
    return float(m.mean()) if m.size else 0.0


def tall(is_dark, printed, g, inside=INSIDE):
    """How much of a settled cell's height, `inside` mm in from its line, the marks in it span, top to bottom."""
    m = marks(is_dark, printed, g, inside)
    rows = np.flatnonzero(m.any(axis=1))
    return float((rows[-1] - rows[0] + 1) / max(1, m.shape[0])) if rows.size else 0.0


def holds_digit(is_dark, printed, g):
    """A box holds a digit when it is marked (`INK`) down at least `DIGIT_TALL` of its height — not a tick across it."""
    return ink(is_dark, printed, g) > INK and tall(is_dark, printed, g) >= DIGIT_TALL


def photo(canon, cells):
    """The run of one answer's settled boxes as photographed, AROUND mm about it: what the reader sees. Not
    cleaned — taking the print out took the pencil lying on it too, and on 24 Sep every reader then stood
    behind the same wrong number (an 8 on its box's side read 3, a 3 below its box read 2; ADR 0035)."""
    m = round(AROUND * PPM)
    x0 = max(0, min(_px(c)[0] for c in cells) - m)
    y0 = max(0, min(_px(c)[1] for c in cells) - m)
    x1 = min(W, max(_px(c)[2] for c in cells) + m)
    y1 = min(H, max(_px(c)[3] for c in cells) + m)
    q = round(QUIET * PPM)
    crop = cv2.copyMakeBorder(canon[y0:y1, x0:x1], q, q, q, q, cv2.BORDER_REPLICATE)
    return cv2.imencode(".png", crop)[1].tobytes()


def _back(M, cells, shape, frame):
    """The run of boxes as (left, top, right, bottom) fractions of the page as it is shown — the photograph
    inside its PDF page (`frame`), so the approval screen crops exactly where the reading came from."""
    x0 = min(_px(c)[0] for c in cells) - 2 * PPM
    y0 = min(_px(c)[1] for c in cells) - 2 * PPM
    x1 = max(_px(c)[2] for c in cells) + 2 * PPM
    y1 = max(_px(c)[3] for c in cells) + 2 * PPM
    quad = np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]).reshape(-1, 1, 2)
    pts = cv2.perspectiveTransform(quad, np.linalg.inv(M)).reshape(-1, 2)
    h, w = shape[:2]
    fx0, fy0, fx1, fy1 = frame
    left, top = fx0 + (fx1 - fx0) * pts[:, 0].min() / w, fy0 + (fy1 - fy0) * pts[:, 1].min() / h
    right, bottom = fx0 + (fx1 - fx0) * pts[:, 0].max() / w, fy0 + (fy1 - fy0) * pts[:, 1].max() / h
    return [round(float(max(0, v)), 4) for v in (left, top, min(1, right), min(1, bottom))]


def _overlap(a, b):
    """Two words over the same pencil: one's span across the strip covers the other's middle. Not any overlap:
    the digit reader pads each number it finds, so two digits side by side overlap at their edges."""
    mid = lambda w: w["x"] + w["w"] / 2  # noqa: E731
    return a["x"] <= mid(b) <= a["x"] + a["w"] or b["x"] <= mid(a) <= b["x"] + b["w"]


def readings(words):
    """→ [(digits, confidence)], one per way the reader's words tile the strip.

    Textract reads one pencil twice: on 24 Sep a strip holding 1 4 0 5 came back as the word "1405" tagged
    printed AND as 1, 4, 0, 5 tagged handwriting, over the same pixels — joined, "14051405", eight digits
    for four boxes, and every such answer went to a person. Words over the same place are alternatives, not
    a sequence: each reading is a largest set of words no two of which overlap, read left to right."""
    words = sorted(words, key=lambda w: w["x"])[:14]
    n, out = len(words), []
    clash = [[_overlap(words[i], words[j]) for j in range(n)] for i in range(n)]
    for mask in range(1, 1 << n):
        pick = [i for i in range(n) if mask >> i & 1]
        if any(clash[i][j] for i in pick for j in pick if i < j):
            continue
        if any(not mask >> j & 1 and not any(clash[j][i] for i in pick) for j in range(n)):
            continue  # not the largest: a word that overlaps none of these was left out
        digits = "".join(re.sub(r"\D", "", words[i]["text"]) for i in pick)
        out.append((digits, min(float(words[i]["confidence"]) for i in pick)))
    return out


def decide(words, inked, floor):
    """→ (digits, confidence, doubt): the reading as many digits long as boxes hold ink, when every such
    reading agrees; otherwise a doubt in words, with the best reading as the guess."""
    found = readings(words)
    if not found or not any(d for d, _ in found):
        return "", 0.0, "ink in the box but no number"
    fits = [r for r in found if len(r[0]) == inked]
    if not fits:
        digits, conf = max(found, key=lambda r: r[1])
        return digits, conf, f"{inked} boxes hold ink but the reader saw {digits}"
    said = sorted({d for d, _ in fits})
    digits, conf = max(fits, key=lambda r: r[1])
    if len(said) > 1:
        return digits, conf, "the reader's readings disagree: " + " / ".join(said)
    if conf < floor:
        return digits, conf, "under the confidence floor"
    return digits, conf, ""


def read_page(img, page_no, pdf, geometry, wanted, cfg, frame=(0, 0, 1, 1), keep=None):
    """One page of a scan → {slot: reading} in the shape `ocr.answers_for` gives, or None when the page will
    not line up with the paper. `wanted`: {slot: (item_key, rid)} for the questions printed on this page.
    `keep`: (slot, png) → path — each answer's crop, blank or written, kept as read (`crops.keeper`)."""
    canon, M = line_up(img, pdf, page_no)
    if canon is None:
        return None
    printed = blank(str(pdf), page_no)
    grey = cv2.cvtColor(canon, cv2.COLOR_BGR2GRAY)
    is_dark = dark(canon)
    runs, works = cells_of(geometry, page_no)
    out = {}
    for slot, (item_key, rid) in wanted.items():
        run = runs.get((item_key, rid))
        if not run:
            continue
        box = _back(M, run, img.shape, frame)
        run = settle(grey, printed, run)
        inked = sum(holds_digit(is_dark, printed, c) for c in run)
        spaces = [settle(grey, printed, [w])[0] for w in works.get(item_key, [])]
        working = (
            "partial" if any(ink(is_dark, printed, w, WORK_INSIDE) > WORK_INK for w in spaces) else "none"
        )
        base = {"working_shown": working, "box": box, "boxes": len(run), "inked": inked, "seen": []}
        seen_as = photo(canon, run)
        if keep:
            base["crop"] = keep(slot, seen_as)
        if not inked:
            out[slot] = {**base, "child_answer": "", "answer_state": "blank", "why": "", "confidence": 100.0}
            continue
        words = sorted(digits.read(seen_as)["words"], key=lambda w: w["x"])
        seen = [{"text": w["text"], "confidence": round(float(w["confidence"]), 1)} for w in words]
        said, confidence, doubt = decide(words, inked, cfg["min_confidence"])
        out[slot] = {
            **base,
            "seen": seen,
            "child_answer": "" if doubt else said,
            "answer_state": "illegible" if doubt else "written",
            "why": doubt,
            "guess": said if doubt else "",
            "confidence": confidence,
        }
    return out
