"""Every question names its skills in the registry (goals/c1-questions-name-their-skills.yaml, slice C1).

BUILD-ORDER, the locked scope of 22 Oct: "every question names its skills in the registry (one or several); a mixed
question says which step tests which skill". The rows are `item_registry_skill`; the database refuses, at commit, a
question with no skill, or with two skills and a row naming no step.
"""

import os

import psycopg
import pytest

from engine.checks import past
from engine.core import db
from tests.test_rung_folded import _kind

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

MIGRATION = db.REPO_ROOT / "supabase/migrations/20261204090000_a_question_names_its_registry_skills.sql"


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _new_question(conn, key="C1TEST"):
    """A copy of a bank question under a new key, as the bank writes one."""
    return conn.execute(
        "insert into item (tenant_id, item_key, template, rung_code, skill_codes, signal, fmt, stem, spec, responses,"
        " tags, case_codes, source, status, skill_set_code, difficulty, eval_type, skill_set_version, generator)"
        " select tenant_id, %s, template, rung_code, skill_codes, signal, fmt, stem, spec, responses, tags,"
        " case_codes, source, status, skill_set_code, difficulty, eval_type, skill_set_version, generator"
        " from item where source = 'generated' and cardinality(skill_codes) > 1 order by item_key limit 1"
        " returning id, tenant_id, skill_codes",
        (key,),
    ).fetchone()


def _checked(conn):
    """What the database says at commit, said now."""
    conn.execute("set constraints item_registry_skill_checked immediate")


def test_every_question_names_a_registry_skill(conn):
    """Every question has a row, every row a real registry key, and the one skill each names is the one its results
    already count (`spec ->> 'skill'`, else the first of `skill_codes`)."""
    assert (
        db.one(
            conn,
            "select count(*) as n from item i where not exists"
            " (select 1 from item_registry_skill x where x.item_id = i.id)",
        )["n"]
        == 0
    )
    assert (
        db.one(
            conn,
            "select count(*) as n from item_registry_skill x where not exists"
            " (select 1 from registry_skill r where r.tenant_id = x.tenant_id and r.code = x.registry_skill)",
        )["n"]
        == 0
    )
    assert (
        db.one(
            conn,
            "select count(*) as n from item i join item_registry_skill x on x.item_id = i.id"
            " where x.registry_skill <> coalesce(i.spec ->> 'skill', i.skill_codes[1])",
        )["n"]
        == 0
    )


def test_a_new_question_names_its_skill_by_itself(conn):
    """Whoever writes a question (the bank, a correction, a legacy import), it names the skill its results count."""
    q = _new_question(conn)
    _checked(conn)
    rows = conn.execute(
        "select registry_skill, step from item_registry_skill where item_id = %s", (q["id"],)
    ).fetchall()
    assert [(r["registry_skill"], r["step"]) for r in rows] == [(q["skill_codes"][0], None)]


def test_a_question_with_no_skill_is_refused(conn):
    q = _new_question(conn)
    conn.execute("delete from item_registry_skill where item_id = %s", (q["id"],))
    with pytest.raises(psycopg.errors.CheckViolation, match="names no registry skill"):
        _checked(conn)


def test_a_mixed_question_says_which_step_tests_which_skill(conn):
    """Two skills with a row naming no step is refused; each skill on its own step, in words, is kept."""
    q = _new_question(conn)
    first, second = q["skill_codes"][0], q["skill_codes"][1]
    conn.execute("savepoint s")
    conn.execute(
        "insert into item_registry_skill (tenant_id, item_id, registry_skill) values (%s, %s, %s)",
        (q["tenant_id"], q["id"], second),
    )
    with pytest.raises(psycopg.errors.CheckViolation, match="names no step"):
        _checked(conn)
    conn.execute("rollback to savepoint s")
    conn.execute("set constraints item_registry_skill_checked deferred")
    conn.execute(
        "update item_registry_skill set step = 1, step_words = 'count on in fives' where item_id = %s",
        (q["id"],),
    )
    conn.execute(
        "insert into item_registry_skill (tenant_id, item_id, registry_skill, step, step_words)"
        " values (%s, %s, %s, 2, 'name the multiple')",
        (q["tenant_id"], q["id"], second),
    )
    _checked(conn)
    rows = conn.execute(
        "select step, registry_skill from item_registry_skill where item_id = %s order by step", (q["id"],)
    ).fetchall()
    assert [(r["step"], r["registry_skill"]) for r in rows] == [(1, first), (2, second)]
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(
            "insert into item_registry_skill (tenant_id, item_id, registry_skill, step, step_words)"
            " values (%s, %s, 'NOT.A.SKILL', 3, 'no such skill')",
            (q["tenant_id"], q["id"]),
        )


def test_past_results_are_the_same_before_and_after(conn):
    """Nimish: "nothing will change for any of the past assessments, scoring etc. right?". The evidence, every
    child's states, every scored answer, the questions and the levels are the same before and after, run again."""
    before = past.fingerprint(conn) | past.fingerprint(conn, past.CURRICULUM)
    conn.execute(MIGRATION.read_text())
    assert past.fingerprint(conn) | past.fingerprint(conn, past.CURRICULUM) == before


def test_writing_a_question_type_keeps_a_levels_declared_kinds(conn):
    """E0's fragility (PR #284): a level's kind the curriculum names, with no question in the bank yet, outlives a
    new question type; a kind the bank stops holding still goes."""
    lvl = db.one(
        conn,
        "select tenant_id, skill_code, difficulty from skill_level order by skill_code, difficulty limit 1",
    )
    conn.execute(
        "insert into question_type (tenant_id, code, fmt, words, marked) values (%s, 'C1.DECLARED', 'C1.DECLARED',"
        " 'a kind no question holds yet', '{computable}')",
        (lvl["tenant_id"],),
    )
    conn.execute(
        "insert into skill_level_question_type (tenant_id, skill_code, difficulty, question_type)"
        " values (%s, %s, %s, 'C1.DECLARED')",
        (lvl["tenant_id"], lvl["skill_code"], lvl["difficulty"]),
    )
    held = db.one(conn, "select count(*) as n from skill_level_question_type where not declared")["n"]
    conn.execute(
        "insert into question_type (tenant_id, code, fmt, words, marked) values (%s, 'C1.OTHER', 'C1.OTHER',"
        " 'another kind', '{computable}')",
        (lvl["tenant_id"],),
    )
    assert (
        db.one(
            conn, "select count(*) as n from skill_level_question_type where question_type = 'C1.DECLARED'"
        )["n"]
        == 1
    )
    assert db.one(conn, "select count(*) as n from skill_level_question_type where not declared")["n"] == held
    link = db.one(
        conn,
        "select skill_code, difficulty, question_type from skill_level_question_type where not declared"
        " order by skill_code, difficulty, question_type limit 1",
    )
    conn.execute(
        "update item set status = 'retired' where skill_set_code = %s and difficulty = %s"
        " and question_type_of(fmt, template) = %s",
        (link["skill_code"], link["difficulty"], link["question_type"]),
    )
    assert (
        db.one(
            conn,
            "select count(*) as n from skill_level_question_type where skill_code = %s and difficulty = %s"
            " and question_type = %s",
            tuple(link.values()),
        )["n"]
        == 0
    )


def test_the_view_b4b_kept_for_one_deploy_is_gone(conn):
    assert _kind(conn, "skill_set") is None
    assert _kind(conn, "item_registry_skill") == "table"
