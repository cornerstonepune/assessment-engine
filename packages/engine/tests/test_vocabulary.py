"""Grades, levels and a child's states are tables, and every link to them a key (goals/b0a-the-vocabulary-is-tables.yaml).

Nimish, 2026-10-20: "we need proper tables". The audit (ADR 0084) found the four level names and the six states as
lists of allowed words in CHECKs and in code, no grade table at all, and a topic's subject and a skill's topic as plain
codes the database never checked.
"""

import os

import psycopg
import pytest

from engine.core import db, loaders, settings, vocabulary

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

MIGRATION = db.REPO_ROOT / "supabase" / "migrations" / "20261119090000_the_vocabulary_is_tables.sql"
SEEDED = {
    "grade": [(g["code"], g["name"]) for g in settings.seed("vocabulary.json", "grades")],
    "difficulty": [(d["code"],) for d in settings.seed("vocabulary.json", "difficulties")],
    "child_state": [
        (s["code"], s["words"], s["colour"], s["needs_work"])
        for s in settings.seed("vocabulary.json", "child_states")
    ],
}
COLUMNS = {"grade": "code, name", "difficulty": "code", "child_state": "code, words, colour, needs_work"}
# (table, column) -> the table its word must be a row of
KEYS = {
    ("topic", "subject_code"): "subject",
    ("skill_set", "topic_code"): "topic",
    ("item", "difficulty"): "difficulty",
    ("prescription", "difficulty"): "difficulty",
    ("sheet_template", "difficulty"): "difficulty",
    ("item_review", "difficulty"): "difficulty",
    ("child_skill_state", "state"): "child_state",
}


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _rows(conn: db.Conn, tenant: db.Id, table: str) -> list[tuple]:
    """A school's rows of one table, in its order."""
    got = conn.execute(f"select {COLUMNS[table]} from {table} where tenant_id = %s order by ord", (tenant,))  # noqa: S608
    return [tuple(r.values()) for r in got.fetchall()]


def test_grades_levels_and_states_are_tables_in_their_order(conn):
    """Each list is the seed's, in the seed's order — so Grade 10 sorts after Grade 9 by a number, never as text — and a
    second load changes nothing."""
    t = loaders._tenant(conn)
    for table, seeded in SEEDED.items():
        assert _rows(conn, t, table) == seeded, table
    grades = [
        r["code"] for r in conn.execute("select code from grade where tenant_id = %s order by ord", (t,))
    ]
    assert grades.index("G10") == grades.index("G9") + 1
    vocabulary.load(conn, t, settings.seed)
    for table, seeded in SEEDED.items():
        assert _rows(conn, t, table) == seeded, f"{table}: a second load moved a row"


def test_every_link_is_a_key_the_database_checks(conn):
    """Each link is a key on (school, code) into the table holding the words, the list of allowed words it replaces is
    gone, and a word that is not a row is refused."""
    for (table, column), target in KEYS.items():
        found = conn.execute(
            "select confrelid::regclass::text as target,"
            " array(select attname from pg_attribute a join unnest(c.conkey) k(n) on a.attnum = k.n"
            "       where a.attrelid = c.conrelid) as cols"
            " from pg_constraint c where c.contype = 'f' and c.conrelid = %s::regclass",
            (table,),
        ).fetchall()
        assert {"target": target, "cols": ["tenant_id", column]} in found, (
            f"{table}.{column} is no key into {target}"
        )
        listed = conn.execute(
            "select conname from pg_constraint c where c.contype = 'c' and c.conrelid = %s::regclass"
            " and pg_get_constraintdef(c.oid) like %s",
            (table, f"%({column} = ANY%"),
        ).fetchall()
        assert listed == [], f"{table}.{column} still lists its words: {listed}"
    for sql in (
        "update topic set subject_code = 'NOPE' where code = 'MUL'",
        "update skill_set set topic_code = 'NOPE' where code = 'SUB.2D2D'",
        "update item set difficulty = 'Expert' where id = (select id from item limit 1)",
    ):
        with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
            conn.execute(sql)


def test_a_new_school_has_the_seed_rows_from_the_moment_it_exists(conn):
    """The keys need their rows before any load runs. A school already there gets them from the migration; a school
    added later, by any route, gets them as it is added — CI, 2026-10-20: a school made by a test had no states, and
    the graph could not rebuild its child's map. Exactly the seed's rows; the migration run again changes nothing."""
    t = loaders._tenant(conn)
    before = {table: _rows(conn, t, table) for table in SEEDED}
    school = conn.execute(
        "insert into tenant (slug, name) values ('b0a-new', 'b0a') returning id"
    ).fetchone()["id"]
    for table, seeded in SEEDED.items():
        assert _rows(conn, school, table) == seeded, f"{table}: a new school and the seed disagree"
    conn.execute(MIGRATION.read_text())
    for table, seeded in SEEDED.items():
        assert _rows(conn, school, table) == seeded, f"{table}: the migration and the seed disagree"
        assert _rows(conn, t, table) == before[table], f"{table}: running the migration again moved a row"


def test_a_new_grade_level_or_state_is_an_insert(conn):
    """Adding a grade, a level, a state or a subject is a row: the key accepts it at once, and no code or migration
    changes."""
    t = loaders._tenant(conn)
    conn.execute("insert into grade (tenant_id, code, name, ord) values (%s, 'G11', 'Grade 11', 99)", (t,))
    conn.execute("insert into difficulty (tenant_id, code, ord) values (%s, 'Expert', 99)", (t,))
    conn.execute("update item set difficulty = 'Expert' where id = (select id from item limit 1)")
    conn.execute(
        "insert into child_state (tenant_id, code, ord, words, colour, needs_work)"
        " values (%s, 'resting', 99, 'resting', 'grey', false)",
        (t,),
    )
    conn.execute("insert into subject (tenant_id, code, name) values (%s, 'HIN', 'Hindi')", (t,))
    conn.execute("update topic set subject_code = 'HIN' where tenant_id = %s and code = 'DATA'", (t,))
    grades = [
        r["code"] for r in conn.execute("select code from grade where tenant_id = %s order by ord", (t,))
    ]
    assert grades[-2:] == ["G10", "G11"]
