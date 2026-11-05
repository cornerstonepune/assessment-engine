"""Two checkers on the same drafts, read side by side (goals/m1-12a-page-format.yaml, Nimish 2026-11-05: "run both
checkers on the 60"). The summary has counts and costs and nothing of the school's; the CSV has the words, for a person."""

import csv
import io
import os

import pytest

from engine.w1_bank import k2_checkers as ck
from tests import test_k2_draft as base

conn = base.conn
_act, run, drafted, Scripted, AGREE = base._act, base.run, base.drafted, base.Scripted, base.AGREE
pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


def fault(part, reason):
    return {"verdict": "disagree", "faults": [{"part": part, "reason": reason}]}


def cost(conn, flow, inr, n=1):
    for _ in range(n):
        conn.execute(
            "insert into flow_run (tenant_id, flow, trigger, status, cost_inr) values (%s, %s, 'engine:dev_eval', 'ok', %s)",
            (conn.t, flow, inr),
        )


@pytest.fixture
def two(conn):
    base._two_checkers(conn)
    for code in ("KX-1", "KX-2", "KX-3"):
        _act(conn, code, f"Activity {code}", objective="the school's objective", materials="Beads")
    # KX-1: both agree. KX-2: Opus finds steps, Sonnet finds steps and level_1. KX-3: Opus finds steps, Sonnet none.
    ask = Scripted(
        {
            **{("k2_page_draft", c): [drafted(uses=[])] for c in ("KX-1", "KX-2", "KX-3")},
            ("k2_page_check", "KX-1"): [AGREE],
            ("k2_page_check", "KX-2"): [fault("steps", "uses rope")],
            ("k2_page_check", "KX-3"): [fault("steps", "uses chalk")],
            ("k2_page_check_b", "KX-1"): [AGREE],
            ("k2_page_check_b", "KX-2"): [
                {
                    "verdict": "disagree",
                    "faults": [{"part": "steps", "reason": "rope"}, {"part": "level_1", "reason": "x"}],
                }
            ],
            ("k2_page_check_b", "KX-3"): [AGREE],
        }
    )
    run(conn, ask)
    return conn


def test_the_summary_counts_agreement_and_what_the_second_checker_missed_and_holds_no_words_of_the_school(
    two,
):
    s = ck.summary(two, two.t, "dev_eval")
    assert s["pages"] == 3
    assert s["pairs"] == {
        "verdicts_agree": 2, "verdicts_differ": 1, "found_every_fault": 2, "missed_a_fault": 1, "found_more": 1,
    }  # fmt: skip
    assert "rope" not in str(s) and "school" not in str(s)


def test_cost_per_page_is_each_checkers_own_spend_over_the_pages_and_the_stop_rule_is_read_from_it(two):
    cost(two, "k2_page_draft", 0.5, 2)  # the maker: Rs 1 over 3 pages
    cost(two, "k2_page_check", 0.3, 2)
    cost(two, "k2_page_check_b", 0.1, 2)
    s = ck.summary(two, two.t, "dev_eval")
    rate = s["inr_per_usd"]
    assert s["checkers"]["k2_page_check"]["usd_per_page"] == pytest.approx(0.6 / 3 / rate, rel=0.01)
    assert s["checkers"]["k2_page_check_b"]["usd_per_page"] == pytest.approx(0.2 / 3 / rate, rel=0.01)
    assert s["maker_usd_per_page"] == pytest.approx(1 / 3 / rate, rel=0.01)
    assert s["usd_per_page"] == pytest.approx((1 + 0.6 + 0.2) / 3 / rate, rel=0.01)
    assert s["within_stop_rule"] is True
    cost(two, "k2_page_draft", 200)
    assert ck.summary(two, two.t, "dev_eval")["within_stop_rule"] is False


def test_the_summary_names_each_checkers_model(two):
    s = ck.summary(two, two.t, "dev_eval")
    assert s["checkers"]["k2_page_check"]["model"] == "claude-opus-5-5"
    assert s["checkers"]["k2_page_check_b"]["model"] == "claude-sonnet-5-5"


def test_the_csv_has_one_row_a_page_with_each_checkers_faults_and_the_schools_words_beside_the_draft(two):
    rows = list(csv.DictReader(io.StringIO(ck.to_csv(ck.rows(two, two.t, "dev_eval")))))
    by = {r["code"]: r for r in rows}
    assert len(rows) == 3
    assert by["KX-2"]["first_verdict"] == "disagree" and by["KX-2"]["second_verdict"] == "disagree"
    assert "steps: uses rope" in by["KX-2"]["first_faults"]
    assert "level_1: x" in by["KX-2"]["second_faults"]
    assert (
        by["KX-2"]["second_found_every_first_fault"] == "yes"
        and by["KX-3"]["second_found_every_first_fault"] == "no"
    )
    assert (
        by["KX-1"]["school_objective"] == "the school's objective"
        and by["KX-1"]["school_materials"] == "Beads"
    )
    assert by["KX-1"]["draft_steps"].startswith("• s")
    assert by["KX-1"]["first_model"] == "claude-opus-5-5"


def test_a_page_with_one_checker_only_is_not_in_the_comparison(conn):
    _act(conn, "KX-1", "A")
    run(conn, Scripted({("k2_page_draft", "KX-1"): [drafted(uses=[])], ("k2_page_check", "KX-1"): [AGREE]}))
    assert ck.rows(conn, conn.t, "dev_eval") == [] and ck.summary(conn, conn.t, "dev_eval")["pages"] == 0
