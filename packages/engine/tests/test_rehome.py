"""The calculation skills by operation and digit shape, their levels the taxonomy's cases (goals/s13, ADR 0034).

The pure tests place questions measured from their numbers onto the seed's skills; the database tests read
the bank after `engine bank rehome` and `engine library build` have run on it.
"""

import json
import os
import pathlib

import pytest

from engine.assess import placing, tags, taxonomy
from engine.assess.items import Item
from engine.core import db
from engine.w1_bank import cases, rehome

SEED = pathlib.Path(__file__).resolve().parents[3] / "supabase/seed"
SKILLS = [
    s
    for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]
    if any("within" in lv["check"] for lv in s["difficulty"].values())
]
MATCHES = {
    c["code"]: c["match"] for c in json.loads((SEED / "taxonomy_cases.json").read_text())["taxonomy_cases"]
}
CALCULATION = {"bare_sum", "column_grid"}


def _place(fmt, spec):
    got = placing.place(
        fmt, tags.derive(Item("x", "x", "R0", [], "P", fmt, False, "", spec, [])), SKILLS, MATCHES
    )
    return got and (got[0]["code"], got[1])


@pytest.mark.parametrize(
    "fmt,spec,home",
    [
        ("column_grid", {"a": 23, "b": 45, "op": "+", "layout": "column"}, ("ADD.2D2D", "Easy")),
        ("bare_sum", {"a": 23, "b": 45, "op": "+", "layout": "horizontal"}, ("ADD.2D2D", "Easy")),
        ("column_grid", {"a": 27, "b": 36, "op": "+", "layout": "column"}, ("ADD.2D2D", "Medium")),
        ("column_grid", {"a": 68, "b": 47, "op": "+", "layout": "column"}, ("ADD.2D2D", "Hard")),
        ("column_grid", {"a": 68, "b": 25, "op": "-", "layout": "column"}, ("SUB.2D2D", "Easy")),
        ("column_grid", {"a": 52, "b": 27, "op": "-", "layout": "column"}, ("SUB.2D2D", "Medium")),
        ("column_grid", {"a": 43, "b": 5, "op": "+", "layout": "column"}, ("ADD.2D1D", "Easy")),
        ("column_grid", {"a": 402, "b": 185, "op": "-", "layout": "column"}, ("SUB.3D3D", "Hard")),
        ("column_grid", {"a": 5000, "b": 1476, "op": "-", "layout": "column"}, ("SUB.4D", "Hard")),
    ],
)
def test_a_question_is_placed_by_its_own_numbers(fmt, spec, home):
    assert _place(fmt, spec) == home


def test_no_two_skills_hold_one_question_and_no_level_names_a_case_its_numbers_cannot_be():
    for s in SKILLS:
        for level, lv in s["difficulty"].items():
            for c in lv["check"]["cases"]:
                taxonomy.within(MATCHES[c], lv["check"]["within"])  # raises on a contradiction
    shapes = [placing.shape(s) for s in SKILLS]
    for a in (23, 5, 402, 4382):
        for b in (45, 7, 185):
            for op in "+-":
                if op == "-" and a < b:
                    continue
                t = tags.derive(
                    Item("x", "x", "R0", [], "P", "column_grid", False, "", {"a": a, "b": b, "op": op}, [])
                )
                assert sum(taxonomy.matches(sh, "column_grid", t) for sh in shapes) <= 1, (a, op, b)


def test_every_replaced_skill_set_is_named_in_the_seed():
    old = rehome.replaced(json.loads((SEED / "skill_sets.json").read_text())["skill_sets"])
    assert set(old) == {
        "ADD.1D.WITHIN10", "ADD.1D.BRIDGE10", "SUB.1D.WITHIN20", "ADDSUB.2D.NOREG", "ADD.2D.REG",
        "SUB.2D.EXCH", "ADD.3D.REG", "SUB.3D.ZERO", "ADDSUB.4D.ADV", "ADD.MULTI.SMALL",
    }  # fmt: skip


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        if not c.execute(
            "select 1 from skill_set where code = 'ADD.2D2D' and status <> 'retired'"
        ).fetchone():
            pytest.skip(
                "the taxonomy-shaped skills are not loaded here: `engine load`, then `engine bank rehome`"
            )
        yield c
        c.rollback()


def _active(conn, where="true"):
    return conn.execute(
        "select i.skill_set_code, i.difficulty, i.fmt, i.tags, s.difficulty as levels from item i"
        " join skill_set s on s.tenant_id = i.tenant_id and s.code = i.skill_set_code"
        " where i.status = 'active' and s.status <> 'retired' and " + where
    ).fetchall()


def test_easy_is_straight_calculation_of_one_operation(conn):
    rows = _active(
        conn,
        "i.skill_set_code in (select code from skill_set where difficulty -> 'Easy' -> 'check' ? 'within')",
    )
    for r in rows:
        if r["difficulty"] == "Advance":
            continue
        within = r["levels"][r["difficulty"]]["check"]["within"]
        assert r["fmt"] in CALCULATION and r["tags"]["operation"] == within["operation"], r
    easy = [r for r in rows if (r["skill_set_code"], r["difficulty"]) == ("ADD.2D2D", "Easy")]
    assert easy and all(
        (r["tags"]["operand_1_digits"], r["tags"]["operand_2_digits"], r["tags"]["regrouping"])
        == (2, 2, "NONE")
        for r in easy
    )
    assert {r["tags"]["presentation"] for r in easy} == {"VERTICAL", "HORIZONTAL"}


def test_only_advance_mixes_kinds_of_question(conn):
    kinds = {}
    for r in _active(
        conn,
        "i.skill_set_code in (select code from skill_set where difficulty -> 'Easy' -> 'check' ? 'within')",
    ):
        kinds.setdefault((r["skill_set_code"], r["difficulty"]), set()).add(r["fmt"])
    assert all(k <= CALCULATION for (_, level), k in kinds.items() if level != "Advance")
    assert any(k - CALCULATION for (_, level), k in kinds.items() if level == "Advance")


def test_every_taxonomy_case_has_a_place(conn):
    where = cases.placed(conn)
    assert len(where) == 269
    assert [c for c, _, _, state in where if state == "unplaced"] == []
    assert {s for c, s, _, state in where if state == "pattern"} == {"5.1", "5.2"}


def test_every_question_moves_to_the_level_its_numbers_put_it_in_and_none_is_lost(conn):
    retired = conn.execute("select code from skill_set where status = 'retired'").fetchall()
    assert retired, "the replaced skill sets are kept, retired"
    left = conn.execute(
        "select count(*) as n from item where status = 'active'"
        " and skill_set_code in (select code from skill_set where status = 'retired')"
    ).fetchone()["n"]
    assert left == 0
    assert cases.outside_their_level(conn) == []
    again = rehome.rehome(conn)
    assert (again["retired_sets"], sum(again["moved"].values()), sum(again["no_place"].values())) == (
        [],
        0,
        0,
    )


def test_worksheets_are_built_one_skill_and_one_level_each(conn):
    bad = conn.execute(
        "select t.code from sheet_template t, unnest(t.item_ids) u(id) join item i on i.id = u.id"
        " where t.source = 'library' and t.retired_at is null"
        " and (i.skill_set_code <> t.skill_set_code or i.difficulty <> t.difficulty) limit 5"
    ).fetchall()
    assert bad == []
    built = conn.execute(
        "select count(distinct (t.skill_set_code, t.difficulty)) as n from sheet_template t"
        " join skill_set s on s.code = t.skill_set_code where t.source = 'library' and t.retired_at is null"
        " and s.difficulty -> 'Easy' -> 'check' ? 'within'"
    ).fetchone()["n"]
    levels = conn.execute(
        "select count(*) as n from skill_set s, jsonb_object_keys(s.difficulty) k"
        " where s.status <> 'retired' and s.difficulty -> 'Easy' -> 'check' ? 'within'"
    ).fetchone()["n"]
    assert built == levels
    assert not conn.execute(
        "select 1 from sheet_template t join skill_set s on s.code = t.skill_set_code"
        " where t.source = 'library' and t.retired_at is null and s.status = 'retired'"
    ).fetchone()
