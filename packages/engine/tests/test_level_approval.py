"""Questions approved level by level (goals/f1d-questions-approved-per-level.yaml, ADR 0073 D2).

Nimish, 2026-10-14: "When I approve a skill, it gets approved throughout all the grades. If I just want to approve
something for a grade level today, I'm not able to do that." A level's questions are approved once, by the coordinator
(a right question is right for every grade); which levels a grade uses is the grade's own plan (F1e). Each level keeps
its own approval: only a change to what makes its questions withdraws it.
"""

import json
import os

import pytest

from engine.core import db

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

SET = "SUB.2D2D"
MIGRATION = db.REPO_ROOT / "supabase" / "migrations" / "20261109090000_a_skill_is_approved_level_by_level.sql"


@pytest.fixture
def conn():
    with db.connect() as c:
        c.execute("update skill_set set level_approved = '{}' where code = %s", (SET,))
        yield c
        c.rollback()


def _levels(conn) -> list[str]:
    return sorted(
        conn.execute("select difficulty from skill_set where code = %s", (SET,)).fetchone()["difficulty"]
    )


def _approve(conn, levels, by="Aseem"):
    conn.execute(
        "update skill_set set level_approved = level_approved"
        " || (select jsonb_object_agg(l, jsonb_build_object('by', %s::text, 'at', now())) from unnest(%s::text[]) l)"
        " where code = %s",
        (by, list(levels), SET),
    )


def _state(conn):
    return conn.execute(
        "select status, ratified_by, version, level_approved from skill_set where code = %s", (SET,)
    ).fetchone()


def _change(conn, level, **fields):
    d = conn.execute("select difficulty from skill_set where code = %s", (SET,)).fetchone()["difficulty"]
    d[level] = {**d[level], **fields}
    conn.execute("update skill_set set difficulty = %s where code = %s", (json.dumps(d), SET))


def test_a_skill_is_approved_when_every_level_it_has_is(conn):
    levels = _levels(conn)
    _approve(conn, levels[:-1])
    s = _state(conn)
    assert s["status"] == "draft", "a level still waits"
    assert sorted(s["level_approved"]) == levels[:-1]
    assert all(a["by"] == "Aseem" and a["at"] for a in s["level_approved"].values()), (
        "each level says who and when"
    )
    _approve(conn, levels[-1:])
    s = _state(conn)
    assert (s["status"], s["ratified_by"]) == ("ratified", "Aseem")


def test_a_changed_rule_withdraws_its_own_level_and_no_other(conn):
    levels = _levels(conn)
    _approve(conn, levels)
    rule = conn.execute(
        "select difficulty -> 'Hard' -> 'check' as c from skill_set where code = %s", (SET,)
    ).fetchone()
    _change(conn, "Hard", check={**rule["c"], "changed_by_a_test": True})
    s = _state(conn)
    assert sorted(s["level_approved"]) == sorted(set(levels) - {"Hard"}), (
        "Hard waits again; the others keep theirs"
    )
    assert s["status"] == "draft"

    # the kinds of question are every level's: changing them withdraws every level
    _approve(conn, ["Hard"])
    conn.execute(
        "update skill_set set formats = formats || '{a_kind_added_by_a_test}' where code = %s", (SET,)
    )
    assert _state(conn)["level_approved"] == {}


def test_changed_words_withdraw_nothing(conn):
    levels = _levels(conn)
    _approve(conn, levels)
    before = _state(conn)
    conn.execute(
        "update skill_set set name = name || ' (reworded)', learning_objective = learning_objective || ' Reworded.'"
        " where code = %s",
        (SET,),
    )
    _change(conn, "Hard", words="Hard, said again in other words by a test")
    s = _state(conn)
    assert sorted(s["level_approved"]) == levels and s["status"] == "ratified", "the questions did not change"
    assert s["version"] > before["version"], "the words are still kept as a version of their own"


def test_a_skill_approved_before_is_approved_at_every_level(conn):
    """A skill approved whole before this keeps its approval at every level it has, by the same person — the state live
    holds, made here with the trigger set aside, then the migration run again over it."""
    conn.execute("alter table skill_set disable trigger skill_set_version_on_change")
    conn.execute(
        "update skill_set set status = 'ratified', ratified_by = 'Aseem', level_approved = '{}' where code = %s",
        (SET,),
    )
    conn.execute("alter table skill_set enable trigger skill_set_version_on_change")
    conn.execute(MIGRATION.read_text())
    s = _state(conn)
    assert sorted(s["level_approved"]) == _levels(conn) and s["status"] == "ratified"
    assert {a["by"] for a in s["level_approved"].values()} == {"Aseem"}
    every = conn.execute(
        "select count(*) filter (where (status = 'ratified') <> (select bool_and(level_approved ? k)"
        "   from jsonb_object_keys(difficulty) k)) as wrong from skill_set"
    ).fetchone()
    assert every["wrong"] == 0, "a skill is approved exactly when every level it has is"
