"""The loader must be idempotent.

Everything downstream joins to these codes. If a second run moved a single row, the registry
could not be trusted as the thing a child's result attaches to — and the damage would only
surface much later, as a skill state that quietly disagrees with the evidence behind it.

These tests hit the real Supabase project, so they skip when no DATABASE_URL is configured.
"""

import json
import os
import pathlib

import pytest

from engine import db, loaders

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


def test_load_does_not_overwrite_a_skill_set_edited_in_the_app():
    """Neha edits a set in the app; the next `engine load` must leave her words alone. An upsert here
    silently discarded her work, and she would have had no way to know.

    Everything happens on one connection and is rolled back. The earlier version committed the edit
    so that `load_all()`'s own connection could see it — which made this the only test that wrote to
    a live spec row, and it showed: two suite runs at once left `SUB.2D.EXCH` edited and unratified,
    and three "flaky" failures elsewhere in the suite were that state, not their own code. The loader
    for this one table is called directly instead, which needs no commit and proves the same clause.
    """
    with db.connect() as conn:
        tenant = loaders._tenant(conn)
        before = conn.execute("select difficulty from skill_set where code = 'SUB.2D.EXCH'").fetchone()[
            "difficulty"
        ]
        edited = {**before, "Easy": {"words": "edited in the app", "check": before["Easy"]["check"]}}
        conn.execute("update skill_set set difficulty = %s where code = 'SUB.2D.EXCH'", (json.dumps(edited),))

        loaders._skill_sets(conn, tenant)  # what `engine load` does for this table, same transaction

        after = conn.execute("select difficulty, status from skill_set where code = 'SUB.2D.EXCH'").fetchone()
        assert after["difficulty"]["Easy"]["words"] == "edited in the app", (
            "the seed overwrote a person's words"
        )
        conn.rollback()
        live = conn.execute("select difficulty from skill_set where code = 'SUB.2D.EXCH'").fetchone()
        assert live["difficulty"]["Easy"]["words"] == before["Easy"]["words"], "and nothing was left behind"


EXPECTED = {
    "tenant": 1,
    "domain": 14,
    "skill": 244,  # the whole map, all 14 domains — not the maths slice
    "milestone": 849,
    "learning_objective": 1750,
    "learning_objective_skill": 2012,
    "activity": 2216,
    "activity_skill": 3711,
    "report_item": 885,
    "trait": 56,
    "rung": 17,
    "level_rule": 12,
    "misconception": 39,
    "case_dimension": 18,
    "coverage_target": 46,
    "prompt": 19,  # + pedagogy_review, language_review (gate 4), misconception_list v1-v4,
    #                question_extract v1+v2 and skill_match v1 (W3, placing a non-ladder paper),
    #                legacy_extract v3+v4 (ADR 0018's contract, then the slot list of ADR 0019)
    "threshold": 12,
    "config": 8,
    "skill_set": 17,
    "subject": 1,
}


@pytest.fixture(scope="module")
def loaded():
    return loaders.load_all()


# The vocabulary is the one table the seed does not own outright: `engine bank misconceptions --apply`
# adds what a prompt found, and `engine bank unclassified` will add what children write. An exact
# count here would fail every time the engine legitimately learned a mistake, so the seed's rows are
# a floor and each one must be present.
GROWS = {"misconception"}


def test_every_table_has_the_expected_number_of_rows(loaded):
    fixed = {k: v for k, v in EXPECTED.items() if k not in GROWS}
    assert {k: loaded[k] for k in fixed} == fixed


def test_the_vocabulary_holds_every_seeded_mistake_and_may_hold_more(loaded):
    seed = json.loads(
        (pathlib.Path(__file__).resolve().parents[3] / "supabase/seed/misconceptions.json").read_text()
    )
    want = {(m["code"], m["op"]) for m in seed["misconceptions"]}
    with db.connect() as conn:
        have = {(r["code"], r["op"]) for r in conn.execute("select code, op from misconception").fetchall()}
    assert want <= have, f"the seed's own mistakes are missing: {sorted(want - have)}"
    assert loaded["misconception"] >= len(want)


def test_milestones_load_for_the_registry_skills(loaded):
    assert loaded["milestone"] > 100


def test_a_second_run_changes_nothing(loaded):
    assert loaders.load_all() == loaded


def test_no_two_bands_of_one_skill_set_declare_the_same_region(loaded):
    """Two bands with one rule draw from one pool and starve each other — R1's Medium and Hard
    did exactly this until Hard was pinned to a story (BUILD-ORDER gate 4, amended)."""
    assert loaders.orphans()["skill_set bands sharing one region"] == []


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
