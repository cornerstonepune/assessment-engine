"""Which printed page each photograph of the newest scan is (read only; CK2). Counts and numbers only: never a child's
name or an image (rule 6). Per copy and per photograph (a page of the copy's own cut file): the tiles of print found
when it is laid on each printed page (`lineup`), `boxes._fits` against each, the page the engine took it for (the stored
`paper_pages` order, i.e. its position in the file) and the page it fits best; whether the printed page names its own
number in words, so a reader knows what the print can say about it."""

import json
import re
from pathlib import Path

import pymupdf

from engine.core import db
from engine.w3_read import boxes, lineup, render_pdf


def _tiles(img, pdf, page):
    """(tiles found, tiles the printed page has) of one photograph laid on one printed page."""
    printed = lineup._printed(str(pdf), page)
    small, s = lineup._grey(img, lineup.SIDE)
    maps = [m for m in (lineup._by_orb(small, s, printed), lineup._by_sift(img, printed)) if m is not None]
    found = max((len(lineup._found(small, s, m, printed)) for m in maps if lineup._holds_paper(m, img.shape)), default=0)
    return found, len(printed[4])


def _says_its_page(pdf):
    """Whether any printed page has its own number in words ('Page 2', '2 of 2') apart from the questions'."""
    with pymupdf.open(str(pdf)) as doc:
        return [bool(re.search(r"\b[Pp]age\s*\d|\b\d\s*(of|/)\s*\d\b", p.get_text())) for p in doc]


with db.connect() as c:
    run = c.execute(
        "select result from flow_run where flow = 'read-scan' order by started_at desc limit 1"
    ).fetchone()
    for cp in (run["result"] or {}).get("copies", []):
        if not cp.get("capture_id"):
            continue
        cap = c.execute(
            "select c.path, si.pdf_path from capture c left join sheet_instance si on si.id = c.sheet_instance_id"
            " where c.id = %s",
            (cp["capture_id"],),
        ).fetchone()
        pdf = cap and cap["pdf_path"]
        cut = cap and cap["path"] and Path(cap["path"]).expanduser()
        if not (pdf and Path(pdf).exists() and cut and cut.exists()):
            print("== copy", cp["copy"], "files not kept")
            continue
        n = len(pymupdf.open(str(pdf)))
        own = boxes._own_print(pdf)
        print("== copy", cp["copy"], "file pages", cp.get("pages"), "paper pages", n, "printed page says its number:",
              _says_its_page(pdf))
        for k, img in enumerate(render_pdf.photos(cut), 1):
            tiles = {p: _tiles(img, pdf, p) for p in range(1, n + 1)}
            fits = {p: round(boxes._fits(img, pdf, p, own), 3) for p in range(1, n + 1)}
            best = max(fits, key=fits.get)
            print(f"  photo {k}: tiles found/of {json.dumps(tiles)} fits {json.dumps(fits)} fits best page {best}"
                  f" | engine took it for page {k}")
