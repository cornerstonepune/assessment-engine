"""Pages held back by a style rule are recorded from the drafts already paid for, with no model call
(goals/m1-12p-advisory-rules.yaml). Every row is a placeholder in a band of the test's own, rolled back."""

import json
import os
import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from engine import cli
from engine.w1_bank import k2_record, map_ledger
from tests.test_k2_draft import BAND, _act, drafted
from tests.test_k2_draft import conn as conn  # the fixture, named so this module's fixtures can use it

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
LONG = "Show the child ten beads on the floor and ask the child to count every single bead out loud twice."


@pytest.fixture(autouse=True)
def soft_rules(conn):
    """The style rules do not hold a page back: the seed's list, whatever copy of the config the database holds."""
    seed = json.loads((Path(__file__).parents[3] / "supabase/seed/config.json").read_text())
    rules = next(r for r in seed["config"] if r["key"] == "k2.format")["value"]["advisory_rules"]
    conn.execute(
        "update config set value = jsonb_set(value, '{advisory_rules}', %s::jsonb) where key = 'k2.format'",
        (json.dumps(rules),),
    )


def kept(*items):
    return [("accepted", {"pages": list(items)})]


def record(conn, replies, write=True):
    lines: list[str] = []
    out = k2_record.record_kept(conn, conn.t, conn.staff, BAND, "draft", replies, write, lines.append)
    return out, lines


def standing(conn):
    return {r["subject_code"]: r for r in map_ledger.standing(conn, conn.t)}


def test_a_page_held_for_a_long_step_is_recorded_from_its_kept_draft_with_a_note_and_no_checker(conn):
    for c in ("KX-1", "KX-2"):
        _act(conn, c, f"Activity {c}")
    out, lines = record(conn, kept({"key": "KX-1", **drafted(steps=[LONG])}))
    row = standing(conn)["KX-1"]
    assert out["recorded"] == 1 and set(standing(conn)) == {"KX-1"}, "KX-2 had no kept draft: left alone"
    assert row["status"] == "needs_person" and row["reason"].startswith("recorded from a kept draft")
    assert "step_too_long" not in row["reason"] and "words" in row["reason"]
    assert row["proposal"]["parts"]["steps"] == [LONG] or "steps" in row["proposal"]["parts"]
    assert any("no model" in ln for ln in lines)


def test_a_draft_that_still_breaks_a_blocking_rule_is_not_recorded(conn):
    _act(conn, "KX-1", "Activity KX-1")
    out, _ = record(conn, kept({"key": "KX-1", **drafted(idea="He counts each bead.")}))
    assert out["recorded"] == 0 and standing(conn) == {} and out["no_accepted_draft"] == 1


def test_a_dry_run_counts_and_writes_nothing(conn):
    _act(conn, "KX-1", "Activity KX-1")
    out, _ = record(conn, kept({"key": "KX-1", **drafted(steps=[LONG])}), write=False)
    assert out["recorded"] == 1 and standing(conn) == {}


def test_a_page_already_recorded_is_not_recorded_twice(conn):
    _act(conn, "KX-1", "Activity KX-1")
    replies = kept({"key": "KX-1", **drafted(steps=[LONG])})
    record(conn, replies)
    again, _ = record(conn, replies)
    assert again["recorded"] == 0 and len(map_ledger.standing(conn, conn.t)) == 1


def test_the_report_names_rules_and_counts_and_no_page_text(conn):
    _act(conn, "KX-1", "Activity KX-1")
    out, lines = record(conn, kept({"key": "KX-1", **drafted(steps=[LONG])}))
    assert out["notes"] == {"step_too_long": 1}
    assert not any(LONG in ln or "KX-1" in ln for ln in lines)


def test_the_command_needs_a_name_for_a_real_run():
    got = CliRunner().invoke(cli.app, ["curriculum", "draft-record", "--stage", "draft"])
    assert got.exit_code != 0 and "--by" in re.sub(r"\x1b\[[0-9;]*m", "", got.output)


def test_apply_can_be_limited_to_the_pages_and_a_page_it_writes_is_a_check_me_draft_a_person_can_edit(conn):
    _act(conn, "KX-1", "Activity KX-1")
    record(conn, kept({"key": "KX-1", **drafted(steps=[LONG])}))
    none = map_ledger.apply(conn, conn.t, conn.staff, True, kind="material")
    assert none == [] and standing(conn)["KX-1"]["status"] == "needs_person"
    done = map_ledger.apply(conn, conn.t, conn.staff, True, kind="page_part")
    assert len(done) == 1
    row = conn.execute(
        "select steps, steps_list from activity where tenant_id = %s and code = 'KX-1'", (conn.t,)
    ).fetchone()
    assert row["steps"].startswith("•") and row["steps_list"] == [LONG]
    mark = conn.execute(
        "select source, check_me from activity_part_source where tenant_id = %s and activity_code = 'KX-1' and part = 'steps'",
        (conn.t,),
    ).fetchone()
    assert mark["source"] == "drafted" and mark["check_me"] is True
