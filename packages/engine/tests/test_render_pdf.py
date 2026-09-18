"""A PDF's pages become images in-process — see engine/render_pdf.py for why the subprocess it
replaces (pdftoppm) is gone rather than kept as a fallback."""
import numpy as np
import pymupdf

from engine import render_pdf


def test_renders_one_bgr_image_per_page(tmp_path):
    doc = pymupdf.open()
    doc.new_page(width=200, height=100)
    doc.new_page(width=200, height=100)
    path = tmp_path / "two_pages.pdf"
    doc.save(path)
    doc.close()

    pages = render_pdf.render(path)

    assert len(pages) == 2
    assert all(isinstance(p, np.ndarray) and p.shape == (209, 417, 3) for p in pages)


def test_a_lower_dpi_gives_a_smaller_image(tmp_path):
    doc = pymupdf.open()
    doc.new_page(width=72, height=72)  # exactly one inch
    path = tmp_path / "one_inch.pdf"
    doc.save(path)
    doc.close()

    assert render_pdf.render(path, dpi=100)[0].shape == (100, 100, 3)
