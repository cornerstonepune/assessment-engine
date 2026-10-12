"""A group of questions answered by ticking, its right answers in one place because a rule since corrected made them,
is drawn again by the refill (goals/l2-live-audit-clean.yaml).

Measured 2026-10-12 on a copy of live (the rehearsal, run 38223287194): REASON.EXPLAIN's 216 questions a level were all
answered "yes" (Easy, Medium) or all "no" (Hard, Advance). Its levels were rewritten on 2026-09-29 to draw true and
false at random (DECISIONS-LOG), and live holds the new levels, but every question made before stayed: each is a fair
question on its own, so no rule retired it, and approving the levels retires none either. The same for ESTIMATE.HUNDRED
Advance's "is it close?" and REASON.FIND_MISTAKE Hard's "where". A level whose own design fixes the answer is not
redrawn: what it draws is no fairer, and that waits for a person (`engine audit`).
"""

import json
import os

import pytest

from engine.core import db
from engine.w1_bank import inventory, refill

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
LEVEL = ("REASON.EXPLAIN", "Easy")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _all_yes(conn):
    """Every stored question of the level keyed "yes", as REASON.EXPLAIN Easy's were before 2026-09-29."""
    conn.execute(
        "update item set responses = (select jsonb_agg(case when x ->> 'kind' = 'tick'"
        " then jsonb_set(x, '{answer}', x -> 'options' -> 0) else x end order by n)"
        " from jsonb_array_elements(responses) with ordinality t(x, n))"
        " where status = 'active' and source = 'generated' and skill_set_code = %s and difficulty = %s",
        LEVEL,
    )
    return conn.execute(
        "select count(*) as n from item where status = 'active' and skill_set_code = %s and difficulty = %s",
        LEVEL,
    ).fetchone()["n"]


def _unfair(conn):
    return [key[:2] for key, *_ in inventory.unfair(inventory.tick_places(conn), refill.fairness_rule(conn))]


def test_a_group_made_by_a_rule_since_corrected_is_drawn_again(conn):
    held = _all_yes(conn)
    assert held >= 40 and LEVEL in _unfair(conn)
    assert refill.redraw_unfair(conn)[LEVEL] == held
    assert refill.top_up(conn, *LEVEL, held) > 0
    assert LEVEL not in _unfair(conn)


def test_a_level_whose_own_design_fixes_the_answer_waits_for_a_person(conn):
    level = conn.execute("select difficulty from skill_set where code = %s", (LEVEL[0],)).fetchone()[
        "difficulty"
    ]
    fixed = dict(level[LEVEL[1]], check=dict(level[LEVEL[1]]["check"], claim_is_true=True))
    conn.execute(
        "update skill_set set difficulty = %s where code = %s",
        (json.dumps(dict(level, Easy=fixed)), LEVEL[0]),
    )
    _all_yes(conn)
    assert refill.redraw_unfair(conn)[LEVEL] == 0
    assert LEVEL in _unfair(conn)


def test_a_kind_the_level_asks_now_and_then_is_drawn_until_it_can_be_judged(conn):
    """REASON.FIND_MISTAKE Hard asks "where the mistake is" on about one question in four. On a copy of live its 54
    were 45 in one column, and one draw of 120 questions held too few "where"s to judge the level by, so the group was
    left (the rehearsal, 2026-10-12): the level is drawn until it has enough of them."""
    places = refill._places_now(conn, "REASON.FIND_MISTAKE", "Hard", "find_mistake", "where", 40)
    assert sum(places.values()) >= 40
    assert not inventory.unfair({"now": places}, refill.fairness_rule(conn))
