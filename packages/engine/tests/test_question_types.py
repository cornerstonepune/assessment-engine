"""B2: a question type is a row, a level's types are rows, one approval covers a type everywhere, and a paper draws only
confirmed levels and approved types (goals/b2-question-types-are-rows.yaml, ADR 0077, decisions B2-1, B2-2 and B2-4).

What a type is, the test works out for itself, as ADR 0077 settled it and not as the code does: the printed format where
the template is only the level's numbers written as a name (ADD.2D2D.REG1, MUL.3D1D, ADD.MULTI3), else the template.
The copy (`bin/testdb`) has every level confirmed and every type in use approved, as live has them; each test withdraws
what it needs withdrawn, inside a transaction rolled back after it."""

import os
import random
import re
import subprocess
from collections import defaultdict

import pytest

from engine.assess import focus, render
from engine.checks import past
from engine.core import db
from engine.w1_bank import question_types
from engine.w2_print import focus_paper, handout, library
from tests.rows import data_steps

NUMBERS = re.compile(r"^(ADD|SUB|MUL|DIV)\.(\dD\dD(\.REG\w*)?|MULTI\d*)$")
CARD_KINDS = {"MUL3.SUM", "MUL3.STORY", "SEQ.ON", "SEQ.BACK", "MULT.NTH", "MULT.FIRST5"}
MIGRATION = next((db.REPO_ROOT / "supabase/migrations").glob("*_question_types_are_rows.sql"), None)

NEEDS_DB = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs the local copy (bin/testdb)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _type(fmt, template):
    return fmt if NUMBERS.match(template or "") else template


def _bank(conn):
    """{(skill, level): {type}} for every active question the bank made, worked out by ADR 0077's rule."""
    out = defaultdict(set)
    for r in conn.execute(
        "select distinct skill_set_code as s, difficulty as l, fmt, template from item"
        " where status = 'active' and source = 'generated'"
    ):
        out[(r["s"], r["l"])].add(_type(r["fmt"], r["template"]))
    return out


def _waits(conn, code):
    """`code` as a new type is: no approval. Rolled back with the test."""
    conn.execute("delete from question_type_approval where question_type = %s", (code,))


def _drawable(conn, code):
    return conn.execute(
        "select count(*)::int as n, count(distinct (skill_set_code, difficulty))::int as levels from drawable_item"
        " where question_type = %s",
        (code,),
    ).fetchone()


def _child(conn, band="G4"):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    return conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s, '1', 'TYPETEST', %s) returning id",
        (tenant, band),
    ).fetchone()["id"]


@NEEDS_DB
def test_every_label_card_kind_and_library_type_is_one_row(conn):
    """Nimish: "we need proper tables". Each type the bank holds is a row of `question_type` with its words, how it
    reaches the child and how it is marked; the 33 labels are the words the types show; the 6 card kinds are types."""
    rows = {r["code"]: r for r in conn.execute("select * from question_type")}
    held = {t for ts in _bank(conn).values() for t in ts}
    assert held <= set(rows), sorted(held - set(rows))
    assert CARD_KINDS <= set(rows), sorted(CARD_KINDS - set(rows))
    labels = {r["fmt"] for r in rows.values()}
    assert len(labels) >= 33 and {r["fmt"] for r in conn.execute("select distinct fmt from item")} <= labels
    for code, r in rows.items():
        assert r["words"] and r["reaches"] in ("printed", "read_aloud", "drawn") and r["marked"], code
    # a type's words are its label's: the types that share a printed format show the same words
    by_label = defaultdict(set)
    for r in rows.values():
        by_label[r["fmt"]].add(r["words"])
    assert all(len(w) == 1 for w in by_label.values()), {k: v for k, v in by_label.items() if len(v) > 1}
    # a type prints its own words unless the maths library draws its line from its numbers
    assert {c for c, r in rows.items() if not r["own_words"]} == {
        c for c, r in rows.items() if r["fmt"] in render.DRAWN_FROM_NUMBERS
    }


@NEEDS_DB
def test_every_level_uses_the_same_types_before_and_after(conn):
    """Nimish: "we need proper tables". Which types a level uses is rows (`skill_level_question_type`), keys into
    `skill_level` and `question_type`; they are exactly the types its questions were made in, and nothing reads
    which types a level uses from the skills' `formats` lists any more."""
    links = defaultdict(set)
    for r in conn.execute("select skill_code, difficulty, question_type from skill_level_question_type"):
        links[(r["skill_code"], r["difficulty"])].add(r["question_type"])
    bank = _bank(conn)
    assert {k: v for k, v in links.items() if v} == {k: v for k, v in bank.items() if v}
    fks = {
        r["target"]
        for r in conn.execute(
            "select confrelid::regclass::text as target from pg_constraint"
            " where contype = 'f' and conrelid = 'skill_level_question_type'::regclass"
        )
    }
    assert {"skill_level", "question_type"} <= fks, fks
    # The skill's list stays only as what the generator makes a level's plain sums in where the level names no format of
    # its own (146 of 178 levels): the bank, its prompts and cases, the check that each listed format can be made, and
    # B1's comparison of rows and blob. Nothing else asks it which types a level uses.
    makers = {
        "packages/engine/engine/w1_bank/bank.py",
        "packages/engine/engine/w1_bank/spec.py",
        "packages/engine/engine/w1_bank/cases.py",
        "packages/engine/engine/checks/audit.py",
        "packages/engine/engine/checks/levels.py",
        "packages/engine/engine/core/loaders.py",
    }
    readers = [
        rel
        for root in ("packages/engine/engine", "apps/web/app", "apps/web/lib", "apps/web/components")
        for p in (db.REPO_ROOT / root).rglob("*")
        if p.suffix in (".py", ".ts", ".tsx")
        and (rel := str(p.relative_to(db.REPO_ROOT))) not in makers
        and re.search(r"""(\.|\[")formats\b|\bformats &&|, formats,""", p.read_text())
    ]
    assert readers == [], readers


@NEEDS_DB
def test_one_approval_covers_a_type_in_every_skill_and_level(conn):
    """Nimish: "all unique formats of questions". One approval of find-the-mistake opens it in every skill and level
    that uses it, and it is the coordinator's, with when."""
    code = "FTM"
    used = {k for k, ts in _bank(conn).items() if code in ts}
    assert len({s for s, _ in used}) >= 2, (
        "find the mistake must be in two skills or more for this to mean anything"
    )
    n = conn.execute(
        "select count(*)::int as n from item where status = 'active' and source = 'generated'"
        " and question_type_of(fmt, template) = %s",
        (code,),
    ).fetchone()["n"]
    _waits(conn, code)
    assert _drawable(conn, code)["n"] == 0
    assert not question_types.state(conn, code)["approved"]

    question_types.approve(conn, code, "Test Coordinator")
    got = _drawable(conn, code)
    assert (got["n"], got["levels"]) == (n, len(used)), "one approval, every skill and level"
    s = question_types.state(conn, code)
    assert s["approved"] and s["by"] == "Test Coordinator" and s["at"]
    with pytest.raises(ValueError, match="names who"):
        question_types.approve(conn, code, "")
    with pytest.raises(LookupError, match="NO.SUCH"):
        question_types.approve(conn, "NO.SUCH", "Test Coordinator")


@NEEDS_DB
def test_the_coordinator_approves_a_type_with_one_command(conn):
    """Nimish: "all unique formats of questions". `engine types approve <type> --by <name>` gives the approval;
    `engine types` lists every type, its words and whether it waits."""
    out = subprocess.run(
        [str(db.REPO_ROOT / "bin/engine"), "types"], capture_output=True, text=True, check=True
    ).stdout
    assert "FTM" in out and "find the mistake" in out and "approved" in out
    done = subprocess.run(
        [
            str(db.REPO_ROOT / "bin/engine"),
            "types",
            "approve",
            "FTM",
            "--by",
            "Test Coordinator",
            "--dry-run",
        ],
        capture_output=True,
        text=True,
    )
    # the copy has every type approved, as live has: approving again changes nothing and says who gave it
    assert done.returncode == 0 and "FTM" in done.stdout and "already approved by" in done.stdout, done.stderr
    nothing = subprocess.run(
        [str(db.REPO_ROOT / "bin/engine"), "types", "approve", "NO.SUCH", "--by", "Test Coordinator"],
        capture_output=True,
        text=True,
    )
    assert nothing.returncode == 1 and "no question type NO.SUCH" in nothing.stderr


def _level_holding(conn, code, also_other=True):
    """A (skill, level) whose questions hold `code` beside another type, with a library worksheet holding it."""
    bank = _bank(conn)
    for (s, lv), ts in sorted(bank.items()):
        if code in ts and (len(ts) > 1 or not also_other):
            sheet = conn.execute(
                "select t.code from sheet_template t, unnest(t.item_ids) x(id) join item i on i.id = x.id"
                " where t.source = 'library' and t.retired_at is null and t.skill_set_code = %s and t.difficulty = %s"
                " and question_type_of(i.fmt, i.template) = %s limit 1",
                (s, lv, code),
            ).fetchone()
            if sheet:
                return s, lv, sheet["code"]
    pytest.fail(f"no level holds {code} beside another type on a library worksheet")


def _types(conn, ids):
    return {
        r["t"]
        for r in conn.execute(
            "select question_type_of(fmt, template) as t from item where id = any(%s)", (list(ids),)
        )
    }


@NEEDS_DB
def test_the_paper_maker_draws_only_confirmed_levels_and_approved_types(conn, tmp_path):
    """Nimish: "all unique formats of questions". Every path that puts a question on a paper — a home or made paper,
    the library's worksheets, a worksheet handed out — reads one rule, `drawable_item`: an active question of an
    approved type at a confirmed level."""
    code = "FTM"
    s, lv, sheet = _level_holding(conn, code)
    _waits(conn, code)
    rung = conn.execute("select rung_code from skill where code = %s", (s,)).fetchone()["rung_code"]
    area = focus.Area(s, rung, lv, 0, 0, None, "practising")
    drawn = focus_paper._draw(conn, [], area, 500, random.Random(1), 7)
    assert drawn and code not in _types(conn, [r["id"] for r in drawn])
    level = library._levels(conn, (s, lv))[0]
    retire, new = library._plan_level(conn, level, library.per_sheet(conn))
    assert sheet in {r["code"] for r in retire}
    assert all(code not in _types(conn, [q["id"] for q in qs]) for qs in new)
    with pytest.raises(ValueError, match="waits for the coordinator"):
        handout.for_children(conn, sheet, [_child(conn)], "2026-W50", "a test", tmp_path)

    # a level not confirmed: none of its questions is drawn, whatever their types
    conn.execute(
        "update skill set level_approved = level_approved - %s::text where code = %s",
        (lv, s),
    )
    assert not conn.execute(
        "select confirmed_at from skill_level where skill_code = %s and difficulty = %s", (s, lv)
    ).fetchone()["confirmed_at"]
    assert focus_paper._draw(conn, [], area, 500, random.Random(1), 7) == []


@NEEDS_DB
def test_a_paper_that_cannot_be_made_names_the_type_that_waits(conn, tmp_path):
    """Nimish: "all unique formats of questions". Asked for a paper whose level's types all wait, the paper-maker
    refuses and names each type in the school's words; an unconfirmed level is named too."""
    (s, lv), types = next((k, ts) for k, ts in sorted(_bank(conn).items()) if "FTM" in ts)
    for t in types:
        _waits(conn, t)
    rung = conn.execute("select rung_code from skill where code = %s", (s,)).fetchone()["rung_code"]
    area = focus.Area(s, rung, lv, 0, 0, None, "asked")
    with pytest.raises(ValueError) as said:
        focus_paper.drawn(conn, [], [(area, 5)], random.Random(1))
    for t in types:
        assert question_types.words(conn, t) in str(said.value), str(said.value)
    assert "waits for the coordinator" in str(said.value)
    assert set(question_types.waiting(conn, s, lv)) == types

    conn.execute("update skill set level_approved = level_approved - %s::text where code = %s", (lv, s))
    with pytest.raises(ValueError, match="not confirmed"):
        focus_paper.drawn(conn, [], [(area, 5)], random.Random(1))


@NEEDS_DB
def test_every_question_in_the_bank_belongs_to_exactly_one_type(conn):
    """Nimish: "simply checks whether a certain question belongs to a certain format". One rule in the database,
    `question_type_of`, puts each question in one type, and it is the rule ADR 0077 settled."""
    rows = conn.execute(
        "select distinct fmt, template, question_type_of(fmt, template) as t from item where source = 'generated'"
    ).fetchall()
    assert rows
    types = {r["code"] for r in conn.execute("select code from question_type")}
    wrong = [(r["fmt"], r["template"], r["t"]) for r in rows if r["t"] != _type(r["fmt"], r["template"])]
    assert wrong == [], wrong[:10]
    assert all(r["t"] in types for r in rows)


@NEEDS_DB
def test_a_new_type_is_an_insert_and_waits_for_approval(conn):
    """Nimish: "everything is now getting built in a proper, scalable way, not as some one-time random effort". A new
    type is one inserted row, no code; its questions are not drawn until the coordinator approves it."""
    s, lv = next(k for k, ts in sorted(_bank(conn).items()) if "WP1" in ts)
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    conn.execute(
        "insert into question_type (tenant_id, code, fmt, words, reaches, marked)"
        " values (%s, 'WP1.NEW', 'word_1step', 'one-step word problem', 'printed', '{computable}')",
        (tenant,),
    )
    conn.execute(
        "update item set template = 'WP1.NEW' where id = (select id from item where status = 'active'"
        " and skill_set_code = %s and difficulty = %s and template = 'WP1' limit 1)",
        (s, lv),
    )
    assert question_types.waiting(conn, s, lv) == ["WP1.NEW"]
    assert _drawable(conn, "WP1.NEW")["n"] == 0
    question_types.approve(conn, "WP1.NEW", "Test Coordinator")
    assert _drawable(conn, "WP1.NEW")["n"] == 1 and question_types.waiting(conn, s, lv) == []


# Where a type is named outside its row: its words, or a list of types to choose among. Drawing a column sum as a grid
# is how that type prints, and stays code (CLAUDE.md: code where correctness is needed).
TYPES = r"""["'](bare_sum|column_grid|word_1step|word_2step|missing_number|find_mistake)["']"""
LIST_OF_TYPES = re.compile(TYPES + r"\s*,\s*" + TYPES)  # two types in a row: a list to choose among
WORDS = re.compile(
    r""":\s*["'](horizontal sum|column sum|one-step word problem|find the mistake|make both sides equal)["']"""
)
EXEMPT = ("packages/engine/engine/assess/", "packages/engine/tests/", "apps/web/tests/")


def _named(rel, text):
    return [f"{rel}:{n}: {line.strip()}" for n, line in enumerate(text.splitlines(), 1)
            if LIST_OF_TYPES.search(line) or WORDS.search(line)]  # fmt: skip


def test_no_file_outside_the_maths_library_names_a_type():
    """Nimish: "everything is now getting built in a proper, scalable way, not as some one-time random effort". A type's
    words and the lists of types a page or query chooses among are rows; no file outside the maths library holds them,
    so adding a type is an insert."""
    assert _named("x.ts", 'const KIND = { bare_sum: "horizontal sum" }')
    assert _named("x.py", "usable = [f for f in ('bare_sum', 'column_grid', 'word_1step')]")
    assert not _named("x.tsx", 'if (it.fmt === "column_grid") return <Grid />')
    found = []
    for root in (
        "packages/engine/engine",
        "apps/web/app",
        "apps/web/lib",
        "apps/web/components",
        "supabase/seed",
    ):
        for p in sorted((db.REPO_ROOT / root).rglob("*")):
            rel = str(p.relative_to(db.REPO_ROOT))
            if (
                p.suffix in (".py", ".ts", ".tsx")
                and not rel.startswith(EXEMPT)
                and "node_modules" not in p.parts
            ):
                found += _named(rel, p.read_text())
    assert found == [], "\n".join(found)


@NEEDS_DB
def test_past_results_are_the_same_before_and_after(conn):
    """Nimish: "nothing will change for any of the past assessments, scoring etc. right?". The evidence (its count and
    checksum), every child's states and every scored answer are the same before and after B2's migration; and the
    fingerprint does see a change, so its sameness means something."""
    assert MIGRATION, "B2's migration is not written yet"
    child = _child(conn, "G3")
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    for right in (True, False, True):
        conn.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, channel, observed_at,"
            " confirmed_by) values (%s, %s, 'NUM.OPS.01', 'R22', %s, 'item', now(), 'test')",
            (tenant, child, right),
        )
    from engine.assess import graph

    graph.rebuild(conn, str(child))
    before = past.fingerprint(conn)
    assert before["evidence"]["n"] >= 3 and before["states"]["n"] >= 1
    conn.execute(data_steps(MIGRATION))
    graph.rebuild(conn, str(child))
    assert past.fingerprint(conn) == before
    conn.execute(
        "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, channel, observed_at,"
        " confirmed_by) values (%s, %s, 'NUM.OPS.01', 'R22', false, 'item', now(), 'test')",
        (tenant, child),
    )
    assert past.fingerprint(conn)["evidence"] != before["evidence"]


@NEEDS_DB
def test_every_type_already_in_use_starts_approved(conn):
    """Nimish: "nothing will change for any of the past assessments, scoring etc. right?". No paper that can be made
    today is refused: the day B2 ships, every type on a paper or at a level already approved starts approved, by the
    rule the migration runs; a type in use nowhere waits."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    conn.execute(
        "insert into question_type (tenant_id, code, fmt, words, reaches, marked)"
        " values (%s, 'UNUSED.TYPE', 'equation', 'make both sides equal', 'printed', '{computable}')",
        (tenant,),
    )
    conn.execute("delete from question_type_approval")
    conn.execute("select internal.question_types_start_approved()")
    held = {t for ts in _bank(conn).values() for t in ts}
    approved = {
        r["question_type"] for r in conn.execute("select distinct question_type from question_type_approval")
    }
    assert held <= approved, sorted(held - approved)
    assert "UNUSED.TYPE" not in approved
    # every level that could make a paper before still can
    short = conn.execute(
        "select distinct i.skill_set_code, i.difficulty from item i where i.status = 'active'"
        " and not exists (select 1 from drawable_item d where d.skill_set_code = i.skill_set_code"
        " and d.difficulty = i.difficulty)"
    ).fetchall()
    assert short == []
