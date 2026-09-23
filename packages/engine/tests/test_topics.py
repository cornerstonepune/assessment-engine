"""Topics (engine/core/topics.py): the tree's level between a subject and its skills. Pure: a fake seed and a
connection that records what it is asked."""

import json
import os
from pathlib import Path

import pytest

from engine.core import topics

SEED = Path(__file__).resolve().parents[3] / "supabase" / "seed"


class Recorder:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))


def _seed(tops, sets):
    return lambda name, key: {"topics.json": tops, "skill_sets.json": [{"code": c} for c in sets]}[name]


def test_every_skill_in_the_seed_sits_in_exactly_one_topic():
    tops = json.loads((SEED / "topics.json").read_text())["topics"]
    sets = [s["code"] for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]]
    placed = [c for t in tops for c in t["skill_sets"]]
    assert sorted(placed) == sorted(sets), "every skill set once, and no topic names one that does not exist"


def test_a_skill_in_no_topic_or_in_two_is_refused():
    one = [{"code": "A", "subject": "NUM", "name": "A", "skill_sets": ["X"]}]
    with pytest.raises(ValueError, match="in no topic: Y"):
        topics.load(Recorder(), "t", _seed(one, ["X", "Y"]))
    two = one + [{"code": "B", "subject": "NUM", "name": "B", "skill_sets": ["X"]}]
    with pytest.raises(ValueError, match="X is in two topics"):
        topics.load(Recorder(), "t", _seed(two, ["X"]))


def test_each_skill_is_placed_under_its_topic_in_the_topics_order():
    tops = [
        {"code": "A", "subject": "NUM", "name": "First", "skill_sets": ["X"]},
        {"code": "B", "subject": "NUM", "name": "Second", "skill_sets": ["Y"]},
    ]
    conn = Recorder()
    topics.load(conn, "t", _seed(tops, ["X", "Y"]))
    inserted = [p for s, p in conn.calls if s.startswith("insert into topic")]
    assert [(p[1], p[4], p[5]) for p in inserted] == [("A", 0, False), ("B", 1, False)]
    placed = {p[2]: p[0] for s, p in conn.calls if s.startswith("update skill_set")}
    assert placed == {"X": "A", "Y": "B"}


def test_only_addition_and_subtraction_is_taught_today():
    """Nimish, 2026-09-23: "I'm surprised we haven't even started teaching multiplication"."""
    tops = json.loads((SEED / "topics.json").read_text())["topics"]
    assert [t["name"] for t in tops if t.get("taught")] == ["Addition & subtraction"]


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
def test_every_taxonomy_case_sits_in_a_taught_skill_and_nothing_else_is_taught():
    """The taxonomy is what the school gave: every case in it is on the site, and a skill that holds none of its
    cases is not — so hiding what is not taught never hides a piece of the taxonomy."""
    from engine.core import db

    with db.connect() as conn:
        rows = conn.execute(
            "select s.code, t.taught, exists (select 1 from item i where i.skill_set_code = s.code"
            "   and i.status = 'active' and cardinality(i.case_codes) > 0) as holds_cases"
            " from skill_set s join topic t on t.tenant_id = s.tenant_id and t.code = s.topic_code"
        ).fetchall()
    assert rows
    assert {r["code"] for r in rows if r["holds_cases"]} == {r["code"] for r in rows if r["taught"]}
