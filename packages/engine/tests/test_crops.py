"""Every answer a person checks is a lesson for the reader (goals/s19-validation-teaches.yaml): the pixels the reader
read, kept beside the scans when it read them (`w3_read/crops.py`), and what the person said the child wrote, from
the one view that defines a checked answer (`answer_checked`)."""

import cv2
import numpy as np
import pytest

from engine.adapters import digits
from engine.core import db
from engine.w3_read import boxes, crops, marking, profiles, render_pdf
from tests import test_boxes
from tests.test_boxes import StandIn, _filled, _fits, _scanned
from tests.test_legacy import _read_the_paper, pytestmark_db

paper = test_boxes.paper  # the six sums and their printed key, drawn once for the module


@pytest.fixture
def reader(monkeypatch):
    stand_in = StandIn()
    monkeypatch.setattr(digits, "read", stand_in.read)
    return stand_in


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def child(conn):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    return conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s,'1','TESTSEC','G2') returning id",
        (tenant,),
    ).fetchone()["id"]


def test_every_answer_the_reader_reads_keeps_the_crop_it_read_beside_the_scans(
    paper, tmp_path, reader, monkeypatch
):
    """Nimish: "All the validations that we are doing right now should help improve the system." A person's check
    can only teach a reader of the pixels it saw: so each answer's crop is kept as the reader read it, blank ones
    too, and the reading says where it is."""
    monkeypatch.setattr(crops, "CROPS", tmp_path / "crops")
    pdf, key = paper
    ids = [it["item_id"] for it in key["items"]]
    wrote = {ids[n - 1]: "" if n == 3 else _fits(key, n) for n in range(1, 7)}
    scan = _scanned(_filled(paper, wrote, {}), tmp_path / "copy01-p1-CS00C0DE.pdf")
    img, frame = render_pdf.photo(scan, 1)
    wanted = {str(n): (it["item_id"], "ans") for n, it in enumerate(key["items"], 1)}

    got = boxes.read_page(
        img,
        1,
        pdf,
        key["geometry"],
        wanted,
        {"min_confidence": 90.0},
        frame=frame,
        keep=crops.keeper(scan, 1),
    )
    handed = {img.tobytes() for img in reader.handed}
    for slot, r in got.items():
        path = crops.path(r["crop"])
        assert path.exists() and path.is_relative_to(tmp_path / "crops"), slot
        kept = cv2.imdecode(np.frombuffer(path.read_bytes(), np.uint8), cv2.IMREAD_GRAYSCALE)
        if r["answer_state"] == "written":
            assert kept.tobytes() in handed, f"question {slot}: the crop kept is not the one the reader read"
    assert got["3"]["answer_state"] == "blank" and crops.path(got["3"]["crop"]).exists(), (
        "a blank is a lesson too"
    )
    # read again, the same file is written again: one crop per answer, never a second copy
    again = boxes.read_page(
        img,
        1,
        pdf,
        key["geometry"],
        wanted,
        {"min_confidence": 90.0},
        frame=frame,
        keep=crops.keeper(scan, 1),
    )
    assert {s: r["crop"] for s, r in again.items()} == {s: r["crop"] for s, r in got.items()}


def _checked(conn, capture):
    return {
        r["item_key"]: r
        for r in conn.execute("select * from answer_checked where capture_id = %s", (capture,)).fetchall()
    }


@pytestmark_db
def test_a_checked_answer_has_one_label_its_crop_and_the_day_it_was_read(
    conn, child, tmp_path, monkeypatch, every_kind_trusted
):
    """Nimish: "Even the ones that you have marked as right and right, we are validating them also. Is this data
    going to be used in a constructive way?" A typed reading is the label; a sign-off keeps the reader's reading as
    the label; a Right/Wrong judgement is not a reading, so it labels nothing (ADR 0027)."""
    capture, ids = _read_the_paper(conn, child, tmp_path, monkeypatch)
    crop = "~/cornerstone/assessments/crops/paper/p1-2.png"
    conn.execute(
        "update item_result set raw_read = (raw_read::jsonb || jsonb_build_object('crop', %s::text))::text where id = %s",
        (crop, ids["legacy/TEST-PAPER/2"]),
    )
    assert _checked(conn, capture) == {}, "nothing is checked until a person checks it"

    marking.correct(conn, ids["legacy/TEST-PAPER/2"], "75", "aseem")
    conn.execute("select resolve_result(%s, 'correct', '{}', 'aseem')", (ids["legacy/TEST-PAPER/3"],))
    conn.execute("select confirm_results(%s, 'aseem')", (child,))

    got = _checked(conn, capture)
    typed = got["legacy/TEST-PAPER/2"]
    assert (typed["label"], typed["how"], typed["crop"]) == ("75", "typed", crop)
    assert typed["read_on"] is not None and typed["fmt"]
    assert "legacy/TEST-PAPER/3" not in got, "a judgement is not a reading"
    signed = [r for k, r in got.items() if r["how"] == "signed off"]
    assert signed and all(r["label"] == r["reading"] for r in signed)
    # the engine's notebook counts from the same rows
    assert {r["item_result_id"] for r in profiles.checked_rows(conn, child)} == {
        r["item_result_id"] for r in got.values()
    }


@pytestmark_db
def test_the_readers_accuracy_is_counted_by_day_and_by_kind_from_the_one_view(
    conn, child, tmp_path, monkeypatch
):
    """Nimish: "How many rounds of validations will we do till we get to more than 95% accuracy?" — answered by the
    reader's accuracy per day the papers were read, and per kind of question, both from `answer_checked`."""
    capture, ids = _read_the_paper(conn, child, tmp_path, monkeypatch)
    reading = conn.execute(
        "select raw_read::jsonb ->> 'child_answer' as a from item_result where id = %s",
        (ids["legacy/TEST-PAPER/2"],),
    ).fetchone()["a"]
    marking.correct(
        conn, ids["legacy/TEST-PAPER/2"], reading + "9", "aseem"
    )  # the reader was wrong on this one
    conn.execute("select confirm_results(%s, 'aseem')", (child,))

    rows = [r for r in _checked(conn, capture).values()]
    day = rows[0]["read_on"]
    report = profiles.report(conn)
    batch = next(b for b in report["batches"] if b["batch"] == day)
    stood = [r for r in rows if not profiles.doubted(r["why"])]
    assert batch["checked"] >= len(rows)
    assert batch["right"] >= sum(profiles._norm(r["reading"]) == profiles._norm(r["label"]) for r in stood)
    assert batch["checked"] == sum(1 for r in report_rows(conn) if r["read_on"] == day)


def report_rows(conn):
    return conn.execute("select read_on from answer_checked").fetchall()
