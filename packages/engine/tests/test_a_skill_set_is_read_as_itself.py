"""A skill set is read as itself everywhere it is read (goals/md0c-a-skill-set-is-read-as-itself.yaml).

Every report and the graph read a skill set through its rung (`skill_set.rung_code`), and nothing kept a second skill
set off a rung. A skill set's own skill was a count of its questions' skills, so equal groups — whose every question
uses Multiplication and Addition — was Addition by the alphabet. And the website took any one of a mistake's names.
"""

import json
import os

import psycopg
import pytest

from engine.assess import operations as O
from engine.core import db, mistake_names
from engine.w2_print import shelf

SEED = db.REPO_ROOT / "supabase" / "seed"


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs the local copy (bin/testdb)")
    with db.connect(db.dsn()) as c:
        yield c
        c.rollback()


def test_a_rung_holds_one_skill_set(conn):
    """The seed puts one skill set on each rung, and the database refuses a second on any rung."""
    sets = json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]
    rungs = [s["rung_code"] for s in sets]
    assert len(rungs) == len(set(rungs)), "one skill set a rung in the seed"
    taken = conn.execute(
        "select tenant_id, rung_code from skill_set where rung_code is not null limit 1"
    ).fetchone()
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute(
            "insert into skill_set (tenant_id, code, rung_code, name, learning_objective, difficulty) values (%s,"
            " 'TEST.TWIN', %s, 'a twin', 'two on one rung', '{}')",
            (taken["tenant_id"], taken["rung_code"]),
        )


def test_a_skill_sets_own_skill_is_the_one_its_rung_declares(conn):
    """A rung lists its skills own first (`rung.skill_codes`); the catalogue a paper is drawn from reads that, not a
    count of its questions' skills, which made equal groups Addition and a budget story Money."""
    declared = {
        r["code"]: r["own"]
        for r in conn.execute(
            "select s.code, r.skill_codes[1] as own from skill_set s"
            " join rung r on r.code = s.rung_code and r.tenant_id = s.tenant_id"
        )
    }
    catalog = {c["code"]: c["own"] for c in shelf._catalog(conn)}
    assert catalog, "the catalogue holds the taught skill sets"
    assert {c: declared[c] for c in catalog} == catalog
    assert catalog["MUL.GROUPS"] == "NUM.OPS.03", "equal groups is Multiplication"


def test_the_website_names_a_mistake_for_its_operation_as_the_engine_does(conn):
    """One rule, read by both: the name for the question's own operation, else for the operation of the skill the
    mistake was charged to; failing that, its name for any operation, else the one name it has, else its code."""
    for written in [*O.SIGNS, "-+", "+-", "?", ""]:  # however a spec writes its operation, folded alike
        sql = conn.execute("select operation_sign(%s) as s", (written,)).fetchone()["s"]
        assert sql == O.sign(written[:1] or None), written
    name_of = mistake_names.names(conn)
    by_operation = conn.execute("select value from config where key = 'skills.by_operation'").fetchone()[
        "value"
    ]
    skills = [None, *by_operation.values(), "NUM.PV.01", "NUM.PRB.02"]
    codes = [r["code"] for r in conn.execute("select distinct code from misconception order by 1")]
    for code in codes:
        for skill in skills:
            for op in (None, "+", "-", "×", "÷", "-+", "*", "−"):
                sql = conn.execute("select mistake_name(%s, %s, %s) as n", (code, skill, op)).fetchone()["n"]
                assert sql == name_of(code, op=op, skill=skill), (code, skill, op)
    wrong_op = {s: name_of("M_WRONG_OP", skill=s) for s in ("NUM.OPS.01", "NUM.OPS.02", "NUM.OPS.03")}
    assert len(set(wrong_op.values())) == 3, wrong_op
    assert "subtracting" in wrong_op["NUM.OPS.02"].lower(), (
        "a subtraction's wrong operation is adding instead"
    )
    assert name_of("M_WRONG_OP", op="-", skill="NUM.PRB.02") == wrong_op["NUM.OPS.02"], (
        "the question's operation first"
    )
    assert name_of("M_WRONG_OP", skill="NUM.PRB.02") == "Chose the wrong operation", (
        "no operation: its name for any"
    )
