"""N8 — a photographed page lined up with the page it was printed from (goals/s23-a-curled-photo-lines-up.yaml).

A phone photograph of a paper on a desk is not the printed page moved and turned. It is seen at an angle, it curls
where the paper lifts off the desk, a crease moves part of it, and the phone's scan app crops it so tight that the
corner marks go first: on 2026-09-24 the top two were cut off both copies of R31-H02 that were read as old papers. No
one straight map puts every answer where it printed — on 24 Sep copy 09 the best one left the bottom row 5-6 mm off,
and a run of boxes can be looked for only 3 mm around where a map puts it, because its boxes repeat every 8.4 mm.

So a page is lined up by its own print, in three moves, each measured on the page itself:

1. A first straight map from features the photograph shares with the printed page, found two ways, because each
   failed on pages the other lined up: ORB matched 37 features on 24 Sep copy 01 and left its lower half 3-7 mm off,
   and SIFT's matches on 23 Sep's first pages collapsed onto one point. Kept is the map under which more of the page's
   print is found. How many features matched is not how well a page lines up: 99 matched on a page left 7 mm off, 40
   on one whose answers were all within 3.2 mm.
2. The printed page is cut into overlapping tiles, and each tile holding print is looked for around where the first
   map puts it. The tiles found without doubt give a better straight map.
3. What that map leaves — the curl — is measured again at every tile, and a smooth field through those offsets carries
   the photograph the rest of the way. The photograph is drawn into the printed page's frame through both at once.

Measured on the 46 photographed pages of 23 and 24 Sep: every page lines up and every answer, 324 of 324, is found
in its boxes. A page on which less than half its print is found does not line up, and is read as an old paper.

Then each answer is found around its own printed question (`settle`): a crease moves one part of a page on its own,
as it moved 24 Sep copy 01's question 10. An answer whose print is not found there is not read at a guessed place.
"""

from functools import lru_cache

import cv2
import numpy as np
import pymupdf

from engine.w3_read import stencil

PPM = 10  # pixels per mm the scan is drawn at in the printed page's frame: 254 dpi, a phone scan's own
W, H = 210 * PPM, 297 * PPM
SIDE = 2000  # the long side ORB features are matched at, as `stencil` does
# SIFT's long side: it works on a copy doubled in size, and at 2000 px one photograph took 715 MB more (measured,
# peak resident memory) on a server of 1.9 GB whose engine has been killed for memory; at 1000, 158 MB
SIFT_SIDE = 1000
PRINTED = 140  # grey under this on the blank page is the paper's own print
FIT = 2.0  # mm a feature may sit off the first map and still count: a curled page's print is 1-3 mm off it
TPM = 5  # pixels per mm tiles are looked for at: fine enough to place one to 0.2 mm
TILE = 24.0  # mm: a tile holds words or boxes enough to be told from its neighbours
STRIDE = 12.0  # mm between tiles: they overlap by half
REACH = (
    8.0  # mm a tile is looked for around where the map puts it: the curl a first map leaves, 6 mm on 24 Sep
)
# A tile is found where its print matches the photograph at least FOUND well (normalised correlation), and CLEAR
# better than anywhere 2 mm or more away: a tile of repeated boxes matches equally well one box along, and is not.
FOUND, CLEAR = 0.3, 0.08
ENOUGH = 0.5  # of the tiles with print, at least this share found, or the page does not line up
AGREE = 3.0  # mm a tile's offset may differ from what the tiles around it say, or it matched something else
SMOOTH = (
    12.0  # mm: how far a tile's offset reaches into the field (a Gaussian's width), as far as the next tile
)
GRID = 2.0  # mm between the points the field is worked out at, then drawn through smoothly
CONTEXT = 10.0  # mm of the printed page around a run of boxes an answer is found by: its own question's print
NEAR = 6.0  # mm an answer is looked for around where the page puts it: a crease moved 24 Sep copy 01's by 6
# mm a run's own boxes then settle it by: a child's large digits outweigh a box's thin lines, and on a lifted test
# page the boxes alone, looked for 3 mm around, settled 3 mm off where the question's print had put them
FINE = 1.0
SEEK = 3.0  # mm the boxes alone are looked for where the question's print says nothing sure: under half a box
# A run's own printed boxes match the photograph at least this well where it is read, when its question's print was
# not found. Measured on the 324 answers of 23 and 24 Sep, lined up: 0.21 at the least, a child's pencil all over the
# boxes; 0.08 where an earlier line-up left a creased answer 6 mm off (24 Sep copy 01, question 10).
BOXES = 0.15

_sift = cv2.SIFT_create(4000)


def _grey(img, side):
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    s = side / max(g.shape[:2])
    return cv2.resize(g, None, fx=s, fy=s, interpolation=cv2.INTER_AREA), s


def _scale(s):
    return np.array([[s, 0, 0], [0, s, 0], [0, 0, 1]], dtype=np.float64)


@lru_cache(maxsize=8)
def blank(pdf, page_no):
    """The printed page, drawn at PPM, grey: the frame every box position is recorded in."""
    with pymupdf.open(pdf) as doc:
        pix = doc[page_no - 1].get_pixmap(
            matrix=pymupdf.Matrix(PPM * 25.4 / 72, PPM * 25.4 / 72), colorspace=pymupdf.csGRAY
        )
        g = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width)
    return cv2.resize(g, (W, H), interpolation=cv2.INTER_AREA)


@lru_cache(maxsize=8)
def _printed(pdf, page_no):
    """The printed page as features are matched on it, and as tiles are cut from it: (grey at SIDE and its scale, SIFT
    keypoints and descriptors at SIFT_SIDE and its scale, the page at TPM, the tiles holding print as (x, y) pixels
    at TPM)."""
    ref = blank(pdf, page_no)
    small, s = _grey(ref, SIDE)
    tiny, t_ref = _grey(ref, SIFT_SIDE)
    keys, desc = _sift.detectAndCompute(tiny, None)
    page = cv2.resize(ref, (W * TPM // PPM, H * TPM // PPM), interpolation=cv2.INTER_AREA)
    t, r, step = round(TILE * TPM), round(REACH * TPM), round(STRIDE * TPM)
    tiles = [
        (x, y)
        for y in range(r, page.shape[0] - t - r + 1, step)
        for x in range(r, page.shape[1] - t - r + 1, step)
        if (page[y : y + t, x : x + t] < PRINTED).mean() > 0.02 and page[y : y + t, x : x + t].std() > 20
    ]
    return small, s, (tiny, t_ref, keys, desc), page, tiles


def _by_sift(img, printed):
    """A first map by SIFT features, photograph pixels → the printed frame, or None."""
    tiny_ref, t_ref, k2, d2 = printed[2]
    tiny, t_child = _grey(img, SIFT_SIDE)
    k1, d1 = _sift.detectAndCompute(tiny, None)
    if d1 is None or d2 is None:
        return None
    # each printed feature matched once, both ways: many photographed features matched to one printed one pulled
    # a map onto a single point on 23 Sep
    pairs = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True).match(d1, d2)
    if len(pairs) < 12:
        return None
    a = np.float32([k1[m.queryIdx].pt for m in pairs]).reshape(-1, 1, 2)
    b = np.float32([k2[m.trainIdx].pt for m in pairs]).reshape(-1, 1, 2)
    Hm, _ = cv2.findHomography(a, b, cv2.RANSAC, FIT * SIFT_SIDE / 297)
    if Hm is None or not stencil.plausible(Hm, tiny.shape, tiny_ref.shape):
        return None
    return _scale(1 / t_ref) @ Hm @ _scale(t_child)


def _by_orb(small, s_child, printed):
    """A first map by ORB features (`stencil.homography`), photograph pixels → the printed frame, or None."""
    ref_small, s_ref = printed[0], printed[1]
    Hm, _ = stencil.homography(small, ref_small)
    if Hm is None or not stencil.plausible(Hm, small.shape, ref_small.shape):
        return None
    return _scale(1 / s_ref) @ Hm @ _scale(s_child)


def _found(small, s_child, M, printed):
    """Each tile of print found where `M` puts the photograph, without doubt: rows (x, y, dx, dy) in mm — the tile's
    middle on the printed page, and how far from it the photograph holds it."""
    page, tiles = printed[3], printed[4]
    seen = cv2.warpPerspective(
        small, _scale(TPM / PPM) @ M @ _scale(1 / s_child), page.shape[::-1], borderValue=255
    )
    t, r, k = round(TILE * TPM), round(REACH * TPM), round(2 * TPM)
    out = []
    for x, y in tiles:
        score = cv2.matchTemplate(
            seen[y - r : y + t + r, x - r : x + t + r], page[y : y + t, x : x + t], cv2.TM_CCOEFF_NORMED
        )
        _, best, _, (bx, by) = cv2.minMaxLoc(score)
        score[max(0, by - k) : by + k + 1, max(0, bx - k) : bx + k + 1] = -1
        if best >= FOUND and best - score.max() >= CLEAR:
            out.append(((x + t / 2) / TPM, (y + t / 2) / TPM, (bx - r) / TPM, (by - r) / TPM))
    return np.float32(out).reshape(-1, 4)


def _weights(at, tiles):
    """How much each tile's offset counts at each point of `at` (mm), by its distance."""
    d2 = (at[..., 0, None] - tiles[:, 0]) ** 2 + (at[..., 1, None] - tiles[:, 1]) ** 2
    return np.exp(-d2 / (2 * SMOOTH**2))


def _agreeing(found):
    """The tiles whose offset the tiles around them bear out: one that matched something else stands out from them."""
    keep = []
    for i in range(len(found)):
        others = np.delete(found, i, axis=0)
        w = _weights(found[i, :2], others)
        if w.sum() < 0.5:  # none near enough to say
            keep.append(i)
            continue
        said = (w[:, None] * others[:, 2:]).sum(0) / w.sum()
        if np.hypot(*(found[i, 2:] - said)) <= AGREE:
            keep.append(i)
    return found[keep]


def _field(found):
    """The curl: the offset (dx, dy) in mm at every GRID mm of the page, each point the tiles' offsets weighed by
    their distance from it."""
    ys, xs = np.mgrid[0 : 297 + GRID : GRID, 0 : 210 + GRID : GRID].astype(np.float32)
    if not len(found):
        return np.zeros_like(xs), np.zeros_like(ys)
    w = _weights(np.stack([xs, ys], -1), found) + 1e-12
    return ((w * found[:, 2]).sum(-1) / w.sum(-1)).astype(np.float32), (
        (w * found[:, 3]).sum(-1) / w.sum(-1)
    ).astype(np.float32)


def line_up(img, pdf, page_no):
    """→ (the photograph drawn in the printed page's frame, and `to_photo`: pixels of that frame → pixels of the
    photograph), or (None, None) when too little of the printed page is found on it."""
    printed = _printed(str(pdf), page_no)
    small, s_child = _grey(img, SIDE)
    tiles = printed[4]
    first = [M for M in (_by_orb(small, s_child, printed), _by_sift(img, printed)) if M is not None]
    best = max(
        ((M, _found(small, s_child, M, printed)) for M in first), key=lambda m: len(m[1]), default=(None, ())
    )
    M, found = best
    if M is None or len(found) < max(8, ENOUGH * len(tiles)):
        return None, None
    where, seen = found[:, :2] * PPM, (found[:, :2] + found[:, 2:]) * PPM
    better, _ = cv2.findHomography(seen, where, cv2.RANSAC, 1.5 * PPM)
    if better is not None and stencil.plausible(better @ M, img.shape, (H, W)):
        M = better @ M
    fx, fy = _field(_agreeing(_found(small, s_child, M, printed)))
    back = np.linalg.inv(M)

    def to_photo(px, py):
        """Pixels of the printed frame → where the photograph holds them: through the curl, then back through M.
        Arrays of any shape, the same shape back."""
        px, py = np.asarray(px, np.float32), np.asarray(py, np.float32)
        x = px.reshape(1, -1) if px.ndim < 2 else px  # a map is two-dimensional
        y = py.reshape(1, -1) if py.ndim < 2 else py
        gx, gy = x / (GRID * PPM), y / (GRID * PPM)
        qx = x + cv2.remap(fx, gx, gy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE) * PPM
        qy = y + cv2.remap(fy, gx, gy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE) * PPM
        z = back[2, 0] * qx + back[2, 1] * qy + back[2, 2]
        ox = (back[0, 0] * qx + back[0, 1] * qy + back[0, 2]) / z
        oy = (back[1, 0] * qx + back[1, 1] * qy + back[1, 2]) / z
        return ox.reshape(px.shape), oy.reshape(py.shape)

    canon = np.empty((H, W, *img.shape[2:]), img.dtype)
    xs = np.arange(W, dtype=np.float32)
    for y0 in range(0, H, 256):  # a strip at a time: the whole frame's maps at once are 50 MB
        px, py = np.meshgrid(xs, np.arange(y0, min(H, y0 + 256), dtype=np.float32))
        mx, my = to_photo(px, py)
        canon[y0 : y0 + len(py)] = cv2.remap(
            img, mx.astype(np.float32), my.astype(np.float32), cv2.INTER_CUBIC, borderValue=(255, 255, 255)
        )
    return canon, to_photo


def _match(grey, printed, box, reach, at=(0, 0)):
    """Where the printed page's `box` (x0, y0, x1, y1 pixels) sits on the lined-up photograph, looked for within `reach`
    mm around `at` pixels from its place → (dx, dy) pixels, how well it matches (normalised correlation), and how much
    better than anywhere 2 mm or more away. The box is cut to what can be looked for inside the frame."""
    s, (ax, ay) = round(reach * PPM), at
    x0, y0 = max(box[0], s - ax), max(box[1], s - ay)
    x1, y1 = min(box[2], W - s - ax), min(box[3], H - s - ay)
    part = printed[y0:y1, x0:x1]
    if part.size == 0 or part.std() < 5:  # nothing printed to find it by
        return ax, ay, 0.0, 0.0
    score = cv2.matchTemplate(
        grey[y0 + ay - s : y1 + ay + s, x0 + ax - s : x1 + ax + s], part, cv2.TM_CCOEFF_NORMED
    )
    _, best, _, (bx, by) = cv2.minMaxLoc(score)
    k = 2 * PPM
    score[max(0, by - k) : by + k + 1, max(0, bx - k) : bx + k + 1] = -1
    return ax + bx - s, ay + by - s, best, best - score.max()


def settle(grey, printed, cells):
    """→ (the recorded `cells` moved together to where their run printed on this photograph, lined up; and whether it
    was found there). First by the answer's own question — the run with CONTEXT mm of the printed page around it,
    looked for within NEAR mm: a crease moves one question on its own, and the words above its boxes say which run is
    its own where boxes alone repeat — then settled by its own boxes within FINE of that. Where the question's print
    says nothing sure, by the boxes alone within SEEK, and found only if they match at least BOXES well. Not box by
    box: one printed square is too little to match on, and jumps."""
    x0, y0 = round(min(c["x"] for c in cells) * PPM), round(min(c["y"] for c in cells) * PPM)
    x1 = round(max(c["x"] + c["w"] for c in cells) * PPM)
    y1 = round(max(c["y"] + c["h"] for c in cells) * PPM)
    around, p = round(CONTEXT * PPM), round(1.5 * PPM)
    run = (x0 - p, y0 - p, x1 + p, y1 + p)
    dx, dy, how, clear = _match(grey, printed, (x0 - around, y0 - around, x1 + around, y1 + around), NEAR)
    if how >= FOUND and clear >= CLEAR:  # found by its question's print: its boxes only settle it
        dx, dy, _, _ = _match(grey, printed, run, FINE, (dx, dy))
        found = True
    else:  # its question's print says nothing sure: its boxes alone, around where the page lined up
        dx, dy, how, _ = _match(grey, printed, run, SEEK)
        found = how >= BOXES
    moved = [
        {**cell, "x": cell["x"] + dx / PPM, "y": cell["y"] + dy / PPM, "from": (cell["x"], cell["y"])}
        for cell in cells
    ]
    return moved, found
