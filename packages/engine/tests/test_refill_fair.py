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


SMALL = ("ADD.1D1D", "Easy")  # its whole region is its target, 108 questions


def _two(conn):
    return [
        r["id"]
        for r in conn.execute(
            "select id from item where status = 'active' and source = 'generated' and skill_set_code = %s"
            " and difficulty = %s order by item_key limit 2",
            SMALL,
        )
    ]


def _status(conn, ids):
    return [
        r["status"] for r in conn.execute("select status from item where id = any(%s) order by id", (ids,))
    ]


def test_a_question_retired_with_no_reason_comes_back_to_a_level_short_of_it(conn):
    """Found 2026-10-12 on a copy of live: ADD.1D1D Easy held 106 of 108 and SUB.2D1D Hard 67 of 72, short by exactly
    the questions made on 18 Sep and retired with no reason recorded; they held the very keys the level draws, so it
    could never be filled. A level short of its target takes back such a question when its rules hold it."""
    ids = _two(conn)
    conn.execute("update item set status = 'retired' where id = any(%s)", (ids,))
    held = conn.execute(
        "select count(*) as n from item where status = 'active' and skill_set_code = %s and difficulty = %s",
        SMALL,
    ).fetchone()["n"]
    refill.top_up(conn, *SMALL, held + 2)
    assert _status(conn, ids) == ["active", "active"]


def test_a_question_retired_for_a_reason_stays_retired(conn):
    """One a person or a rule retired, its reason recorded, is not brought back to fill a level."""
    ids = _two(conn)
    for i in ids:
        conn.execute(
            "insert into item_feedback (tenant_id, item_id, actor, verdict, note)"
            " select tenant_id, id, 'a person', 'retire', 'not a question for this level' from item where id = %s",
            (i,),
        )
    held = conn.execute(
        "select count(*) as n from item where status = 'active' and skill_set_code = %s and difficulty = %s",
        SMALL,
    ).fetchone()["n"]
    refill.top_up(conn, *SMALL, held + 2)
    assert _status(conn, ids) == ["retired", "retired"]
