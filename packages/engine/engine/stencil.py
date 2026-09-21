"""The blank page a paper was printed from, rebuilt from the children who sat it — and each child's
page read against it (ADR 0022).

The standard form pipeline is: align the scan to a template, read each field where the template
says it is. There is no unmarked copy of any paper on disk, so the template is rebuilt from the
corpus: every child's copy of a page is aligned to one of them (ORB features, RANSAC homography)
and the per-pixel MEDIAN is taken. What the paper printed is on every copy and survives; what one
child wrote is on one copy and is voted away. Measured: 300-1000 inliers a page, clean printed
pages for every paper at least two children sat.

What the blank buys the reader is the one distinction Textract makes worst — whose mark is this?
Textract tags each word HANDWRITING or PRINTED by how it looks, and a child's neat "400" written
inside a printed box looks printed: nine answers in nine boxes, all perfectly legible, came back as
one. Against the blank the question is answered by the paper itself: a word on the child's page
that the blank does not hold, at that place, is the child's. And the questions and boxes are found
on the clean blank, where no child's digit sits inside a printed question line and no pencil
crosses a box's border.

A paper only one child sat has no blank to rebuild — one copy votes for its own handwriting — and
is read exactly as before.
"""

import json
import re
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np

from engine.adapters import ocr

TEMPLATES = Path(__file__).resolve().parents[3] / "data" / "paper-templates"
# Every copy, and the blank, is drawn this long on its long side before it is aligned or averaged.
# The scans run from 1754 px (a 150-dpi render) to 6782 (a phone photograph); a common size is what
# makes a per-pixel median mean anything.
SIDE = 2000


def grey(jpeg, side=SIDE):
    img = cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_GRAYSCALE)
    s = side / max(img.shape[:2])
    return cv2.resize(img, None, fx=s, fy=s, interpolation=cv2.INTER_AREA)


def homography(src, dst):
    """→ (3x3 mapping src pixels to dst pixels, RANSAC inliers), or (None, n) when it will not fit."""
    orb = cv2.ORB_create(5000)
    k1, d1 = orb.detectAndCompute(src, None)
    k2, d2 = orb.detectAndCompute(dst, None)
    if d1 is None or d2 is None:
        return None, 0
    matches = sorted(cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True).match(d1, d2), key=lambda m: m.distance)
    matches = matches[: max(12, len(matches) // 4)]
    if len(matches) < 12:
        return None, len(matches)
    a = np.float32([k1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
    b = np.float32([k2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
    H, mask = cv2.findHomography(a, b, cv2.RANSAC, 5.0)
    return (H, int(mask.sum())) if H is not None else (None, 0)


def plausible(H, src_shape, dst_shape):
    """A homography that turns a page into a sliver or a bow tie matched the wrong features. The
    page's corners must land as a convex shape of about the page's own area."""
    h, w = src_shape[:2]
    quad = cv2.perspectiveTransform(np.float32([[0, 0], [w, 0], [w, h], [0, h]]).reshape(-1, 1, 2), H)
    ratio = cv2.contourArea(quad) / float(dst_shape[0] * dst_shape[1])
    return cv2.isContourConvex(quad.astype(np.float32)) and 0.5 <= ratio <= 2.0


def build(jpegs):
    """Copies of one page → (the blank, how many copies went into it, inliers per aligned copy)."""
    greys = [grey(j) for j in jpegs]
    # The reference is the copy of median size: warping everything onto an outlier's frame
    # stretches the whole stack to fit one bad photograph.
    ref = sorted(greys, key=lambda g: g.shape[0] * g.shape[1])[len(greys) // 2]
    stack, inliers = [ref], []
    for g in greys:
        if g is ref:
            continue
        H, n = homography(g, ref)
        inliers.append(n)
        if H is not None and plausible(H, g.shape, ref.shape):
            stack.append(cv2.warpPerspective(g, H, (ref.shape[1], ref.shape[0]), borderValue=255))
    return np.median(np.stack(stack), axis=0).astype(np.uint8), len(stack), inliers


def _path(form, page):
    return TEMPLATES / f"{form}-p{page}"


def save(form, page, blank, read, boxes):
    TEMPLATES.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(_path(form, page).with_suffix(".png")), blank)
    _path(form, page).with_suffix(".json").write_text(json.dumps({"read": read, "boxes": boxes}))
    load.cache_clear()


def drop(form, page):
    for suffix in (".png", ".json"):
        _path(form, page).with_suffix(suffix).unlink(missing_ok=True)
    load.cache_clear()


@lru_cache(maxsize=32)
def load(form, page):
    """The blank for one page of a printed form, or None where there is none."""
    png, js = _path(form, page).with_suffix(".png"), _path(form, page).with_suffix(".json")
    if not (png.exists() and js.exists()):
        return None
    return {"grey": cv2.imread(str(png), cv2.IMREAD_GRAYSCALE), **json.loads(js.read_text())}


def _scale(shape):
    """Fractions of a page → its pixels."""
    return np.diag([shape[1], shape[0], 1.0])


def _map_box(M, x0, y0, x1, y1):
    pts = cv2.perspectiveTransform(np.float32([[x0, y0], [x1, y0], [x1, y1], [x0, y1]]).reshape(-1, 1, 2), M)
    xs, ys = pts[:, 0, 0], pts[:, 0, 1]
    return float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())


def empty_at(blank, M, w, cfg):
    """Is the blank page empty where this word sits? Measured on the blank's pixels, never on
    Textract's reading of it: a median of several photographs is soft, and a reader that misses a
    printed word there would call the paper empty where it is not.

    The patch is the word's box, shrunk a sixth on each side: a child's digit crowding the border of
    a printed box must not pick up the border's ink and be taken for print.
    """
    x0, y0, x1, y1 = _map_box(M, w["x"], w["y"], w["x"] + w["w"], w["y"] + w["h"])
    dx, dy = (x1 - x0) / 6, (y1 - y0) / 6
    g = blank["grey"]
    h, wd = g.shape
    patch = g[
        max(0, int((y0 + dy) * h)) : int((y1 - dy) * h), max(0, int((x0 + dx) * wd)) : int((x1 - dx) * wd)
    ]
    return patch.size > 0 and float((patch < 128).mean()) < cfg["stencil_empty"]


def promote(words, blank, M, printed_numbers, cfg):
    """The child's words, with every number Textract called PRINTED given back to the child where the
    blank is empty at that place.

    Textract tags a word by how it looks, and a child's neat "30" inside a printed box looks printed:
    on one Grade 3 page the answers 30, 8, 70, 100, 13 and 1113 were all tagged PRINT at 98-99% —
    each read correctly, then set aside as the paper's.

    One direction only, and never for a number the paper prints on this page. Handwriting is never
    turned into print — where most children wrote the same answer in the same box, the median keeps
    a ghost of it, and a ghost must not make a child's answer disappear. And a page photographed on
    a curve does not line up with its blank to the pixel: a printed operand that lands on white
    because of it must still be the paper's, so a number the questions print is left exactly as
    Textract tagged it.
    """
    out = []
    for w in words:
        v = ocr.value_of(w["text"]) if not w["hand"] else None
        if v and v not in printed_numbers and empty_at(blank, M, w, cfg):
            w = {**w, "hand": True}
        out.append(w)
    return out


def read_page(jpeg, slots, cfg, cli, form=None, page_no=1, symbolic=(), use_boxes=False, reread=None):
    """One page → {slot: reading}. Everything is read on the child's own page, exactly as before;
    the blank, where the paper has one, answers only "is this 'printed' number really the paper's?"

    The first design moved the child's words onto the blank and anchored on the blank's lines. On
    flat scans that lined up to half a percent of the page; on a curved phone photograph to ten, and
    a blank averaged from photographs is soft enough that Textract misread its question numbers. On
    the 83 hand-checked answers it put every answer of one quiz on the question below: 18 silently
    wrong. The child's crisp page keeps every job it was doing well.
    """
    page = ocr.read(jpeg, cli)
    blank = load(form, page_no) if form else None
    lined_up = 0
    if blank is not None:
        child = grey(jpeg)
        H, n = homography(child, blank["grey"])
        if (
            H is not None
            and n >= cfg["stencil_min_inliers"]
            and plausible(H, child.shape, blank["grey"].shape)
        ):
            # child fractions → child pixels → blank pixels → blank fractions
            M = np.linalg.inv(_scale(blank["grey"].shape)) @ H @ _scale(child.shape)
            # Every number the page prints: in its questions, and anywhere else the blank shows print —
            # a heading's "4-Digit Numbers", a paper's "(20 Questions)".
            printed_numbers = {ocr.value_of(t) for q in slots.values() for t in re.findall(r"\d[\d,]*", q)}
            printed_numbers |= {ocr.value_of(w["text"]) for w in blank["read"]["words"] if not w["hand"]}
            # and the question numbers themselves: "10." printed beside "9 x 6 =" was taken off a
            # photograph that lines up with its blank to a percent or two, landed on white, and came
            # back as a child's answer of 10 — to a question the child had left blank.
            printed_numbers |= {m.group() for k in slots for m in [re.match(r"\d+", k)] if m}
            page = {**page, "words": promote(page["words"], blank, M, printed_numbers, cfg)}
            lined_up = n
    boxes = ocr.printed_boxes(jpeg, cfg) if use_boxes else ()
    out = ocr.answers_for(page, slots, cfg, symbolic, boxes, reread)
    if lined_up:
        for r in out.values():
            r["stencil"] = lined_up
    return out


def copies(conn):
    """{(printed form, page): [(file, page within that file, name-band mask)]} for every live capture.

    From the map the database already holds, never from file names. A paper that prints the same
    sheet as another — the Grade 4 child sat the Grade 3 Level A paper under its own header — names
    it as `printed_as`, and its copy votes in that sheet's blank.
    """
    rows = conn.execute(
        "select c.path, c.pages, st.key as paper, array_agg(distinct (i.spec->>'page')::int) as read"
        " from capture c"
        " join sheet_instance si on si.id = c.sheet_instance_id"
        " join sheet_template st on st.id = si.sheet_template_id"
        " join item_result r on r.capture_id = c.id join item i on i.id = r.item_id"
        " where c.superseded_by is null group by c.id, c.path, c.pages, st.id"
    ).fetchall()
    out = {}
    for r in rows:
        paper = r["paper"] if isinstance(r["paper"], dict) else json.loads(r["paper"])
        form = paper.get("printed_as", paper["code"])
        masks = {p["n"]: p.get("mask", 0) for p in paper.get("pages", [])}
        for k, page in enumerate(sorted(r["read"]), 1):
            src = Path(r["path"]).expanduser()
            out.setdefault((form, page), []).append((src, k if r["pages"] > 1 else 1, masks.get(page, 0)))
    return out
