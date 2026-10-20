"""Grades are read from the `grade` table everywhere, and every grade a row holds is a key into it
(goals/b0b-grades-from-the-table.yaml, ADR 0085).

The audit (ADR 0084) found the grades as a list in the website (Grade 1 to 4 and "Reasoning · Grade 2 and up"), a grade's
number read out of its code in eleven places (`"G10"[1]` is "1"; `left("G10", 2)` is "G1") and grades sorted as text
("G10" before "G2"). A Grade 10 skill could not have shown on the curriculum page, and would have been read as Grade 1
where it did.
"""

import io
import os
import re
import tokenize
import uuid

import psycopg
import pytest

from engine.core import db, loaders, settings
from engine.w2_print import shelf, week_note

NEEDS_DB = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

GRADES = settings.seed("vocabulary.json", "grades")
# Where a grade may be named: the maths library (its paper's layout for the youngest grade, ADR 0085), the seed, the
# migrations, the tests and the proofs, whose requests are in the school's own terms.
SCANNED = {
    "packages/engine/engine": (".py",),
    "apps/web/app": (".ts", ".tsx"),
    "apps/web/lib": (".ts", ".tsx"),
    "apps/web/components": (".ts", ".tsx"),
    "n8n/workflows": (".json",),
}
EXEMPT = ("packages/engine/engine/assess/", "packages/engine/engine/checks/")
_CODE = "|".join(re.escape(g["code"]) for g in sorted(GRADES, key=lambda g: -len(g["code"])))
_NAME = "|".join(re.escape(g["name"]) for g in GRADES if g["name"] != g["code"])
NAMING = [
    # a grade's code or name, written in the code: the table holds them
    (re.compile(rf"""["'`](?:{_CODE})\+?["'`]"""), "a grade's code"),
    (re.compile(r"G\d+\+"), 'a "this grade and up" code'),
    (re.compile(rf"""["'`>](?:{_NAME})\b|\bGrade (?:\d|\{{|\$\{{)"""), "a grade's name"),
    # a grade's number read out of its code: "G10" is read as 1 by any of these
    (re.compile(r"\b(?:band|grade)\w*\s*\[\s*1\s*:"), "a grade read out of its code"),
    (re.compile(r"\b(?:band|grade)\w*\.slice\(\s*1"), "a grade read out of its code"),
    (re.compile(r"(?:band|grade)\w*\)?\.replace\(/\\D/g"), "a grade read out of its code"),
    (
        re.compile(r"\b(?:left|substring|regexp_replace)\(\s*(?:coalesce\()?[\w.]*(?:band|grade)", re.I),
        "a grade read out of its code",
    ),
    (re.compile(r"""\b(?:band|grade)\w*\.startswith\(\s*["']"""), "a grade read out of its code"),
    (
        re.compile(r"\b(?:band|grade)\b.*\bisdigit\(|\bisdigit\(.*\b(?:band|grade)\b"),
        "a grade read out of its code",
    ),
    # grades sorted as text: "G10" comes before "G2"
    (re.compile(r"\border by\s+[\w.]*\bband\b(?!_)", re.I), "grades sorted as text"),
    (re.compile(r"\b(?:min|max)\(\s*[\w.]*band\s*\)", re.I), "grades sorted as text"),
    (re.compile(r"\bband\b.*\.sort\(\)"), "grades sorted as text"),
]


def _python_code(text: str) -> str:
    """The file without its comments and docstrings, line for line: prose may say "Grade 3" of a paper it remembers."""
    lines = text.split("\n")
    prev = tokenize.INDENT
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        doc = tok.type == tokenize.STRING and prev in (tokenize.INDENT, tokenize.NEWLINE, tokenize.DEDENT)
        if tok.type == tokenize.COMMENT or doc:
            (r0, c0), (r1, c1) = tok.start, tok.end
            for r in range(r0, r1 + 1):
                start = c0 if r == r0 else 0
                end = c1 if r == r1 else len(lines[r - 1])
                lines[r - 1] = lines[r - 1][:start] + " " * (end - start) + lines[r - 1][end:]
        if tok.type not in (tokenize.NL, tokenize.COMMENT):
            prev = tok.type
    return "\n".join(lines)


def _ts_code(text: str) -> str:
    """The file without its comments, line for line."""
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group().count("\n"), text, flags=re.S)
    return re.sub(r"(?<![:\\\w\"'`])//.*", "", text)


def _named(root: str, path: str, text: str) -> list[str]:
    code = (
        _python_code(text)
        if path.endswith(".py")
        else _ts_code(text)
        if path.endswith((".ts", ".tsx"))
        else text
    )
    return [
        f"{path}:{n}: {why}: {line.strip()[:100]}"
        for n, line in enumerate(code.split("\n"), 1)
        for pattern, why in NAMING
        if pattern.search(line)
    ]


def test_the_scan_sees_what_it_looks_for():
    """Each way of naming a grade the audit found, as the scan reads it — so the test below fails for the right reason."""
    for line in (
        'if band == "G1":',
        'grade = f"Grade {band[1:]}"',
        "const g = Number(band.replace(/\\D/g, ''))",
        "left(r.band, 2) as band",
        "substring(r.band from 2 for 1)::int",
        "order by c.band, c.section",
        '["G2+", "Reasoning · Grade 2 and up"]',
        "{`Grade ${c.band.slice(1)}`}",
        'digits = "".join(ch for ch in str(band or "") if ch.isdigit())',
        "const bands = [...new Set(nodes.map((n) => n.band))].sort();",
    ):
        assert _named("x", "x.ts", line), line
    for line in (
        "// a Grade 3 paper",
        "/* G2 */ const x = 1",
        "order by c.band_ord",
        "select band from child",
    ):
        assert not _named("x", "x.ts", line), line
    assert not _named("x", "x.py", '"""Aseem\'s five Grade 3 reports."""\nx = 1  # Grade 3\n')


def test_no_file_outside_the_maths_library_names_a_grade():
    """Nimish: "everything is now getting built in a proper, scalable way, not as some one-time random effort". A grade
    is a row of `grade`, with its name and its order: no page or query outside the maths library names one, reads one
    out of its code or sorts grades as text, so adding Grade 11 is an insert."""
    found = []
    for root, exts in SCANNED.items():
        for p in sorted((db.REPO_ROOT / root).rglob("*")):
            rel = str(p.relative_to(db.REPO_ROOT))
            if p.suffix in exts and "node_modules" not in p.parts and not rel.startswith(EXEMPT):
                found += _named(root, rel, p.read_text())
    assert found == [], "\n".join(found)


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


# Every column that holds a grade.
GRADE_COLUMNS = [
    ("rung", "band"),
    ("child", "band"),
    ("sheet_template", "band"),
    ("blueprint", "band"),
    ("level_rule", "band"),
    ("milestone", "band"),
    ("learning_objective", "band"),
    ("activity", "band"),
    ("report_item", "band"),
    ("trait", "band"),
]


@NEEDS_DB
def test_every_grade_a_row_holds_is_a_key_into_grade(conn):
    """Nimish: "we need proper tables". Each column that holds a grade is a key on (school, code) into `grade`, and a
    level's grade (`skill_set.level_band`) is checked against it on every write: a grade that is not a row is refused."""
    for table, column in GRADE_COLUMNS:
        found = conn.execute(
            "select confrelid::regclass::text as target,"
            " array(select attname from pg_attribute a join unnest(c.conkey) k(n) on a.attnum = k.n"
            "       where a.attrelid = c.conrelid) as cols"
            " from pg_constraint c where c.contype = 'f' and c.conrelid = %s::regclass",
            (table,),
        ).fetchall()
        assert {"target": "grade", "cols": ["tenant_id", column]} in found, (
            f"{table}.{column} is no key into grade"
        )
    t = loaders._tenant(conn)
    for bad in (
        "update rung set band = 'G11' where code = 'R11'",
        f"insert into child (tenant_id, roll_no, section, band) values ('{t}', '1', 'B0B', 'Grade 3')",
    ):
        with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
            conn.execute(bad)
    for bad in ('{"Hard": "G11"}', '{"Hard": "G2+"}', '{"Expert": "G2"}'):
        with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
            conn.execute("update skill_set set level_band = %s::jsonb where code = 'MUL.2D1D'", (bad,))
    with conn.transaction():
        conn.execute("update skill_set set level_band = '{\"Hard\": \"G10\"}'::jsonb where code = 'MUL.2D1D'")


@NEEDS_DB
def test_reasoning_is_grade_2(conn):
    """Nimish's decision (B3 on the design): "G2+" becomes Grade 2 — it already meant first met in Grade 2, which is
    what every level's grade means. No row and no seed holds it, and a Grade 2, 3 or 4 child is still given reasoning."""
    for table, column in GRADE_COLUMNS:
        held = conn.execute(f"select count(*) as n from {table} where {column} like '%%+'").fetchone()["n"]  # noqa: S608
        assert held == 0, f"{table}.{column} still holds a '+' grade"
    plus = conn.execute(
        "select count(*) as n from skill_set s, jsonb_each_text(s.level_band) e where e.value like '%%+'"
    ).fetchone()["n"]
    assert plus == 0, "a level's grade still holds a '+'"
    assert all(r["band"] == "G2" for r in settings.seed("rungs.json", "rungs") if r["code"] in ("X1", "X2"))
    for band in ("G2", "G3", "G4"):
        assert shelf._read_levels(conn, band)["REASON.FIND_MISTAKE"], (
            f"a {band} child is no longer given reasoning"
        )
    assert not shelf._read_levels(conn, "G1")["REASON.FIND_MISTAKE"]


def _child(conn, tenant, section, band):
    conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s, %s, %s, %s)",
        (tenant, uuid.uuid4().hex[:6], section, band),
    )


@NEEDS_DB
def test_grade_10_sorts_after_grade_9_and_is_never_read_as_grade_1(conn):
    """Grades sort by their order in `grade`, never by their code as text ("G10" < "G9"), and a grade is its row, never
    a number read from its code ("G10"[1] is 1): a class of one Grade 9 and one Grade 10 child is Grade 9 (the lower on
    a tie); a Grade 10 skill is a Grade 10 child's and class's, and never a Grade 1 child's."""

    t = loaders._tenant(conn)
    section = f"B0B{uuid.uuid4().hex[:4]}"
    _child(conn, t, section, "G10")
    _child(conn, t, section, "G9")
    assert conn.execute("select class_band(%s, %s) as b", (t, section)).fetchone()["b"] == "G9"
    assert conn.execute("select grade_ord(%s, 'G10') > grade_ord(%s, 'G9') as later", (t, t)).fetchone()[
        "later"
    ]

    conn.execute("update skill_set set level_band = '{}'::jsonb where code = 'ADD.2D2D'")
    conn.execute(
        "update rung set band = 'G10' where tenant_id = %s and code = (select rung_code from skill_set where code = 'ADD.2D2D')",
        (t,),
    )
    assert shelf._read_levels(conn, "G10")["ADD.2D2D"], "a Grade 10 skill is a Grade 10 child's"
    assert not shelf._read_levels(conn, "G1")["ADD.2D2D"], "a Grade 10 skill read as Grade 1"
    assert "ADD.2D2D" in week_note.options(conn, "G10")
    assert "ADD.2D2D" not in week_note.options(conn, "G1")
