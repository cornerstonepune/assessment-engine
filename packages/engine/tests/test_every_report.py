"""Every parent report that is due, written at once (`w4_close/every_report.py`, goals/w4d-every-report-written.yaml).
Nimish, 2026-09-30: "the reports havent been generated for grade 3; please go ahead and generate all the reports".
Test_parent_report's Grade 2 child, Ria, with a classmate who has nothing signed off yet. The model is stood in for;
the database is the local copy, rolled back."""

import os
from contextlib import contextmanager

import pytest
from typer.testing import CliRunner

from engine.cli import app
from engine.w4_close import every_report
from engine.w4_close import parent_report as P
from tests import test_parent_report as parent_tests

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
NAME, writer, _good = parent_tests.NAME, parent_tests.writer, parent_tests._good
conn, child = (
    parent_tests.conn,
    parent_tests.child,
)  # the fixtures: Ria and her paper, on a rolled-back connection


@pytest.fixture
def shared(conn, monkeypatch):
    """Each report is written on connections of its own, as on the server; here they are the test's one, so the
    rolled-back children are seen and nothing written stays."""

    class Shared:
        def __getattr__(self, name):
            return getattr(conn, name)

        def commit(self):
            pass

    monkeypatch.setattr(P.db, "connect", contextmanager(lambda *a, **k: (yield Shared())))
    return conn


def _mine(conn, child, band=None):
    """This test's children among everyone due on the copy."""
    return [d for d in every_report.due(conn, band) if d["child_id"] == str(child)]


def test_every_report_due_is_written_and_one_still_true_is_left_as_it_is(shared, child, monkeypatch):
    """Nimish, 2026-09-30: "please go ahead and generate all the reports". A child with answers signed off and no report
    is due; one with nothing signed off is not; once written, a report still true of the answers is left alone, and
    an answer signed off after it makes it due again."""
    t = shared.execute("select tenant_id from child where id = %s", (child,)).fetchone()["tenant_id"]
    empty = shared.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s, '2', 'PR-TEST', 'G2') returning id",
        (t,),
    ).fetchone()["id"]

    (ria,) = _mine(shared, child)
    assert (ria["band"], ria["section"], ria["roll_no"], ria["why"]) == (
        "G2",
        "PR-TEST",
        "1",
        "no report yet",
    )
    assert NAME not in str(ria), "a child is named by class and roll, never by name"
    assert not _mine(shared, empty), "nothing signed off, nothing to report"
    assert not _mine(shared, child, "G3"), "only the band asked for"

    monkeypatch.setattr(
        P.llm, "generate", writer(lambda conn, purpose, variables, **k: _good(variables["facts"]))
    )
    done = every_report.write_each("nimish", [ria])
    assert [(d["child_id"], d["kept"], d["error"]) for d in done] == [(str(child), True, None)]
    note = P.latest(shared, child)
    assert note["stale"] is False and note["approved_by"] is None, "kept as a draft an educator approves"
    run = shared.execute(
        "select trigger from flow_run where flow = %s order by created_at desc limit 1", (P.FLOW,)
    ).fetchone()
    assert run["trigger"] == f"nimish: {child}", "a run of its own, as the page's button starts"
    assert not _mine(shared, child), "a report still true of the answers is left as it is"

    shared.execute(
        "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,"
        " observed_at, confirmed_by) values (%s,%s,'NUM.OPS.01','R21',true,'{}','item',now(),'t')",
        (t, child),
    )
    assert [d["why"] for d in _mine(shared, child)] == [
        "its facts changed since it was written: answers signed off, or the child's grade"
    ]


def test_a_report_not_kept_is_named_by_class_and_roll_and_the_command_fails(shared, child, monkeypatch):
    """Nimish, 2026-09-30: "the reports havent been generated for grade 3". Nothing said which were missing. The command
    names each child it wrote for, by class and roll, with whether the report was kept or why not, and fails while
    any report due was not kept."""

    def stubborn(conn, purpose, variables, meta=None, version=None):
        return {**_good(variables["facts"]), "summary": "[child] is weak at subtraction."}

    monkeypatch.setattr(P.llm, "generate", writer(stubborn))
    mine = _mine(shared, child)
    monkeypatch.setattr(every_report, "due", lambda conn, band=None: mine)
    out = CliRunner().invoke(
        app, ["report", "parents", "--by", "nimish"], env={"NO_COLOR": "1", "COLUMNS": "200"}
    )
    assert out.exit_code == 1, out.output
    assert "G2 PR-TEST roll 1" in out.output and "not kept" in out.output and "'weak'" in out.output
    assert "0 of 1 kept" in out.output and NAME not in out.output
    assert P.latest(shared, child) is None

    monkeypatch.setattr(
        P.llm, "generate", writer(lambda conn, purpose, variables, **k: _good(variables["facts"]))
    )
    out = CliRunner().invoke(
        app, ["report", "parents", "--by", "nimish"], env={"NO_COLOR": "1", "COLUMNS": "200"}
    )
    assert out.exit_code == 0 and "G2 PR-TEST roll 1  kept" in out.output and "1 of 1 kept" in out.output

    monkeypatch.setattr(every_report, "due", lambda conn, band=None: [])
    out = CliRunner().invoke(
        app, ["report", "parents", "--by", "nimish"], env={"NO_COLOR": "1", "COLUMNS": "200"}
    )
    assert out.exit_code == 0 and "nothing due" in out.output
