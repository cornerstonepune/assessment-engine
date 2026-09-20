"""N3 — a legacy paper becomes items, a scan becomes candidate results, a person's confirmation
becomes evidence, and the graph functions turn that into states and a next step. The model is
stubbed: what is under test is everything code does around it."""

import json
import os

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

    def answers(page, slots, cfg=None):
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
def test_paper_scan_confirm_graph(conn, child, tmp_path, monkeypatch):
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
    assert (
        by["2"]["status"] == "wrong" and by["2"]["codes"] == ["M_NOCARRY"] and by["2"]["working"] == "partial"
    )
    assert by["4"]["status"] == "blank"
    assert by["5"]["status"] == "needs_teacher"
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
