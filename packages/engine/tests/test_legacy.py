"""N3 — a legacy paper becomes items, a scan becomes candidate results, a person's confirmation
becomes evidence, and the graph functions turn that into states and a next step. The model is
stubbed: what is under test is everything code does around it."""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np
import pymupdf
import pytest

from engine import db, legacy
from engine.adapters import llm, ocr
from engine.assess import graph

# ---- pure: shape → rung, and marking by lookup


@pytest.mark.parametrize(
    "text, expect",
    [
        ("348 + 27 =", ("+", 348, 27)),
        ("425 − 38", ("-", 425, 38)),  # U+2212, as the model writes minus
        ("42\n+16", ("+", 42, 16)),  # a column sum read as two lines still parses
        ("Simran picked 24 red apples", None),
    ],
)
def test_parse_expr(text, expect):
    assert legacy.parse_expr(text) == expect


@pytest.mark.parametrize(
    "op, a, b, rung",
    [
        ("+", 42, 16, "R4"),
        ("+", 46, 38, "R5"),
        ("-", 52, 26, "R6"),
        ("-", 70, 38, "R6"),
        ("+", 286, 457, "R9"),
        ("-", 425, 38, "R9"),
        ("-", 500, 247, "R10"),
        ("+", 2345, 1678, "R12"),
    ],
)
def test_rung_from_shape(op, a, b, rung):
    assert legacy.rung_for(op, a, b) == rung


def _spec(kind="bare"):
    return {"kind": kind, "answer": 375}


def _resp():
    return {"answer": "375", "misconceptions": {"M_NOCARRY": 365, "M_FACT_PM1": 374}}


def test_mark_keeps_three_signals_apart():
    """Rule 5, and now ADR 0018's fourth case. `answer_state` is the reader saying which of four
    things it saw rather than the caller guessing from an empty string — v2 returned the same empty
    `child_answer` for "wrote nothing" and "wrote something I cannot read"."""

    def m(read, spec=None, resp=None):
        return legacy.mark(spec or _spec(), resp or _resp(), read)

    assert m({"child_answer": "375", "answer_state": "written", "working_summary": ""}) == (
        "correct",
        [],
        "none",
    )
    assert m({"child_answer": "374", "answer_state": "written", "working_summary": "columns"}) == (
        "wrong",
        ["M_FACT_PM1"],
        "partial",
    )
    assert m({"child_answer": "", "answer_state": "blank", "working_summary": ""}) == ("blank", [], "none")

    # working but no final answer is not a blank and not a wrong: a person decides
    assert m({"child_answer": "", "answer_state": "written", "working_summary": "started columns"})[0] == (
        "needs_teacher"
    )

    # writing that cannot be made out is never reported as a blank — the collapse rule 5 forbids
    assert m({"child_answer": "", "answer_state": "illegible", "working_summary": ""})[0] == "unreadable"
    assert m({"child_answer": "3?5", "answer_state": "written", "working_summary": ""})[0] == "unreadable"

    # only an educator's tick is visible: the outcome is knowable, the child's answer is not, and
    # working backwards from the tick would invent an answer out of an adult's opinion of it
    assert (
        m(
            {
                "child_answer": "",
                "answer_state": "not_visible",
                "educator_mark": "right",
                "working_summary": "",
            }
        )[0]
        == "needs_teacher"
    )

    assert (
        m(
            {"child_answer": "because it is big", "answer_state": "written", "working_summary": ""},
            spec=_spec("text"),
            resp={"answer": None},
        )[0]
        == "needs_teacher"
    )


def test_a_find_the_mistake_answer_is_marked_only_where_it_agrees_with_the_key():
    """The judgement is not checkable; the number is, and only on agreement.

    Such a question prints its operands and the wrong answer, so the region holds four or five
    numbers and the reader is not entitled to say which one the child stood behind. An agreement
    settles; a disagreement is as likely to be the wrong number picked as a child who is wrong,
    and marking it would put a silent error into a child's graph.
    """

    def m(read, resp):
        return legacy.mark(_spec("text"), resp, read)

    written = {"answer_state": "written", "working_summary": ""}
    # Aryan's 234 + 178: the child wrote 412 and the key says 412
    assert m({**written, "child_answer": "412"}, {"answer": 412})[0] == "correct"
    assert m({**written, "child_answer": "1,264"}, {"answer": "1264"})[0] == "correct"
    # a fragment read out of the working ("2" where the answer is 75) is never marked wrong
    assert m({**written, "child_answer": "2"}, {"answer": 75})[0] == "needs_teacher"
    # nor is a printed operand the child copied
    assert m({**written, "child_answer": "5432"}, {"answer": 3556})[0] == "needs_teacher"
    # a text item with no numeric key at all still goes to a person
    assert m({**written, "child_answer": "because it is big"}, {"answer": None})[0] == "needs_teacher"
    # and a blank is still a blank: the child did not attempt it (rule 5)
    assert m({"child_answer": "", "answer_state": "blank", "working_summary": ""}, {"answer": 412})[0] == (
        "blank"
    )


def test_working_shown_is_taken_from_the_reader_not_guessed_from_a_summary():
    """v2 had no way to say `full`, so a ponytail comment admitted every page read `partial`."""
    assert (
        legacy.mark(
            _spec(),
            _resp(),
            {
                "child_answer": "375",
                "answer_state": "written",
                "working_shown": "full",
                "working_summary": "full column method",
            },
        )[2]
        == "full"
    )


def test_normalise_answer_reads_units_and_commas():
    assert legacy.normalise_answer("43 apples") == "43"
    assert legacy.normalise_answer("ans=43") == "43"
    assert legacy.normalise_answer("A 48") == "48"
    assert legacy.normalise_answer("3?5") == "3?5"
    assert legacy.normalise_answer("1,264.") == "1264"
    assert legacy.normalise_answer("") == ""


def test_a_typed_answer_whose_key_is_not_a_number_is_marked_by_the_keys_own_form():
    """Nimish typed 12,34,45,78 for "Arrange from smallest to largest: 45, 12, 78, 34" and the answer
    never left the queue: the commas were stripped as if it were 1,264, the one number 12344578 met a
    key that is not a number, and it went back to a person — every time, for every child. 29 answers
    on the live queue had such a key (2026-09-21). Only a person's reading reaches this: the reader
    hands these slots over without a guess (`ocr.answers_for`)."""

    def m(key, wrote):
        return legacy.mark(
            {"kind": "missing"}, {"answer": key}, {"child_answer": wrote, "answer_state": "written"}
        )[0]

    assert m("12, 34, 45, 78", "12,34,45,78") == "correct"
    assert m("12, 34, 45, 78", "12 34 45 78") == "correct"
    assert m("12, 34, 45, 78", "12, 35, 45, 78") == "wrong"
    assert m("12, 34, 45, 78", "78, 45, 34, 12") == "wrong"  # largest first
    assert m("<", "<") == "correct"
    assert m("<", "456 < 465") == "correct"  # the whole statement typed, the sign is what is asked
    assert m("<", ">") == "wrong"
    assert m("True", "true") == "correct"
    assert m("Not true", "not  true") == "correct"
    assert m("Not true", "True") == "wrong"
    assert m("even", "Even") == "correct"
    assert m("1/2", "1 / 2") == "correct"
    assert m("375", "375") == "correct"  # a number key is still marked as a number


def test_a_typed_sign_and_a_lost_digit_are_named_as_aseem_named_them():
    """Two of his five reports name mistakes the vocabulary did not have: Labbhansh wrote 456 > 465,
    and Rudraksh wrote 6,243 for 62,413 (2026-09-21)."""
    wrote = {"answer_state": "written", "working_summary": ""}

    def m(key, predicted, child_answer, kind="bare"):
        return legacy.mark(
            {"kind": kind},
            {"answer": key, "misconceptions": predicted},
            {**wrote, "child_answer": child_answer},
        )[:2]

    assert m("<", {"M_COMPARE_REVERSED": ">"}, ">", kind="missing") == ("wrong", ["M_COMPARE_REVERSED"])
    assert m("<", {"M_COMPARE_REVERSED": ">"}, "=", kind="missing") == ("wrong", [])
    assert m("62413", {"M_FACT_PM10": 62423}, "6,243") == ("wrong", ["M_DIGIT_DROPPED"])
    # a predicted wrong answer wins; the rule is only for what nothing else explains
    assert m("62413", {"M_FACT_PM10": 62423}, "62423") == ("wrong", ["M_FACT_PM10"])
    # entering a comparison question stores the other sign as its predicted mistake
    item = legacy._template_item(
        {"code": "T"}, {"n": 1, "kind": "missing", "rung": "R11", "question": "456 ___ 465", "answer": "<"}
    )
    assert item["responses"][0]["misconceptions"] == {"M_COMPARE_REVERSED": ">"}


# ---- with the database, inside one rolled-back transaction

pytestmark_db = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)"
)

PAPER = {
    "code": "TEST-PAPER",
    "title": "test",
    "band": "G2",
    "week": "test",
    "date": "2026-09-11",
    "pages": [{"n": 1, "mask": 0}],
    "items": [
        {"n": 1, "page": 1, "expr": "46 + 38", "question": "46 + 38"},
        {"n": 2, "page": 1, "expr": "57 + 28", "question": "57 + 28"},
        {"n": 3, "page": 1, "expr": "68 + 27", "question": "68 + 27"},
        {"n": 4, "page": 1, "expr": "59 + 24", "question": "59 + 24"},
        {"n": 5, "page": 1, "kind": "text", "rung": "X1", "question": "Explain."},
    ],
}


def fake_ocr(monkeypatch, asked=None):
    """Stand in for Textract. `import_scan` reads with OCR now, not a model (ADR 0019), so the
    thing to stub is the adapter — and stubbing `answers_for` rather than `read` keeps the test
    about the import path instead of about page geometry, which `test_ocr.py` owns."""
    monkeypatch.setattr(ocr, "client", lambda *a, **k: None)
    monkeypatch.setattr(ocr, "read", lambda image, cli=None: {"lines": [], "words": []})

    def answers(page, slots, cfg=None, symbolic=(), boxes=(), reread=None):
        if asked is not None:
            asked.append(slots)
        return {
            r["slot"]: {
                "child_answer": r["child_answer"],
                "answer_state": r["answer_state"],
                "confidence": 99.0,
                # The real adapter derives this from handwriting in the region beyond the answer
                # itself; the fixture says the same thing with a summary, so mirror it rather than
                # hard-coding "none" and quietly dropping rule 5's third signal.
                "working_shown": r.get("working_shown")
                or ("partial" if r.get("working_summary") else "none"),
                "working_summary": r.get("working_summary", ""),
                "self_corrected": r.get("self_corrected", False),
                "educator_mark": r.get("educator_mark", "none"),
            }
            for r in READ["items"]
            if r["slot"] in slots
        }

    monkeypatch.setattr(ocr, "answers_for", answers)


READ = {
    "resolution": {"status": "complete", "saw": "a question page", "unresolved": []},
    "items": [
        {
            "slot": "1",
            "question_as_printed": "46 + 38",
            "child_answer": "84",
            "answer_state": "written",
            "working_summary": "",
            "self_corrected": False,
        },
        {
            "slot": "2",
            "question_as_printed": "57 + 28",
            "child_answer": "75",
            "answer_state": "written",
            "working_summary": "columns",
            "self_corrected": False,
        },  # M_NOCARRY
        {
            "slot": "3",
            "question_as_printed": "68 + 27",
            "child_answer": "85",
            "answer_state": "written",
            "working_summary": "",
            "self_corrected": False,
        },  # M_NOCARRY again
        {
            "slot": "4",
            "question_as_printed": "59 + 24",
            "child_answer": "",
            "answer_state": "blank",
            "working_summary": "",
            "self_corrected": False,
        },
        {
            "slot": "5",
            "question_as_printed": "Explain.",
            "child_answer": "because",
            "answer_state": "written",
            "working_summary": "",
            "self_corrected": False,
        },
        {
            "slot": "9",
            "question_as_printed": "extra",
            "child_answer": "1",
            "answer_state": "written",
            "working_summary": "",
            "self_corrected": False,
        },
    ],
}


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def child(conn):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    cid = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s,'1','TESTSEC','G2') returning id",
        (tenant,),
    ).fetchone()["id"]
    conn.execute(
        "insert into pii.child (tenant_id, child_id, first_name) values (%s,%s,'Aarav')", (tenant, cid)
    )
    return cid


@pytestmark_db
def test_paper_scan_confirm_graph(conn, child, tmp_path, monkeypatch, every_kind_trusted):
    path = tmp_path / "paper.json"
    path.write_text(json.dumps(PAPER))
    legacy.load_paper(conn, path)
    _, items = legacy.paper_rows(conn, "TEST-PAPER")
    assert items["1"]["spec"]["kind"] == "bare" and items["1"]["spec"]["answer"] == 84
    assert items["2"]["responses"][0]["misconceptions"]["M_NOCARRY"] == 75
    # re-entering the paper updates rather than duplicates
    legacy.load_paper(conn, path)
    assert (
        conn.execute("select count(*) as n from sheet_template where batch_id = 'TEST-PAPER'").fetchone()["n"]
        == 1
    )

    scan = tmp_path / "scan.jpg"
    scan.write_bytes(b"")
    monkeypatch.setattr(legacy, "render_pages", lambda p, pages=None: [b"jpeg"])
    monkeypatch.setattr(legacy, "mask_name_band", lambda j, f: j)
    asked = []
    fake_ocr(monkeypatch, asked)
    monkeypatch.setattr(
        llm,
        "generate",
        lambda conn, purpose, variables, images=(): asked.append((purpose, variables)) or READ,
    )

    s = legacy.import_scan(conn, scan, "TEST-PAPER", child, "test")
    # The reader is handed the page's answer SLOTS and their printed questions, so a slot it cannot
    # find reports itself rather than silently never appearing — the defect that lost three answers
    # per child on every sheet of one paper.
    assert len(asked) == 1
    slots = asked[0]
    assert sorted(slots) == ["1", "2", "3", "4", "5"]
    assert slots["1"] == "46 + 38"
    by = {r["item"]: r for r in s["results"]}
    assert by["1"]["status"] == "correct"
    # Two wrongs and a blank on the engine's reading alone wait for a person (ADR 0029), beside the
    # judgement question that always did. Rule 5's third signal is kept while it waits.
    assert [by[k]["status"] for k in ("2", "3", "4", "5")] == ["needs_teacher"] * 4
    assert by["2"]["working"] == "partial"
    # Nothing unmatched, and it cannot be: the reader is HANDED the slots the paper has, so a slot
    # that is not printed on the paper can never come back. The model path could return one — the
    # fixture still carries a slot 9 that this paper does not print — and the caller had to notice
    # and discard it. Being unable to invent is better than catching an invention.
    assert s["unmatched"] == []
    assert "9" not in {r["item"] for r in s["results"]}
    assert (
        conn.execute("select status from capture where id = %s", (s["capture_id"],)).fetchone()["status"]
        == "processed"
    )

    # nothing counts until a person confirms
    assert graph.next_difficulty(conn, child, "ADD.2D.REG") == (None, "band_default", [])
    assert (
        conn.execute("select count(*) as n from child_skill_state where child_id = %s", (child,)).fetchone()[
            "n"
        ]
        == 0
    )

    # A person says what the child wrote on the three the engine held, and the engine marks each by
    # lookup — the diagnosis is the engine's, the reading is the person's.
    held = {
        r["key"]: r["id"]
        for r in conn.execute(
            "select i.item_key as key, r.id from item_result r join item i on i.id = r.item_id"
            " where r.capture_id = %s",
            (s["capture_id"],),
        ).fetchall()
    }
    assert legacy.correct(conn, held["legacy/TEST-PAPER/2"], "75", "aseem")["codes"] == ["M_NOCARRY"]
    assert legacy.correct(conn, held["legacy/TEST-PAPER/3"], "85", "aseem")["status"] == "wrong"
    assert legacy.correct(conn, held["legacy/TEST-PAPER/4"], "", "aseem")["status"] == "blank"

    n = legacy.confirm(conn, child, "aseem")
    assert n == 4  # the needs_teacher row waits for a person
    ev = conn.execute(
        "select rung_code, correct, misconception_codes from evidence_event where child_id = %s order by rung_code",
        (child,),
    ).fetchall()
    # Four rows on one rung: one right, two wrong, one blank. Asserted as a tally and not as a
    # sequence, because the query orders by rung_code and every row here is R5 — Postgres may hand
    # them back in any order within that. This assertion used to be a list and failed about one run
    # in three, which is what made three other tests look flaky (STATE.md, 2026-09-20).
    assert [e["rung_code"] for e in ev] == ["R5"] * 4
    assert sorted((e["correct"] is None, e["correct"]) for e in ev) == [
        (False, False),
        (False, False),
        (False, True),
        (True, None),
    ]

    states = {
        r["rung_code"]: r
        for r in conn.execute("select * from child_skill_state where child_id = %s", (child,)).fetchall()
    }
    assert (
        states["R5"]["state"] == "patterned_error" and states["R5"]["repeating_misconception"] == "M_NOCARRY"
    )
    assert (states["R5"]["n_events"], states["R5"]["n_correct"]) == (3, 1)

    # 1 of 3 on R5 is under demote_below: the next ADD.2D.REG sheet steps down and names the mistake
    assert graph.next_difficulty(conn, child, "ADD.2D.REG") == ("Easy", "from_state", ["M_NOCARRY"])

    # a person settles the row the machine could not; the map is rebuilt from it
    rid = conn.execute(
        "select r.id from item_result r join item i on i.id = r.item_id where i.item_key = 'legacy/TEST-PAPER/5'"
    ).fetchone()["id"]
    conn.execute("select resolve_result(%s, 'correct', '{}', 'aseem')", (rid,))
    assert (
        conn.execute("select state from item_result where id = %s", (rid,)).fetchone()["state"] == "confirmed"
    )
    assert (
        conn.execute(
            "select n_events from child_skill_state where child_id = %s and rung_code = 'X1'", (child,)
        ).fetchone()["n_events"]
        == 1
    )


@pytestmark_db
def test_reimporting_the_same_file_returns_the_existing_capture(conn, child, tmp_path, monkeypatch):
    """The September batch's double count (HANDOFF.md): the same file read for the same child a
    second time must not create a second capture or ask the model again."""
    path = tmp_path / "paper.json"
    path.write_text(json.dumps(PAPER))
    legacy.load_paper(conn, path)

    scan = tmp_path / "scan.jpg"
    scan.write_bytes(b"the same bytes both times")
    monkeypatch.setattr(legacy, "render_pages", lambda p, pages=None: [b"jpeg"])
    monkeypatch.setattr(legacy, "mask_name_band", lambda j, f: j)
    asked = []
    fake_ocr(monkeypatch, asked)

    first = legacy.import_scan(conn, scan, "TEST-PAPER", child, "test")
    second = legacy.import_scan(conn, scan, "TEST-PAPER", child, "test")

    assert len(asked) == 1  # the second import never called the model
    assert second["capture_id"] == first["capture_id"]
    assert second["already"] is True and second["already_results"] == len(first["results"])
    n = conn.execute(
        "select count(*) as n from capture where sheet_instance_id ="
        " (select sheet_instance_id from capture where id = %s)",
        (first["capture_id"],),
    ).fetchone()["n"]
    assert n == 1


@pytestmark_db
def test_a_paper_a_person_signed_off_is_never_read_again(conn, child, tmp_path, monkeypatch):
    """A better reader re-reads the corpus. A paper a teacher has already signed off must keep her
    signature: superseding its capture would take her approved answers out of the child's ladder."""
    path = tmp_path / "paper.json"
    path.write_text(json.dumps(PAPER))
    legacy.load_paper(conn, path)
    scan = tmp_path / "scan.jpg"
    scan.write_bytes(b"signed off, then read again")
    monkeypatch.setattr(legacy, "render_pages", lambda p, pages=None: [b"jpeg"])
    monkeypatch.setattr(legacy, "mask_name_band", lambda j, f: j)
    asked = []
    fake_ocr(monkeypatch, asked)

    first = legacy.import_scan(conn, scan, "TEST-PAPER", child, "test")
    conn.execute("update item_result set state = 'confirmed' where capture_id = %s", (first["capture_id"],))
    again = legacy.import_scan(conn, scan, "TEST-PAPER", child, "test", again=True)
    _untouched(conn, asked, first, again)


@pytestmark_db
def test_a_paper_a_person_has_corrected_is_never_read_again(conn, child, tmp_path, monkeypatch):
    """Not signed off yet, only corrected: still a person's work. A re-read took six of Nimish's
    corrections before this was guarded."""
    path = tmp_path / "paper.json"
    path.write_text(json.dumps(PAPER))
    legacy.load_paper(conn, path)
    scan = tmp_path / "scan.jpg"
    scan.write_bytes(b"corrected, not yet signed, then read again")
    monkeypatch.setattr(legacy, "render_pages", lambda p, pages=None: [b"jpeg"])
    monkeypatch.setattr(legacy, "mask_name_band", lambda j, f: j)
    asked = []
    fake_ocr(monkeypatch, asked)

    first = legacy.import_scan(conn, scan, "TEST-PAPER", child, "test")
    rid = conn.execute(
        "select id from item_result where capture_id = %s limit 1", (first["capture_id"],)
    ).fetchone()["id"]
    legacy.correct(conn, rid, "42", "a teacher")
    again = legacy.import_scan(conn, scan, "TEST-PAPER", child, "test", again=True)
    _untouched(conn, asked, first, again)


def _untouched(conn, asked, first, again):
    assert len(asked) == 1  # not read a second time
    assert again["capture_id"] == first["capture_id"] and again["already"] is True
    live = conn.execute("select superseded_by from capture where id = %s", (first["capture_id"],)).fetchone()[
        "superseded_by"
    ]
    assert live is None


@pytestmark_db
def test_dedupe_supersedes_every_live_capture_but_the_best_one(conn, child, tmp_path):
    """A capture inserted twice for the same (sheet, file) — as the CLI produced before
    import_scan was idempotent — is reduced to one live row; nothing is deleted (rule 4)."""
    path = tmp_path / "paper.json"
    path.write_text(json.dumps(PAPER))
    legacy.load_paper(conn, path)
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    template = conn.execute("select id from sheet_template where batch_id = 'TEST-PAPER'").fetchone()["id"]
    instance = conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status)"
        " values (%s,'LEGACY-DEDUPE-TEST',%s,%s,'returned') returning id",
        (tenant, template, child),
    ).fetchone()["id"]

    scan = tmp_path / "scan.jpg"
    scan.write_bytes(b"dedupe me")
    first = conn.execute(
        "insert into capture (tenant_id, path, pages, sheet_instance_id, status) values (%s,%s,1,%s,'error')"
        " returning id",
        (tenant, str(scan), instance),
    ).fetchone()["id"]
    second = conn.execute(
        "insert into capture (tenant_id, path, pages, sheet_instance_id, status) values (%s,%s,1,%s,'processed')"
        " returning id",
        (tenant, str(scan), instance),
    ).fetchone()["id"]

    # dedupe operates tenant-wide, so other live captures already in the shared database are
    # swept up too (and, within this rolled-back transaction, deduped themselves) — only the
    # effect on this test's own two rows is asserted precisely.
    backfilled, voided = legacy.dedupe(conn)

    assert backfilled >= 2 and voided >= 1
    rows = {
        r["id"]: r
        for r in conn.execute(
            "select id, superseded_by, file_sha256 from capture where id in (%s,%s)", (first, second)
        ).fetchall()
    }
    assert rows[first]["superseded_by"] == second  # the errored one is voided in favour of the processed one
    assert rows[second]["superseded_by"] is None
    assert rows[first]["file_sha256"] == rows[second]["file_sha256"]

    # running it again is a no-op: nothing left to backfill or void
    assert legacy.dedupe(conn) == (0, 0)


@pytestmark_db
def test_a_correction_is_a_new_row_and_the_engine_marks_it_again(conn, child, tmp_path, monkeypatch):
    """The approval screen's whole mechanism (rule 4).

    A person says what the child wrote; the engine marks it again by lookup, because marking is a
    lookup and a teacher must never be asked to do arithmetic the engine can do. The machine's own
    reading stays exactly where it was — overwrite it and the reader can never again be scored
    against the page it read, which is the measurement the whole of W3 rests on.
    """
    path = tmp_path / "paper.json"
    path.write_text(json.dumps(PAPER))
    legacy.load_paper(conn, path)
    scan = tmp_path / "scan.jpg"
    scan.write_bytes(b"")
    monkeypatch.setattr(legacy, "render_pages", lambda p, pages=None: [b"jpeg"])
    monkeypatch.setattr(legacy, "mask_name_band", lambda j, f: j)
    fake_ocr(monkeypatch)
    legacy.import_scan(conn, scan, "TEST-PAPER", child, "test")

    row = conn.execute(
        "select r.id, r.raw_read, r.status from item_result r join item i on i.id = r.item_id"
        " where i.item_key = 'legacy/TEST-PAPER/2'"
    ).fetchone()
    assert (row["status"], json.loads(row["raw_read"])["child_answer"]) == ("needs_teacher", "75")

    out = legacy.correct(conn, row["id"], "85", "neha@school")
    assert (out["was"], out["now"], out["status"]) == ("75", "85", "correct")

    after = conn.execute(
        "select raw_read, status, misconception_codes from item_result where id = %s", (row["id"],)
    ).fetchone()
    assert json.loads(after["raw_read"])["child_answer"] == "75", (
        "the engine's own reading is never overwritten"
    )
    assert (after["status"], after["misconception_codes"]) == ("correct", [])

    # Looking again and changing your mind leaves BOTH rows behind, in order.
    legacy.correct(conn, row["id"], "", "neha@school")
    said = conn.execute(
        "select model_read, human_read, by from read_correction where item_result_id = %s order by created_at",
        (row["id"],),
    ).fetchall()
    assert [(s["model_read"], s["human_read"]) for s in said] == [("75", "85"), ("75", "")]
    assert (
        conn.execute("select status from item_result where id = %s", (row["id"],)).fetchone()["status"]
        == "blank"
    )


@pytestmark_db
def test_a_correction_feeds_the_next_measurement_of_the_reader(conn, child, tmp_path, monkeypatch):
    """A teacher's correction IS a hand-verified response, so the gold set the reader is measured
    against grows by using the system rather than by a data-entry project."""
    from engine import read_eval

    path = tmp_path / "paper.json"
    path.write_text(json.dumps(PAPER))
    legacy.load_paper(conn, path)
    scan = tmp_path / "scan.jpg"
    scan.write_bytes(b"")
    monkeypatch.setattr(legacy, "render_pages", lambda p, pages=None: [b"jpeg"])
    monkeypatch.setattr(legacy, "mask_name_band", lambda j, f: j)
    fake_ocr(monkeypatch)
    legacy.import_scan(conn, scan, "TEST-PAPER", child, "test")
    rid = conn.execute(
        "select r.id from item_result r join item i on i.id = r.item_id"
        " where i.item_key = 'legacy/TEST-PAPER/2'"
    ).fetchone()["id"]
    legacy.correct(conn, rid, "85", "neha@school")

    seed = read_eval.gold_sheets()
    grown = read_eval.gold_sheets(conn)
    assert sum(len(s["answers"]) for s in grown) > sum(len(s["answers"]) for s in seed)
    mine = next(s for s in grown if s["paper"] == "TEST-PAPER")
    assert mine["answers"] == [{"n": "2", "part": "", "child_answer": "85", "answer_state": "written"}]


@pytestmark_db
def test_signing_off_one_paper_does_not_sign_off_another(
    conn, child, tmp_path, monkeypatch, every_kind_trusted
):
    """A signature has to mean the person read the thing they signed. `confirm_results` took every
    candidate answer a child had, wherever it came from, which was right while the only screen was
    Child Growth — and wrong the moment a screen shows one photograph."""
    path = tmp_path / "paper.json"
    path.write_text(json.dumps(PAPER))
    legacy.load_paper(conn, path)
    monkeypatch.setattr(legacy, "render_pages", lambda p, pages=None: [b"jpeg"])
    monkeypatch.setattr(legacy, "mask_name_band", lambda j, f: j)
    fake_ocr(monkeypatch)
    first, second = tmp_path / "one.jpg", tmp_path / "two.jpg"
    first.write_bytes(b"one")
    second.write_bytes(b"two")
    a = legacy.import_scan(conn, first, "TEST-PAPER", child, "test")["capture_id"]
    b = legacy.import_scan(conn, second, "TEST-PAPER", child, "test")["capture_id"]

    n = conn.execute("select confirm_results(%s, 'neha', %s) as n", (child, a)).fetchone()["n"]
    # The one answer on that paper the engine may settle alone; its wrongs and blank wait for a person
    # and cannot be signed off past one (ADR 0029).
    assert n == 1
    live = {
        r["capture_id"]: r["n"]
        for r in conn.execute(
            "select capture_id, count(*) as n from item_result where state = 'confirmed'"
            " and capture_id in (%s, %s) group by capture_id",
            (a, b),
        ).fetchall()
    }
    assert live == {a: 1}, "the second paper is untouched until someone reads it"


def test_a_one_digit_sum_is_not_a_two_digit_column_sum():
    """The shape rule read "4 + 3" as width 2 with no regrouping and filed it under R4 — 2-digit
    columns — so a child who cannot add within 10 would have been recorded as failing at place
    value. The Cambridge Level D paper is entirely single digits, and it is the paper the weakest
    child in the school sat."""
    assert legacy.rung_for("+", 4, 3) == "R1"  # adds within 10
    assert legacy.rung_for("+", 7, 5) == "R2"  # crosses 10
    assert legacy.rung_for("-", 9, 4) == "R3"  # subtracts within 20
    assert legacy.rung_for("+", 23, 4) == "R4"  # and two digits still read as two digits
    assert legacy.rung_for("+", 148, 7) == "R9"


# ---- the scan, as a person is shown it


def _one_page_pdf(tmp_path, width, height):
    doc = pymupdf.open()
    doc.new_page(width=width, height=height)
    path = tmp_path / "scan.pdf"
    doc.save(path)
    doc.close()
    return path


@pytest.mark.parametrize(
    "width, height, long_side",
    [
        (2635, 3906, 2400),  # a WhatsApp "scan": a 36 x 54 inch page, 5490 x 8138 px at 150 dpi
        (595, 842, 1755),  # A4 at 150 dpi is already smaller, and is shown exactly as it was read
    ],
)
def test_a_page_is_shown_no_larger_than_a_screen_needs(tmp_path, width, height, long_side):
    jpeg = legacy.page_crop(_one_page_pdf(tmp_path, width, height), 1)
    assert max(cv2.imdecode(np.frombuffer(jpeg, np.uint8), cv2.IMREAD_COLOR).shape[:2]) == long_side


def test_a_burst_of_requests_for_one_paper_draws_it_once(tmp_path, monkeypatch):
    """The approval page asks for every answer's picture at once, and each request drew the whole
    paper for itself: twelve 45-megapixel drawings at the same moment took 3.3 GB on a 2 GB server,
    the engine was killed, and every picture on the live page came back broken (2026-09-21)."""
    path = _one_page_pdf(tmp_path, 200, 100)
    drawn = []
    draw = legacy.render_pages

    def slow(p, *args, **kwargs):
        drawn.append(p)
        time.sleep(0.2)  # long enough for all eight to arrive while the first is still drawing
        return draw(p, *args, **kwargs)

    monkeypatch.setattr(legacy, "render_pages", slow)
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda _: legacy.page_crop(path, 1), range(8)))
    assert len(drawn) == 1


@pytestmark_db
def test_marking_again_never_undoes_what_a_person_said(conn, child, tmp_path, monkeypatch):
    """`remark` rebuilt every mark from the reader's own reading, so after a person had said the child
    wrote 85 where the reader saw 75, marking again put the reader's 75 back — and a person's Right
    on a judgement went back to the queue. Found before it ever ran on live rows (2026-09-21)."""
    path = tmp_path / "paper.json"
    path.write_text(json.dumps(PAPER))
    legacy.load_paper(conn, path)
    scan = tmp_path / "scan.jpg"
    scan.write_bytes(b"")
    monkeypatch.setattr(legacy, "render_pages", lambda p, *a, **k: [b"jpeg"])
    monkeypatch.setattr(legacy, "mask_name_band", lambda j, f: j)
    fake_ocr(monkeypatch)
    s = legacy.import_scan(conn, scan, "TEST-PAPER", child, "test")
    two = conn.execute(
        "select r.id, r.status from item_result r join item i on i.id = r.item_id"
        " where r.capture_id = %s and i.item_key = 'legacy/TEST-PAPER/2'",
        (s["capture_id"],),
    ).fetchone()
    assert two["status"] == "needs_teacher"  # the reader saw 75 for 57 + 28, and a wrong waits (ADR 0029)

    legacy.correct(conn, two["id"], "85", "a person")
    legacy.remark(conn, child)

    after = conn.execute("select status from item_result where id = %s", (two["id"],)).fetchone()
    assert after["status"] == "correct"


@pytestmark_db
def test_a_judgement_is_never_counted_as_a_reading(conn, child, tmp_path, monkeypatch):
    """Pressing Right on "the child wrote 76" judges the answer, not the reading. The reader's gold set
    counted each judgement as a verified reading and scored the reader right on its own misread — a
    find-the-mistake 75 read as 76 (2026-09-21). A typed reading still counts."""
    path = tmp_path / "paper.json"
    path.write_text(json.dumps(PAPER))
    legacy.load_paper(conn, path)
    scan = tmp_path / "scan.jpg"
    scan.write_bytes(b"")
    monkeypatch.setattr(legacy, "render_pages", lambda p, *a, **k: [b"jpeg"])
    monkeypatch.setattr(legacy, "mask_name_band", lambda j, f: j)
    fake_ocr(monkeypatch)
    s = legacy.import_scan(conn, scan, "TEST-PAPER", child, "test")
    two = conn.execute(
        "select r.id, r.tenant_id, r.capture_id from item_result r join item i on i.id = r.item_id"
        " where r.capture_id = %s and i.item_key = 'legacy/TEST-PAPER/2'",
        (s["capture_id"],),
    ).fetchone()

    def gold():
        return [r["human_read"] for r in legacy.corrections(conn) if r["item_key"] == "legacy/TEST-PAPER/2"]

    conn.execute(
        "insert into read_correction (tenant_id, child_id, capture_id, item_result_id, model_read, human_read,"
        " by, judged) values (%s,%s,%s,%s,'75','75','a person','correct')",
        (two["tenant_id"], child, two["capture_id"], two["id"]),
    )
    assert gold() == []

    legacy.correct(conn, two["id"], "85", "a person")
    assert gold() == ["85"]


def _read_test_paper(conn, child, tmp_path, monkeypatch):
    """TEST-PAPER entered and one scan of it read → {item_key: row} of what the engine stored."""
    path = tmp_path / "paper.json"
    path.write_text(json.dumps(PAPER))
    legacy.load_paper(conn, path)
    scan = tmp_path / "scan.jpg"
    scan.write_bytes(b"")
    monkeypatch.setattr(legacy, "render_pages", lambda p, *a, **k: [b"jpeg"])
    monkeypatch.setattr(legacy, "mask_name_band", lambda j, f: j)
    fake_ocr(monkeypatch)
    s = legacy.import_scan(conn, scan, "TEST-PAPER", child, "test")
    return {
        r["key"].rsplit("/", 1)[1]: {**r, "read": json.loads(r["raw_read"])}
        for r in conn.execute(
            "select i.item_key as key, r.id, r.status, r.misconception_codes as codes, r.raw_read"
            " from item_result r join item i on i.id = r.item_id where r.capture_id = %s",
            (s["capture_id"],),
        ).fetchall()
    }


@pytestmark_db
def test_the_engine_settles_a_right_answer_alone_and_holds_a_wrong_or_blank_one(
    conn, child, tmp_path, monkeypatch, every_kind_trusted
):
    """ADR 0029. A misread almost never lands on the exact key, so a right answer the reader read
    stands; a wrong or a blank is as often the reader's failure as the child's — of 30 the engine had
    settled alone, 9 were right answers it had not read (STATE.md, 2026-09-21). Each waits for a
    person, its reading kept and offered as the guess, and counts once a person says what was written."""
    rows = _read_test_paper(conn, child, tmp_path, monkeypatch)
    assert rows["1"]["status"] == "correct"

    two, four = rows["2"], rows["4"]
    assert (two["status"], two["codes"]) == ("needs_teacher", [])
    assert (two["read"]["child_answer"], two["read"]["answer_state"]) == (
        "75",
        "written",
    )  # the reading stays
    assert (two["read"]["guess"], two["read"]["why"]) == ("75", legacy.HELD["wrong"])
    assert (four["status"], four["read"]["why"]) == ("needs_teacher", legacy.HELD["blank"])

    # the person's reading settles each, and the engine marks it by lookup as before
    out = legacy.correct(conn, two["id"], "75", "a person")
    assert (out["status"], out["codes"]) == ("wrong", ["M_NOCARRY"])
    assert legacy.correct(conn, four["id"], "", "a person")["status"] == "blank"


@pytestmark_db
def test_marking_again_holds_a_wrong_or_blank_the_engine_had_settled_alone(
    conn, child, tmp_path, monkeypatch, every_kind_trusted
):
    """Every live answer was marked before ADR 0029, so 185 wrongs and 95 blanks stood on the engine's
    reading alone. Marking again puts each in front of a person, leaves an answer a person settled
    exactly as the person left it, and changes nothing the second time."""
    rows = _read_test_paper(conn, child, tmp_path, monkeypatch)
    for k, status in (("2", "wrong"), ("4", "blank")):  # as the old rule stored them
        read = {f: v for f, v in rows[k]["read"].items() if f not in ("why", "guess")}
        conn.execute(
            "update item_result set status = %s, raw_read = %s where id = %s",
            (status, json.dumps(read), rows[k]["id"]),
        )
    legacy.correct(conn, rows["3"]["id"], "85", "a person")
    assert legacy.remark(conn, child) == 2

    after = {
        r["id"]: r
        for r in conn.execute(
            "select id, status, raw_read from item_result where id = any(%s)",
            ([rows[k]["id"] for k in ("1", "2", "3", "4")],),
        ).fetchall()
    }
    assert [after[rows[k]["id"]]["status"] for k in ("1", "2", "3", "4")] == [
        "correct",
        "needs_teacher",
        "wrong",  # the person's reading, untouched
        "needs_teacher",
    ]
    assert json.loads(after[rows["2"]["id"]]["raw_read"])["guess"] == "75"
    assert legacy.remark(conn, child) == 0


# ---------------------------------------------------------------- ADR 0032: the reader learns


def test_a_right_answer_waits_for_a_person_until_its_kind_of_question_is_trusted():
    """Until the reader's readings of a kind have matched people 95% of the time over the last fifty
    checks, a right answer waits too — its reading the one-click guess. A wrong or a blank waited already."""
    read = {"child_answer": "84", "answer_state": "written", "confidence": 97.0}
    assert legacy.mark_read(_spec(), {"answer": 84}, read)[0] == "correct"
    assert (
        legacy.mark_read(_spec(), {"answer": 84}, read, {"n": 50, "right": 50, "trusted": True})[0]
        == "correct"
    )
    status, codes, _, held = legacy.mark_read(
        _spec(), {"answer": 84}, read, {"n": 50, "right": 41, "trusted": False}
    )
    assert (status, codes, held["guess"]) == ("needs_teacher", [], "84")
    assert (
        held["why"]
        == "read as a right answer; a person checks every answer of this kind until the reader is trusted on it (41 of the last 50 right)"
    )
    assert legacy.mark_read(_spec(), {"answer": 84}, read, legacy.UNTRUSTED)[0] == "needs_teacher"


@pytestmark_db
def test_the_childs_notebook_changes_the_next_import_of_that_child(
    conn, child, tmp_path, monkeypatch, every_kind_trusted
):
    """The loop: a person's checks on this child's earlier papers, and the next paper reads differently.
    Slot 1 reads 84 at 99%; this child's 8 has been read for a 3 twice, so it is flagged with 84 as
    the one-click guess, and the reader is handed her own floor."""
    import json as _json

    from engine import profiles

    path = tmp_path / "paper.json"
    path.write_text(json.dumps(PAPER))
    legacy.load_paper(conn, path)
    scan = tmp_path / "scan.jpg"
    scan.write_bytes(b"")
    monkeypatch.setattr(legacy, "render_pages", lambda p, pages=None: [b"jpeg"])
    monkeypatch.setattr(legacy, "mask_name_band", lambda j, f: j)
    fake_ocr(monkeypatch)
    floors = []
    real = ocr.answers_for

    def probe(page, slots, cfg=None, *a, **kw):
        floors.append(cfg["min_confidence"])
        return real(page, slots, cfg, *a, **kw)

    monkeypatch.setattr(ocr, "answers_for", probe)
    notes = profiles.build(
        [
            {
                "fmt": "legacy_bare",
                "model_read": "84",
                "human_read": "34",
                "confidence": 96.0,
                "why": "",
                "answer_state": "written",
                "guess": "",
                "capture_id": "c",
                "page": 1,
                "box": None,
            }
        ]
        * 2
        + [
            {
                "fmt": "legacy_bare",
                "model_read": "5",
                "human_read": "5",
                "confidence": 60.0,
                "why": "",
                "answer_state": "written",
                "guess": "",
                "capture_id": "c",
                "page": 1,
                "box": None,
            }
        ]
        * 10
    )
    assert notes["confusions"] == {"8>3": 2} and notes["floor"] == 70
    conn.execute(
        "insert into child_reading_profile (tenant_id, child_id, notes) select tenant_id, id, %s from child where id = %s",
        (_json.dumps({**notes, "floor": 90}), child),
    )
    s = legacy.import_scan(conn, scan, "TEST-PAPER", child, "test")
    assert floors == [90.0]
    one = next(r for r in s["results"] if r["item"] == "1")
    assert one["status"] == "unreadable"  # the reader's own doubt, with the guess beside it
    stored = conn.execute(
        "select r.raw_read from item_result r join item i on i.id = r.item_id where right(i.item_key, 2) = '/1' and r.capture_id = %s",
        (s["capture_id"],),
    ).fetchone()["raw_read"]
    stored = _json.loads(stored) if isinstance(stored, str) else stored
    assert stored["why"] == "this child's 8 has been read for a 3 before" and stored["guess"] == "84"


@pytestmark_db
def test_a_person_s_corrections_change_the_childs_next_paper_with_no_command_in_between(
    conn, child, tmp_path, monkeypatch, every_kind_trusted
):
    """The loop as a teacher lives it (ADR 0032): she corrects two answers where the reader took this
    child's 3 for an 8, and the child's NEXT paper comes back with its 8s held for her — nobody ran
    `engine read profile` in between."""
    import json as _json

    path = tmp_path / "paper.json"
    path.write_text(json.dumps(PAPER))
    legacy.load_paper(conn, path)
    monkeypatch.setattr(legacy, "render_pages", lambda p, pages=None: [b"jpeg"])
    monkeypatch.setattr(legacy, "mask_name_band", lambda j, f: j)
    fake_ocr(monkeypatch)
    first = tmp_path / "week1.jpg"
    first.write_bytes(b"one")
    week1 = legacy.import_scan(conn, first, "TEST-PAPER", child, "test")
    ids = {
        r["item_key"].rsplit("/", 1)[1]: r["id"]
        for r in conn.execute(
            "select r.id, i.item_key from item_result r join item i on i.id = r.item_id where r.capture_id = %s",
            (week1["capture_id"],),
        ).fetchall()
    }
    legacy.correct(conn, ids["1"], "34", "a teacher")  # the reader said 84
    legacy.correct(conn, ids["3"], "35", "a teacher")  # the reader said 85

    second = tmp_path / "week2.jpg"
    second.write_bytes(b"two")
    week2 = legacy.import_scan(conn, second, "TEST-PAPER", child, "test")
    raw = conn.execute(
        "select r.raw_read from item_result r join item i on i.id = r.item_id"
        " where r.capture_id = %s and right(i.item_key, 2) = '/1'",
        (week2["capture_id"],),
    ).fetchone()["raw_read"]
    read = _json.loads(raw) if isinstance(raw, str) else raw
    assert read["why"] == "this child's 8 has been read for a 3 before" and read["guess"] == "84"
    # and in week 1, before any correction, the same reading was stood behind
    assert next(r for r in week1["results"] if r["item"] == "1")["status"] == "correct"
