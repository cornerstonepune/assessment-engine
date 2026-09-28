"""N12 — a child's report in the shape of Aseem's (goals/w4b-report.yaml, `w4_close/report.py`), and the report read
back against his findings. A real paper is read, checked by a person and signed off on the way — the same path as
`test_gold.py`, whose helpers these reuse. On the copy, inside one rolled-back transaction."""

import os

import pytest
import test_gold

from engine.assess import graph
from engine.w3_read import gold, marking
from engine.w4_close import report

# the same child, paper and reading as W3's gold
conn, child, _read, _transcribe = test_gold.conn, test_gold.child, test_gold._read, test_gold._transcribe

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


def _signed_off(conn, child, tmp_path, monkeypatch, wrote):
    skill = _read(conn, child, tmp_path, monkeypatch, wrote)
    result = conn.execute(
        "select r.id from item_result r join item i on i.id = r.item_id where i.item_key = 'legacy/GOLD-TEST/1'"
    ).fetchone()["id"]
    marking.correct(conn, result, wrote, "a person")
    marking.confirm(conn, child, "a person")
    graph.rebuild(conn, child)
    return skill


def test_a_faulty_concept_comes_with_the_childs_own_example(conn, child, tmp_path, monkeypatch):
    """Nimish: "the system is able to see that there are certain areas where the child lags." The report says which
    mistake, how often, and shows it the way Aseem does — the question, what the child wrote, the right answer."""
    skill = _signed_off(conn, child, tmp_path, monkeypatch, "5147")
    got = report.build(conn, child)
    f = next(f for f in got["faulty"] if f["mistake"] == "M_SMALL_FROM_LARGE")
    assert f["times"] == 1 and f["skill_code"] == skill and f["name"]
    assert f["example"]["wrote"] == "5147" and "8" in f["example"]["question"]
    assert str(f["example"]["right"]) == "4853"
    assert got["strong"] == [], "one wrong answer makes nothing strong"


def test_the_report_reaches_aseems_finding_and_says_why_when_it_does_not(conn, child, tmp_path, monkeypatch):
    """Rule 11 (Nimish: "whenever you find an issue — don't apply a band aid; solve the root cause."): the report is
    checked against the findings of the reports it copies the shape of, not against itself."""
    skill = _signed_off(conn, child, tmp_path, monkeypatch, "5147")
    gold.load(conn, _transcribe(tmp_path, skill))
    gold.confirm(conn, "a person")
    reports = {str(child): report.build(conn, child)}
    got = [r for r in report.against(gold.check(conn), reports) if r["child_id"] == child]
    assert [r["in_report"] for r in got] == [True]

    empty = {str(child): {"strong": [], "faulty": [], "unexplained": [], "next": None}}
    missed = [r for r in report.against(gold.check(conn), empty) if r["child_id"] == child]
    assert missed[0]["in_report"] is False and missed[0]["why"] == "the mistake is not in the report"


def test_a_finding_the_papers_do_not_hold_is_counted_apart_and_strong_is_never_faulty():
    findings = [
        {
            "child_id": "a",
            "verdict": "strong",
            "skill_code": "S1",
            "misconception_code": None,
            "outcome": "in the graph",
        },
        {
            "child_id": "a",
            "verdict": "faulty",
            "skill_code": "S2",
            "misconception_code": None,
            "outcome": "not in the papers",
        },
    ]
    faulty = {
        "strong": [],
        "faulty": [{"mistake": "M_X", "skill_code": "S1"}],
        "unexplained": [],
        "next": None,
    }
    got = report.against(findings, {"a": faulty})
    assert got[0]["in_report"] is False and got[0]["why"] == "called faulty in the report"
    assert got[1]["in_report"] is None and got[1]["why"] == "not in the papers"


def test_a_report_over_http_is_the_reports_and_an_unknown_child_is_not_found(
    conn, child, tmp_path, monkeypatch
):
    from fastapi.testclient import TestClient

    from engine.api import deps
    from engine.api.app import app

    _signed_off(conn, child, tmp_path, monkeypatch, "5147")
    monkeypatch.setenv("ENGINE_KEY", "k")
    app.dependency_overrides[deps.get_conn] = lambda: (yield conn)
    try:
        with TestClient(app, headers={"X-Engine-Key": "k"}) as client:
            r = client.get(f"/report/{child}")
            assert r.status_code == 200, r.text
            assert r.json()["faulty"][0]["example"]["wrote"] == "5147"
            assert client.get("/report/00000000-0000-0000-0000-000000000000").status_code == 404
    finally:
        app.dependency_overrides.clear()
