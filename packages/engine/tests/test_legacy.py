"""N3 — a legacy paper becomes items, a scan becomes candidate results, a person's confirmation
becomes evidence, and the graph functions turn that into states and a next step. The model is
stubbed: what is under test is everything code does around it."""
import json
import os

import pytest

from engine import db, legacy
from engine.adapters import llm
from engine.assess import graph

# ---- pure: shape → rung, and marking by lookup

@pytest.mark.parametrize("text, expect", [
    ("348 + 27 =", ("+", 348, 27)),
    ("425 − 38", ("-", 425, 38)),        # U+2212, as the model writes minus
    ("42\n+16", ("+", 42, 16)),          # a column sum read as two lines still parses
    ("Simran picked 24 red apples", None),
])
def test_parse_expr(text, expect):
    assert legacy.parse_expr(text) == expect


@pytest.mark.parametrize("op, a, b, rung", [
    ("+", 42, 16, "R4"), ("+", 46, 38, "R5"), ("-", 52, 26, "R6"), ("-", 70, 38, "R6"),
    ("+", 286, 457, "R9"), ("-", 425, 38, "R9"), ("-", 500, 247, "R10"), ("+", 2345, 1678, "R12"),
])
def test_rung_from_shape(op, a, b, rung):
    assert legacy.rung_for(op, a, b) == rung


def _spec(kind="bare"):
    return {"kind": kind, "answer": 375}


def _resp():
    return {"answer": "375", "misconceptions": {"M_NOCARRY": 365, "M_FACT_PM1": 374}}


def test_mark_keeps_three_signals_apart():
    assert legacy.mark(_spec(), _resp(), {"child_answer": "375", "attempted": True, "working_summary": ""}) == ("correct", [], "none")
    assert legacy.mark(_spec(), _resp(), {"child_answer": "374", "attempted": True, "working_summary": "columns"}) == ("wrong", ["M_FACT_PM1"], "partial")
    assert legacy.mark(_spec(), _resp(), {"child_answer": "", "attempted": False, "working_summary": ""}) == ("blank", [], "none")
    # working but no final answer is not a blank and not a wrong: a person decides
    assert legacy.mark(_spec(), _resp(), {"child_answer": "", "attempted": True, "working_summary": "started columns"})[0] == "needs_teacher"
    assert legacy.mark(_spec(), _resp(), {"child_answer": "3?5", "attempted": True, "working_summary": ""})[0] == "unreadable"
    assert legacy.mark(_spec("text"), {"answer": None}, {"child_answer": "because it is big", "attempted": True, "working_summary": ""})[0] == "needs_teacher"


def test_normalise_answer_reads_units_and_commas():
    assert legacy.normalise_answer("43 apples") == "43"
    assert legacy.normalise_answer("ans=43") == "43"
    assert legacy.normalise_answer("A 48") == "48"
    assert legacy.normalise_answer("3?5") == "3?5"
    assert legacy.normalise_answer("1,264.") == "1264"
    assert legacy.normalise_answer("") == ""


# ---- with the database, inside one rolled-back transaction

pytestmark_db = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

PAPER = {
    "code": "TEST-PAPER", "title": "test", "band": "G2", "week": "test", "date": "2026-09-11",
    "pages": [{"n": 1, "mask": 0}],
    "items": [
        {"n": 1, "page": 1, "expr": "46 + 38", "question": "46 + 38"},
        {"n": 2, "page": 1, "expr": "57 + 28", "question": "57 + 28"},
        {"n": 3, "page": 1, "expr": "68 + 27", "question": "68 + 27"},
        {"n": 4, "page": 1, "expr": "59 + 24", "question": "59 + 24"},
        {"n": 5, "page": 1, "kind": "text", "rung": "X1", "question": "Explain."},
    ],
}

READ = {"page_note": "", "items": [
    {"n": 1, "part": "", "question_as_printed": "46 + 38", "child_answer": "84", "attempted": True, "working_summary": "", "self_corrected": False},
    {"n": 2, "part": "", "question_as_printed": "57 + 28", "child_answer": "75", "attempted": True, "working_summary": "columns", "self_corrected": False},  # M_NOCARRY
    {"n": 3, "part": "", "question_as_printed": "68 + 27", "child_answer": "85", "attempted": True, "working_summary": "", "self_corrected": False},        # M_NOCARRY again
    {"n": 4, "part": "", "question_as_printed": "59 + 24", "child_answer": "", "attempted": False, "working_summary": "", "self_corrected": False},
    {"n": 5, "part": "", "question_as_printed": "Explain.", "child_answer": "because", "attempted": True, "working_summary": "", "self_corrected": False},
    {"n": 9, "part": "", "question_as_printed": "extra", "child_answer": "1", "attempted": True, "working_summary": "", "self_corrected": False},
]}


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def child(conn):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    cid = conn.execute("insert into child (tenant_id, roll_no, section, band) values (%s,'1','TESTSEC','G2') returning id",
                       (tenant,)).fetchone()["id"]
    conn.execute("insert into pii.child (tenant_id, child_id, first_name) values (%s,%s,'Aarav')", (tenant, cid))
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
    assert conn.execute("select count(*) as n from sheet_template where batch_id = 'TEST-PAPER'").fetchone()["n"] == 1

    scan = tmp_path / "scan.jpg"
    scan.write_bytes(b"")
    monkeypatch.setattr(legacy, "render_pages", lambda p, pages=None: [b"jpeg"])
    monkeypatch.setattr(legacy, "mask_name_band", lambda j, f: j)
    asked = []
    monkeypatch.setattr(llm, "generate", lambda conn, purpose, variables, images=(): asked.append((purpose, variables)) or READ)

    s = legacy.import_scan(conn, scan, "TEST-PAPER", child, "test")
    assert asked == [("legacy_extract", {"expected": "5"})]
    by = {r["item"]: r for r in s["results"]}
    assert by["1"]["status"] == "correct"
    assert by["2"]["status"] == "wrong" and by["2"]["codes"] == ["M_NOCARRY"] and by["2"]["working"] == "partial"
    assert by["4"]["status"] == "blank"
    assert by["5"]["status"] == "needs_teacher"
    assert s["unmatched"] == ["9"]
    assert conn.execute("select status from capture where id = %s", (s["capture_id"],)).fetchone()["status"] == "processed"

    # nothing counts until a person confirms
    assert graph.next_difficulty(conn, child, "ADD.2D.REG") == (None, "band_default", [])
    assert conn.execute("select count(*) as n from child_skill_state where child_id = %s", (child,)).fetchone()["n"] == 0

    n = legacy.confirm(conn, child, "aseem")
    assert n == 4  # the needs_teacher row waits for a person
    ev = conn.execute("select rung_code, correct, misconception_codes from evidence_event where child_id = %s order by rung_code",
                      (child,)).fetchall()
    assert [(e["rung_code"], e["correct"]) for e in ev] == [("R5", True), ("R5", False), ("R5", False), ("R5", None)]

    states = {r["rung_code"]: r for r in conn.execute("select * from child_skill_state where child_id = %s", (child,)).fetchall()}
    assert states["R5"]["state"] == "patterned_error" and states["R5"]["repeating_misconception"] == "M_NOCARRY"
    assert (states["R5"]["n_events"], states["R5"]["n_correct"]) == (3, 1)

    # 1 of 3 on R5 is under demote_below: the next ADD.2D.REG sheet steps down and names the mistake
    assert graph.next_difficulty(conn, child, "ADD.2D.REG") == ("Easy", "from_state", ["M_NOCARRY"])

    # a person settles the row the machine could not; the map is rebuilt from it
    rid = conn.execute("select r.id from item_result r join item i on i.id = r.item_id where i.item_key = 'legacy/TEST-PAPER/5'").fetchone()["id"]
    conn.execute("select resolve_result(%s, 'correct', '{}', 'aseem')", (rid,))
    assert conn.execute("select state from item_result where id = %s", (rid,)).fetchone()["state"] == "confirmed"
    assert conn.execute("select n_events from child_skill_state where child_id = %s and rung_code = 'X1'", (child,)).fetchone()["n_events"] == 1
