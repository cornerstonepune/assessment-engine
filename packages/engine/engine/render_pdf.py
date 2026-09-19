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


def render(path, dpi: int = DPI):
    """One BGR image (OpenCV's own order) per page, top to bottom."""
    zoom = dpi / 72  # PDF units are 1/72 inch; pymupdf's Matrix scales by that ratio
    matrix = pymupdf.Matrix(zoom, zoom)
    with pymupdf.open(path) as doc:
        pages = []
        for page in doc:
            pix = page.get_pixmap(matrix=matrix, colorspace=pymupdf.csRGB)
            rgb = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
            pages.append(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    return pages
