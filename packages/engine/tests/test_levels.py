"""The four levels are read from `difficulty` everywhere (goals/b0c-levels-from-the-table.yaml).

Nimish, 2026-10-20: "we need proper tables". B0a made the levels a table; until now the engine, the website and the
database's own `next_difficulty` each wrote the four names, their order and their worksheet letters again. Here no file
outside the maths library (engine/assess) may name one, and what a child is given does not move: the next level their
answers call for, and the letter in every worksheet code, are what they were before.
"""

import ast
import os
import re
from pathlib import Path

import pytest

from engine.core import db, loaders, settings, vocabulary
from engine.w2_print import library, prescribe, shelf

REPO = db.REPO_ROOT
LEVELS = [d["code"] for d in settings.seed("vocabulary.json", "difficulties")]
NAMED = re.compile(r"\b(" + "|".join(LEVELS) + r")\b")
LETTERS = "".join(code[0] for code in LEVELS)  # the letters a worksheet code's pattern would list: "EMHA"
needs_db = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


def _python_strings(path: Path) -> list[tuple[int, str]]:
    """Every string a Python file's code holds, docstrings aside (they are prose, as comments are)."""
    tree = ast.parse(path.read_text())
    docs = {
        id(n.body[0].value)
        for n in ast.walk(tree)
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        and n.body
        and isinstance(n.body[0], ast.Expr)
        and isinstance(n.body[0].value, ast.Constant)
    }
    return [
        (n.lineno, n.value)
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs
    ]


def _script_code(path: Path) -> list[tuple[int, str]]:
    """A TypeScript file's lines with its comments taken out: the code, its strings and its page text."""
    text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group().count("\n"), path.read_text(), flags=re.S)
    text = re.sub(r"(^|[^:\\])//.*", r"\1", text)
    return list(enumerate(text.splitlines(), 1))


def _files() -> list[Path]:
    engine = [p for p in (REPO / "packages/engine/engine").rglob("*.py") if "assess" not in p.parts]
    web = [
        p
        for d in ("app", "lib", "components")
        for p in (REPO / "apps/web" / d).rglob("*.ts*")
        if p.suffix in (".ts", ".tsx")
    ]
    return engine + web + sorted((REPO / "n8n/workflows").glob("*.json"))


def test_no_file_outside_the_maths_library_names_a_level():
    """The engine, the website and n8n read the levels from the table: none writes a level's name in its code, nor the
    letters of the worksheet codes. A level is a row: renaming one, or adding a fifth, is an insert."""
    found = []
    for path in _files():
        lines = (
            _python_strings(path)
            if path.suffix == ".py"
            else _script_code(path)
            if path.suffix in (".ts", ".tsx")
            else list(enumerate(path.read_text().splitlines(), 1))
        )
        for n, text in lines:
            if NAMED.search(text) or LETTERS in text:
                found.append(f"{path.relative_to(REPO)}:{n}: {text.strip()[:100]}")
    assert not found, "\n".join(found)


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@needs_db
def test_no_database_function_names_a_level(conn):
    """The database's own functions read `difficulty` too. The one that writes the rows for a new school is their seed
    (B0a; tests/test_vocabulary.py keeps it equal to vocabulary.json), so it alone may."""
    rows = conn.execute(
        "select n.nspname || '.' || p.proname as f from pg_proc p join pg_namespace n on n.oid = p.pronamespace"
        " where n.nspname in ('public', 'internal') and p.prosrc ~ %s"
        " and (n.nspname, p.proname) <> ('internal', 'school_vocabulary')",
        (r"\m(" + "|".join(LEVELS) + r")\M",),
    ).fetchall()
    assert [r["f"] for r in rows] == []


@needs_db
def test_the_order_and_the_letters_are_the_tables(conn):
    """What the engine reads is the table: its order, and each level's letter in a worksheet code — the letters the
    codes have always had."""
    assert list(vocabulary.levels(conn)) == LEVELS
    assert vocabulary.letters(conn) == {"Easy": "E", "Medium": "M", "Hard": "H", "Advance": "A"}
    conn.execute("update difficulty set ord = 9 - ord")
    assert list(vocabulary.levels(conn)) == LEVELS[::-1]


SET = "ADD.2D2D"


def _child(conn, prior: str | None, right: int, answered: int) -> str:
    """A child of a section of their own with `right` of `answered` confirmed answers on SET's rung, last prescribed
    at `prior`."""
    tenant = loaders._tenant(conn)
    rung = conn.execute("select rung_code from skill where code = %s", (SET,)).fetchone()["rung_code"]
    child = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s, '1', 'B0C-TEST', 'G2') returning id",
        (tenant,),
    ).fetchone()["id"]
    for i in range(answered):
        conn.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, channel, observed_at,"
            " confirmed_by) values (%s, %s, 'NUM.OPS.01', %s, %s, 'item', now(), 'test')",
            (tenant, child, rung, i < right),
        )
    if prior:
        conn.execute(
            "insert into prescription (tenant_id, child_id, week, kind, skill_set_code, difficulty, rule_fired)"
            " values (%s, %s, '2026-W43', 'practice', %s, %s, 'test')",
            (tenant, child, SET, prior),
        )
    return child


# (last prescribed, right, answered) -> (the level next, the rule): the rule as it was before B0c, written out
BEFORE = {
    (None, 1, 2): (None, "band_default"),
    (None, 9, 10): ("Hard", "from_state"),
    (None, 6, 10): ("Medium", "from_state"),
    (None, 3, 10): ("Easy", "from_state"),
    ("Easy", 3, 10): ("Easy", "from_state"),
    ("Easy", 9, 10): ("Medium", "from_state"),
    ("Hard", 9, 10): ("Advance", "from_state"),
    ("Hard", 3, 10): ("Medium", "from_state"),
    ("Advance", 9, 10): ("Advance", "from_state"),
    ("Advance", 6, 10): ("Advance", "from_state"),
}


@needs_db
@pytest.mark.parametrize(("prior", "right", "answered"), list(BEFORE))
def test_the_next_level_is_what_it_was(conn, prior, right, answered):
    """The next level a child's answers call for — up one at four in five right, down one under half, kept between —
    is what it was when `next_difficulty` wrote the four names itself."""
    child = _child(conn, prior, right, answered)
    got = conn.execute("select difficulty, rule from next_difficulty(%s, %s)", (child, SET)).fetchone()
    assert (got["difficulty"], got["rule"]) == BEFORE[(prior, right, answered)]


@needs_db
def test_a_level_added_is_a_row_the_engine_takes(conn):
    """A fifth level is an insert: the engine lists it last, gives it its letter, lets an educator choose it, and a
    child at the hardest level who keeps getting it right moves up to it."""
    tenant = loaders._tenant(conn)
    conn.execute(
        "insert into difficulty (tenant_id, code, ord, letter) values (%s, 'Olympiad', 4, 'O')", (tenant,)
    )
    assert vocabulary.levels(conn)[-1] == "Olympiad"
    assert vocabulary.letters(conn)["Olympiad"] == "O"
    child = _child(conn, "Advance", 9, 10)
    got = conn.execute("select difficulty from next_difficulty(%s, %s)", (child, SET)).fetchone()
    assert got["difficulty"] == "Olympiad"
    p = conn.execute("select id from prescription where child_id = %s", (child,)).fetchone()["id"]
    prescribe.override(conn, p, "Olympiad", "test", "a fifth level")
    with pytest.raises(ValueError, match="is not one of"):
        prescribe.override(conn, p, "Impossible", "test", "no such level")
    conn.execute("update difficulty set ord = 9 - ord where tenant_id = %s", (tenant,))
    assert shelf.rule(conn)["order"][0] == "Olympiad"


@needs_db
def test_every_worksheet_code_keeps_its_letter(conn):
    """Every library worksheet's code carries its level's letter from the table — the same letter it was printed with —
    and the library makes new codes from the table too."""
    wrong = conn.execute(
        "select t.code, t.difficulty, d.letter from sheet_template t"
        " join difficulty d on d.tenant_id = t.tenant_id and d.code = t.difficulty"
        " where t.source = 'library' and substring(t.code from '-([A-Z])[0-9]+$') <> d.letter"
    ).fetchall()
    assert wrong == []
    assert (
        library.code_of(vocabulary.letters(conn), {"rung_code": "R22", "difficulty": "Medium"}, 7)
        == "R22-M07"
    )
