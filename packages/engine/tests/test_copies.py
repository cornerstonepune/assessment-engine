"""`engine read file --names`: the copies of library worksheets in one scanned file, each given to the child whose
name is on it, read and marked as any paper is.

A worksheet is printed exactly as the library prints it (`library.pdf`), two copies are "scanned" into one file as
a school scanner hands them over (`test_sorting._scanned`), and the reader is stood in for (`test_legacy.fake_ocr`)
so the test is about which child each copy lands on and how it is marked, not about handwriting.
"""

import os
import uuid

import pymupdf
import pytest

from engine.adapters import ocr
from engine.core import db
from engine.w2_print import library
from engine.w3_read import copies, second_reader
from tests.test_sorting import _scanned


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs the local copy (bin/testdb)")
    with db.connect(db.dsn()) as c:
        yield c
        c.rollback()


@pytest.fixture
def worksheet(conn, tmp_path, monkeypatch):
    """A library worksheet of twelve word problems, as the library deals one, and its printed PDF."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()
    ids = [
        r["id"]
        for r in conn.execute(
            "select id from item where fmt = 'word_2step' and status = 'active' order by item_key limit 12"
        )
    ]
    if not tenant or len(ids) < 12:
        pytest.skip("needs the seed and the bank on the copy")
    code = f"R8-H9{uuid.uuid4().int % 100:02d}"  # a code as the library writes one
    conn.execute(
        "insert into sheet_template (tenant_id, band, week, variant, source, code, skill_set_code, difficulty,"
        " item_ids) values (%s, 'G2', 'library', 99, 'library', %s, 'WORD.1_2STEP', 'Hard', %s)",
        (tenant["id"], code, ids),
    )
    monkeypatch.setattr(library, "PDF_DIR", tmp_path / "worksheets")
    monkeypatch.setattr(copies, "CUT", tmp_path / "scans")
    return tenant["id"], code, ids, library.pdf(conn, code)


def _child(conn, tenant, roll, name):
    cid = conn.execute(
        "insert into child (tenant_id, roll_no, band, section) values (%s, %s, 'G2', %s) returning id",
        (tenant, roll, SECTION),
    ).fetchone()["id"]
    conn.execute(
        "insert into pii.child (tenant_id, child_id, first_name) values (%s,%s,%s)", (tenant, cid, name)
    )
    return cid


SECTION = f"T{uuid.uuid4().hex[:4]}"


def stand_in_reader(conn, ids, monkeypatch):
    """The reader, stood in for: question 1 read right, question 2 read wrong, every other one read blank."""
    keys = {r["id"]: r["responses"][0]["answer"] for r in conn.execute(
        "select id, responses from item where id = any(%s)", (ids,)
    )}  # fmt: skip
    monkeypatch.setattr(ocr, "client", lambda *a, **k: None)
    monkeypatch.setattr(ocr, "read", lambda image, cli=None: {"lines": [], "words": []})
    wrote = {"1": keys[ids[0]], "2": str(int(keys[ids[1]]) + 1)}

    def answers(page, slots, cfg=None, symbolic=(), boxes=(), reread=None):
        return {
            s: {"child_answer": wrote.get(s, ""), "answer_state": "written" if s in wrote else "blank",
                "confidence": 99.0, "working_shown": "none"}
            for s in slots
        }  # fmt: skip

    monkeypatch.setattr(ocr, "answers_for", answers)
    monkeypatch.setattr(second_reader, "propose", lambda conn, r, *a, **k: (r, ""))


def test_each_question_is_found_on_its_page_in_its_printed_words_and_the_name_band_stops_above_question_1(
    conn, worksheet
):
    _, _, ids, pdf = worksheet
    words, band = copies.printed(pdf)
    stems = {r["id"]: r["stem"] for r in conn.execute("select id, stem from item where id = any(%s)", (ids,))}
    assert sorted(words) == list(range(1, 13))
    for n, iid in enumerate(ids, 1):
        page, text = words[n]
        assert text.split()[:5] == stems[iid].split()[:5], (n, text)
        assert 1 <= page <= len(pymupdf.open(pdf))
    first = pymupdf.open(pdf)[0]
    name = next(w for w in first.get_text("words") if w[4] == "Name:")
    q1 = next(w for w in first.get_text("words") if w[4] == "1" and w[0] < 60)
    assert name[3] / first.rect.height < band < q1[1] / first.rect.height


def test_two_copies_land_on_the_two_children_named_each_answer_marked_against_its_key(
    conn, worksheet, tmp_path, monkeypatch
):
    tenant, code, ids, pdf = worksheet
    one, two = _child(conn, tenant, "41", "Asha"), _child(conn, tenant, "42", "Bina")
    stand_in_reader(conn, ids, monkeypatch)
    scan = _scanned([pdf, pdf], tmp_path / "class.pdf")

    got = copies.read(conn, scan, SECTION, ["Asha", "42"], "test", pages_of=lambda c: len(pymupdf.open(pdf)))
    assert [(c["code"], c["child_id"], c["answers"]) for c in got] == [(code, one, 12), (code, two, 12)]
    for cid in (one, two):
        rows = conn.execute(
            "select i.id, r.rid, r.status, r.raw_read::jsonb ->> 'why' as why from item_result r join capture c on c.id = r.capture_id"
            " join sheet_instance si on si.id = c.sheet_instance_id join item i on i.id = r.item_id"
            " where si.child_id = %s",
            (cid,),
        ).fetchall()
        why = {r["id"]: (r["status"], r["why"] or "") for r in rows}
        assert {r["rid"] for r in rows} == {"ans"} and len(why) == 12
        # Every answer waits for a person, each with the engine's verdict as its reason: a right one until the
        # reader is trusted on word problems (ADR 0032), a wrong one and a blank always (ADR 0029).
        assert why[ids[0]][0] == "needs_teacher" and why[ids[0]][1].startswith("read as a right answer")
        assert why[ids[1]][1].startswith("read as a wrong answer") and why[ids[2]][1].startswith(
            "read as blank"
        )
    cut = sorted((tmp_path / "scans").rglob("*.pdf"))
    assert [len(pymupdf.open(p)) for p in cut] == [len(pymupdf.open(pdf))] * 2

    again = copies.read(
        conn, scan, SECTION, ["Asha", "42"], "test", pages_of=lambda c: len(pymupdf.open(pdf))
    )
    assert [c["already"] for c in again] == [True, True]
    n = conn.execute(
        "select count(*) as n from capture c join sheet_instance si on si.id = c.sheet_instance_id"
        " where si.child_id = any(%s) and c.superseded_by is null",
        ([one, two],),
    ).fetchone()["n"]
    assert n == 2, "a second run reads nothing twice"


def test_a_copy_left_unnamed_is_skipped_and_the_wrong_number_of_names_is_refused(conn, worksheet, tmp_path):
    tenant, code, _, pdf = worksheet
    _child(conn, tenant, "43", "Chitra")
    scan = _scanned([pdf, pdf], tmp_path / "class.pdf")
    length = lambda c: len(pymupdf.open(pdf))  # noqa: E731
    with pytest.raises(ValueError, match=r"2 copies(.|\n)*copy 2: pages \d+–\d+, R8-H9"):
        copies.read(conn, scan, SECTION, ["Chitra"], "test", pages_of=length)
    with pytest.raises(ValueError, match="0 children called 'Nobody'"):
        copies.read(conn, scan, SECTION, ["Nobody", "?"], "test", pages_of=length)
