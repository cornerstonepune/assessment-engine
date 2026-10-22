"""The rung folded into the skill, and the registry's table named `registry_skill` (goals/b4-the-rung-folded-in.yaml,
ADR 0084, decisions B4-1 to B4-3).

Nimish, 2026-10-20: "we need proper tables". Each skill had exactly one rung, which held four facts about it: its grade,
its place on the ladder, its description and its registry skills. They are the skill's own columns now, and the rung's
code is the skill's permanent second code, so nothing already recorded is rewritten to point at a skill.
"""

import os
import re

import psycopg
import pytest

from engine.assess import graph
from engine.checks import past
from engine.core import db, settings
from engine.w2_print import shelf

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

MIGRATION = db.REPO_ROOT / "supabase/migrations/20261201090000_the_rung_folded_into_the_skill.sql"
# Every file that may hold a query: the engine, its tests, the website, n8n and the scripts. Migrations are history.
SOURCES = [
    *(db.REPO_ROOT / "packages/engine/engine").rglob("*.py"),
    *(db.REPO_ROOT / "packages/engine/tests").rglob("*.py"),
    *(db.REPO_ROOT / "apps/web/lib").rglob("*.ts"),
    *(db.REPO_ROOT / "apps/web/app").rglob("*.ts"),
    *(db.REPO_ROOT / "apps/web/app").rglob("*.tsx"),
    *(db.REPO_ROOT / "n8n/workflows").glob("*.json"),
    *(p for p in (db.REPO_ROOT / "bin").iterdir() if p.is_file()),
]
THIS = os.path.abspath(__file__)


def _reads(table):
    """A query naming `table` as a table: after from, join, into, update or table, never as part of a longer name."""
    return re.compile(
        rf"\b(from|join|into|update|table|truncate)\s+(public\.)?{table}\b(?![_.(])", re.IGNORECASE
    )


def _files_reading(table):
    rx = _reads(table)
    return sorted(
        f"{p.relative_to(db.REPO_ROOT)}:{i}"
        for p in SOURCES
        if os.path.abspath(p) != THIS
        for i, line in enumerate(p.read_text(errors="ignore").splitlines(), 1)
        if rx.search(line)
    )


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _kind(conn, name):
    row = conn.execute(
        "select c.relkind from pg_class c join pg_namespace n on n.oid = c.relnamespace"
        " where n.nspname = 'public' and c.relname = %s",
        (name,),
    ).fetchone()
    return row and {"r": "table", "v": "view"}[row["relkind"]]


def _refused(conn, sql, params=()):
    try:
        with conn.transaction():
            conn.execute(sql, params)
    except (psycopg.errors.IntegrityError, psycopg.errors.RaiseException):
        return True
    return False


def test_each_skill_holds_its_rungs_grade_order_and_description(conn):
    """Every rung the seed writes is one skill's: its grade, place, description and registry skills, in their order."""
    rungs = {r["code"]: r for r in settings.seed("rungs.json", "rungs")}
    skills = {
        r["rung_code"]: r
        for r in conn.execute(
            "select rung_code, grade, ladder_order, descriptor, registry_codes from skill_set"
        )
    }
    assert rungs.keys() == skills.keys()
    for code, r in rungs.items():
        s = skills[code]
        assert (s["grade"], s["ladder_order"], s["descriptor"], s["registry_codes"]) == (
            r["band"],
            r["ladder_order"],
            r["descriptor"],
            r["skill_codes"],
        ), code
    # a grade is a key, and a registry skill is still a row's key (B3), now kept equal to the skill's own list
    assert _refused(conn, "update skill_set set grade = 'G99' where rung_code = 'R36'")
    assert _refused(
        conn,
        "update skill_set set registry_codes = registry_codes || '{NOT.A.SKILL}' where rung_code = 'R36'",
    )


def test_every_rung_code_on_record_is_a_skills_second_code(conn):
    """A question's rung is a key into the skill's second code, as it was into the rung; what the graph and the cards
    hold names a skill by it. Each skill has exactly one."""
    assert conn.execute(
        "select count(*) = count(distinct (tenant_id, rung_code)) as one from skill_set"
    ).fetchone()["one"]
    for table in ("item", "evidence_event", "child_skill_state", "class_card", "skill_set_version"):
        left = conn.execute(
            f"select distinct x.rung_code from {table} x where not exists"
            " (select 1 from skill_set s where s.tenant_id = x.tenant_id and s.rung_code = x.rung_code)"
        ).fetchall()
        assert left == [], (table, left)
    item = conn.execute("select id from item limit 1").fetchone()
    assert item, "a database with questions"
    assert _refused(conn, "update item set rung_code = 'NO.SUCH.RUNG' where id = %s", (item["id"],))


def test_no_file_reads_the_rung_table(conn):
    """B4-3: no file reads the `rung` table; it is gone. Its name answers, as a view, for the one deploy that may still
    run the code from before (the next deploy drops it); the maths library's word stays (it reads no table)."""
    assert _files_reading("rung") == []
    assert _kind(conn, "rung") in (None, "view")


def test_the_tables_carry_the_names_nimish_chose(conn):
    """B4-1, registry first: the registry's skills are `registry_skill`, and no file reads `skill` (which the school's
    skills take in the next deploy), so a reader left behind cannot read the school's skills for the registry's."""
    assert _kind(conn, "registry_skill") == "table"
    assert _kind(conn, "skill") in (None, "view")
    assert _files_reading("skill") == []
    assert conn.execute("select count(*) as n from registry_skill").fetchone()["n"] == len(
        settings.seed("registry.json", "skills")
    )


def test_a_new_grade_or_registry_skill_on_a_skill_moves_its_levels_and_links(conn):
    """What the rung's triggers did, the skill's own do: a level not moved follows its skill's grade, and the registry
    links equal the skill's list."""
    s = conn.execute(
        "select code, rung_code from skill_set where level_band = '{}' and difficulty ? 'Easy' limit 1"
    ).fetchone()
    conn.execute("update skill_set set grade = 'G4' where code = %s", (s["code"],))
    assert {
        r["grade"] for r in conn.execute("select grade from skill_level where skill_code = %s", (s["code"],))
    } == {"G4"}
    other = conn.execute(
        "select code from registry_skill where code <> all(select unnest(registry_codes) from skill_set where code = %s)"
        " limit 1",
        (s["code"],),
    ).fetchone()["code"]
    conn.execute(
        "update skill_set set registry_codes = registry_codes || %s::text where code = %s", (other, s["code"])
    )
    links = {
        r["registry_skill"]
        for r in conn.execute(
            "select registry_skill from skill_registry_link where skill_code = %s", (s["code"],)
        )
    }
    listed = conn.execute("select registry_codes from skill_set where code = %s", (s["code"],)).fetchone()
    assert links == set(listed["registry_codes"]) and other in links


def test_evidence_count_and_checksum_equal_before_and_after(conn):
    """Nimish: "nothing will change for any of the past assessments, scoring etc. right?". The evidence (count and
    checksum), every child's states and every scored answer are the same before and after the migration, run again on a
    database that has them; and the fingerprint does see a change, so its sameness means something."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    child = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s, '1', 'RUNGTEST', 'G3') returning id",
        (tenant,),
    ).fetchone()["id"]
    add = (
        "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, channel, observed_at,"
        " confirmed_by, misconception_codes) values (%s, %s, 'NUM.OPS.01', 'R45', %s, 'item', now(), 'test', '{}')"
    )
    for right in (True, False, True):
        conn.execute(add, (tenant, child, right))
    graph.rebuild(conn, str(child))
    before = past.fingerprint(conn)
    assert before["evidence"]["n"] >= 3 and before["states"]["n"] >= 1
    conn.execute(MIGRATION.read_text())
    graph.rebuild(conn, str(child))
    assert past.fingerprint(conn) == before
    conn.execute(add, (tenant, child, False))
    assert past.fingerprint(conn)["evidence"] != before["evidence"]


def test_every_childs_map_and_paper_is_the_same_before_and_after(conn):
    """A child's map and a paper read a skill's place, grade and own registry skill: they are the rung's, as the seed
    wrote them, so every map is drawn and every paper chosen as before. A skill's levels keep their grades: a level
    moved keeps its grade, any other has its skill's, which was its rung's."""
    rungs = {r["code"]: r for r in settings.seed("rungs.json", "rungs")}
    for c in shelf._catalog(conn, None, every=True):
        r = rungs[c["rung"]]
        assert c["order"] == r["ladder_order"], c["code"]
        assert c["own"] in (None, r["skill_codes"][0]), c["code"]
    moved = {
        (r["code"], level): grade
        for r in conn.execute("select code, level_band from skill_set")
        for level, grade in r["level_band"].items()
    }
    for r in conn.execute(
        "select l.skill_code, l.difficulty, l.grade, s.rung_code from skill_level l"
        " join skill_set s on s.tenant_id = l.tenant_id and s.code = l.skill_code"
    ):
        want = moved.get((r["skill_code"], r["difficulty"]), rungs[r["rung_code"]]["band"])
        assert r["grade"] == want, (r["skill_code"], r["difficulty"])
