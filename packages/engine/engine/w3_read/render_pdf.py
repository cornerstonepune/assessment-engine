"""A PDF's pages as images, in memory. Replaces the earlier `pdftoppm` subprocess (poppler),
which failed transiently on about a third of a real import batch — no `python` traceback, just a
non-zero exit from a spawned process under load, retried by re-running the whole import by hand.
Rendering in-process removes the subprocess entirely, so there is nothing left to be flaky. No
temp directory and no system binary: a legacy import is run from more than one machine, and this
needs nothing beyond the Python dependency."""

import cv2
import numpy as np
import pymupdf

DPI = 150  # legible handwriting, ~1 MB a page
# 150 is MEASURED, not a default anyone liked the look of. These scans hold more than the engine
# reads: a scanner writes a 2331 x 3165 photograph into an A4-sized page, which is 282 dpi, and
# drawing that page at 150 discards 47% of the pixels the file already held. Reading it larger was
# tried on the 82-response gold set and it buys coverage with silence, which is the one trade
# rule 5 forbids:
#
#     150 dpi   79.3% exact   1 silently wrong     <- in service
#     200 dpi   84.2% exact   5 silently wrong
#     native    76.8% exact   1 silently wrong     (198-282 dpi, per file)
#
# More pixels find more answers AND stand behind more of the wrong ones. Do not raise this without
# putting the silent-error count beside it. The second look (`ocr.reread_dpi`) is a different
# thing and is allowed to go large, because it re-reads ONE answer that is already flagged and
# nothing it produces is believed unless it clears the floor on its own.

# One A4 page at the resolution a doubtful answer is looked at again in (500 dpi). A ceiling for
# THAT render only — `render(path)` with no cap draws a page exactly as it always has.
#
# The cap exists because a WhatsApp "scan" is a photograph wrapped in a PDF: its page box is
# already 2635 x 3906 points — 36 x 54 inches — so 500 dpi asks MuPDF for an 18299 x 27125 image
# and it refuses outright with `FzErrorLimit: Overly large image`. Such a page has no resolution to
# spare in any case, being the photograph's own pixels already, so it clamps back to DPI and the
# second look earns its keep there by cropping rather than by re-rendering.
MAX_PIXELS = 25_000_000


def render(path, dpi: int = DPI, max_pixels: int = 0, long_side: int = 0):
    """One BGR image (OpenCV's own order) per page, top to bottom.

    `max_pixels` caps how large a page may be drawn, and NEVER below `DPI`: a render that came back
    smaller than the one the page was first read at would be a second look with fewer pixels than
    the first, which is how "Answer=43" came back as "4".

    `long_side` is for SHOWING a page, never for reading one: no side longer than that, and never
    larger than `dpi` would draw it.
    """
    floor = DPI / 72
    with pymupdf.open(path) as doc:
        pages = []
        for page in doc:
            # PDF units are 1/72 inch; pymupdf's Matrix scales by that ratio
            zoom = dpi / 72  # PDF units are 1/72 inch; pymupdf's Matrix scales by that ratio
            wanted = (page.rect.width * zoom) * (page.rect.height * zoom)
            if max_pixels and wanted > max_pixels:
                zoom = max(floor, zoom * (max_pixels / wanted) ** 0.5)
            if long_side:
                zoom = min(zoom, long_side / max(page.rect.width, page.rect.height))
            matrix = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix, colorspace=pymupdf.csRGB)
            rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            pages.append(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    _let_go()
    return pages


def _let_go():
    """Empty MuPDF's own store of the images it decoded. Once a page is our array it is never asked for again,
    but the store kept each one, up to 256 MB: reading the 24 Sep file held 500 MB where a page at a time needs
    230, beside a digit reader, on a server of 1.9 GB with no swap (2026-09-26)."""
    pymupdf.TOOLS.store_shrink(100)


# A phone's "scan" is a photograph wrapped in a PDF page: 2000-3000 pixels across, placed on an A4 page with
# white bands where the shapes differ. Drawing that page at 150 dpi throws half the photograph away — the
# QR on it went from about 8 pixels a module to 4, and 13 of 16 codes on the 2026-09-24 file stopped
# reading. The photograph itself is what a code or a box is read from.
def photo(path, page_no=1):
    """One page as the pixels it holds: the photograph inside a scan's PDF page, at its own size, with
    where it sits on the page as (left, top, right, bottom) fractions; a drawn page, or an image file, whole."""
    path = str(path)
    if path.lower().endswith((".jpg", ".jpeg", ".png")):
        return cv2.imread(path), (0.0, 0.0, 1.0, 1.0)
    with pymupdf.open(path) as doc:
        page = doc[page_no - 1]
        images = page.get_images()
        rects = page.get_image_rects(images[0][0]) if len(images) == 1 else []
        if len(rects) == 1 and abs(rects[0]) >= 0.8 * abs(page.rect):
            pix = pymupdf.Pixmap(doc, images[0][0])
            if pix.n - pix.alpha != 3 or pix.alpha:
                pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
            rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            r, p = rects[0], page.rect
            frame = (r.x0 / p.width, r.y0 / p.height, r.x1 / p.width, r.y1 / p.height)
            out = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), frame
            _let_go()
            return out
        zoom = 254 / 72  # a drawn page at a photograph's own resolution, near enough
        pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), colorspace=pymupdf.csRGB)
        rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        out = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), (0.0, 0.0, 1.0, 1.0)
        _let_go()
        return out


def photos(path):
    """Every page of a file as `photo` gives it, in order, one at a time."""
    if str(path).lower().endswith((".jpg", ".jpeg", ".png")):
        yield photo(path)[0]
        return
    with pymupdf.open(str(path)) as doc:
        n = len(doc)
    for i in range(1, n + 1):
        yield photo(path, i)[0]
