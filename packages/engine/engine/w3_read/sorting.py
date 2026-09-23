"""N8 — one scanned file of many children's papers, sorted by the QR code on each page.

A school scanner hands over one PDF for a whole class. Each page the engine printed carries its sheet's QR
(`CS` + 6 hex, `assemble._qr`), so the file sorts itself: every page is drawn, its QR is read — lined up by
the page's four corner marks first, exactly as marking does (`assess.mark`), else searched for on the page as
it came — and each code is looked up in `sheet_instance`, which says whose paper it is and what was printed.
Nothing is written: this says what is in the file before anything reads a child's answers from it.
"""

import re

import cv2

from engine.assess import mark
from engine.w3_read import render_pdf

OURS = re.compile(r"^CS[0-9A-F]{6}$")


def qr_of(img) -> str | None:
    """The QR code on one page, or None."""
    canon, _ = mark.deskew(img)
    if canon is not None and (code := mark.read_qr(canon)):
        return code
    det = cv2.QRCodeDetector()
    for scale in (1.0, 0.5, 2.0):
        im = img if scale == 1.0 else cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        code, _, _ = det.detectAndDecode(im)
        if code:
            return code
    return None


def group(codes: list[str | None]) -> list[dict]:
    """Pages in file order → papers: a run of pages with one code is one paper; a page with no code joins the
    paper before it, flagged, since a sheet's later pages carry the same code and a missing one is a bad scan."""
    out = []
    for n, code in enumerate(codes, 1):
        if code and out and out[-1]["qr"] == code:
            out[-1]["pages"].append(n)
        elif code or not out:
            out.append({"qr": code, "pages": [n], "unread": [] if code else [n]})
        else:
            out[-1]["pages"].append(n)
            out[-1]["unread"].append(n)
    return out


def sort_file(conn, path) -> list[dict]:
    """Each paper in the file: its pages, its QR, and whose paper the database says it is (None when no sheet
    has that code). Pages are drawn at the resolution the reader uses (`render_pdf.DPI`)."""
    papers = group([qr_of(img) for img in render_pdf.render(path)])
    codes = [p["qr"] for p in papers if p["qr"]]
    known = {
        r["qr_code"]: dict(r)
        for r in conn.execute(
            "select si.qr_code, si.kind, si.week, ch.band, ch.section, ch.roll_no, t.source,"
            "       coalesce(t.key ->> 'title', t.code, t.batch_id) as paper,"
            "       coalesce(array_length(t.item_ids, 1), 0) as questions,"
            "       (select count(*) from capture c where c.sheet_instance_id = si.id and c.superseded_by is null)"
            "         as captures"
            " from sheet_instance si join sheet_template t on t.id = si.sheet_template_id"
            " left join child ch on ch.id = si.child_id where si.qr_code = any(%s)",
            (codes,),
        )
    }
    for p in papers:
        p["ours"] = bool(p["qr"] and OURS.match(p["qr"]))
        p["sheet"] = known.get(p["qr"])
    return papers
