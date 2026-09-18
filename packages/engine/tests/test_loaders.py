"""The loader must be idempotent.

Everything downstream joins to these codes. If a second run moved a single row, the registry
could not be trusted as the thing a child's result attaches to — and the damage would only
surface much later, as a skill state that quietly disagrees with the evidence behind it.

These tests hit the real Supabase project, so they skip when no DATABASE_URL is configured.
"""
import json
import os

import pytest

from engine import db, loaders

pytestmark = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)"
)

def test_load_does_not_overwrite_a_skill_set_edited_in_the_app():
    """Neha edits a set in the app; the next `engine load` must leave her words alone. An upsert
    here silently discarded her work, and she would have had no way to know."""
    with db.connect() as conn:
        before = conn.execute(
            "select difficulty from skill_set where code = 'SUB.2D.EXCH'").fetchone()["difficulty"]
        edited = {**before, "Easy": {"words": "edited in the app", "check": before["Easy"]["check"]}}
        conn.execute("update skill_set set difficulty = %s where code = 'SUB.2D.EXCH'",
                     (json.dumps(edited),))
        conn.commit()
    try:
        loaders.load_all()
        with db.connect() as conn:
            after = conn.execute(
                "select difficulty from skill_set where code = 'SUB.2D.EXCH'").fetchone()["difficulty"]
        assert after["Easy"]["words"] == "edited in the app"
    finally:
        with db.connect() as conn:
            conn.execute("update skill_set set difficulty = %s where code = 'SUB.2D.EXCH'",
                         (json.dumps(before),))
            conn.commit()


EXPECTED = {
    "tenant": 1,
    "skill": 37,
    "rung": 16,
    "level_rule": 12,
    "misconception": 27,
    "case_dimension": 18,
    "coverage_target": 46,
    "prompt": 7,
    "threshold": 10,
    "config": 6,
    "skill_set": 4,
}


@pytest.fixture(scope="module")
def loaded():
    return loaders.load_all()


def test_every_table_has_the_expected_number_of_rows(loaded):
    assert {k: loaded[k] for k in EXPECTED} == EXPECTED


def test_milestones_load_for_the_registry_skills(loaded):
    assert loaded["milestone"] > 100


def test_a_second_run_changes_nothing(loaded):
    assert loaders.load_all() == loaded


def test_no_code_refers_to_something_that_does_not_exist(loaded):
    assert {k: v for k, v in loaders.orphans().items() if v} == {}


def test_only_one_prompt_version_is_active_per_purpose(loaded):
    with db.connect() as conn:
        rows = conn.execute(
            "select purpose, count(*) as n from prompt where active group by purpose having count(*) > 1"
        ).fetchall()
    assert rows == []


def test_every_rung_band_is_a_band_the_levels_know_about(loaded):
    with db.connect() as conn:
        rows = conn.execute(
            "select distinct r.band from rung r"
            " where r.band not like '%+%'"
            " and not exists (select 1 from level_rule l where l.band = r.band)"
        ).fetchall()
    assert rows == [], f"rung bands with no level rule: {rows}"
