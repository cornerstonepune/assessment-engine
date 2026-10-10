"""Every answer a question asks for counts (goals/md0a-every-answer-counts.yaml).

A printed question can ask for more than one answer: an estimate and the exact answer, a check and whether the sum was
right, a corrected answer and the reason. Before this, a library worksheet's question with more than one answer was never
read, and wherever a result was marked or shown its question's first answer stood in for its own. Each answer here is
read in its own boxes, marked against its own key, waits for a person where the engine cannot read it, and counts as its
own evidence.

These print a library worksheet and stand both readers in (`test_copies`), so they are about where each answer lands and
how it is marked, shown and counted, not about handwriting. Each answer on its own, with no database, is
`test_each_answer.py`.
"""

import json
import os
import uuid

import pymupdf
import pytest

from engine.adapters import ocr
from engine.checks import audit
from engine.core import db
from engine.w1_bank import learned, mistake_guess
from engine.w2_print import library
from engine.w3_read import (
    again,
    boxes,
    copies,
    keys,
    marking,
    naming,
    profiles,
    second_reader,
)
from engine.w4_close import report
from tests.test_each_answer import _wrote
from tests.test_sorting import _scanned as _scanned_file

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

    trusted = {"n": 50, "right": 50, "trusted": True, "to_trust": 0}
    monkeypatch.setattr(profiles, "kind_trust", lambda conn: {f: trusted for f, _ in SHAPES})
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
                # two keys a test can tell apart: 273 + 627 is estimated 900 and is 900, one answer said twice
                " and responses->0->>'answer' is distinct from responses->1->>'answer'"
                # the sheet is ADD.2D2D's: its questions add and take away. Drawn first by key, a × or ÷ estimate or check
                # the bank happened to hold put a multiplication on it (the bank is drawn afresh on every build)
                " and spec->>'op' in ('+', '-')"
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
                out[slot] = {"child_answer": "", "answer_state": "for_a_person", "why": boxes.FOR_A_PERSON,
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
        assert status[(i, "right")] == ("needs_teacher", boxes.FOR_A_PERSON), "a tick waits for a person"
    for i in ids[8:]:
        assert status[(i, "ans")][0] == "correct"
        assert status[(i, "why")][0] == "needs_teacher", "a reason waits for a person"


def test_a_person_typing_one_answer_marks_it_against_that_answers_own_key(
    conn, worksheet, tmp_path, monkeypatch, every_kind_trusted
):
    _, ids, _, _ = worksheet
    _, rows, keys_ = _read_copy(conn, worksheet, tmp_path, monkeypatch)
    # the estimate's own key typed as the exact answer: right against the estimate, wrong against the exact answer
    item = next(i for i in ids[:4] if keys_[i]["est"]["answer"] != keys_[i]["ans"]["answer"])
    got = marking.correct(conn, rows[(item, "ans")]["id"], keys_[item]["est"]["answer"], "test")
    assert got["status"] != "correct", "marked against its own key, not the estimate's"
    got = marking.correct(conn, rows[(item, "ans")]["id"], keys_[item]["ans"]["answer"], "test")
    assert got["status"] == "correct"


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
    first, second = ids[0], ids[1]
    marking.correct(conn, rows[(second, "ans")]["id"], str(int(keys_[second]["ans"]["answer"]) + 1), "test")
    marking.correct(conn, rows[(first, "est")]["id"], str(int(keys_[first]["est"]["answer"]) + 500), "test")
    marking.confirm(conn, child, "test")
    evidence = conn.execute(
        "select distinct r.rid, e.correct from evidence_event e join item_result r on r.id = e.item_result_id"
        " where r.item_id = %s",
        (second,),
    ).fetchall()
    assert {(e["rid"], e["correct"]) for e in evidence} == {("est", True), ("ans", False)}
    # the child's report shows a wrong answer beside its own right answer, not its question's first
    wrong = {r["answer"]: r for r in conn.execute(report.WRONG, (child, None, None))}
    assert keys_[second]["ans"]["answer"] != keys_[second]["est"]["answer"], (
        "the two keys differ on this question"
    )
    assert report._example(wrong[rows[(second, "ans")]["id"]])["right"] == keys_[second]["ans"]["answer"]
    # a wrong answer to the sum no named mistake explains is a way of working it to learn; a wrong estimate is not
    pair = [rows[(second, "ans")]["id"], rows[(first, "est")]["id"]]
    conn.execute("update item_result set misconception_codes = '{}' where id = any(%s)", (pair,))
    found = {str(r["result_id"]) for r in learned.unexplained(conn)}
    assert str(rows[(second, "ans")]["id"]) in found and str(rows[(first, "est")]["id"]) not in found


def test_the_second_reader_guesses_each_answer_into_its_own_row(
    conn, worksheet, tmp_path, monkeypatch, every_kind_trusted
):
    """Two answers to one question, both waiting with a doubted reading: each gets its own guess. Keyed by question,
    one reading stood for both and its guess was written into the other's row."""
    _, ids, _, child = worksheet
    _, rows, _ = _read_copy(conn, worksheet, tmp_path, monkeypatch)
    pair = [rows[(ids[0], "est")]["id"], rows[(ids[0], "ans")]["id"]]
    for k, rid in enumerate(pair):
        conn.execute(
            "update item_result set status = 'needs_teacher', raw_read = %s where id = %s",
            (json.dumps({"child_answer": "", "answer_state": "written", "why": "under the confidence floor",
                         "box": [0.1, 0.1 + k / 10, 0.3, 0.15 + k / 10], "guess": ""}), rid),
        )  # fmt: skip
    monkeypatch.setattr(profiles, "current", lambda conn, child_id: {})
    monkeypatch.setattr(
        second_reader, "propose", lambda conn, r, *a, **k: ({s: {**x, "guess": s} for s, x in r.items()}, "")
    )
    second_reader.backfill(conn, {}, [child])
    guesses = {
        str(r["id"]): r["guess"]
        for r in conn.execute(
            "select id, raw_read::jsonb ->> 'guess' as guess from item_result where id = any(%s)", (pair,)
        )
    }
    assert all(guesses[str(rid)].endswith(str(rid)) for rid in pair), guesses


def test_what_a_person_reads_and_names_is_each_answers_own(
    conn, worksheet, tmp_path, monkeypatch, every_kind_trusted
):
    """A person names a mistake of the sum only on the sum's own answer; a tick a person read is no measure of the
    reader; the second reader crops each answer from the page of the file it is on; and an answer a person already
    worked on gets its number on the copy when the copy is read again, its reading left as they left it."""
    code, ids, pdf, child = worksheet
    _, rows, keys_ = _read_copy(conn, worksheet, tmp_path, monkeypatch)
    est, ans = rows[(ids[1], "est")]["id"], rows[(ids[1], "ans")]["id"]
    conn.execute(
        "update item_result set status = 'wrong', misconception_codes = '{}' where id = any(%s)",
        ([est, ans],),
    )
    with pytest.raises(ValueError, match="not its question's sum"):
        naming.name_mistake(conn, est, mistake_guess.NONE, "test")
    assert naming.name_mistake(conn, ans, mistake_guess.NONE, "test")["code"] == mistake_guess.NONE
    tick = rows[(ids[4], "right")]["id"]
    marking.correct(conn, tick, "right", "test")
    seen = conn.execute(
        "select never_read, page, file_page from answer_checked where item_result_id = %s", (tick,)
    ).fetchone()
    assert seen["never_read"] and seen["page"] == seen["file_page"] == 1
    conn.execute(
        "update item_result set status = 'needs_teacher', raw_read = (raw_read::jsonb"
        ' || \'{"file_page": 2, "why": "under the floor"}\')::text where id = %s',
        (est,),
    )
    waiting = {str(r["id"]): r["page"] for r in second_reader._waiting(conn, [child])}
    assert waiting[str(est)] == 2, "cropped from the page of the file its photograph is"
    conn.execute("update item_result set raw_read = (raw_read::jsonb - 'slot')::text where id = %s", (tick,))
    copies.read(conn, tmp_path / "class.pdf", SECTION, ["Esha"], "test", pages_of=lambda c: len(pymupdf.open(pdf)),
                again=True)  # fmt: skip
    again_ = conn.execute("select raw_read::jsonb as raw from item_result where id = %s", (tick,)).fetchone()[
        "raw"
    ]
    assert again_["slot"].endswith(".right") and again_["why"] == boxes.FOR_A_PERSON


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
    # each card is shown under its question's number on this copy, recorded when it was read
    slots = {
        rid: conn.execute(
            "select result_slot(i.item_key, r.raw_read::jsonb) as slot, r.raw_read::jsonb ->> 'slot' as raw"
            " from item_result r join item i on i.id = r.item_id where r.id = %s",
            (rows[(ids[0], rid)]["id"],),
        ).fetchone()
        for rid in ("est", "ans")
    }
    assert (
        slots["est"]["slot"] == slots["ans"]["slot"] == slots["est"]["raw"] and slots["est"]["slot"].isdigit()
    )
    assert slots["ans"]["raw"] == slots["est"]["raw"] + ".ans"


def test_every_answer_names_a_response_of_its_question(
    conn, worksheet, tmp_path, monkeypatch, every_kind_trusted
):
    _, ids, _, _ = worksheet
    _, rows, _ = _read_copy(conn, worksheet, tmp_path, monkeypatch)
    keys_of = {r["item_key"] for r in conn.execute("select item_key from item where id = any(%s)", (ids,))}

    def mine():
        return [
            f for f in audit.every_answer_names_a_response_of_its_question(conn) if f.split()[0] in keys_of
        ]

    assert mine() == [], "every result this copy made is for an answer its question asks for"
    conn.execute("update item_result set rid = 'nope' where id = %s", (rows[(ids[0], "est")]["id"],))
    assert len(mine()) == 1 and "'nope'" in mine()[0], "one that is not is named"
