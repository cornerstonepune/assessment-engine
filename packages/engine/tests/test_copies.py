"""`engine read file --names`: the copies of library worksheets in one scanned file, each given to the child whose
name is on it, read and marked as any paper is.

A worksheet is printed exactly as the library prints it (`library.pdf`), two copies are "scanned" into one file as
a school scanner hands them over (`test_sorting._scanned`), and the reader is stood in for (`test_legacy.fake_ocr`)
so the test is about which child each copy lands on and how it is marked, not about handwriting.
"""

import json
import os
import uuid

import pymupdf
import pytest

from engine.adapters import ocr
from engine.core import db
from engine.w2_print import library
from engine.w3_read import boxes, copies, copy_scores, second_reader
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
    """Both readers, stood in for: question 1 read right, question 2 read wrong, every other one read blank."""
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
    # a worksheet that recorded where its boxes print is read in them, by the digit reader, not by `answers_for`
    monkeypatch.setattr(
        boxes, "read_page", lambda img, page_no, pdf, geometry, wanted, cfg, **k: answers(None, wanted)
    )
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


def test_a_copy_whose_file_starts_at_its_second_page_is_read_against_the_questions_on_the_pages_it_holds(
    conn, worksheet, tmp_path, monkeypatch
):
    """2026-09-29: one child's copy photographed across two files. The second file's pages — the paper's later
    ones — were read as its first, against the first page's questions and answer key, and signed off that way. The
    page each photograph is comes from what it prints (`boxes.placed`), not from where it sits in the file."""
    tenant, code, ids, pdf = worksheet
    with pymupdf.open(pdf) as doc:
        n = len(doc)
        assert n >= 2, "the worksheet needs a second page for this to mean anything"
        later = pymupdf.open()
        later.insert_pdf(doc, from_page=1, to_page=n - 1)
        later.save(tmp_path / "later.pdf")
    child = _child(conn, tenant, "43", "Chitra")
    stand_in_reader(conn, ids, monkeypatch)
    scan = _scanned([tmp_path / "later.pdf"], tmp_path / "second-file.pdf")

    got = copies.read(conn, scan, SECTION, ["Chitra"], "test", pages_of=lambda c: n)
    assert [(c["code"], c["child_id"]) for c in got] == [(code, child)]
    words, _ = copies.printed(pdf)
    on_later = {ids[q - 1] for q, (page, _) in words.items() if page >= 2}
    rows = conn.execute(
        "select r.item_id, r.raw_read::jsonb as raw from item_result r where r.capture_id = %s",
        (got[0]["capture_id"],),
    ).fetchall()
    assert rows and {r["item_id"] for r in rows} <= on_later, (
        "an answer landed on a question its file does not hold"
    )
    for r in rows:
        page = next(pg for q, (pg, _) in words.items() if ids[q - 1] == r["item_id"])
        assert (r["raw"]["page"], r["raw"]["file_page"]) == (page, page - 1)


def test_a_reading_that_put_answers_on_questions_its_pages_do_not_hold_is_replaced_checks_and_all(
    conn, worksheet, tmp_path, monkeypatch
):
    """The copy read before its pages were placed, and signed off that way: its reading is replaced, not kept for the
    sign-off's sake — the checks were made against another question's words and key — and the note says so."""
    tenant, code, ids, pdf = worksheet
    with pymupdf.open(pdf) as doc:
        n = len(doc)
        later = pymupdf.open()
        later.insert_pdf(doc, from_page=1, to_page=n - 1)
        later.save(tmp_path / "later.pdf")
    _child(conn, tenant, "44", "Devika")
    stand_in_reader(conn, ids, monkeypatch)
    scan = _scanned([tmp_path / "later.pdf"], tmp_path / "second-file.pdf")
    first = copies.read(conn, scan, SECTION, ["Devika"], "test", pages_of=lambda c: n)[0]["capture_id"]
    words, _ = copies.printed(pdf)
    on_page_1 = next(ids[q - 1] for q, (page, _) in words.items() if page == 1)
    conn.execute(  # what the old reading did: an answer on a question of a page this file does not hold, signed off
        "insert into item_result (tenant_id, capture_id, item_id, rid, raw_read, status, state, confirmed_by)"
        " values (%s, %s, %s, 'ans', '{}', 'wrong', 'confirmed', 'tester@example.org')",
        (tenant, first, on_page_1),
    )

    again = copies.read(conn, scan, SECTION, ["Devika"], "test", pages_of=lambda c: n)[0]
    assert again["capture_id"] != first
    replaced = conn.execute("select superseded_by from capture where id = %s", (first,)).fetchone()
    assert replaced["superseded_by"] == again["capture_id"]
    assert any("no longer count" in note for note in again["notes"]), again["notes"]


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
    # the scan's score, per child by roll number — what `/read/scan/{name}/copies` gives
    score = copy_scores.of_scan(conn, scan)
    assert [(s["roll_no"], s["code"], s["right"], s["wrong"], s["blank"]) for s in score] == [
        ("41", code, 1, 1, 10),
        ("42", code, 1, 1, 10),
    ]

    again = copies.read(
        conn, scan, SECTION, ["Asha", "42"], "test", pages_of=lambda c: len(pymupdf.open(pdf))
    )
    assert [c["already"] for c in again] == [True, True]
    # read afresh by a better reader, with nobody there to name them: each copy keeps the child a person named
    first = {c["child_id"]: c["capture_id"] for c in again}
    afresh = copies.read(
        conn, scan, SECTION, None, "test", pages_of=lambda c: len(pymupdf.open(pdf)), again=True
    )
    assert [(c["child_id"], c.get("skipped", False)) for c in afresh] == [(one, False), (two, False)]
    assert all(c["capture_id"] != first[c["child_id"]] for c in afresh), "read afresh, not the old reading"
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


def test_a_question_whose_number_is_not_found_on_the_page_takes_its_page_from_the_key_the_renderer_wrote(
    conn, worksheet, monkeypatch
):
    """`nothing read: 8` on 2026-09-24: question 8's number was not found on the printed page. The page each
    question prints on is in the key written beside the PDF; the question's words are its own."""
    _, code, ids, pdf = worksheet
    words, band = copies.printed(pdf)
    drawn = copies._pages_in_key(pdf)
    keys = {
        r["id"]: r["item_key"]
        for r in conn.execute("select id, item_key from item where id = any(%s)", (ids,))
    }
    assert {n: drawn[keys[i]] for n, i in enumerate(ids, 1)} == {n: p for n, (p, _) in words.items()}

    monkeypatch.setattr(copies, "printed", lambda path: ({n: w for n, w in words.items() if n != 8}, band))
    _, by_key, unread = copies.paper(conn, code)
    assert "8" in by_key and 8 not in unread
    assert by_key["8"]["spec"]["page"] == words[8][0]
    assert by_key["8"]["spec"]["question"].split()[:4] == words[8][1].split()[:4]


def test_a_copy_printed_before_a_story_was_keyed_again_reads_its_boxes_by_the_key_it_has_now(conn, worksheet):
    """A worksheet's key file names each box by its question's key as it was printed. A story keyed again since (`bank
    rekey`, ADR 0053) is found through the key it had, so a copy printed before reads as it did: ADR 0050 rejected
    changing a stored key in place for exactly this, before a key change was a row of its own."""
    tenant, code, ids, pdf = worksheet
    now = conn.execute("select item_key from item where id = %s", (ids[0],)).fetchone()["item_key"]
    was = f"WP2-{uuid.uuid4().hex[:8]}"  # the key it was printed under
    key_file = pdf.with_suffix(".key.json")
    printed = json.loads(key_file.read_text(encoding="utf-8"))
    assert any(cell["item"] == now for cell in printed["geometry"])
    printed["geometry"] = [{**c, "item": was if c["item"] == now else c["item"]} for c in printed["geometry"]]
    key_file.write_text(json.dumps(printed), encoding="utf-8")
    conn.execute(
        "insert into item_key_change (tenant_id, item_id, old_key, new_key, why) values (%s, %s, %s, %s, 'a test')",
        (tenant, ids[0], was, now),
    )
    paper, by_key, unread = copies.paper(conn, code, pdf)
    keys = {r["item_key"] for r in conn.execute("select item_key from item where id = any(%s)", (ids,))}
    assert {
        cell["item"] for cell in paper["key"]["geometry"]
    } == keys  # every box named by its question's key now
    assert unread == [] and "1" in by_key
    assert copies._pages_in_key(pdf, paper["key"]["geometry"])[now] == by_key["1"]["spec"]["page"]


def test_a_copy_cut_where_the_server_cannot_see_it_moves_to_where_the_scans_live(tmp_path, monkeypatch):
    """2026-09-24: the first copies were cut inside the repository, which the server does not mount; the next read
    moves each to `~/cornerstone/assessments/copies` rather than cutting it again, so its bytes — and so the
    capture it was read into — stay the same."""
    monkeypatch.setattr(copies, "CUT", tmp_path / "assessments" / "copies")
    monkeypatch.setattr(copies, "WAS_CUT", tmp_path / "repo" / "data" / "scans")
    old = tmp_path / "repo" / "data" / "scans" / "class" / "copy01-R8-H02.pdf"
    old.parent.mkdir(parents=True)
    old.write_bytes(b"%PDF the copy as first cut")
    moved = copies._cut(tmp_path / "class.pdf", [1, 2, 3], "copy01-R8-H02.pdf")
    assert moved == tmp_path / "assessments" / "copies" / "class" / "copy01-R8-H02.pdf"
    assert moved.read_bytes() == b"%PDF the copy as first cut" and not old.exists()


@pytest.mark.parametrize("layout", ["2026-09-21", "today"])
def test_a_copy_with_no_kept_pdf_is_read_in_the_layout_its_page_was_printed_in(
    conn, tmp_path, monkeypatch, layout
):
    """goals/s18-read-as-printed.yaml: the 23 Sep copies were printed before L3 and their PDF was not kept. The
    reader draws the worksheet in every layout it has printed in and reads the copy in the one it matches."""
    from tests.test_library import _six_sums

    monkeypatch.setattr(library, "PDF_DIR", tmp_path / "worksheets")
    monkeypatch.setattr(copies, "CUT", tmp_path / "scans")
    code = _six_sums(conn)
    drawn = library.printed(conn, code)
    pdf = drawn[layout] if layout in drawn else drawn[next(iter(drawn))]
    scan = _scanned([pdf], tmp_path / "class.pdf")

    assert copies._as_printed(conn, code, copies._cut(scan, [1], "copy01.pdf")) == pdf


def test_a_childs_kept_pdf_that_records_no_boxes_gives_way_to_the_layout_the_page_matches(
    tmp_path, monkeypatch
):
    """23 Sep, R8-H01 copies 07 and 08: each was printed for its child and that PDF was kept — but drawn before the
    renderer recorded where its boxes are. Read against it, the copy had no boxes to read in and fell back to the
    old reader, which took 66 from the working for a child who wrote 34. Spare copies of the same sheet, with no
    kept PDF, were read in their boxes (goals/s18). A kept PDF is used only when it says where its boxes are."""
    bare = tmp_path / "printed-for-child.pdf"
    bare.write_bytes(b"%PDF")
    bare.with_suffix(".key.json").write_text(json.dumps({"items": []}))
    monkeypatch.setattr(copies, "_as_printed", lambda conn, code, cut: "the layout the page matches")
    assert (
        copies._read_from(None, "R8-H01", {"pdf_path": str(bare)}, "cut.pdf") == "the layout the page matches"
    )

    boxed = tmp_path / "printed-with-boxes.pdf"
    boxed.write_bytes(b"%PDF")
    boxed.with_suffix(".key.json").write_text(
        json.dumps({"geometry": [{"page": 1, "item": "x", "kind": "digit"}]})
    )
    assert copies._read_from(None, "R8-H01", {"pdf_path": str(boxed)}, "cut.pdf") == str(boxed)
    assert copies._read_from(None, "R8-H01", None, "cut.pdf") == "the layout the page matches"
    assert (
        copies._read_from(None, "R8-H01", {"pdf_path": str(tmp_path / "gone.pdf")}, "c")
        == "the layout the page matches"
    )
