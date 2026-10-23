"""Every story's numbers fit its story (goals/md4d2a-story-ranges.yaml).

Assumption A9 (docs/design/multiplication-division-taxonomy.md): "Each story template carries the range its numbers may
take, so no box holds 933 pencils." Measured 2026-10-11: 74 of the 76 older templates said no range and took their
sizes from the level alone, and the bank held "has 9685 marbles", 93 × 96 combinations of stickers and backgrounds,
and rows of 98 chairs. Every check reads the question as drawn, finding its template by its words."""

import json
import os
import pathlib
import random
import re

import pytest

from engine.assess import draw, verify, words
from engine.core import db
from engine.w1_bank import bank, cases
from tests.rows import tenant

ROOT = pathlib.Path(__file__).resolve().parents[3]
SETS = {s["code"]: s for s in json.loads((ROOT / "supabase/seed/skill_sets.json").read_text())["skill_sets"]}
MATCHES = {
    c["code"]: c["match"]
    for c in json.loads((ROOT / "supabase/seed/taxonomy_cases.json").read_text())["taxonomy_cases"]
}
# the numbers a story's words hold; a story read from a table holds its two in the table
NUMBER = re.compile(r"\{([a-d])\}")


def _named(t):
    return set(NUMBER.findall(t["text"])) | ({"a", "b"} if t.get("table") else set())


def _bounds(v):
    return (v[0], v[-1]) if isinstance(v, list) else (v, v)


def test_every_story_template_says_the_range_of_each_number_it_holds():
    """Each story says the range each number in it may take: a story that sets its own numbers (`numbers`), or any
    other, the range its level's sizes are held inside (`range`). A question of numbers alone (`bare_sum`, "How many
    5s make 40?") has no story for its numbers to fit."""
    missing, wrong = [], []
    for i, t in enumerate(words.templates()):
        if t["fmt"] == "bare_sum":
            continue
        said = t.get("numbers") or t.get("range") or {}
        missing += [f"{i} {t['structure']} {k}: {t['text'][:50]}" for k in sorted(_named(t)) if k not in said]
        wrong += [f"{i} {k}: {v}" for k, v in said.items() if not 0 < _bounds(v)[0] <= _bounds(v)[1]]
    assert missing == []
    assert wrong == []


@pytest.mark.parametrize("code", sorted(SETS))
def test_every_story_a_level_draws_holds_numbers_its_template_allows(code):
    """Every story every level of this skill draws holds each of its numbers inside the range its template says."""
    outside = []
    for level, d in SETS[code]["difficulty"].items():
        check = d.get("check") or {}
        if not check.get("cases"):
            continue
        matches = cases.on_level(check, MATCHES)
        for seed in range(3):
            for _, it in draw.level(random.Random(seed), check, matches, SETS[code]["rung_code"], 24):
                t = words.template_of(it.stem)
                said = (t or {}).get("numbers") or (t or {}).get("range") or {}
                for k, v in said.items():
                    lo, hi = _bounds(v)
                    if k in it.spec and isinstance(it.spec[k], int) and not lo <= it.spec[k] <= hi:
                        outside.append(f"{level}: {k}={it.spec[k]} outside {lo}–{hi}: {it.stem}")
    assert outside == []


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def test_a_story_in_the_bank_outside_its_range_is_retired(conn):
    """A story drawn before its template said its range, still in the bank, is named for retiring as a question outside
    its level is (`refill.retire_outside`), so `engine bank refill` replaces it and no paper prints it again."""
    stem = "Each box has 933 pencils. There are 4 boxes. How many pencils are there altogether?"
    assert words.template_of(stem)["structure"] == "EQUAL_GROUPS"
    cand = {
        "format": "word_1step",
        "op": "×",
        "a": 933,
        "b": 4,
        "answer": 3732,
        "stem": stem,
        "misconceptions": [],
    }
    # it names its skill set's registry skills, as `bank.fill` gives every question it makes (C1)
    skills = conn.execute("select registry_codes from skill where code = 'MUL.3D1D'").fetchone()[
        "registry_codes"
    ]
    it = verify.to_item(cand, SETS["MUL.3D1D"]["rung_code"], skills=list(skills))
    assert bank._insert(conn, tenant(conn), it, "MUL.3D1D", "Easy")
    named = {r["item_key"]: r["why"] for r in cases.outside_their_level(conn)}
    assert it.item_id in named
    assert "a story holds a = 933, outside 2–24" in named[it.item_id]
