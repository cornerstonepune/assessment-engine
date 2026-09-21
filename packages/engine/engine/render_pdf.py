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


def render(path, dpi: int = DPI, max_pixels: int = 0):
    """One BGR image (OpenCV's own order) per page, top to bottom.

    `max_pixels` caps how large a page may be drawn, and NEVER below `DPI`: a render that came back
    smaller than the one the page was first read at would be a second look with fewer pixels than
    the first, which is how "Answer=43" came back as "4".
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
            matrix = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=matrix, colorspace=pymupdf.csRGB)
            rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            pages.append(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    return pages
