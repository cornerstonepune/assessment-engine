"""The digit reader (ADR 0035, `adapters/digits.py`): PaddleOCR off the shelf, in a process of its own that lives
only while there is reading to do. These tests run the real reader — the models download on first use."""

import os
import signal
import time
from concurrent.futures.process import BrokenProcessPool

import cv2
import numpy as np
import pytest

from engine.adapters import digits

BOX_W, BOX_H = 84, 100  # one answer box, drawn at the reader's 10 px a mm


def _boxes(text, cross=False):
    """A run of printed boxes as a phone photographs it — lines left in — with `text` written one digit a box.
    `cross`: every digit sits a third of a box to the right and hangs below, over the printed lines."""
    pad = 20
    img = np.full((BOX_H + 2 * pad, BOX_W * len(text) + 2 * pad, 3), 250, np.uint8)
    for k, d in enumerate(text):
        x0 = pad + k * BOX_W
        cv2.rectangle(img, (x0, pad), (x0 + BOX_W, pad + BOX_H), (30, 30, 30), 3)
        dx, dy = (BOX_W // 3, BOX_H // 4) if cross else (0, 0)
        cv2.putText(img, d, (x0 + 18 + dx, pad + 78 + dy), cv2.FONT_HERSHEY_SIMPLEX, 2.4, (60, 60, 60), 5)
    return cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])[1].tobytes()


def _said(page):
    return "".join(w["text"] for w in sorted(page["words"], key=lambda w: w["x"]))


@pytest.fixture(autouse=True)
def _stopped():
    yield
    digits.stop()


def test_digits_in_their_boxes_are_read_with_the_lines_left_in():
    page = digits.read(_boxes("1405"))
    assert _said(page) == "1405"
    for w in page["words"]:
        assert 0 <= w["x"] < w["x"] + w["w"] <= 1 and 0 < w["confidence"] <= 100 and w["hand"]


def test_a_digit_written_across_its_box_line_is_read_whole():
    # 24 Sep: an 8 touching its box's side, a 3 hanging below it — the print taken out took the pencil with it
    assert _said(digits.read(_boxes("838", cross=True))) == "838"


def test_the_reader_leaves_when_it_has_nothing_to_read(monkeypatch):
    monkeypatch.setattr(digits, "IDLE", 1.0)
    digits.read(_boxes("7"))
    pids = digits.workers()
    assert len(pids) == 1
    time.sleep(3)
    assert digits.workers() == []
    with pytest.raises(ProcessLookupError):
        os.kill(pids[0], 0)  # its memory is back: on the server the engine and the reader share 1.9 GB


def test_a_reader_killed_between_scans_is_started_again():
    digits.read(_boxes("5"))
    os.kill(digits.workers()[0], signal.SIGKILL)  # what the out-of-memory killer does to the largest process
    time.sleep(0.5)
    assert _said(digits.read(_boxes("29"))) == "29"


def test_a_reader_that_keeps_dying_says_so_in_words(monkeypatch):
    def dies(_image_bytes):
        raise BrokenProcessPool("killed")

    monkeypatch.setattr(digits, "_submit", dies)
    with pytest.raises(digits.ReaderStopped, match="stopped twice"):
        digits.read(_boxes("5"))


def test_the_floor_is_the_threshold_row_on_the_engines_scale():
    assert digits.settings(None) == {"min_confidence": 90.0}
