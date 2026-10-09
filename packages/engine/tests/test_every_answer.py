"""Every answer a question asks for counts (goals/md0a-every-answer-counts.yaml).

A printed question can ask for more than one answer: an estimate and the exact answer, a check and whether the sum was
right, a corrected answer and the reason. Before this, a library worksheet's question with more than one answer was never
read, and wherever a result was marked or shown its question's first answer stood in for its own. Each answer here is
read in its own boxes, marked against its own key, waits for a person where the engine cannot read it, and counts as its
own evidence.

The unit tests need nothing; the box test prints a real paper and stands a shape-matcher in for the reader
(`test_boxes`); the end-to-end tests print a library worksheet and stand both readers in (`test_copies`), so they are
about where each answer lands and how it is marked, not about handwriting.
"""

import os
import random
import uuid

import pymupdf
import pytest

from engine.adapters import ocr
from engine.assess import diagnosis, equality, estimate, geometry
from engine.assess.pick import Sheet
from engine.assess.render import render_sheet
from engine.checks import audit
from engine.core import db
from engine.w2_print import library
from engine.w3_read import again, boxes, copies, keys, marking, render_pdf, second_reader
from tests.test_boxes import StandIn, _scanned, _write
from tests.test_sorting import _scanned as _scanned_file


def _wrote(text):
    return {"child_answer": text, "answer_state": "written" if text else "blank", "working_shown": "none"}


# ---------------------------------------------------------------------------------------------- marking, one answer


def test_an_estimate_within_its_own_tolerance_is_right_and_one_outside_it_is_wrong():
    """An estimate's key carries how far a fair estimate may land from it (`Response.tolerance`). Nothing that marked a
    child's paper read it: 80 for an estimate keyed 70 within ten was marked wrong."""
    est = {"rid": "est", "kind": "digits", "answer": "70", "tolerance": 10, "misconceptions": {}}
    assert marking.mark({}, est, _wrote("70"))[0] == "correct"
    assert marking.mark({}, est, _wrote("80"))[0] == "correct"
    assert marking.mark({}, est, _wrote("85"))[0] == "wrong"
    exact = {"rid": "ans", "kind": "digits", "answer": "75", "misconceptions": {}}
    assert marking.mark({}, exact, _wrote("76"))[0] == "wrong", "an answer with no tolerance is exact"


def test_a_written_reason_is_judged_by_a_person_never_marked_unreadable():
    """A reason the child writes ("why") is a sentence. Its own kind says so; it was marked unreadable because only the
    question's kind was asked."""
    why = {"rid": "why", "kind": "text", "answer": None}
    assert marking.mark({}, why, _wrote("she forgot to carry the one"))[0] == "needs_teacher"
    assert marking.mark({}, why, _wrote(""))[0] == "blank"


def test_each_answer_is_marked_against_its_own_key():
    """A slot carries the answer it is for; the first answer of its question never stands in for it."""
    est = {"rid": "est", "kind": "digits", "answer": "70", "tolerance": 10, "misconceptions": {}}
    ans = {"rid": "ans", "kind": "digits", "answer": "68", "misconceptions": {"M_NOCARRY": "58"}}
    slot = {"spec": {}, "responses": [est, ans], "response": ans}
    assert marking.response_of(slot) is ans
    assert marking.response_of({"spec": {}, "responses": [est, ans]}) is est, (
        "a paper's own slot: its one answer"
    )
    assert marking.mark_read({}, marking.response_of(slot), _wrote("68"))[0] == "correct"


# ---------------------------------------------------------------------------------------------- reading, every box


@pytest.fixture(scope="module")
def two_answer_paper(tmp_path_factory):
    """Two estimate-then-work-it-out questions, a check with a tick and a corrected answer with a reason, printed."""
    rng = random.Random(11)

    def drawn(
        make,
    ):  # a generator refuses numbers that do not make its question: draw again, as the bank does
        for _ in range(50):
            try:
                return make()
            except RuntimeError:
                continue
        raise RuntimeError("no numbers in fifty draws")

    qs = [
        drawn(lambda: estimate.estimate_then_calc(rng, "R5", "Procedural", "+", 2, 2, [0, 1]))
        for _ in range(2)
    ]
    qs.append(drawn(lambda: equality.inverse_check(rng, "R16", "Conceptual", "+", digits=2)))
    qs.append(drawn(lambda: diagnosis.find_mistake(rng, "X2", "Stretch", "+", digits=2)))
    out = tmp_path_factory.mktemp("two")
    key = render_sheet(
        Sheet("CS00C0D2", "G2", "Focus", 1, "W1", qs, title="Practice"), out, week_label="Practice"
    )
    return out / "CS00C0D2.pdf", key, qs


def test_every_answer_of_a_question_is_read_in_its_own_boxes(two_answer_paper, tmp_path, monkeypatch):
    """Each number a question asks for is read where it was written; a tick or a sentence is not a number, so the
    digit reader is never handed it — a person reads it, shown the place it was written."""
    reader = StandIn()
    monkeypatch.setattr(boxes.digits, "read", reader.read)
    pdf, key, qs = two_answer_paper
    runs, _ = geometry.cells_of(key["geometry"], 1)
    by_id = {it["item_id"]: q for it, q in zip(key["items"], qs, strict=True)}
    written = {}
    img = render_pdf.render(pdf, dpi=boxes.PPM * 25.4)[0]
    for (item, rid), run in runs.items():
        response = next(r for r in by_id[item].responses if r.rid == rid)
        if response.kind != "digits":
            continue
        text = str(int(response.answer) + (1 if rid == "ans" else 0))[-len(run) :]  # the exact answer one out
        written[(item, rid)] = text
        for cell, ch in zip(run, text.rjust(len(run)), strict=True):
            if ch.strip():
                _write(img, cell, ch, boxes.PPM)
    scan = _scanned(img, tmp_path / "scan.pdf")
    answers = {(g["item"], g["resp"]) for g in key["geometry"] if g["page"] == 1 and g.get("kind") != "work"}
    wanted = {f"{n}.{rid}": (item, rid) for n, (item, rid) in enumerate(sorted(answers))}
    people = {
        s for s, (item, rid) in wanted.items()
        if next(r for r in by_id[item].responses if r.rid == rid).kind != "digits"
    }  # fmt: skip
    assert people, "the paper prints a tick and a sentence"
    photo, frame = render_pdf.photo(scan, 1)
    got = boxes.read_page(
        photo, 1, pdf, key["geometry"], wanted, ocr.settings(), frame=frame, for_a_person=people
    )
    assert set(got) == set(wanted), "every answer the paper asks for comes back"
    for slot, (item, rid) in wanted.items():
        if slot in people:
            assert got[slot]["answer_state"] == "for_a_person" and "a person" in got[slot]["why"]
            assert got[slot]["child_answer"] == "" and len(got[slot]["box"]) == 4
        else:
            assert got[slot]["child_answer"] == written[(item, rid)], slot


# ---------------------------------------------------------------------------------------------- a worksheet, end to end


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs the local copy (bin/testdb)")
    with db.connect(db.dsn()) as c:
        yield c
        c.rollback()


SHAPES = [("estimate_then_calc", "est:digits,ans:digits"), ("inverse_check", "check:digits,right:tick"),
          ("find_mistake", "ans:digits,why:text")]  # fmt: skip


@pytest.fixture
def every_kind_trusted(monkeypatch):
    """ADR 0032's gate out of the way for this worksheet's own kinds (`conftest.every_kind_trusted` trusts the kinds of
    a paper entered by hand), and no spot-check: a test about where each answer lands, not about the reader's standing."""
    from engine.w3_read import profiles

    trusted = {"n": 50, "right": 50, "trusted": True}
    monkeypatch.setattr(profiles, "kind_trust", lambda conn, window=50: {f: trusted for f, _ in SHAPES})
    monkeypatch.setattr(marking, "spot_rate", lambda conn: 0.0)


SECTION = f"E{uuid.uuid4().hex[:4]}"


@pytest.fixture
def worksheet(conn, tmp_path, monkeypatch):
    """A library worksheet of twelve questions of two answers each: four of each shape, as the library deals one."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()
    ids = []
    for fmt, shape in SHAPES:
        ids += [
            r["id"]
            for r in conn.execute(
                "select id from item where fmt = %s and status = 'active' and (select string_agg(x->>'rid' || ':' ||"
                " (x->>'kind'), ',' order by o) from jsonb_array_elements(responses) with ordinality t(x, o)) = %s"
                " order by item_key limit 4",
                (fmt, shape),
            )
        ]
    if not tenant or len(ids) < 12:
        pytest.skip("needs the seed and the bank on the copy")
    code = f"R5-A9{uuid.uuid4().int % 100:02d}"
    conn.execute(
        "insert into sheet_template (tenant_id, band, week, variant, source, code, skill_set_code, difficulty,"
        " item_ids) values (%s, 'G2', 'library', 99, 'library', %s, 'ADD.2D2D', 'Advance', %s)",
        (tenant["id"], code, ids),
    )
    monkeypatch.setattr(library, "PDF_DIR", tmp_path / "worksheets")
    monkeypatch.setattr(copies, "CUT", tmp_path / "scans")
    child = conn.execute(
        "insert into child (tenant_id, roll_no, band, section) values (%s, '51', 'G2', %s) returning id",
        (tenant["id"], SECTION),
    ).fetchone()["id"]
    conn.execute(
        "insert into pii.child (tenant_id, child_id, first_name) values (%s,%s,'Esha')", (tenant["id"], child)
    )
    return code, ids, library.pdf(conn, code), child


def _keys(conn, ids):
    return {
        r["id"]: {x["rid"]: x for x in r["responses"]}
        for r in conn.execute("select id, responses from item where id = any(%s)", (ids,))
    }


def _read_copy(conn, worksheet, tmp_path, monkeypatch):
    """The worksheet read for its child with both readers stood in for: every estimate written right; the exact answer
    right on the first estimate question, one out on the second, blank on the other two; every check and every
    corrected answer right; a tick and a reason come back for a person, as the box reader returns them."""
    code, ids, pdf, child = worksheet
    keys_ = _keys(conn, ids)
    monkeypatch.setattr(ocr, "client", lambda *a, **k: None)
    monkeypatch.setattr(ocr, "read", lambda image, cli=None: {"lines": [], "words": []})
    monkeypatch.setattr(second_reader, "propose", lambda conn, r, *a, **k: (r, ""))
    estimates = ids[:4]

    def what(item_id, rid):
        key = keys_[item_id][rid]["answer"]
        if rid == "ans" and item_id in estimates:
            return {0: key, 1: str(int(key) + 1)}.get(estimates.index(item_id), "")
        return key

    def read_page(img, page_no, pdf, geometry, wanted, cfg, frame=None, keep=None, for_a_person=()):
        by_key = {
            r["item_key"]: r["id"]
            for r in conn.execute("select id, item_key from item where id = any(%s)", (ids,))
        }
        out = {}
        for slot, (item_key, rid) in wanted.items():
            if slot in for_a_person:
                out[slot] = {"child_answer": "", "answer_state": "for_a_person", "why": "a person reads this answer",
                             "box": [0.1, 0.1, 0.2, 0.1], "confidence": 0.0, "working_shown": "none"}  # fmt: skip
            else:
                out[slot] = {**_wrote(what(by_key[item_key], rid)), "confidence": 99.0}
        return out

    monkeypatch.setattr(boxes, "read_page", read_page)
    scan = _scanned_file([pdf], tmp_path / "class.pdf")
    got = copies.read(conn, scan, SECTION, ["Esha"], "test", pages_of=lambda c: len(pymupdf.open(pdf)))
    rows = conn.execute(
        "select r.id, r.item_id, r.rid, r.status, r.raw_read::jsonb ->> 'why' as why, r.capture_id"
        " from item_result r join capture c on c.id = r.capture_id join sheet_instance si on si.id = c.sheet_instance_id"
        " where si.child_id = %s and c.superseded_by is null",
        (child,),
    ).fetchall()
    return got, {(r["item_id"], r["rid"]): r for r in rows}, keys_


def test_a_library_worksheet_gives_every_answer_its_own_slot(conn, worksheet):
    code, ids, pdf, _ = worksheet
    _, by_key, unread = copies.paper(conn, code, pdf)
    assert unread == [], "no question is left for nobody"
    assert len(by_key) == 24, "two answers on each of twelve questions"
    for it in by_key.values():
        response = marking.response_of(it)
        assert it["spec"]["answer"] == response["answer"], "a slot is keyed by its own answer"
    assert {marking.response_of(it)["rid"] for it in by_key.values()} == {
        "est",
        "ans",
        "check",
        "right",
        "why",
    }


def test_every_answer_on_a_copy_is_read_marked_and_counted(
    conn, worksheet, tmp_path, monkeypatch, every_kind_trusted
):
    code, ids, _, _ = worksheet
    got, rows, keys_ = _read_copy(conn, worksheet, tmp_path, monkeypatch)
    assert [c["answers"] for c in got] == [24], "every answer the worksheet asks for is a result"
    assert {(i, rid) for i in ids for rid in keys_[i]} == set(rows), (
        "one result for each answer, by its own id"
    )
    status = {k: (r["status"], r["why"] or "") for k, r in rows.items()}
    first, second = ids[0], ids[1]
    assert status[(first, "est")][0] == "correct" and status[(first, "ans")][0] == "correct"
    assert status[(second, "ans")][1].startswith("read as a wrong answer"), "one out: a person checks it"
    assert status[(ids[2], "ans")][1].startswith("read as blank")
    for i in ids[4:8]:
        assert status[(i, "check")][0] == "correct"
        assert status[(i, "right")] == ("needs_teacher", "a person reads this answer"), (
            "a tick waits for a person"
        )
    for i in ids[8:]:
        assert status[(i, "ans")][0] == "correct"
        assert status[(i, "why")][0] == "needs_teacher", "a reason waits for a person"


def test_a_person_typing_one_answer_marks_it_against_that_answers_own_key(
    conn, worksheet, tmp_path, monkeypatch, every_kind_trusted
):
    _, ids, _, _ = worksheet
    _, rows, keys_ = _read_copy(conn, worksheet, tmp_path, monkeypatch)
    second = rows[(ids[1], "ans")]
    got = marking.correct(conn, second["id"], keys_[ids[1]]["ans"]["answer"], "test")
    assert got["status"] == "correct", (
        "the exact answer typed is right against the exact answer, not the estimate"
    )


def test_marking_again_keeps_each_answer_on_its_own_key(
    conn, worksheet, tmp_path, monkeypatch, every_kind_trusted
):
    _, ids, _, child = worksheet
    _, rows, _ = _read_copy(conn, worksheet, tmp_path, monkeypatch)
    assert again.remark(conn, child) == 0, "nothing read changes its mark when marked again by the same rule"
    now = conn.execute(
        "select status from item_result where id = %s", (rows[(ids[0], "ans")]["id"],)
    ).fetchone()
    assert now["status"] == "correct"


def test_each_answer_signed_off_is_its_own_evidence(
    conn, worksheet, tmp_path, monkeypatch, every_kind_trusted
):
    _, ids, _, child = worksheet
    _, rows, keys_ = _read_copy(conn, worksheet, tmp_path, monkeypatch)
    second = ids[1]
    marking.correct(conn, rows[(second, "ans")]["id"], str(int(keys_[second]["ans"]["answer"]) + 1), "test")
    marking.confirm(conn, child, "test")
    evidence = conn.execute(
        "select distinct r.rid, e.correct from evidence_event e join item_result r on r.id = e.item_result_id"
        " where r.item_id = %s",
        (second,),
    ).fetchall()
    assert {(e["rid"], e["correct"]) for e in evidence} == {("est", True), ("ans", False)}


def test_the_right_answer_shown_on_each_card_is_its_own(
    conn, worksheet, tmp_path, monkeypatch, every_kind_trusted
):
    _, ids, _, _ = worksheet
    _, rows, keys_ = _read_copy(conn, worksheet, tmp_path, monkeypatch)
    capture = rows[(ids[0], "est")]["capture_id"]
    shown = {s["id"]: s["right"] for s in keys.shown(conn, capture)}
    for (item, rid), r in rows.items():
        if rid in ("est", "ans", "check"):
            assert shown[str(r["id"])] == keys_[item][rid]["answer"], (rid, item)
    picked = conn.execute(
        "select result_response(i.responses, r.rid) ->> 'rid' as rid, result_part(i.responses, r.rid) as part,"
        " result_part('[{\"rid\": \"a\"}]', 'a') as alone"
        " from item_result r join item i on i.id = r.item_id where r.id = %s",
        (rows[(ids[0], "ans")]["id"],),
    ).fetchone()
    assert picked["rid"] == "ans", "the website reads an answer's own key by the same rule"
    # two cards for one question say which answer each is; a one-answer question's card is as it was
    assert picked["part"] == "answer 2 of 2 · exact", picked
    assert picked["alone"] is None


def test_every_answer_names_a_response_of_its_question(
    conn, worksheet, tmp_path, monkeypatch, every_kind_trusted
):
    _read_copy(conn, worksheet, tmp_path, monkeypatch)
    assert audit.every_answer_names_a_response_of_its_question(conn) == []
