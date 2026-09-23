"""Topics (engine/core/topics.py): the tree's level between a subject and its skills. Pure: a fake seed and a
connection that records what it is asked."""

import json
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
    assert [(p[1], p[4]) for p in inserted] == [("A", 0), ("B", 1)]
    placed = {p[2]: p[0] for s, p in conn.calls if s.startswith("update skill_set")}
    assert placed == {"X": "A", "Y": "B"}
