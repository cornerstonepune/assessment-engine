"""`engine past` lists which children's states changed, and why (goals/gr1-state-from-recent-evidence.yaml).

Nimish, 2026-11-03: "Rehearse on a copy of live. engine past must show which children's states change, and why." The
rehearsal keeps every child's states before the migration and lists, after the graph is rebuilt, each that moved: the
child's id (never a name), the skill, from what to what, and the numbers the rule decided it on. Rolls back.
"""

import pytest
import yaml

from engine.checks import past, scenarios_graph
from engine.core import db

GOAL = db.REPO_ROOT / "goals" / "gr1-state-from-recent-evidence.yaml"
CLEARED = next(
    sc
    for sc in yaml.safe_load(GOAL.read_text())["scenarios"]
    if sc["name"] == "Two September mistakes then twenty right is not a repeating mistake"
)


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def test_past_lists_each_state_that_changed_and_why(conn):
    child, skill = scenarios_graph.ledger(conn, CLEARED)
    conn.execute("select rebuild_child_skill_state(%s)", (child,))
    # the graph as the old rule left it: the two September mistakes, repeating for ever
    conn.execute(
        "update child_skill_state set state = 'patterned_error', repeating_misconception = 'M_ALIGN_LEFT'"
        " where child_id = %s",
        (child,),
    )
    before = past.snapshot(conn)
    conn.execute("select rebuild_child_skill_state(%s)", (child,))
    c = past.changes(conn, before)
    mine = [m for m in c["states"] if m["child"] == str(child)]
    assert [(m["skill"], m["rung"], m["from"], m["to"]) for m in mine] == [
        (skill["registry"], skill["rung_code"], "patterned_error", "secure_to_recheck")
    ]
    assert (
        mine[0]["why"]
        == "at Medium: 10 of 10 right (1.00) on 2 day(s), latest day 1.00, not re-checked, repeating none"
    )
    lines = past.report(c)
    assert lines[0].startswith("children with a state: ") and "whose state changed: 1;" in lines[0]
    assert "  patterned_error -> secure_to_recheck: 1" in lines
    assert any(str(child) in line and "(was repeating M_ALIGN_LEFT)" in line for line in lines)
    assert not any("Goal" in line for line in lines), "rule 6: the child's id, never their name"
    # nothing moved: nothing listed
    assert past.changes(conn, past.snapshot(conn)) == {"children": c["children"], "states": [], "levels": []}
