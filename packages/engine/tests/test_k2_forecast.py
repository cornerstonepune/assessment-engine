"""The forecast reads what the calls cost once they have been made (goals/m1-12d-measured-forecast.yaml, task M1-12d).

Until a run has been paid for the token counts are assumptions (config row k2.drafting) and the forecast says so. After it
the cost of a call, and the share of pages a checker sent back, are read from flow_run and the ledger, and the forecast
says how many calls it learned them from. Rows of the test's own, rolled back."""

import os
import re

import pytest

from engine.w1_bank import k2_draft as draft
from engine.w1_bank import map_ledger
from engine.w1_bank.map_agents import Proposal
from tests import test_k2_draft as base

conn = base.conn
pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


def paid(conn, flow, inr, n, version=4, status="ok"):
    for _ in range(n):
        conn.execute(
            "insert into flow_run (tenant_id, flow, trigger, status, cost_inr, request) values (%s,%s,'engine:dev_eval',%s,%s,%s)",
            (conn.t, flow, status, inr, f'{{"version": {version}}}'),
        )


def dollars(text, word="about"):
    return float(re.search(rf"{word} \$([0-9.]+)", text).group(1))


def test_with_nothing_paid_for_yet_everything_is_assumed_and_the_forecast_says_so(conn):
    text = draft.forecast(conn, "dev_eval", 60)
    assert "assumed" in text and "measured" not in text.replace("not measured", "")


def test_the_cost_of_a_call_is_read_from_the_calls_made_once_there_are_enough_of_them(conn):
    before = draft.forecast(conn, "dev_eval", 60)
    paid(conn, "k2_page_draft", 400, 6)  # far dearer than assumed
    after = draft.forecast(conn, "dev_eval", 60)
    assert "k2_page_draft measured over 6 calls" in after
    assert dollars(after) > dollars(before) * 5
    assert "k2_page_check assumed" in after, "the checker has not been paid for yet"


def test_too_few_calls_are_not_enough_to_go_on(conn):
    paid(conn, "k2_page_draft", 400, 4)
    assert "token counts assumed, not measured" in draft.forecast(conn, "dev_eval", 60)


def test_only_answered_calls_of_the_version_that_will_be_asked_are_counted(conn):
    paid(conn, "k2_page_draft", 400, 6, version=3)  # the old maker
    paid(conn, "k2_page_draft", 400, 6, status="error")
    assert "token counts assumed, not measured" in draft.forecast(conn, "dev_eval", 60)


def _drafted(conn, n, sent_back):
    made = [
        Proposal(
            "page_part", f"KX-{i}", {"parts": {}, "flags": [], "history": [{"round": 1}] + ([{"round": 2}] if i < sent_back else [])},
            0.9, "k2_page_draft v4", "", [], "agree", "needs_person", "r",
        )
        for i in range(n)
    ]  # fmt: skip
    map_ledger.record(conn, conn.t, made, conn.staff)


def test_the_share_of_pages_sent_back_is_read_from_the_ledger_once_there_are_enough(conn):
    plain = draft.forecast(conn, "dev_eval", 60)
    _drafted(conn, 20, sent_back=20)  # every page was sent back
    every = draft.forecast(conn, "dev_eval", 60)
    assert "pages sent back measured over 20 pages" in every and dollars(every) > dollars(plain)
    assert "token counts assumed, not measured" in plain
