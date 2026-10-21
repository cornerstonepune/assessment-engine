"""The bank fills every level every time (goals/bank-fills-every-time.yaml).

CI failed now and then on "every unit meets its target" (ADD.2D1D Hard 172 of 175 on #235; SUB.3D2D Advance while
#234 was built), and main passed at the same commit. A level whose cases make barely more questions than it asks for
found its last few once in thousands of random draws, and its budget of draws sometimes ran out first. A case's draws
now end, when they run dry, on the list of every question it can be (`draw.listed`), in a random order.

The proof draws a fresh bank, stored nowhere, under fixed seeds and with a tenth of a real build's draws: a level that
fills like that fills with ten times the margin. `BANK_FILL_SEEDS` says which seeds, `first:last` (CI runs 0:2; the goal
runs twenty, ten at a time, each half inside the half hour a goal's command is given)."""

import json
import os
import pathlib
import random

import pytest

from engine.assess import draw
from engine.core import db
from engine.w1_bank import bank, cases, inventory, refill
from engine.w1_bank.spec import read as spec

ROOT = pathlib.Path(__file__).resolve().parents[3]
SETS = {s["code"]: s for s in json.loads((ROOT / "supabase/seed/skill_sets.json").read_text())["skill_sets"]}
CASES = {
    c["code"]: c["match"]
    for c in json.loads((ROOT / "supabase/seed/taxonomy_cases.json").read_text())["taxonomy_cases"]
}
SEEDS = range(*map(int, os.getenv("BANK_FILL_SEEDS", "0:2").split(":")))
TENTH = 200  # draws a question is given before its case is listed; a real build gives 2000 (`draw.level`)
needs_db = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture(scope="module")
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _alone(code, level, target, seed, tries):
    """[(case, question)] of one level drawn as the first in a fresh bank, each case to its share."""
    check = SETS[code]["difficulty"][level]["check"]
    matches = cases.on_level(check, CASES)
    quotas = refill.shortfall(check, matches, target)
    rung = SETS[code]["rung_code"]
    return draw.level(random.Random(seed), check, matches, rung, target, quotas=quotas, tries_per_item=tries)


@pytest.mark.parametrize(
    "code,level,target",
    # 180 questions in its three cases for 175; S33 makes 72; TP05 makes 162 in a million pairs
    [("ADD.2D1D", "Hard", 175), ("SUB.3D2D", "Hard", 216), ("MUL.TENS", "Medium", 216)],
)
def test_a_level_its_cases_barely_hold_fills_even_with_one_draw_a_question(code, level, target):
    """One random draw a question, then the list: the level fills, every case to its share where it can make it, and
    no question twice. Before, ADD.2D1D Hard drew 4 to 14 of its 175 like this (five seeds)."""
    for seed in range(3):
        got = _alone(code, level, target, seed, tries=1)
        assert len(got) >= target, (code, level, seed, len(got))
        assert len({it.item_id for _, it in got}) == len(got)


def test_the_list_of_a_case_is_every_question_it_can_be():
    """A14, 2-digit + 1-digit in columns where the carry makes a 3-digit answer, counted by hand: 91 + 9 up to 99 + 9."""
    check = SETS["ADD.2D1D"]["difficulty"]["Hard"]["check"]
    made = draw.listed(cases.on_level(check, CASES)["A14"], check, SETS["ADD.2D1D"]["rung_code"])
    by_hand = {(a, b) for a in range(10, 100) for b in range(1, 10) if a + b >= 100}
    assert {(it.spec["a"], it.spec["b"]) for it in made} == by_hand
    assert {it.fmt for it in made} == {"column_grid"} and len(made) == 45


def _fresh_build(conn, seed):
    """{(skill set, level): (questions drawn, target)} for every level, drawn in refill's order with one set of keys
    across them all, so a level finds only what the levels before it left; stored nowhere."""
    rng, seen, out = random.Random(seed), set(), {}
    for r in inventory.coverage(conn):
        _, s, check = spec(conn, r["code"], r["difficulty"])
        if check.get("cases"):
            matches = cases.for_level(conn, check)
            quotas = refill.shortfall(check, matches, r["target"])
            got = draw.level(rng, check, matches, s["rung_code"], r["target"], seen, TENTH, quotas)
            n = len(got)
        else:
            n = bank.fill_native(conn, r["code"], r["difficulty"], r["target"], dry_run=True, rng=rng)[0][
                "accepted"
            ]
        out[(r["code"], r["difficulty"])] = (n, r["target"])
    return out


@needs_db
@pytest.mark.parametrize("seed", SEEDS)
def test_a_fresh_bank_fills_every_level_to_its_target_under_every_seed(conn, seed):
    built = _fresh_build(conn, seed)
    assert len(built) == len(inventory.coverage(conn))
    short = {
        f"{code} {level}": f"{n} of {target}" for (code, level), (n, target) in built.items() if n < target
    }
    assert not short, f"seed {seed}: {short}"


@needs_db
def test_a_level_that_cannot_reach_its_target_says_exactly_why(conn):
    """ADD.2D1D Hard asked for 10,000: each of its cases says how many it is short, what it can make at all (A14's 45,
    counted by hand) and how many of those the bank already holds (counted here from the rows)."""
    held = conn.execute(
        "select count(*) as n from item where status = 'active' and skill_set_code = 'ADD.2D1D' and difficulty = 'Hard'"
    ).fetchone()["n"]
    a14_held = conn.execute(
        "select count(distinct (spec->>'a', spec->>'b')) as n from item where fmt = 'column_grid' and spec->>'op' = '+'"
        " and (spec->>'a')::int between 10 and 99 and (spec->>'b')::int between 1 and 9"
        " and (spec->>'a')::int + (spec->>'b')::int >= 100"
    ).fetchone()["n"]
    a14_here = conn.execute(
        "select count(*) as n from item where status = 'active' and skill_set_code = 'ADD.2D1D' and difficulty = 'Hard'"
        " and 'A14' = any(case_codes)"
    ).fetchone()["n"]
    lines = refill.why_short(conn, "ADD.2D1D", "Hard", 10_000)
    assert lines[0] == f"ADD.2D1D Hard holds {held} of 10000:"
    share = -(-10_000 // 3)
    assert (
        f"  A14: {share - a14_here} short; it can make 45 questions and the bank holds {a14_held} of them"
        in lines
    )
    assert [line.split(":")[0].strip() for line in lines[1:]] == ["A14", "A15", "A16"]
    assert refill.why_short(conn, "ADD.2D1D", "Hard", held) == []
