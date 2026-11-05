"""The kept replies of a draft run, judged again by code (goals/m1-12d-draft-replay.yaml).

A paid reply is kept on its flow_run row. Judging those replies again with the run's own judge says which rule each
page broke on each ask, with no model call and no page text: counts and rule names only (the job log is public)."""

import json
import os
from datetime import UTC, datetime, timedelta

import pytest

from engine.w1_bank import k2_replay as rp
from tests import test_k2_draft as base
from tests.test_k2_format import FMT, ROWS, RULES, VOCAB, WANT, fmt, page

conn = base.conn
JUDGE = fmt.judger(ROWS, VOCAB, FMT, RULES)
LONG = ["Show ten beads on the floor and ask the child to count each one aloud twice, slowly."]


def tally(*replies, want=None):
    return rp.tally([("accepted", r) for r in replies], want or WANT, JUDGE)


def test_each_ask_of_a_page_is_counted_with_the_rule_it_broke():
    got = tally([page(steps=LONG)], [page(steps=LONG)], [page()])
    assert got["replies"] == 3 and got["refused"] == 0
    assert got["attempts"] == [
        {"attempt": 1, "asked": 1, "good": 0, "faults": {"step_too_long": 1}},
        {"attempt": 2, "asked": 1, "good": 0, "faults": {"step_too_long": 1}},
        {"attempt": 3, "asked": 1, "good": 1, "faults": {}},
    ]
    assert got["pages_good"] == 1 and got["pages_never_good"] == 0


def test_a_reply_in_the_prompts_own_shape_an_object_holding_the_pages_is_judged_as_the_run_judged_it():
    got = tally({"pages": [page()]}, {"pages": [page(steps=LONG)]})
    assert got["pages_good"] == 1 and got["pages_never_good"] == 0
    assert got["attempts"][0] == {"attempt": 1, "asked": 1, "good": 1, "faults": {}}
    assert got["attempts"][1]["faults"] == {"step_too_long": 1}, "never 'missing': the page is in the reply"


def test_a_page_never_good_is_counted_and_a_refused_reply_is_a_reply_with_nothing_in_it():
    got = rp.tally([("refused", [page()]), ("accepted", [page(steps=LONG)])], WANT, JUDGE)
    assert got["replies"] == 2 and got["refused"] == 1
    assert got["pages_good"] == 0 and got["pages_never_good"] == 1
    assert got["attempts"][0]["faults"] == {"step_too_long": 1}


def test_a_key_nobody_asked_for_is_not_counted_and_the_output_holds_no_page_text():
    got = tally([page(key="ZZ", steps=LONG), page(steps=LONG)])
    assert got["attempts"][0]["asked"] == 1
    assert "beads" not in json.dumps(got).casefold() and "child" not in json.dumps(got).casefold()


def test_the_rules_are_named_in_the_report_most_often_broken_first():
    lines = rp.lines(tally([page(steps=LONG)], [page(steps=LONG)]))
    assert json.loads(lines[0]) == {"replies": 2, "refused": 0, "pages_good": 0, "pages_never_good": 1}
    assert json.loads(lines[1])["faults"] == {"step_too_long": 1}


pytestmark_db = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)"
)


@pytestmark_db
def test_the_latest_run_is_read_from_the_rows_of_the_stage_and_an_older_run_is_left_out(conn):
    now = datetime.now(UTC)

    def keep(minutes, outcome, reply):
        conn.execute(
            "insert into flow_run (tenant_id, flow, trigger, status, started_at, result)"
            " values (%s, 'k2_page_draft', 'engine:dev_eval', 'ok', %s, %s)",
            (conn.t, now + timedelta(minutes=minutes), json.dumps({"outcome": outcome, "reply": reply})),
        )

    keep(0, "accepted", [{"key": "OLD"}])
    keep(60, "accepted", [{"key": "NEW1"}])
    keep(61, "refused", [])
    got = rp.stored(conn, "dev_eval", gap_minutes=10.0)
    assert [o for o, _ in got][-2:] == ["accepted", "refused"] and all(r != [{"key": "OLD"}] for _, r in got)
