"""A campaign's cap can be a month's (task M1-16: "the cost of model calls for this step ... stays under a monthly cap
that is a setting"). `llm_budget` adds up a campaign's spend over all time; a campaign that names `"window": "month"` adds
up the school's current calendar month only, and starts again the month after. Written before the change."""

import os

import pytest

from engine.adapters import llm_budget
from engine.core import db

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

CAMP = {
    "purposes": ["materials_read"],
    "cap_usd": 2,
    "margin_usd": 0.25,
    "stale_minutes": 10,
    "inr_per_usd": 88,
    "window": "month",
}


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _call(conn, cost_inr, months_ago=0):
    conn.execute(
        "insert into flow_run (tenant_id, flow, trigger, status, cost_inr, started_at, finished_at)"
        " select id, 'materials_read', 'engine', 'ok', %s, now() - make_interval(months => %s),"
        " now() - make_interval(months => %s) from tenant where slug = %s",
        (cost_inr, months_ago, months_ago, db.tenant_slug()),
    )


def test_a_call_this_month_counts_and_stops_the_campaign_at_its_limit(conn):
    _call(conn, 176)  # ₹176 is $2.00 at ₹88: over the limit of $1.75
    with pytest.raises(llm_budget.Refused):
        llm_budget.check(conn, db.tenant_slug(), "materials_read", camps={"m1-16": CAMP})


def test_last_months_spend_does_not_count_against_this_months_cap(conn):
    _call(conn, 500, months_ago=2)
    llm_budget.check(conn, db.tenant_slug(), "materials_read", camps={"m1-16": CAMP})  # does not raise


def test_a_campaign_with_no_window_still_counts_all_time(conn):
    _call(conn, 500, months_ago=2)
    whole = {k: v for k, v in CAMP.items() if k != "window"}
    with pytest.raises(llm_budget.Refused):
        llm_budget.check(conn, db.tenant_slug(), "materials_read", camps={"m1-16": whole})


def test_a_stage_of_a_monthly_campaign_counts_the_same_month(conn):
    camp = CAMP | {"stages": {"eval": 1.0, "live": None}, "order": ["eval", "live"], "stage_margin_usd": 0}
    conn.execute(
        "insert into flow_run (tenant_id, flow, trigger, status, cost_inr, started_at, finished_at)"
        " select id, 'materials_read', 'engine:eval', 'ok', 500, now() - interval '2 months', now() - interval '2 months'"
        " from tenant where slug = %s",
        (db.tenant_slug(),),
    )
    llm_budget.check(
        conn, db.tenant_slug(), "materials_read", "eval", {"m1-16": camp}
    )  # last months's stage spend: not counted
