"""The school's skills are the table `skill` (goals/b4b-the-skill-is-called-skill.yaml, decision B4-1, deploy 2 of 2).

Nimish, 2026-10-20: "we need proper tables". B4 renamed the registry's table `registry_skill`; this renames the
school's `skill_set` to `skill`, and drops the two names B4 kept answering for one deploy.
"""

import os

import pytest

from engine.assess import graph
from engine.checks import past
from engine.core import db
from tests.test_rung_folded import _files_reading, _kind

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

MIGRATION = db.REPO_ROOT / "supabase/migrations/20261202090000_the_skill_is_called_skill.sql"


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def test_the_schools_skills_are_the_table_skill(conn):
    """`skill` holds the school's skills, each with its second code and grade; the registry's are `registry_skill`."""
    assert _kind(conn, "skill") == "table"
    assert _kind(conn, "registry_skill") == "table"
    row = conn.execute("select code, rung_code, grade from skill where code = 'MUL.FACTS'").fetchone()
    assert row and row["rung_code"] and row["grade"]


def test_no_file_reads_skill_set_as_a_table(conn):
    """No query names `skill_set` as a table; `skill_set_code` and `skill_set_version`, columns, keep their names."""
    assert _files_reading("skill_set") == []
    assert _kind(conn, "skill_set") in (None, "view")


def test_the_names_b4_kept_for_one_deploy_are_gone(conn):
    """B4 left `rung` answering for the one deploy in which the code before it might run; that deploy is past."""
    assert _kind(conn, "rung") is None


def test_past_results_are_the_same_before_and_after(conn):
    """Nimish: "nothing will change for any of the past assessments, scoring etc. right?". The evidence (count and
    checksum), every child's states and every scored answer are the same before and after the migration, run again."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    child = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s, '1', 'SKILLTEST', 'G3') returning id",
        (tenant,),
    ).fetchone()["id"]
    conn.execute(
        "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, channel, observed_at,"
        " confirmed_by, misconception_codes) values (%s, %s, 'NUM.OPS.01', 'R45', false, 'item', now(), 'test', '{}')",
        (tenant, child),
    )
    graph.rebuild(conn, str(child))
    before = past.fingerprint(conn)
    conn.execute(MIGRATION.read_text())
    graph.rebuild(conn, str(child))
    assert past.fingerprint(conn) == before
