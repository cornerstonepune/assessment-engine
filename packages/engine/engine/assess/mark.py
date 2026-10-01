"""A photographed page made square again by its four corner marks, and the QR that names it.

`deskew` finds the black corner squares and warps the page onto the canonical grid the printed sheet was drawn on
(`PPM` pixels per millimetre); `read_qr` reads the code from the canonical page. Reading the answers is
`w3_read/`'s. The prototype's synthetic round trip (fake answers, a fake photo, a printed-digit reader) went
unused once real scans arrived, and was deleted (goals/p2-less-code.yaml).
"""

import cv2
import numpy as np

PPM = 8  # pixels per mm in the canonical deskewed image
W, H = 210 * PPM, 297 * PPM
FID_MM = 7.0
FID_OFF = 6.0  # fiducial size and offset from page edge (render.py CSS)
FID_CENTERS = {
    "tl": (FID_OFF + FID_MM / 2, FID_OFF + FID_MM / 2),
    "tr": (210 - FID_OFF - FID_MM / 2, FID_OFF + FID_MM / 2),
    "bl": (FID_OFF + FID_MM / 2, 297 - FID_OFF - FID_MM / 2),
    "br": (210 - FID_OFF - FID_MM / 2, 297 - FID_OFF - FID_MM / 2),
}

# ------------------------------------------------------------------ deskew


def find_fiducials(img):
    """Return dict tl/tr/bl/br -> (x, y) pixel centres of the four black corner squares, or None."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    g = cv2.GaussianBlur(g, (5, 5), 0)
    _, bw = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    cnts, _ = cv2.findContours(bw, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    h, w = g.shape
    page_area = h * w
    cands = []
    for c in cnts:
        a = cv2.contourArea(c)
        if a < page_area * 1.5e-4 or a > page_area * 4e-3:  # a 7mm square on A4 is ~0.08% of the page
            continue
        x, y, bw_, bh_ = cv2.boundingRect(c)
        ar = bw_ / float(bh_)
        fill = a / float(bw_ * bh_)
        if 0.6 < ar < 1.6 and fill > 0.75 and g[y : y + bh_, x : x + bw_].mean() < 90:
            cands.append((x + bw_ / 2, y + bh_ / 2, a))
    if len(cands) < 4:
        return None
    # pick the candidate nearest each image corner
    corners = {"tl": (0, 0), "tr": (w, 0), "bl": (0, h), "br": (w, h)}
    out = {}
    for k, (cx, cy) in corners.items():
        best = min(cands, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
        out[k] = (best[0], best[1])
    # sanity: the four picks must be distinct and roughly rectangular
    pts = np.array([out["tl"], out["tr"], out["br"], out["bl"]], dtype=np.float32)
    if len({tuple(p) for p in pts}) < 4:
        return None
    return out


def deskew(img):
    fids = find_fiducials(img)
    if fids is None:
        return None, None
    src = np.array([fids["tl"], fids["tr"], fids["br"], fids["bl"]], dtype=np.float32)
    dst = (
        np.array(
            [FID_CENTERS["tl"], FID_CENTERS["tr"], FID_CENTERS["br"], FID_CENTERS["bl"]], dtype=np.float32
        )
        * PPM
    )
    Hm = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img, Hm, (W, H), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255)), fids


def read_qr(canon):
    det = cv2.QRCodeDetector()
    # QR sits top-right; try the region first, then the whole page
    x0, y0 = int((210 - 16 - 17 - 4) * PPM), int((15 - 4) * PPM)
    roi = canon[y0 : y0 + int(27 * PPM), x0 : x0 + int(27 * PPM)]
    for im in (roi, canon):
        for scale in (1.0, 2.0):
            im2 = (
                cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC) if scale != 1 else im
            )
            s = det.detectAndDecode(im2)[0]
            if s:
                return s
    return None


# ------------------------------------------------------------------ crops
