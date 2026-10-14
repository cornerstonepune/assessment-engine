"""An approval is withdrawn only by a person's change (supabase/migrations/20261006090000_only_what_is_taught.sql).

Nimish, 2026-09-23: "it is still showing 10 skills for me to approve" — the engine's upkeep rewrote each skill's list
of the mistakes its questions can show, and the versioning trigger read that as a new rule and withdrew the approval.
Against the real schema, rolled back."""

import os

import pytest

from engine.core import db

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        c.execute("update skill_set set status = 'ratified', ratified_by = 'Nimish' where code = 'SUB.2D2D'")
        yield c
        c.rollback()


def _status(conn):
    return conn.execute("select status, ratified_by from skill_set where code = 'SUB.2D2D'").fetchone()


def test_the_engine_keeping_the_mistake_list_up_to_date_never_withdraws_an_approval(conn):
    conn.execute(
        "update skill_set set misconception_codes = misconception_codes || '{M_TEST_ADDED}' where code = 'SUB.2D2D'"
    )
    assert dict(_status(conn)) == {"status": "ratified", "ratified_by": "Nimish"}


def test_a_person_changing_a_levels_rule_still_asks_for_approval_again(conn):
    """A level's rule — what makes its questions — changed by a person is a rule no one has approved. Its words alone are
    not its rule: since 2026-10-14 (goals/f1d-questions-approved-per-level.yaml, Nimish taking the coherence list's B3)
    an approval is of the questions, and rewording a skill withdraws nothing (tests/test_level_approval.py)."""
    conn.execute(
        "update skill_set set difficulty = jsonb_set(difficulty, '{Hard,check,edited}', 'true') where code = 'SUB.2D2D'"
    )
    assert dict(_status(conn)) == {"status": "draft", "ratified_by": None}
