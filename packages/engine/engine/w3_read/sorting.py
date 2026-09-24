"""N8 — one scanned file of many children's papers, sorted by the QR code on each page.

A school scanner hands over one PDF for a whole class. Each page the engine printed carries a QR: a child's own
paper carries its sheet's (`CS` + 6 hex, `assemble._qr`), looked up in `sheet_instance` for whose paper it is; a
library worksheet carries the worksheet's code (`R8-H02`, `library.pdf`), the same on every child's copy, so its
pages are counted off in the worksheet's own length, and whose each copy is can only be read from the name
written on it. Every page is drawn and its QR read — lined up by the page's four corner marks first, exactly as
marking does (`assess.mark`), else searched for on the page as it came. Nothing is written: this says what is
in the file before anything reads a child's answers from it.
"""

import re

import cv2
import pymupdf

from engine.adapters import ocr
from engine.assess import mark
from engine.w3_read import render_pdf

OURS = re.compile(r"^CS[0-9A-F]{6}$")
WORKSHEET = re.compile(r"^[RMX]\d{1,2}-[EMHA]\d{2,3}$")  # the library's codes, as the website checks them


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


# Letters a reader mistakes for one another in a printed code (a scan's "CS56DB32" is read "CS560832"): folded alike
# on both sides, the printed code and a code this system printed still meet.
_FOLD = str.maketrans(
    {"O": "0", "Q": "0", "D": "0", "S": "5", "I": "1", "L": "1", "B": "8", "G": "6", "Z": "2"}
)
_SEEN = re.compile(r"C\s*[S5]\s*([0-9A-Z]{6})")


def printed_code(lines, known) -> str | None:
    """The code printed as words under a page's QR (`CS3DB381`), read from the page's text where the QR itself
    would not scan: the one code this system printed that a code on the page matches, allowing for the letters a
    reader mistakes (`_FOLD`). None when nothing matches, or two different printed codes do (a double scan)."""
    folded = {}
    for k in known:
        folded.setdefault(k[2:].translate(_FOLD), set()).add(k)
    found = set()
    for line in lines:
        for m in _SEEN.finditer(line.upper()):
            found |= folded.get(m.group(1).translate(_FOLD), set())
    return found.pop() if len(found) == 1 else None


def _text_of(img, cli):
    ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return [line["text"] for line in ocr.read(jpg.tobytes(), cli)["lines"]]


def group(codes: list[str | None], length=lambda code: 0) -> list[dict]:
    """Pages in file order → papers: a run of pages with one code is one paper; a page with no code joins the
    paper before it, flagged, since a sheet's later pages carry the same code and a missing one is a bad scan.
    `length(code)` is how many pages one copy has when every child's copy carries the same code (a library
    worksheet); such a run is cut into copies of that many pages."""
    out = []
    for n, code in enumerate(codes, 1):
        last = out[-1] if out else None
        full = last and length(last["qr"]) and len(last["pages"]) >= length(last["qr"])
        if code and last and last["qr"] == code and not full:
            last["pages"].append(n)
        elif code or not last or full:
            # a page with no code after a whole copy is taken for another copy of the same library worksheet —
            # never for another child's own paper, whose code is theirs alone
            guess = last and full and WORKSHEET.match(last["qr"] or "") and last["qr"]
            out.append({"qr": code or guess or None, "pages": [n], "unread": [] if code else [n]})
        else:
            last["pages"].append(n)
            last["unread"].append(n)
    # A page with no code read, after a copy already whole, was guessed above as a copy of the worksheet before
    # it. Where the copy after it is short by exactly those pages, they are its first pages: on 2026-09-23 page 27
    # was R5-H14's first page, and taken for another R2-E12 it would have been marked against R2-E12's questions.
    merged = []
    for p in out:
        prev = merged[-1] if merged else None
        need = p["qr"] and length(p["qr"])
        if (
            prev and need and prev["pages"] == prev["unread"] and prev["pages"][-1] + 1 == p["pages"][0]
            and len(prev["pages"]) + len(p["pages"]) == need
        ):  # fmt: skip
            merged[-1] = {
                "qr": p["qr"],
                "pages": prev["pages"] + p["pages"],
                "unread": prev["unread"] + p["unread"],
            }
        else:
            merged.append(p)
    return merged


def worksheets(conn, codes) -> dict:
    """{code: the library worksheet} for the codes that are one: its skill, level and questions."""
    return {
        r["code"]: dict(r)
        for r in conn.execute(
            "select t.code, coalesce(s.name, t.skill_set_code) as skill, t.difficulty as level, t.band,"
            "       coalesce(array_length(t.item_ids, 1), 0) as questions"
            " from sheet_template t left join skill_set s on s.tenant_id = t.tenant_id and s.code = t.skill_set_code"
            " where t.source = 'library' and t.code = any(%s)",
            (list(codes),),
        )
    }


def sort_file(conn, path, pages_of=None, read_text=None) -> list[dict]:
    """Each paper in the file: its pages, its QR, and whose paper the database says it is — a child's own sheet
    (`sheet`), a library worksheet (`worksheet`, whose copy it is being written on it, not in the code), or
    neither. Pages are drawn at the resolution the reader uses (`render_pdf.DPI`). `pages_of(code)` is a library
    worksheet's length in pages, by default its printed PDF's (`library.pdf`); a child's own paper is as long as
    it printed (`sheet_instance.key`). `read_text(img)` gives a page's lines of text, for a QR that will not scan."""
    images = render_pdf.render(path)
    codes = [qr_of(img) for img in images]
    if any(c is None for c in codes):
        # a QR the scan spoiled: the same code is printed beside it in words, read with the page's text
        mine = [
            r["qr_code"] for r in conn.execute("select qr_code from sheet_instance where qr_code like 'CS%%'")
        ]
        read_text = read_text or (lambda img, cli=ocr.client(): _text_of(img, cli))
        codes = [c or printed_code(read_text(img), mine) for c, img in zip(codes, images)]
    library = worksheets(conn, {c for c in codes if c and WORKSHEET.match(c)})
    if pages_of is None:
        from engine.w2_print import library as printed

        pages_of = lambda code: len(pymupdf.open(printed.pdf(conn, code)))  # noqa: E731
    length = {c: pages_of(c) for c in library}
    length |= {
        r["qr_code"]: r["pages"]
        for r in conn.execute(
            "select qr_code, (key ->> 'pages')::int as pages from sheet_instance"
            " where qr_code = any(%s) and key ? 'pages'",
            ([c for c in codes if c and OURS.match(c)],),
        )
    }
    papers = group(codes, lambda c: length.get(c, 0))
    codes = [p["qr"] for p in papers if p["qr"]]
    known = {
        r["qr_code"]: dict(r)
        for r in conn.execute(
            "select si.qr_code, si.kind, si.week, si.child_id, si.pdf_path, ch.band, ch.section, ch.roll_no, t.source, t.code,"
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
        p["ours"] = bool(p["qr"] and (OURS.match(p["qr"]) or p["qr"] in library))
        p["sheet"] = known.get(p["qr"])
        p["worksheet"] = library.get(p["qr"])
        p["length"] = length.get(p["qr"], 0)
    return papers
