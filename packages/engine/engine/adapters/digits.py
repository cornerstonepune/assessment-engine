"""The digit reader: what reads a child's digits in the answer boxes of a paper this system printed (ADR 0035).

PaddleOCR, off the shelf (its PP-OCRv6 detector and recogniser, English), handed each answer's run of boxes as
the phone photographed it — printed lines left in. Measured on 133 answers of the real 24 Sep scan against
Textract on the same crops: 85% read exactly against 70%, and at the floor it stands behind 102 with one wrong.
Taking the print out first cost every reader more than it saved: the pencil lying on a line went with it
(an 8 read 3, a 3 read 2). Textract stays for what it reads well: printed codes and the old papers (`ocr`).

It is not a service, but it is kept apart the way one is. Loaded, it holds ~600 MB the operating system cannot
page out, on a server of 1.9 GB with no swap beside an engine of ~250 MB. So it runs in a process of its own,
started by the first answer to read and ended after IDLE seconds with nothing to read: the memory is back once a
scan is read, and if the machine runs out it is the reader the kernel stops, not the engine — the scan's run
then says so in words (`ReaderStopped`), never a blank.
"""

import multiprocessing
import threading
from concurrent.futures import ProcessPoolExecutor
from concurrent.futures.process import BrokenProcessPool

import cv2
import numpy as np

IDLE = 60.0  # seconds with nothing to read before the reader's process ends and gives its memory back

_lock = threading.Lock()
_pool = None
_timer = None
_busy = 0
_model = None  # in the reader's own process only


class ReaderStopped(RuntimeError):
    pass


def settings(conn=None):
    """{"min_confidence": the floor on the engine's 0-100 scale}: `read.auto_confirm_above`, the row that has
    always meant "a cell read above this skips the confirm queue", 0.90 until a person changes it."""
    value = 0.90
    if conn is not None:
        row = conn.execute("select value from threshold where key = 'read.auto_confirm_above'").fetchone()
        value = float(row["value"]) if row else value
    return {"min_confidence": round(100 * value, 1)}


def _load():
    global _model
    from paddleocr import PaddleOCR  # here, never in the engine's own process

    # oneDNN off: Paddle 3.3's oneDNN path fails on CPU ("ConvertPirAttribute2RuntimeAttribute not support")
    _model = PaddleOCR(
        lang="en",
        use_doc_orientation_classify=False,
        use_doc_unwarping=False,
        use_textline_orientation=False,
        enable_mkldnn=False,
    )


def _words(image_bytes):
    """In the reader's process: one image → words in the shape `ocr.read` gives (x, w fractions; 0-100)."""
    img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
    h, w = img.shape[:2]
    r = _model.predict(img)[0]
    out = []
    for text, score, poly in zip(r["rec_texts"], r["rec_scores"], r["rec_polys"]):
        xs, ys = [float(p[0]) for p in poly], [float(p[1]) for p in poly]
        out.append(
            {
                "text": text,
                "confidence": round(100 * float(score), 2),
                "hand": True,  # nothing printed reaches it but the box lines, which it does not read as text
                "x": min(xs) / w,
                "y": min(ys) / h,
                "w": (max(xs) - min(xs)) / w,
                "h": (max(ys) - min(ys)) / h,
            }
        )
    return out


def _submit(image_bytes):
    global _pool, _busy
    with _lock:
        if _pool is None:
            ctx = multiprocessing.get_context(
                "spawn"
            )  # a clean process: nothing of the engine's is copied in
            _pool = ProcessPoolExecutor(max_workers=1, mp_context=ctx, initializer=_load)
        _busy += 1
        pool = _pool
    try:
        return pool.submit(_words, image_bytes).result()
    finally:
        with _lock:
            _busy -= 1
        _idle_later()


def _idle_later():
    global _timer
    with _lock:
        if _timer is not None:
            _timer.cancel()
        _timer = threading.Timer(IDLE, _idle)
        _timer.daemon = True
        _timer.start()


def _idle():
    with _lock:
        if _busy:
            return
    stop()


def _forget():
    """The process died (killed for memory, most likely): drop it, so the next answer starts a fresh one."""
    global _pool
    with _lock:
        pool, _pool = _pool, None
    if pool is not None:
        pool.shutdown(wait=False, cancel_futures=True)


def stop():
    """End the reader's process now and give its memory back."""
    global _pool, _timer
    with _lock:
        pool, _pool = _pool, None
        timer, _timer = _timer, None
    if timer is not None:
        timer.cancel()
    if pool is not None:
        pool.shutdown(wait=True, cancel_futures=True)


def workers():
    """The reader's process ids, while it is running."""
    with _lock:
        return list(_pool._processes) if _pool is not None else []


def read(image_bytes, cli=None):
    """An answer's run of boxes (jpeg/png bytes) → {"lines": [], "words": [...]}, as `ocr.read` gives it.
    `cli` is accepted and unused, so either reader can be called the same way."""
    for _ in range(2):
        try:
            return {"lines": [], "words": _submit(image_bytes)}
        except BrokenProcessPool:
            _forget()
    raise ReaderStopped(
        "the digit reader stopped twice while reading (most likely the server ran out of memory); read it again"
    )
