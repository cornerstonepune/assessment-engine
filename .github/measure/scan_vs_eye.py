"""What the engine read on the newest scan, answer by answer, to grade it against a person's reading by page (read
only). Pages, codes, questions and reads only: never a child's name or an image (rule 6). Each answer carries its
question number on the sheet (`raw_read.slot`) and the paper's page; each copy, the reader's note for each page and
how much of each printed page the box reader found on the photograph (`lineup`), so a page read by its words instead
of its boxes says why."""

import json
from pathlib import Path

import numpy as np

import numpy as np

from engine.core import db
from engine.w3_read import lineup, render_pdf


def _why(scan, pdf, page):
    """Which first map fails on a page, and on what: ORB's inliers, SIFT's matches, the photograph's greys, and the
    tiles found with the photograph turned half round."""
    import cv2

    from engine.w3_read import stencil

    img, _ = render_pdf.photo(scan, page)
    printed = lineup._printed(str(pdf), page)
    small, s = lineup._grey(img, lineup.SIDE)
    Hm, inl = stencil.homography(small, printed[0])
    orb = "none" if Hm is None else ("plausible" if stencil.plausible(Hm, small.shape, printed[0].shape) else "implausible")
    tiny, _ = lineup._grey(img, lineup.SIFT_SIDE)
    k1, d1 = lineup._sift.detectAndCompute(tiny, stencil.NO_MASK)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    turned = cv2.rotate(img, cv2.ROTATE_180)
    sm2, s2 = lineup._grey(turned, lineup.SIDE)
    maps = [m for m in (lineup._by_orb(sm2, s2, printed), lineup._by_sift(turned, printed)) if m is not None]
    found180 = max((len(lineup._found(sm2, s2, m, printed)) for m in maps), default=0)
    return {"orb": orb, "orb_inliers": inl, "sift_keys": len(k1), "sift_ref_keys": len(printed[2][2]),
            "by_sift": lineup._by_sift(img, printed) is not None, "grey_mean": round(float(g.mean()), 1),
            "grey_p5_p95": [int(v) for v in np.percentile(g, [5, 95])], "dtype": str(img.dtype), "shape": img.shape,
            "found_turned_180": found180}


def _lines_up(scan, pdf, page):
    """(tiles found, tiles the printed page has, the share `lineup.line_up` needs) for one photographed page."""
    img, _ = render_pdf.photo(scan, page)
    printed = lineup._printed(str(pdf), page)
    small, s = lineup._grey(img, lineup.SIDE)
    maps = [m for m in (lineup._by_orb(small, s, printed), lineup._by_sift(img, printed)) if m is not None]
    found = max((len(lineup._found(small, s, m, printed)) for m in maps), default=0)
    return found, len(printed[4]), lineup.ENOUGH


with db.connect() as c:
    run = c.execute(
        "select id, trigger, status, started_at, finished_at, result from flow_run"
        " where flow = 'read-scan' order by started_at desc limit 1"
    ).fetchone()
    print("-- run", run["status"], run["started_at"], run["finished_at"], "pages", (run["result"] or {}).get("pages"))
    for cp in (run["result"] or {}).get("copies", []):
        meta = {k: cp.get(k) for k in ("copy", "pages", "code", "answers", "skipped", "why", "lacks", "no_code", "missing", "notes")}
        print("== copy", json.dumps(meta))
        if not cp.get("capture_id"):
            continue
        cap = c.execute(
            "select c.path, si.pdf_path from capture c left join sheet_instance si on si.id = c.sheet_instance_id"
            " where c.id = %s",
            (cp["capture_id"],),
        ).fetchone()
        pdf = cap and cap["pdf_path"]
        scan = cap and cap["path"] and Path(cap["path"]).expanduser()
        print("  printed pdf kept:", bool(pdf and Path(pdf).exists()), "| scan kept:", bool(scan and scan.exists()))
        if pdf and Path(pdf).exists() and scan and scan.exists():
            for p in range(1, 3):
                try:
                    img, _ = render_pdf.photo(scan, p)
                    print("  lineup page", p, "photo px", img.shape[:2], "found / tiles / needs", _lines_up(scan, pdf, p))
                    if cp["copy"] in (1, 4):
                        print("  why page", p, json.dumps(_why(scan, pdf, p), default=str))
                except Exception as e:  # noqa: BLE001 — a measure says what failed and goes on
                    print("  lineup page", p, "failed:", type(e).__name__)
        rows = []
        for r in c.execute(
            "select r.rid, r.status, r.state, r.read_confidence, r.working_shown, r.raw_read,"
            " a.standing from item_result r left join answer_standing a on a.item_result_id = r.id"
            " where r.capture_id = %s",
            (cp["capture_id"],),
        ):
            raw = r["raw_read"] or ""
            try:
                j = json.loads(raw)
            except (ValueError, TypeError):
                j = {}
            slot = str(j.get("slot") or "?")
            keep = {k: j.get(k) for k in ("read", "value", "guess", "box", "why") if j.get(k) not in (None, "")}
            rows.append((float(slot.split(".")[0]) if slot.split(".")[0].isdigit() else 99.0, slot, j.get("page"), r, keep))
        for _, slot, page, r, keep in sorted(rows, key=lambda t: (t[0], t[1])):
            print("  Q" + slot, "p", page, r["status"], r["state"], r["standing"], r["read_confidence"], r["working_shown"],
                  json.dumps(keep, default=str))
_ = np  # the photograph arrays lineup returns are numpy's
