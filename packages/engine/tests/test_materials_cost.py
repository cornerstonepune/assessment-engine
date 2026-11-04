"""`engine materials cost` (task M1-16, brick 1): what the note-reading step has cost this month against its cap, from
the calls already recorded in `flow_run`. It only reads: it never calls a model. After the first real notes it replaces
the design note's assumed token counts with measured ones. Written before the code."""

import os

import pytest
from typer.testing import CliRunner

from engine.adapters import llm
from engine.cli import app
from engine.core import db
from engine.w2_print import materials_cost as cost

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        c.execute("delete from flow_run where flow = 'materials_read'")
        yield c
        c.rollback()


def _call(conn, inr, tin, tout, months_ago=0, status="ok"):
    conn.execute(
        "insert into flow_run (tenant_id, flow, trigger, status, cost_inr, tokens_in, tokens_out, started_at, finished_at)"
        " select id, 'materials_read', 'engine', %s, %s, %s, %s, now() - make_interval(months => %s),"
        " now() - make_interval(months => %s) from tenant where slug = %s",
        (status, inr, tin, tout, months_ago, months_ago, db.tenant_slug()),
    )


def test_this_months_calls_tokens_and_cost_are_counted_against_the_cap(conn, monkeypatch):
    monkeypatch.setattr(llm, "generate", lambda *a, **k: pytest.fail("the cost report must not call a model"))
    _call(conn, 4.4, 4000, 200)
    _call(conn, 8.8, 6000, 300)
    got = cost.report(conn)
    assert (got["calls"], got["tokens_in"], got["tokens_out"]) == (2, 10000, 500)
    assert got["cost_inr"] == pytest.approx(13.2)
    assert got["cost_usd"] == pytest.approx(13.2 / 88)
    assert got["cap_usd"] == 2 and got["limit_usd"] == 1.75
    assert got["share_of_limit"] == pytest.approx((13.2 / 88) / 1.75)
    assert got["avg_tokens_in"] == 5000 and got["avg_tokens_out"] == 250


def test_last_months_calls_are_not_this_months(conn):
    _call(conn, 500, 9000, 900, months_ago=2)
    assert cost.report(conn)["calls"] == 0


def test_a_call_that_failed_is_counted_separately_and_its_cost_still_counts(conn):
    _call(conn, 4.4, 4000, 200)
    _call(conn, 4.4, 4000, 0, status="error")
    got = cost.report(conn)
    assert (got["calls"], got["errors"]) == (2, 1) and got["cost_inr"] == pytest.approx(8.8)


def test_a_month_with_no_calls_says_so_without_dividing_by_nothing(conn):
    got = cost.report(conn)
    assert got["calls"] == 0 and got["avg_tokens_in"] is None and got["share_of_limit"] == 0


def test_the_command_prints_the_month_in_a_line_a_person_can_read(conn, monkeypatch):
    conn.commit()
    monkeypatch.setattr(llm, "generate", lambda *a, **k: pytest.fail("no model call"))
    _call(conn, 4.4, 4000, 200)
    conn.commit()
    try:
        out = CliRunner().invoke(app, ["materials", "cost"])
        assert out.exit_code == 0, out.output
        assert "this month: 1 calls" in out.output and "of the cap" in out.output
    finally:
        conn.execute("delete from flow_run where flow = 'materials_read'")
        conn.commit()


def test_a_call_still_running_is_not_counted_as_failed_and_the_spend_is_said_to_be_unknown(conn):
    _call(conn, 4.4, 4000, 200)
    conn.execute(
        "insert into flow_run (tenant_id, flow, trigger, status, started_at)"
        " select id, 'materials_read', 'engine', 'running', now() from tenant where slug = %s",
        (db.tenant_slug(),),
    )
    conn.execute(
        "insert into flow_run (tenant_id, flow, trigger, status, started_at, finished_at)"
        " select id, 'materials_read', 'engine', 'ok', now(), now() from tenant where slug = %s",
        (db.tenant_slug(),),
    )
    got = cost.report(conn)
    assert got["errors"] == 0 and got["running"] == 1 and got["cost_unknown"] == 1
    assert got["spend_known"] is False
