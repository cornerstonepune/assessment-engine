"""Why a photographed page of the newest scan does not line up (read only; goals/r1b-read-again.yaml). Numbers only:
never a name or an image (rule 6). For each page `lineup.line_up` refuses, and for one page it takes, beside it:

- each first map (ORB, SIFT): whether it holds a paper, its matches, and the printed page's corners in the photograph
  (where the paper is, and whether the photograph cut part of it off);
- how many of the printed tiles fall inside the photograph's picture at all, under that map;
- the tiles found, where on the page (their extent in mm) and how far off the map left them;
- the tiles found when the map is refined from what it found, round by round, and looked for twice as far;
- how sharp and how lit the paper is (the Laplacian's variance, the grey's spread), against a page that lines up."""

import json
from pathlib import Path

import cv2
import numpy as np

from engine.core import db
from engine.w3_read import lineup, render_pdf

PAGES = {3: (1,), 4: (1,), 7: (1,), 8: (1, 2), 1: (1,)}  # copy → its pages that failed on 22 Oct; copy 1 lines up


def _corners(M, shape):
    back = np.linalg.inv(M)
    page = np.array([[0, 0], [lineup.W, 0], [lineup.W, lineup.H], [0, lineup.H]], np.float32).reshape(-1, 1, 2)
    quad = cv2.perspectiveTransform(page, back).reshape(-1, 2)
    h, w = shape[:2]
    return [[round(float(x) / w, 2), round(float(y) / h, 2)] for x, y in quad]


def _inside(M, img, printed):
    """Share of the printed tiles whose middle the map puts on the photograph's picture (not the white around it)."""
    tiles = printed[4]
    mids = np.array([[(x + lineup.TILE * lineup.TPM / 2) * lineup.PPM / lineup.TPM,
                      (y + lineup.TILE * lineup.TPM / 2) * lineup.PPM / lineup.TPM] for x, y in tiles], np.float32)
    at = cv2.perspectiveTransform(mids.reshape(-1, 1, 2), np.linalg.inv(M)).reshape(-1, 2)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    h, w = g.shape
    ok = (at[:, 0] >= 0) & (at[:, 0] < w) & (at[:, 1] >= 0) & (at[:, 1] < h)
    pic = np.zeros(len(at), bool)
    for i in np.where(ok)[0]:
        x, y = int(at[i, 0]), int(at[i, 1])
        pic[i] = g[max(0, y - 3): y + 4, max(0, x - 3): x + 4].min() < 250  # pure white is the page the photo lies on
    return round(float(pic.mean()), 2)


def _found_said(f):
    if not len(f):
        return {"n": 0}
    return {"n": len(f), "x_mm": [int(f[:, 0].min()), int(f[:, 0].max())], "y_mm": [int(f[:, 1].min()), int(f[:, 1].max())],
            "off_mm_median": round(float(np.median(np.hypot(f[:, 2], f[:, 3]))), 1)}


def _refined(small, s, M, printed, rounds=3):
    out = []
    for _ in range(rounds):
        f = lineup._found(small, s, M, printed)
        out.append(len(f))
        if len(f) < 8:
            break
        better, _ = cv2.findHomography((f[:, :2] + f[:, 2:]) * lineup.PPM, f[:, :2] * lineup.PPM, cv2.RANSAC,
                                       1.5 * lineup.PPM)
        if better is None:
            break
        M = better @ M
    out.append(len(lineup._found(small, s, M, printed)))
    return out


def _paper_quality(img, M):
    """Sharpness and light of the paper itself: the photograph drawn into the printed frame, small, its middle."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    seen = cv2.warpPerspective(g, lineup._scale(0.5) @ M, (lineup.W // 2, lineup.H // 2), borderValue=(255,))
    mid = seen[100:-100, 100:-100]
    return {"laplacian_var": round(float(cv2.Laplacian(mid, cv2.CV_64F).var()), 1),
            "grey_p5_p50_p95": [int(v) for v in np.percentile(mid, [5, 50, 95])]}


def why(scan, pdf, page):
    img, _ = render_pdf.photo(scan, page)
    printed = lineup._printed(str(pdf), page)
    small, s = lineup._grey(img, lineup.SIDE)
    out = {"tiles": len(printed[4]), "needs": int(np.ceil(lineup.ENOUGH * len(printed[4])))}
    for name, M in (("orb", lineup._by_orb(small, s, printed)), ("sift", lineup._by_sift(img, printed))):
        if M is None:
            out[name] = None
            continue
        r = {"holds_paper": lineup._holds_paper(M, img.shape), "paper_corners_in_photo": _corners(M, img.shape),
             "tiles_on_picture": _inside(M, img, printed), "found": _found_said(lineup._found(small, s, M, printed)),
             "refined_rounds": _refined(small, s, M, printed), **_paper_quality(img, M)}
        was = lineup.REACH
        try:
            lineup.REACH = 2 * was
            r["found_reach_16mm"] = len(lineup._found(small, s, M, printed))
        finally:
            lineup.REACH = was
        out[name] = r
    canon, _ = lineup.line_up(img, pdf, page)
    out["lines_up_now"] = canon is not None
    for k in (cv2.ROTATE_90_CLOCKWISE, cv2.ROTATE_90_COUNTERCLOCKWISE):
        c2, _ = lineup.line_up(cv2.rotate(img, k), pdf, page)
        out[f"lines_up_rotated_{k}"] = c2 is not None
    c3, _ = lineup.line_up(cv2.flip(img, 1), pdf, page)
    out["lines_up_mirrored"] = c3 is not None
    return out


with db.connect() as c:
    run = c.execute("select result from flow_run where flow = 'read-scan' order by started_at desc limit 1").fetchone()
    for cp in (run["result"] or {}).get("copies", []):
        if cp.get("copy") not in PAGES or not cp.get("capture_id"):
            continue
        cap = c.execute("select c.path, si.pdf_path from capture c join sheet_instance si on si.id = c.sheet_instance_id"
                        " where c.id = %s", (cp["capture_id"],)).fetchone()
        scan, pdf = Path(cap["path"]).expanduser(), cap["pdf_path"]
        for p in PAGES[cp["copy"]]:
            try:
                print("== copy", cp["copy"], "page", p, json.dumps(why(scan, pdf, p), default=str))
            except Exception as e:  # noqa: BLE001 — a measure says what failed and goes on
                print("== copy", cp["copy"], "page", p, "failed:", type(e).__name__, str(e)[:200])
