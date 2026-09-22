"""A PDF's pages become images in-process — see engine/render_pdf.py for why the subprocess it
replaces (pdftoppm) is gone rather than kept as a fallback."""

import numpy as np
import pymupdf

from engine.w3_read import render_pdf


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


def test_a_long_side_draws_an_oversized_page_small_and_leaves_a4_as_it_is_read(tmp_path):
    """A WhatsApp "scan" is a photograph in a 36 x 54 inch page: 5490 x 8138 at 150 dpi. Drawn that
    large and then shrunk for a screen, its first view took 5 s on the server; drawn at the size it
    is shown, there is nothing to shrink."""
    doc = pymupdf.open()
    doc.new_page(width=2635, height=3906)
    doc.new_page(width=595, height=842)  # A4
    path = tmp_path / "whatsapp_then_a4.pdf"
    doc.save(path)
    doc.close()

    big, a4 = render_pdf.render(path, long_side=2400)

    assert max(big.shape[:2]) == 2400
    assert a4.shape[:2] == (1755, 1240)  # 150 dpi, the reader's own size: a cap never enlarges
