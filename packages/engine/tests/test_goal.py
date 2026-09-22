"""The functional goal, run as a test: does the engine do its job on every defined scenario?

`goals/w1-build-the-bank.yaml` states what W1 is for in one sentence and lists the scenarios that
prove it. This test runs them, and `engine goal w1-build-the-bank` runs the same thing plus the
whole-repo criteria. The bar is 100%: a scenario that produces 19 of 20 questions has not met it.

`test_every_invariant_holds` is the other half — the sweep that answers "what else is wrong that
nothing looks at?" rather than waiting for a test to trip over it.
"""

import os

import pytest

from engine import audit, db, goal, scenarios

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

GOAL = "w1-build-the-bank"


@pytest.fixture(scope="module")
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def test_every_invariant_holds(conn):
    """Every invariant code can keep. The ones a person closes (an approval) are counted by `engine audit`
    and by the goal that names it, not here."""
    broken = {name: v for name, v in audit.run(conn) if v and name not in audit.AWAITS_A_PERSON}
    assert not broken, f"invariants violated: { {k: v[:3] for k, v in broken.items()} }"


def test_an_invariant_that_waits_for_a_person_says_so_in_words(conn):
    waiting = {name: v for name, v in audit.run(conn) if v and name in audit.AWAITS_A_PERSON}
    assert all(isinstance(line, str) and line for v in waiting.values() for line in v)
    assert audit.AWAITS_A_PERSON <= {name for name, _ in audit.INVARIANTS}


def test_the_goals_scenarios_are_the_ones_we_agreed(conn):
    """A goal nobody can lose: the scenario list is part of the repository, not a session's memory."""
    spec = goal.load(GOAL)
    assert spec["goal"].strip()
    names = [s["name"] for s in goal.scenarios_of(spec)]
    assert len(names) >= 8 and len(set(names)) == len(names)
    for s in goal.scenarios_of(spec):
        assert {"skill_set", "difficulty"} <= s.keys()


def test_every_scenario_meets_the_bar_completely(conn):
    results = scenarios.run(goal.scenarios_of(goal.load(GOAL)), conn)
    short = {sc["name"]: failures for sc, _m, failures in results if failures}
    assert not short, f"{len(short)} of {len(results)} scenarios short of the bar: {short}"
