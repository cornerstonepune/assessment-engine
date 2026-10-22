"""A skill's levels are rows (goals/b1-levels-are-rows.yaml, ADR 0084).

Nimish, 2026-10-20: "we need proper tables". A level, its grade and its approval lived inside three JSON objects on
`skill_set` (`difficulty`, `level_band`, `level_approved`) that the database never checked. Now each level is a row of
`skill_level` with real keys, filled from the blob by the migration and kept equal to it while the blob is still
written; the readers move to the rows, and the rows are proved to draw the same questions as the blob did.
"""

import os
import re

import psycopg
import pytest

from engine.checks import levels as check
from engine.core import db, levels, loaders
from engine.w1_bank import spec
from engine.w2_print import shelf

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

MIGRATION = db.REPO_ROOT / "supabase" / "migrations" / "20261123090000_the_levels_are_rows.sql"
SKILL = "SUB.2D2D"
# The readers moved to the rows; the writers stay on the blob, kept equal by the trigger (ADR 0087).
MOVED = [
    "packages/engine/engine/w1_bank/spec.py",
    "packages/engine/engine/w1_bank/cases.py",
    "packages/engine/engine/w1_bank/review.py",
    "packages/engine/engine/w1_bank/story_shape.py",
    "packages/engine/engine/w2_print/week_note.py",
    "packages/engine/engine/checks/audit.py",
    "packages/engine/engine/core/references.py",
    "packages/engine/engine/w3_read/legacy.py",
    "packages/engine/engine/cli.py",
    "packages/engine/engine/w1_bank/inventory.py",
    "packages/engine/engine/w1_bank/rehome.py",
    "packages/engine/engine/w2_print/library.py",
    "packages/engine/engine/w2_print/prescribe.py",
    "packages/engine/engine/w2_print/shelf.py",
    "packages/engine/engine/w2_print/focus_paper.py",
    "packages/engine/engine/assess/focus.py",
    "apps/web/lib/queries-bank.ts",
    "apps/web/lib/queries-people.ts",
    "apps/web/lib/workflows.ts",
    "apps/web/lib/queries.ts",
    "apps/web/lib/queries-curriculum.ts",
    "apps/web/lib/queries-children.ts",
    "apps/web/lib/queries-worksheets.ts",
    "apps/web/lib/queries-taxonomy.ts",
    "apps/web/lib/maker.ts",
    "apps/web/app/(app)/curriculum-table.tsx",
    "apps/web/app/(app)/worksheets/page.tsx",
    "apps/web/app/(app)/worksheets/[qr]/page.tsx",
    "apps/web/app/(app)/papers/approve/page.tsx",
    "apps/web/app/(app)/skill-sets/[code]/page.tsx",
    "apps/web/app/(app)/skill-sets/[code]/level-approval.tsx",
]
# a read of the blob: its levels selected, walked or asked after; its grades; its approvals; a skill selected whole
BLOB = re.compile(
    r"select code, difficulty|(?<!as )difficulty from skill_set|jsonb_(?:each|object_keys)\((?:\w+\.)?difficulty\)"
    r"|\b\w+\.difficulty (?:\?|->) \w+\.|level_band|level_approved|select \* from skill_set"
)


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _level(conn, code, difficulty):
    return conn.execute(
        "select * from skill_level where skill_code = %s and difficulty = %s", (code, difficulty)
    ).fetchone()


def test_every_level_is_a_row_with_keys_the_database_checks(conn):
    """One row per skill and level, its level a key into `difficulty`, its grade a key into `grade`, its skill a key into
    `skill_set`: a level or a grade that is not a row is refused, and the website cannot write a level behind the blob."""
    n = conn.execute("select count(*) as n from skill_set, jsonb_object_keys(difficulty)").fetchone()["n"]
    assert n == conn.execute("select count(*) as n from skill_level").fetchone()["n"] > 0
    keys = {
        (r["target"], tuple(r["cols"]))
        for r in conn.execute(
            "select confrelid::regclass::text as target,"
            " array(select attname::text from pg_attribute a join unnest(c.conkey) with ordinality k(n, i) on a.attnum = k.n"
            "       where a.attrelid = c.conrelid order by k.i) as cols"
            " from pg_constraint c where c.contype = 'f' and c.conrelid = 'skill_level'::regclass"
        )
    }
    assert {
        ("skill_set", ("tenant_id", "skill_code")),
        ("difficulty", ("tenant_id", "difficulty")),
        ("grade", ("tenant_id", "grade")),
    } <= keys
    for sql in (
        f"update skill_level set grade = 'G42' where skill_code = '{SKILL}' and difficulty = 'Easy'",
        f"update skill_level set difficulty = 'Expert' where skill_code = '{SKILL}' and difficulty = 'Easy'",
    ):
        with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
            conn.execute(sql)
    web = conn.execute(
        "select has_table_privilege('app_web', 'skill_level', 'insert') or has_table_privilege('app_web', 'skill_level',"
        " 'update') or has_table_privilege('app_web', 'skill_level', 'delete') as writes"
    ).fetchone()
    assert not web["writes"], "the website writes the blob, never a level behind it, until its writers move"


def test_the_rows_hold_what_the_blob_holds_grades_and_approvals_counted_equal(conn):
    """Level by level the rows give back the blob exactly — its words, its rule, its grade (named in `level_band`, else
    the skill's own), its approval — and the counts of levels per grade and of approved levels are equal."""
    report = check.compare(conn, draws=0)
    assert report["disagree"] == [], report["disagree"][:5]
    assert report["levels"] == report["rows"] > 0
    assert report["grades"]["blob"] == report["grades"]["rows"]
    assert report["approved"]["blob"] == report["approved"]["rows"]
    s = conn.execute("select difficulty from skill_set where code = %s", (SKILL,)).fetchone()
    assert levels.of(conn, SKILL) == s["difficulty"]


def test_the_generator_draws_the_same_questions_from_the_rows_as_from_the_blob(conn):
    """For every skill and level, the generator's draw on one seed from the rows is the draw from the blob — and the
    draw is real: a level with a different rule draws different questions on the same seed."""
    report = check.compare(conn, draws=4)
    assert report["drawn"] == report["drawable"], "a level drew nothing to compare"
    assert report["disagree"] == [], report["disagree"][:5]
    s = spec.row(conn, SKILL)
    easy, hard = s["difficulty"]["Easy"]["check"], s["difficulty"]["Hard"]["check"]
    assert check.draw(conn, s, easy, seed=1, n=4) == check.draw(conn, s, easy, seed=1, n=4)
    assert check.draw(conn, s, easy, seed=1, n=4) != check.draw(conn, s, hard, seed=1, n=4)


def test_a_change_to_the_blob_is_a_change_to_the_rows_whoever_writes_it(conn):
    """While the blob is still what the website and the loader write, every write reaches the rows at once: a level's
    words, its grade moved, its approval, a level added or taken away, the skill's own grade moved."""
    conn.execute(
        "update skill_set set difficulty = jsonb_set(difficulty, '{Easy,words}', '\"Two 2-digit numbers, no exchange.\"'),"
        ' level_band = level_band || \'{"Hard": "G3"}\' where code = %s',
        (SKILL,),
    )
    assert _level(conn, SKILL, "Easy")["looks_like"] == "Two 2-digit numbers, no exchange."
    assert _level(conn, SKILL, "Hard")["grade"] == "G3"
    conn.execute(
        "update skill_set set level_approved = level_approved || jsonb_build_object('Medium',"
        " jsonb_build_object('by', 'Achal', 'at', now())) where code = %s",
        (SKILL,),
    )
    assert _level(conn, SKILL, "Medium")["confirmed_by"] == "Achal"
    conn.execute("update skill_set set difficulty = difficulty - 'Advance' where code = %s", (SKILL,))
    assert _level(conn, SKILL, "Advance") is None
    rung = conn.execute("select rung_code from skill_set where code = %s", (SKILL,)).fetchone()["rung_code"]
    conn.execute("update rung set band = 'G4' where code = %s", (rung,))
    assert _level(conn, SKILL, "Medium")["grade"] == "G4", "a level not moved follows its skill's grade"
    assert _level(conn, SKILL, "Hard")["grade"] == "G3", "a level moved keeps the grade it was moved to"
    assert check.compare(conn, draws=0)["disagree"] == []


def test_a_level_keeps_its_own_version_history(conn):
    """A change to what one level asks files that level's previous version, and only that level's: its neighbours keep
    their version. The history the skill kept before is carried onto each level, and the migration run twice changes
    nothing."""
    before = {
        r["difficulty"]: r["version"]
        for r in conn.execute("select difficulty, version from skill_level where skill_code = %s", (SKILL,))
    }
    old = _level(conn, SKILL, "Medium")
    conn.execute(
        "update skill_set set difficulty = jsonb_set(difficulty, '{Medium,words}', '\"Changed words.\"') where code = %s",
        (SKILL,),
    )
    after = {
        r["difficulty"]: r["version"]
        for r in conn.execute("select difficulty, version from skill_level where skill_code = %s", (SKILL,))
    }
    assert after == {**before, "Medium": before["Medium"] + 1}
    filed = conn.execute(
        "select looks_like, rule from skill_level_version where skill_code = %s and difficulty = 'Medium'"
        " and version = %s",
        (SKILL, before["Medium"]),
    ).fetchone()
    assert filed == {"looks_like": old["looks_like"], "rule": old["rule"]}
    t = loaders._tenant(conn)
    rows = conn.execute(
        "select count(*) as n from skill_level_version where tenant_id = %s", (t,)
    ).fetchone()["n"]
    conn.execute(MIGRATION.read_text())
    assert (
        conn.execute("select count(*) as n from skill_level_version where tenant_id = %s", (t,)).fetchone()[
            "n"
        ]
        == rows
    )
    # the migration's first run on a database whose skills have a history: each level's carried onto it
    conn.execute("delete from skill_level_version")
    conn.execute("delete from skill_level")
    conn.execute(MIGRATION.read_text())
    assert {
        r["difficulty"]: r["version"]
        for r in conn.execute("select difficulty, version from skill_level where skill_code = %s", (SKILL,))
    } == after
    carried = conn.execute(
        "select looks_like, rule from skill_level_version where skill_code = %s and difficulty = 'Medium'"
        " and version = %s",
        (SKILL, before["Medium"]),
    ).fetchone()
    assert carried == {"looks_like": old["looks_like"], "rule": old["rule"]}
    assert check.compare(conn, draws=0)["disagree"] == []


def test_the_moved_readers_read_the_rows_not_the_blob(conn):
    """A reader that has moved sees a level as its row says, even where the blob says otherwise. The two can only part
    with the trigger that keeps them equal switched off, as here."""
    conn.execute("set local session_replication_role = replica")
    conn.execute(
        "update skill_level set looks_like = 'Read from the row.' where skill_code = %s and difficulty = 'Easy'",
        (SKILL,),
    )
    conn.execute("set local session_replication_role = origin")
    assert spec.row(conn, SKILL)["difficulty"]["Easy"]["words"] == "Read from the row."
    prompt_input, s, _ = spec.read(conn, SKILL, "Easy")
    assert prompt_input["difficulty"] == "Easy: Read from the row."
    blob = conn.execute(
        "select difficulty -> 'Easy' ->> 'words' as w from skill_set where code = %s", (SKILL,)
    )
    assert blob.fetchone()["w"] != "Read from the row."
    assert levels.every(conn)[SKILL]["Easy"]["words"] == "Read from the row."
    # a level approved and moved to another grade in its row alone: the papers' shelf sees both
    top = conn.execute("select code from grade order by ord desc limit 1").fetchone()["code"]
    conn.execute("set local session_replication_role = replica")
    conn.execute(
        "update skill_level set confirmed_by = 'row', confirmed_at = now(), grade = %s"
        " where skill_code = %s and difficulty = 'Easy'",
        (top, SKILL),
    )
    conn.execute("update skill_set set level_approved = '{}' where code = %s", (SKILL,))
    conn.execute("set local session_replication_role = origin")
    assert "Easy" in shelf.approved_levels(conn)[SKILL]
    own = conn.execute(
        "select r.band from skill_set s join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code"
        " where s.code = %s",
        (SKILL,),
    ).fetchone()["band"]
    assert "Easy" not in shelf._read_levels(conn, own)[SKILL]
    assert "Easy" in shelf._read_levels(conn, None)[SKILL]
    # the writers still write the blob (the seed's levels, an approval of every level), and read what they write;
    # nothing else in a moved file reads it
    writers = {
        "cases.py": ['"select code, difficulty, formats from skill_set order by code"'],
        "spec.py": [
            "\"update skill_set set level_approved = (select jsonb_object_agg(k, jsonb_build_object('by', %s::text,"
            ' \'at\', now()))"\n        " from jsonb_object_keys(difficulty) k), updated_at = now()"'
        ],
        # who last moved a level to another grade is the skill's record (goals/c1-whole-curriculum.yaml), not a level's
        "queries.ts": ["s.level_band_by as moved_by, s.level_band_at as moved_at"],
    }
    for f in MOVED:
        text = (db.REPO_ROOT / f).read_text()
        for w in writers.get(f.rsplit("/", 1)[-1], []):
            assert w in text, f"{f}: the writer this test names has moved; say where"
            text = text.replace(w, "")
        assert not BLOB.findall(text), f"{f} still reads the blob: {BLOB.findall(text)}"
