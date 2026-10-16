"""L12a (goals/l12a-where-pencil-is-told-from-paper.yaml): where a pencil mark is told from the paper, measured.

16 Oct, Grade 3: roll 4 wrote 862 with its 6 in pencil so faint that its darkest 2% is 21% darker than the paper, and
the reader asks 28% (`boxes.dark`). "2 boxes hold ink but the reader saw 862": a right answer waited. The line is set
from what people settled, never from one answer (L12b). This measures it: on a paper as the engine prints one, then
on a copy read and settled as a school's is.
"""

import json
from pathlib import Path

import cv2
import pymupdf

from engine.adapters import digits, ocr
from engine.assess import geometry
from engine.w2_print import handout
from engine.w3_read import boxes, copies, ink_line, render_pdf, second_reader
from tests import rows, test_copies
from tests.test_boxes import FONT, SCALE, THICK, StandIn, _cells, _scanned, paper  # noqa: F401 (fixture)
from tests.test_copies import _child

conn, worksheet = test_copies.conn, test_copies.worksheet


def _pencil(img, cell, ch, grey):
    """One digit written into a box as `_write` does, in pencil of the grey given: 45 is a firm hand, 200 a faint one."""
    x, y, w, h = (cell[k] * boxes.PPM for k in ("x", "y", "w", "h"))
    (tw, th), _ = cv2.getTextSize(ch, FONT, SCALE, THICK)
    org = (int(x + (w - tw) / 2), int(y + (h + th) / 2))
    cv2.putText(img, ch, org, FONT, SCALE, (grey, grey, grey), THICK, cv2.LINE_AA)


def test_a_digit_in_faint_pencil_is_ink_at_a_fainter_line_and_an_empty_box_at_none(paper, tmp_path):  # noqa: F811
    pdf, key = paper
    img = render_pdf.render(pdf, dpi=boxes.PPM * 25.4)[0]
    runs, _ = _cells(key)
    three = [k for k, run in runs.items() if len(run) == 3]
    written, empty = three[0], three[1]
    for cell, ch, grey in zip(runs[written], "862", (45, 200, 45)):  # the 6 faint, as roll 4's was
        _pencil(img, cell, ch, grey)
    scan = _scanned(img, tmp_path / "faint.pdf")
    photo, _ = render_pdf.photo(scan, 1)

    got = ink_line.inked_at(
        photo, 1, pdf, key["geometry"], {"written": written, "empty": empty}, (0.72, 0.88)
    )
    assert got["written"] == {0.72: 2, 0.88: 3}, "the faint 6 is ink only at the fainter line"
    assert got["empty"] == {0.72: 0, 0.88: 0}, "a box left empty is ink at neither"


def test_the_reader_reads_at_the_line_its_row_holds_and_says_which(paper, conn, tmp_path):  # noqa: F811
    """L12b (goals/l12b-the-ink-line-is-a-row.yaml): the line is `read.ink_line`, measured on live; the box reader reads
    at the line its settings carry, and each reading says the line it was read at."""
    row = conn.execute("select value from threshold where key = 'read.ink_line'").fetchone()
    assert row and digits.settings(conn)["ink_line"] == float(row["value"]) == 0.76, (
        "measured on live, 2026-10-16"
    )
    pdf, key = paper
    img = render_pdf.render(pdf, dpi=boxes.PPM * 25.4)[0]
    runs, _ = _cells(key)
    written = next(k for k, run in runs.items() if len(run) == 3)
    for cell, ch, grey in zip(runs[written], "862", (45, 200, 45)):
        _pencil(img, cell, ch, grey)
    photo, frame = render_pdf.photo(_scanned(img, tmp_path / "faint.pdf"), 1)
    wanted = {"q": written}
    for line, inked in ((0.72, 2), (0.88, 3)):
        got = boxes.read_page(
            photo, 1, pdf, key["geometry"], wanted, {**ocr.settings(), "ink_line": line}, frame=frame
        )
        assert (got["q"]["inked"], got["q"]["ink_line"]) == (inked, line)


def test_each_line_says_how_many_answers_agree_lose_ink_gain_ink_and_how_many_blanks_are_given_ink():
    measured = [(3, {0.72: 2, 0.8: 3}), (0, {0.72: 0, 0.8: 1}), (2, {0.72: 2, 0.8: 2})]
    assert ink_line.tally(measured, (0.72, 0.8)) == {
        0.72: {"answers": 3, "agree": 2, "lose": 1, "gain": 0, "blank_given_ink": 0},
        0.8: {"answers": 3, "agree": 2, "lose": 0, "gain": 1, "blank_given_ink": 1},
    }


def test_only_answers_a_person_settled_on_a_copy_read_in_its_boxes_are_measured(conn):
    read = rows.a_read_paper(
        conn,
        [
            {"status": "wrong", "read": "82", "typed": "862"},  # a person typed what the child wrote
            {"status": "correct", "read": "35", "state": "confirmed"},  # signed off as read
            {"status": "blank", "read": "", "state": "confirmed"},  # a blank, signed off
            {"status": "correct", "read": "35"},  # nobody has looked
            {
                "status": "correct",
                "read": "35",
                "state": "confirmed",
            },  # read before the boxes were (no `boxes`)
        ],
    )
    for n, r in enumerate(read["results"][:4]):
        conn.execute(
            "update item_result set raw_read = (raw_read::jsonb || %s::jsonb)::text where id = %s",
            (json.dumps({"boxes": 3, "inked": 2, "page": 1, "file_page": 1, "slot": str(n + 1)}), r),
        )
    got = ink_line.settled(conn, [read["capture"]])
    assert sorted((str(r["result"]), r["digits"]) for r in got) == sorted(
        [(str(read["results"][0]), 3), (str(read["results"][1]), 2), (str(read["results"][2]), 0)]
    )


def test_a_read_copy_a_person_settled_is_measured_as_the_reader_found_its_boxes(
    conn, worksheet, tmp_path, monkeypatch
):
    """A worksheet printed for a child (its own code, its boxes recorded), each answer's digits written into its boxes,
    scanned, read by the box reader (a shape-matcher stands in for the handwriting reader) and signed off as read:
    at the reader's own line, every answer's boxes holding ink are as many as the digits it was signed off with."""
    tenant, code, ids, _ = worksheet
    kid = _child(conn, tenant, "71", "Kavya")
    printed = handout.for_children(conn, code, [kid], "2026-W42", "educator@school", tmp_path / "print")
    kept = conn.execute("select pdf_path from sheet_instance where child_id = %s", (kid,)).fetchone()[
        "pdf_path"
    ]
    key = json.loads(Path(kept).with_suffix(".key.json").read_text())
    pages = render_pdf.render(printed, dpi=boxes.PPM * 25.4)
    answers = {r["id"]: str(r["responses"][0]["answer"]) for r in conn.execute(
        "select id, item_key, responses from item where id = any(%s)", (ids,)
    )}  # fmt: skip
    by_key = {
        r["item_key"]: r["id"]
        for r in conn.execute("select id, item_key from item where id = any(%s)", (ids,))
    }
    for page_no, img in enumerate(pages, 1):
        runs, _ = geometry.cells_of(key["geometry"], page_no)
        for (item_key, _rid), run in runs.items():
            wrote = answers.get(by_key.get(item_key), "")
            for cell, ch in zip(run, wrote.rjust(len(run))):
                if ch.strip():
                    _pencil(img, cell, ch, 45)
    doc = pymupdf.open()
    for img in pages:
        ok, jpg = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 80])
        doc.new_page(width=595, height=842).insert_image(pymupdf.Rect(0, 0, 595, 842), stream=jpg.tobytes())
    doc.save(tmp_path / "class.pdf")
    reader = StandIn()
    monkeypatch.setattr(digits, "read", reader.read)
    monkeypatch.setattr(ocr, "client", lambda *a, **k: None)
    monkeypatch.setattr(ocr, "read", lambda image, cli=None: {"lines": [], "words": []})
    monkeypatch.setattr(second_reader, "propose", lambda conn, r, *a, **k: (r, ""))
    (got,) = copies.read(conn, tmp_path / "class.pdf", "", [], "test")
    assert got["child_id"] == kid and got["answers"], got
    conn.execute(
        "update item_result set state = 'confirmed', confirmed_by = 'tester@example.org' where capture_id = %s"
        " and raw_read::jsonb ->> 'answer_state' in ('written', 'blank')",
        (got["capture_id"],),
    )

    report = ink_line.measure(conn, (0.76, 0.88), [got["capture_id"]])
    at = report["lines"][0.76]
    assert at["answers"] > 0 and at["agree"] == at["answers"], report
    assert report["measured"] == at["answers"] == report["stored"] and not report["unmeasured"], report
