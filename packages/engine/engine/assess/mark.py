"""Marking scaffold: photo -> deskew via fiducials -> QR -> crop every response cell by geometry -> read -> mark by lookup.

Digit reading is pluggable (`Reader`). The default uses tesseract in single-character mode, which is
adequate for printed digits (used by the synthetic round-trip test) and NOT adequate for children's
handwriting — that step is a vision model in the pilot. Everything else in this file is the part that
has to be right regardless of which reader is used.
"""
import json, subprocess, random
from pathlib import Path
import numpy as np
import cv2

PPM = 8                      # pixels per mm in the canonical deskewed image
W, H = 210 * PPM, 297 * PPM
FID_MM = 7.0; FID_OFF = 6.0  # fiducial size and offset from page edge (render.py CSS)
FID_CENTERS = {"tl": (FID_OFF + FID_MM/2, FID_OFF + FID_MM/2), "tr": (210 - FID_OFF - FID_MM/2, FID_OFF + FID_MM/2),
               "bl": (FID_OFF + FID_MM/2, 297 - FID_OFF - FID_MM/2), "br": (210 - FID_OFF - FID_MM/2, 297 - FID_OFF - FID_MM/2)}

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
        if a < page_area * 1.5e-4 or a > page_area * 4e-3:      # a 7mm square on A4 is ~0.08% of the page
            continue
        x, y, bw_, bh_ = cv2.boundingRect(c)
        ar = bw_ / float(bh_)
        fill = a / float(bw_ * bh_)
        if 0.6 < ar < 1.6 and fill > 0.75 and g[y:y + bh_, x:x + bw_].mean() < 90:
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
    dst = np.array([FID_CENTERS["tl"], FID_CENTERS["tr"], FID_CENTERS["br"], FID_CENTERS["bl"]], dtype=np.float32) * PPM
    Hm = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(img, Hm, (W, H), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255)), fids

def read_qr(canon):
    det = cv2.QRCodeDetector()
    # QR sits top-right; try the region first, then the whole page
    x0, y0 = int((210 - 16 - 17 - 4) * PPM), int((15 - 4) * PPM)
    roi = canon[y0:y0 + int(27 * PPM), x0:x0 + int(27 * PPM)]
    for im in (roi, canon):
        for scale in (1.0, 2.0):
            im2 = cv2.resize(im, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC) if scale != 1 else im
            s, pts, _ = det.detectAndDecode(im2)
            if s:
                return s
    return None

# ------------------------------------------------------------------ crops

def crop_cells(canon, key, page):
    """Yield (geometry_record, crop_bgr) for every response cell on this page."""
    for g in key["geometry"]:
        if g["page"] != page:
            continue
        pad = 0.6  # mm inside the border so the printed box line is excluded
        x0, y0 = int((g["x"] + pad) * PPM), int((g["y"] + pad) * PPM)
        x1, y1 = int((g["x"] + g["w"] - pad) * PPM), int((g["y"] + g["h"] - pad) * PPM)
        yield g, canon[y0:y1, x0:x1]

# ------------------------------------------------------------------ readers

class Reader:
    def read_digit(self, crop):
        """-> (char or '' for blank, confidence 0..1)"""
        raise NotImplementedError
    def is_ticked(self, crop):
        g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        return (g < 128).mean() > 0.12

class TesseractReader(Reader):
    """Printed-digit reader for the synthetic test. Not for handwriting."""
    def read_digit(self, crop):
        g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        ink = (g < 128).mean()
        if ink < 0.02:
            return "", 0.95
        g = cv2.resize(g, None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
        _, g = cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        g = cv2.copyMakeBorder(g, 40, 40, 40, 40, cv2.BORDER_CONSTANT, value=255)
        tmp = Path("/tmp/_cell.png"); cv2.imwrite(str(tmp), g)
        for psm in ("10", "13", "8"):
            r = subprocess.run(["tesseract", str(tmp), "stdout", "--psm", psm, "-c", "tessedit_char_whitelist=0123456789"],
                               capture_output=True, text=True)
            s = r.stdout.strip()
            if s and s[0].isdigit():
                return s[0], 0.8
        return "?", 0.2

# ------------------------------------------------------------------ marking

def mark_sheet(canon_pages, key, reader):
    """canon_pages: {page_no: canonical image}. Returns per-response results."""
    by_resp = {}
    for page, canon in canon_pages.items():
        for g, crop in crop_cells(canon, key, page):
            by_resp.setdefault((g["item"], g["resp"]), []).append((g, crop))
    items = {i["item_id"]: i for i in key["items"]}
    results = []
    for (iid, rid), cells in by_resp.items():
        it = items[iid]; r = next(x for x in it["responses"] if x["rid"] == rid)
        cells.sort(key=lambda c: c[0]["k"])
        if r["kind"] == "digits":
            chars, confs = [], []
            for g, crop in cells:
                ch, cf = reader.read_digit(crop); chars.append(ch); confs.append(cf)
            raw = "".join(chars).strip()
            conf = min(confs) if confs else 0
            if raw == "":
                status, tags = "blank", []
            elif "?" in raw or not raw.isdigit():
                status, tags = "unreadable", []
            else:
                v = int(raw); ans = int(r["answer"])
                if v == ans or (r.get("tolerance") and abs(v - ans) <= r["tolerance"]):
                    status, tags = "correct", []
                else:
                    tags = [code for code, wrong in r["misconceptions"].items() if int(wrong) == v]
                    status = "wrong"
            results.append(dict(item=iid, n=it["n"], rung=it["rung"], resp=rid, kind="digits", answer=r["answer"], read=raw,
                                confidence=round(conf, 2), status=status, misconceptions=tags or (["unclassified"] if status == "wrong" else [])))
        elif r["kind"] == "tick":
            ticked = [g["opt"] for g, crop in cells if reader.is_ticked(crop)]
            status = "blank" if not ticked else ("correct" if ticked == [r["answer"]] else "wrong")
            results.append(dict(item=iid, n=it["n"], rung=it["rung"], resp=rid, kind="tick", answer=r["answer"], read=ticked, confidence=0.9, status=status, misconceptions=[]))
        else:
            g, crop = cells[0]
            ink = (cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) < 128).mean()
            results.append(dict(item=iid, n=it["n"], rung=it["rung"], resp=rid, kind="text", answer=None, read=None, confidence=0,
                                status="blank" if ink < 0.005 else "needs_teacher", misconceptions=[], rubric=r.get("rubric")))
    results.sort(key=lambda x: (x["n"], x["resp"]))
    return results

# ------------------------------------------------------------------ synthetic round-trip

def simulate_photo(page_png, rng, out_path):
    """Perspective-warp a rendered page onto a 'desk', add blur and uneven light, like a phone photo."""
    img = cv2.imread(str(page_png))
    h, w = img.shape[:2]
    desk = np.full((int(h * 1.3), int(w * 1.3), 3), (120, 140, 160), np.uint8)
    noise = rng.integers(-12, 12, desk.shape, dtype=np.int16); desk = np.clip(desk.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    # destination quad: page placed with random tilt
    ox, oy = int(w * 0.12), int(h * 0.1)
    j = lambda s: rng.integers(-int(s), int(s))
    dst = np.array([[ox + j(w * .06), oy + j(h * .05)], [ox + w + j(w * .06), oy + j(h * .05)],
                    [ox + w + j(w * .06), oy + h + j(h * .05)], [ox + j(w * .06), oy + h + j(h * .05)]], dtype=np.float32)
    src = np.array([[0, 0], [w, 0], [w, h], [0, h]], dtype=np.float32)
    Hm = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(img, Hm, (desk.shape[1], desk.shape[0]), borderValue=(0, 0, 0))
    mask = cv2.warpPerspective(np.full((h, w), 255, np.uint8), Hm, (desk.shape[1], desk.shape[0]))
    out = desk.copy(); out[mask > 0] = warped[mask > 0]
    # uneven light + blur
    yy, xx = np.mgrid[0:out.shape[0], 0:out.shape[1]]
    grad = (0.82 + 0.18 * (xx / out.shape[1]) * (yy / out.shape[0]))[..., None]
    out = np.clip(out * grad, 0, 255).astype(np.uint8)
    out = cv2.GaussianBlur(out, (3, 3), 0)
    cv2.imwrite(str(out_path), out)
    return out

def write_fake_answers(page_png, key, page, rng, out_path, error_rate=0.25):
    """Type answers into the cells of a rendered page (printed digits — a stand-in for handwriting),
    sometimes writing a misconception answer instead, so the marker has something to diagnose."""
    img = cv2.imread(str(page_png)); h, w = img.shape[:2]
    ppm = w / 210.0
    truth = {}
    items = {i["item_id"]: i for i in key["items"]}
    resp_cells = {}
    for g in key["geometry"]:
        if g["page"] == page:
            resp_cells.setdefault((g["item"], g["resp"]), []).append(g)
    for (iid, rid), cells in resp_cells.items():
        r = next(x for x in items[iid]["responses"] if x["rid"] == rid)
        cells.sort(key=lambda c: c["k"])
        if r["kind"] == "digits":
            val = r["answer"]; chosen = None
            if r["misconceptions"] and rng.random() < error_rate:
                chosen = rng.choice(list(r["misconceptions"].keys())); val = str(r["misconceptions"][chosen])
            if rng.random() < 0.06:
                val = ""; chosen = "blank"
            truth[(iid, rid)] = (val, chosen)
            s = val.rjust(len(cells))
            for g, ch in zip(cells, s):
                if ch.strip():
                    cx, cy = (g["x"] + g["w"] / 2) * ppm, (g["y"] + g["h"] / 2) * ppm
                    cv2.putText(img, ch, (int(cx - 0.32 * g["w"] * ppm), int(cy + 0.33 * g["h"] * ppm)), cv2.FONT_HERSHEY_SIMPLEX, g["h"] * ppm / 32, (20, 20, 40), 2, cv2.LINE_AA)
        elif r["kind"] == "tick":
            pick = r["answer"] if rng.random() > error_rate else rng.choice(r["options"])
            truth[(iid, rid)] = (pick, None)
            for g in cells:
                if g["opt"] == pick:
                    x0, y0 = int((g["x"] + 1) * ppm), int((g["y"] + 1) * ppm); x1, y1 = int((g["x"] + g["w"] - 1) * ppm), int((g["y"] + g["h"] - 1) * ppm)
                    cv2.line(img, (x0, y1), (x1, y0), (20, 20, 40), 2); cv2.line(img, (x0, y0), (x1, y1), (20, 20, 40), 2)
    cv2.imwrite(str(out_path), img)
    return truth

def roundtrip(sheet_dir, sheet_id, seed=1, workdir="out/_roundtrip"):
    """Render page images -> fake answers -> fake photo -> deskew -> QR -> crop -> read -> mark. Returns a report."""
    sheet_dir, workdir = Path(sheet_dir), Path(workdir); workdir.mkdir(parents=True, exist_ok=True)
    key = json.loads((sheet_dir / f"{sheet_id}.key.json").read_text())
    rng = np.random.default_rng(seed); prng = random.Random(seed)
    subprocess.run(["pdftoppm", "-r", "200", "-png", str(sheet_dir / f"{sheet_id}.pdf"), str(workdir / sheet_id)], check=True)
    pages = sorted(p for p in workdir.glob(f"{sheet_id}-*.png") if p.stem.split("-")[-1].isdigit())
    canon_pages, truth, qr_ok = {}, {}, []
    class R(random.Random): pass
    for p, png in enumerate(pages, start=1):
        filled = workdir / f"{sheet_id}-p{p}-filled.png"
        t = write_fake_answers(png, key, p, prng, filled)
        truth.update(t)
        photo = workdir / f"{sheet_id}-p{p}-photo.jpg"
        simulate_photo(filled, rng, photo)
        img = cv2.imread(str(photo))
        canon, fids = deskew(img)
        if canon is None:
            return dict(ok=False, error=f"fiducials not found on page {p}")
        cv2.imwrite(str(workdir / f"{sheet_id}-p{p}-deskewed.png"), canon)
        qr = read_qr(canon); qr_ok.append(qr == sheet_id)
        canon_pages[p] = canon
    results = mark_sheet(canon_pages, key, TesseractReader())
    # geometry check independent of the reader: does each digit cell contain ink exactly when a digit was written there?
    ink_ok = ink_n = 0
    for p, canon in canon_pages.items():
        for g, crop in crop_cells(canon, key, p):
            if g["kind"] != "digit": continue
            tv = truth.get((g["item"], g["resp"]))
            if tv is None: continue
            written = tv[0]
            ncells = sum(1 for x in key["geometry"] if x["item"] == g["item"] and x["resp"] == g["resp"] and x["kind"] == "digit")
            s_ = written.rjust(ncells)
            expect_ink = bool(s_[g["k"]].strip()) if g["k"] < len(s_) else False
            has_ink = (cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) < 128).mean() > 0.02
            ink_n += 1; ink_ok += (expect_ink == has_ink)
    # compare with truth
    agree = total = 0; diag_hits = diag_total = 0
    for r in results:
        tv = truth.get((r["item"], r["resp"]))
        if tv is None or r["kind"] == "text":
            continue
        total += 1
        written, chosen = tv
        if r["kind"] == "digits":
            expected = "blank" if written == "" else ("correct" if int(written) == int(r["answer"]) or (r.get("tolerance") and abs(int(written) - int(r["answer"])) <= r["tolerance"]) else "wrong")
            agree += (r["status"] == expected)
            if chosen and chosen != "blank":
                diag_total += 1; diag_hits += (chosen in r["misconceptions"])
        else:
            expected = "correct" if written == r["answer"] else "wrong"
            agree += (r["status"] == expected)
    return dict(ok=True, sheet_id=sheet_id, pages=len(pages), qr_decoded=qr_ok, responses_scored=total,
                cell_geometry_agreement=round(ink_ok / ink_n, 3) if ink_n else None,
                status_agreement=round(agree / total, 3) if total else None,
                planted_misconceptions=diag_total, misconception_recovered=round(diag_hits / diag_total, 3) if diag_total else None,
                results=results)
