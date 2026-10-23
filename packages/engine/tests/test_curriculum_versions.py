"""The curriculum published as numbered versions (goals/c3-the-curriculum-in-numbered-versions.yaml, slice C3).

BUILD-ORDER, the locked scope of 22 Oct: "the curriculum published as numbered versions; every new result names its
version; an edit takes effect from the next week". A version is `curriculum_version` with every skill at its version
(`curriculum_version_skill`); `curriculum_in_force` names the newest whose Monday has come.
"""

import os
from datetime import date

import psycopg
import pytest

from engine.checks import past
from engine.core import db
from tests import rows

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

MIGRATION = db.REPO_ROOT / "supabase/migrations/20261206090000_the_curriculum_is_published_in_versions.sql"
# a week after every version a database holds, whenever this runs; times in Pune
WEDNESDAY = "2030-01-02 10:00+05:30"
SUNDAY_NIGHT = "2030-01-06 23:30+05:30"
MONDAY = "2030-01-07 00:30+05:30"


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _publish(conn, at=WEDNESDAY):
    return db.one(
        conn, "select publish_curriculum(%s, 'a coordinator', '', %s) as n", (rows.tenant(conn), at)
    )["n"]


def _in_force(conn, at):
    return db.one(conn, "select curriculum_in_force(%s, %s) as n", (rows.tenant(conn), at))["n"]


def _skills(conn, number):
    return {
        r["skill_code"]: r["skill_version"]
        for r in conn.execute(
            "select s.skill_code, s.skill_version from curriculum_version_skill s"
            " join curriculum_version v on v.id = s.curriculum_version_id where v.tenant_id = %s and v.number = %s",
            (rows.tenant(conn), number),
        ).fetchall()
    }


def test_version_one_is_the_curriculum_as_it_stands(conn):
    v1 = db.one(conn, "select takes_effect from curriculum_version where number = 1 and tenant_id = %s",
                (rows.tenant(conn),))  # fmt: skip
    assert v1["takes_effect"].isoweekday() == 1 and v1["takes_effect"] <= date.today()
    every = {r["code"]: r["version"] for r in conn.execute("select code, version from skill").fetchall()}
    published = {
        r["skill_code"] for r in conn.execute("select skill_code from curriculum_version_skill").fetchall()
    }
    assert every and set(every) <= published
    assert _in_force(conn, "now()") is not None


def test_publishing_numbers_the_next_version_from_the_next_monday(conn):
    """Published on a Wednesday: the next number, in force from the Monday after, not before, by the school's clock."""
    before = _in_force(conn, SUNDAY_NIGHT)
    n = _publish(conn)
    assert n == db.one(conn, "select max(number) as n from curriculum_version where tenant_id = %s",
                       (rows.tenant(conn),))["n"]  # fmt: skip
    assert db.one(conn, "select takes_effect from curriculum_version where number = %s", (n,))[
        "takes_effect"
    ] == date(2030, 1, 7)
    assert _in_force(conn, SUNDAY_NIGHT) == before
    assert _in_force(conn, MONDAY) == n


def test_an_edit_takes_effect_from_the_next_week(conn):
    """A skill edited and the curriculum published on a Wednesday: that week still names the version without the
    edit; from Monday the version in force holds the skill at its new version."""
    code = db.one(conn, "select code from skill order by code limit 1")["code"]
    was = db.one(conn, "select version from skill where code = %s", (code,))["version"]
    conn.execute(
        "update skill set learning_objective = learning_objective || ' (edited)' where code = %s", (code,)
    )
    now = db.one(conn, "select version from skill where code = %s", (code,))["version"]
    assert now == was + 1
    n = _publish(conn)
    assert _skills(conn, _in_force(conn, SUNDAY_NIGHT))[code] == was
    assert _skills(conn, _in_force(conn, MONDAY))[code] == now == _skills(conn, n)[code]


def test_every_new_result_names_its_version(conn):
    """A scored answer and an evidence record name the version in force when they are written, by themselves."""
    paper = rows.a_read_paper(conn, [{"status": "correct", "read": "5"}])
    in_force = _in_force(conn, "now()")
    assert (
        db.one(conn, "select curriculum_version as v from item_result where id = %s", (paper["results"][0],))[
            "v"
        ]
        == in_force
    )
    e = conn.execute(
        "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, channel, observed_at)"
        " values (%s, %s, 'NUM.OPS.01', 'R1', true, 'teacher_override', now()) returning curriculum_version",
        (rows.tenant(conn), paper["child"]),
    ).fetchone()
    assert e["curriculum_version"] == in_force


def test_a_published_version_is_never_edited(conn):
    _publish(conn)
    for table in ("curriculum_version", "curriculum_version_skill"):
        with pytest.raises(psycopg.Error), conn.transaction():
            conn.execute(f"update {table} set updated_at = now()")
        with pytest.raises(psycopg.Error), conn.transaction():
            conn.execute(f"delete from {table}")


def test_past_results_are_the_same_before_and_after(conn):
    """Nimish: "nothing will change for any of the past assessments, scoring etc. right?"."""
    before = past.fingerprint(conn) | past.fingerprint(conn, past.CURRICULUM)
    conn.execute(MIGRATION.read_text())
    assert past.fingerprint(conn) | past.fingerprint(conn, past.CURRICULUM) == before
