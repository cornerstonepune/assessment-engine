"""A paper this system printed is read where it printed (goals/s16-read-the-boxes.yaml).

The renderer records where every answer box sits, to the tenth of a millimetre, in the key it writes beside
each PDF (`render.GEOM_JS`). So a scan of that paper needs no searching: the page is lined up with the page
it was printed from, each box is cut out at its recorded place, and only what is inside the boxes is handed to
the reader. This is what a form reader does, and what the old-paper reader (`ocr.answers_for`) could not do,
because nobody knew where those papers' answers lived: it took the handwritten number nearest the printed
question, which on 2026-09-24 was the child's working.

What code decides here, and the reader is never asked: whether a box is blank (a count of dark pixels), how
many boxes hold ink (the same), whether the working space was written in (the third signal, rule 5). The
reader is asked one thing — which digits are in this strip of boxes — and its answer stands only when it has
exactly as many digits as boxes hold ink.

Lining up is by the printed page's own features (ORB, RANSAC; `stencil.homography`), not by the corner marks:
a phone's "scan" app crops the page tight and the marks are the first thing it cuts off (every page of the
2026-09-24 file). A page that will not line up is read as an old paper, and says so.
"""

import re
from functools import lru_cache

import cv2
import numpy as np
import pymupdf

from engine.adapters import ocr
from engine.assess.geometry import cells_of
from engine.w3_read import stencil

PPM = 10  # pixels per mm the scan is drawn at in the printed page's frame: 254 dpi, a phone scan's own
W, H = 210 * PPM, 297 * PPM
EDGE = 0.8  # mm each side of a printed box line painted out before the reader sees the strip
INSIDE = 0.7  # mm inside its printed line a cell is measured for ink, so the line itself never counts
# A pencil digit fills 3-15% of its cell; JPEG noise and a shadow on white, measured under 0.3%.
INK = 0.012
WORK_INK = 0.004  # this much of the working space written on is the third signal (rule 5)
WORK_INSIDE = 1.5  # mm: the working box's dashed border and its printed label stay outside the measure
MARGIN = 4  # mm of white around a strip: Textract is a document reader, and a bare word comes back in bits
MIN_INLIERS = 60  # fewer matched features than this and the page is not the one it claims to be
SIDE = 2000  # the long side features are matched at, as `stencil` does


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


def dark(canon, printed):
    """Where the page is written on: darker than its own surroundings, so a shadow across a photograph is
    not ink and a faint pencil on a bright page is — and not where the paper itself prints (`printed`, the
    blank page in the same frame): a box's line and the word "working" are the paper's, never the child's."""
    g = cv2.cvtColor(canon, cv2.COLOR_BGR2GRAY)
    background = cv2.blur(g, (8 * PPM, 8 * PPM))
    theirs = cv2.dilate((printed < 140).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    return (g < background * 0.72) & ~theirs


def _px(g, inside=0.0):
    """A recorded cell, in canonical pixels, shrunk `inside` mm on every side."""
    x0, y0 = int((g["x"] + inside) * PPM), int((g["y"] + inside) * PPM)
    x1, y1 = int((g["x"] + g["w"] - inside) * PPM), int((g["y"] + g["h"] - inside) * PPM)
    return max(0, x0), max(0, y0), min(W, max(x0 + 1, x1)), min(H, max(y0 + 1, y1))


def ink(is_dark, g, inside=INSIDE):
    x0, y0, x1, y1 = _px(g, inside)
    return float(is_dark[y0:y1, x0:x1].mean())


def strip(canon, cells):
    """The run of one answer's boxes, their printed lines painted out, white all round: what the reader sees."""
    x0 = min(_px(c)[0] for c in cells)
    y0 = min(_px(c)[1] for c in cells)
    x1 = max(_px(c)[2] for c in cells)
    y1 = max(_px(c)[3] for c in cells)
    patch = canon[y0:y1, x0:x1].copy()
    e = max(1, int(EDGE * PPM))
    for c in cells:
        cx0, cy0, cx1, cy1 = (v - o for v, o in zip(_px(c), (x0, y0, x0, y0)))
        patch[max(0, cy0 - e) : cy0 + e, :] = 255
        patch[max(0, cy1 - e) : cy1 + e, :] = 255
        patch[:, max(0, cx0 - e) : cx0 + e] = 255
        patch[:, max(0, cx1 - e) : cx1 + e] = 255
    m = MARGIN * PPM
    patch = cv2.copyMakeBorder(patch, m, m, m, m, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    return cv2.imencode(".jpg", patch, [cv2.IMWRITE_JPEG_QUALITY, 92])[1].tobytes()


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


def read_page(img, page_no, pdf, geometry, wanted, cli, cfg, frame=(0, 0, 1, 1)):
    """One page of a scan → {slot: reading} in the shape `ocr.answers_for` gives, or None when the page will
    not line up with the paper. `wanted`: {slot: (item_key, rid)} for the questions printed on this page."""
    canon, M = line_up(img, pdf, page_no)
    if canon is None:
        return None
    is_dark = dark(canon, blank(str(pdf), page_no))
    runs, works = cells_of(geometry, page_no)
    out = {}
    for slot, (item_key, rid) in wanted.items():
        run = runs.get((item_key, rid))
        if not run:
            continue
        inked = sum(ink(is_dark, c) > INK for c in run)
        working = (
            "partial"
            if any(ink(is_dark, w, WORK_INSIDE) > WORK_INK for w in works.get(item_key, []))
            else "none"
        )
        box = _back(M, run, img.shape, frame)
        base = {"working_shown": working, "box": box, "boxes": len(run), "inked": inked, "seen": []}
        if not inked:
            out[slot] = {**base, "child_answer": "", "answer_state": "blank", "why": "", "confidence": 100.0}
            continue
        words = sorted((w for w in ocr.read(strip(canon, run), cli)["words"]), key=lambda w: w["x"])
        digits = "".join(re.sub(r"\D", "", w["text"]) for w in words)
        seen = [{"text": w["text"], "confidence": round(float(w["confidence"]), 1)} for w in words]
        confidence = min((float(w["confidence"]) for w in words), default=0.0)
        doubt = ""
        if not digits:
            doubt = "ink in the box but no number"
        elif len(digits) != inked:
            doubt = f"{inked} boxes hold ink but the reader saw {digits}"
        elif confidence < cfg["min_confidence"]:
            doubt = "under the confidence floor"
        out[slot] = {
            **base,
            "seen": seen,
            "child_answer": "" if doubt else digits,
            "answer_state": "illegible" if doubt else "written",
            "why": doubt,
            "guess": digits if doubt else "",
            "confidence": confidence,
        }
    return out
