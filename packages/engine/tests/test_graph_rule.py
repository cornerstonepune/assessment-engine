"""The graph's rule on recent evidence (goals/gr1-state-from-recent-evidence.yaml).

Nimish, 2026-11-03, from the learning-science review: the next paper's level pooled every answer at every level, a
repeating mistake never cleared, the share was all-time, "observers" counted papers, and ready-to-move-up was volume.
Each scenario is a ledger worked out by hand in the goal file; these tests run the same ledgers through the database,
so the goal and the suite can never say different things. Every test rolls back.
"""

import pytest
import yaml

from engine.checks import scenarios_graph
from engine.core import db
from tests.rows import tenant

GOAL = db.REPO_ROOT / "goals" / "gr1-state-from-recent-evidence.yaml"
SCENARIOS = {sc["name"]: sc for sc in yaml.safe_load(GOAL.read_text())["scenarios"]}


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _check(conn, name):
    sc = SCENARIOS[name]
    got, failures = scenarios_graph.run(conn, sc)
    assert failures == [], f"{name}: {got}"


def test_easy_answers_right_never_carry_a_child_past_medium_answers_wrong(conn):
    _check(
        conn, "Easy answers right never carry a child past Medium answers wrong (the review's own example)"
    )


def test_the_next_level_reads_the_last_two_papers_at_the_current_level(conn):
    for name in (
        "A repeating mistake clears after three right answers on a later paper",  # days 5 and 2 only: 6 of 8, stays
        "A latest paper under the bar takes secure away",  # days 21 and 3 only: 7 of 10, stays
    ):
        _check(conn, name)


def test_a_child_moved_up_and_not_yet_tested_stays_at_the_new_level(conn):
    _check(conn, "A child moved up and not yet tested at the new level stays there")


def test_two_september_mistakes_then_twenty_right_is_not_a_repeating_mistake(conn):
    _check(conn, "Two September mistakes then twenty right is not a repeating mistake")


def test_a_repeating_mistake_clears_after_later_right_answers(conn):
    _check(conn, "A repeating mistake is current and named")
    _check(conn, "A repeating mistake clears after three right answers on a later paper")


def test_a_level_reads_only_its_last_answers(conn):
    _check(
        conn, "A latest paper under the bar takes secure away"
    )  # day 0's five right are outside the window
    _check(conn, "Blanks are answers given, not right or wrong, and too few say not enough yet")


def test_two_papers_on_one_day_are_not_secure(conn):
    _check(conn, "Two papers on one day are not secure, however many answers they hold")


def test_a_latest_paper_under_the_bar_is_not_secure(conn):
    _check(conn, "A latest paper under the bar takes secure away")


def test_secure_is_provisional_until_a_paper_two_weeks_later(conn):
    _check(
        conn, "Two September mistakes then twenty right is not a repeating mistake"
    )  # days 9 and 12: to re-check
    _check(conn, "A paper two weeks later re-checks a level, and it is then ready to move up")


def test_a_harder_paper_two_weeks_later_rechecks_the_easier_level(conn):
    _check(conn, "A harder paper two weeks later re-checks the easier level")


def test_ready_to_move_up_is_rechecked_secure_with_a_harder_level(conn):
    _check(conn, "A paper two weeks later re-checks a level, and it is then ready to move up")
    _check(conn, "Re-checked at the hardest level is secure")


def _state(conn, days, adults):
    """The rule on a level that meets every other condition of secure, re-checked, with a harder level above."""
    return db.one(
        conn,
        "select public.graph_state_of(%s, 10, 1.0, %s, %s, null, 1.0, true, true) as s",
        (tenant(conn), days, adults),
    )["s"]


def test_observers_are_days_and_adults_who_saw_it(conn):
    """Days for every kind; adults only where the evidence names who saw it (a written answer names none: 0)."""
    assert _state(conn, 1, 0) == "practising"  # one day, however many papers
    assert _state(conn, 2, 0) == "stretch_ready"  # written: no adult named, days decide
    assert _state(conn, 2, 1) == "practising"  # observed by one adult only
    assert _state(conn, 2, 2) == "stretch_ready"


RULE_ROWS = {
    "state.min_events",
    "state.window_answers",
    "state.secure_min_answers",
    "state.min_days",
    "state.min_adults",
    "state.repeat_min",
    "state.repeat_clears_after",
    "state.recheck_days",
    "next_sheet.promote_at",
    "next_sheet.demote_below",
    "next_sheet.papers",
}


def test_every_number_of_the_rule_is_a_row(conn):
    """Every number the rule reads is a threshold row, and moving one moves the rule: three right answers no longer
    clear a mistake once the row asks for four."""
    have = {r["key"] for r in conn.execute("select key from threshold where tenant_id = %s", (tenant(conn),))}
    assert RULE_ROWS <= have
    assert "state.min_observers" not in have  # papers were never observers
    src = db.one(
        conn,
        "select string_agg(prosrc, ' ') as s from pg_proc where proname in"
        " ('graph_state_of', 'graph_level_window', 'next_difficulty')",
    )["s"]
    for key in RULE_ROWS:
        assert key in src, key
    conn.execute("update threshold set value = 4 where key = 'state.repeat_clears_after'")
    sc = dict(SCENARIOS["A repeating mistake clears after three right answers on a later paper"])
    got = scenarios_graph.measure(conn, sc)
    assert got["skill"] == "patterned_error" and got["repeating"] == "M_ALIGN_LEFT"


def test_the_new_state_is_a_row_not_counted_as_secure(conn):
    """'secure, to re-check' is a row of child_state: still worked on by a next paper, nearly secure in a parent's
    report, never counted secure in Levels to review or the report card."""
    row = db.one(
        conn,
        "select words, needs_work, enough, move_up, nearly from child_state where tenant_id = %s"
        " and code = 'secure_to_recheck'",
        (tenant(conn),),
    )
    assert row["words"] == "secure, to re-check"
    assert row["enough"] and row["needs_work"] and row["nearly"] and not row["move_up"]
