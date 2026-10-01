"""A child's states, rebuilt from their answers by `rebuild_child_skill_state`, the one function every caller of
assess/graph.py and every signing-off function goes through."""

import os
import threading
import time

import pytest

from engine.core import db
from tests.rows import a_child, tenant

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

REBUILD = "select rebuild_child_skill_state(%s)"


def _a_child_with_an_answer() -> str:
    """Committed, so two connections see it: a child in a class of its own (`rows.a_child`), with one signed-off
    answer on a skill its rung holds, so no other test's count or check meets anything new."""
    with db.connect() as c:
        child = a_child(c)
        on = db.one(
            c,
            "select code, skill_codes[1] as skill from rung where tenant_id = %s and cardinality(skill_codes) > 0"
            " order by code limit 1",
            (tenant(c),),
        )
        c.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, channel, observed_at,"
            " confirmed_by) values (%s, %s, %s, %s, true, 'teacher_override', now(), 'a person')",
            (tenant(c), child, on["skill"], on["code"]),
        )
    return str(child)


def test_two_rebuilds_of_one_child_at_once_both_finish():
    """An educator signs a paper off while a deploy marks every answer again: two rebuilds of one child at once. Each
    deleted the states that were there before both began, and the second's insert failed on the first's rows with a
    duplicate key (goals/p2-live-recovers.yaml)."""
    child = _a_child_with_an_answer()
    failed: list[Exception] = []
    with db.connect() as first, db.connect() as second, db.connect() as look:
        first.execute(REBUILD, (child,))  # written, not yet committed

        def again():
            try:
                second.execute(REBUILD, (child,))
                second.commit()
            except Exception as e:  # what the second rebuild raised is the finding
                failed.append(e)
                second.rollback()

        thread = threading.Thread(target=again)
        thread.start()
        for _ in range(200):  # until the second is waiting on the first
            waiting = look.execute(
                "select wait_event_type from pg_stat_activity where pid = %s", (second.info.backend_pid,)
            ).fetchone()
            look.rollback()  # a transaction reads one snapshot of pg_stat_activity
            if waiting and waiting["wait_event_type"] == "Lock":
                break
            time.sleep(0.05)
        first.commit()
        thread.join(10)
    assert failed == []
    with db.connect() as c:
        assert (
            db.one(c, "select count(*) as n from child_skill_state where child_id = %s", (child,))["n"] == 1
        )
