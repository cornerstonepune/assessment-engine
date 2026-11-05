"""Skills the examples did not show are offered to a person, who adds them or not (goals/m1-12c-skill-offers.yaml)."""

import os
import uuid

import pytest

from engine.w1_bank import map_ledger
from engine.w1_bank import skill_offers as so
from engine.w1_bank.map_agents import Rules, propose, read_band
from tests import test_map_ledger as base
from tests.test_map_ledger import BAND, _band, _staff

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
conn = base.conn
CODE = "ACT-KX-0101"


def proposals(conn, t, skills=("NUM.CNT.01", "NUM.CNT.02"), confidence=0.9, asked=frozenset()):
    """Run the proposer on the gap activity with one example shown (the nearest)."""
    band = read_band(conn, t, BAND, frozenset({CODE}))
    rules = Rules(0.8, 0.0, 1, skill_confidence=0.7, from_examples=True, use_checker=False)

    def ask(purpose, about, variables):
        return {
            "skills": list(skills),
            "objective_code": "",
            "objective_text": "",
            "levels": {},
            "confidence": confidence,
        }

    return [p for p in propose(band, [CODE], ask, rules, asked) if p.kind.startswith("skill")]


def made(conn, skills=("NUM.CNT.01", "NUM.CNT.02"), confidence=0.9):
    """Record what the proposer proposes for the gap activity."""
    t = _band(conn)
    staff = _staff(conn, t)
    map_ledger.record(conn, t, proposals(conn, t, skills, confidence), staff)
    return t, staff


def test_the_offers_waiting_name_the_activity_the_skill_and_what_was_proposed_with_it(conn):
    t, _ = made(conn)
    (offer,) = [w for w in so.waiting(conn, t) if w["kind"] == "offer"]
    assert offer["activity"] == {"code": CODE, "name": "Count shells in a basket", "section": "Maths"}
    assert [s["code"] for s in offer["skills"]] == ["NUM.CNT.02"]
    assert [s["code"] for s in offer["also"]] == ["NUM.CNT.01"]
    assert offer["confidence"] == 0.9 and "nearest examples" in offer["reason"]
    assert uuid.UUID(offer["id"])


def test_a_proposal_that_passed_on_its_own_is_not_waiting(conn):
    t, _ = made(conn)
    assert [w["kind"] for w in so.waiting(conn, t)] == ["offer"], "the shown skill auto-passed at 0.9"


def test_a_shown_skill_under_the_confidence_bar_waits_too_as_a_proposal_not_an_offer(conn):
    t, _ = made(conn, skills=("NUM.CNT.01",), confidence=0.6)
    assert [(w["kind"], [s["code"] for s in w["skills"]]) for w in so.waiting(conn, t)] == [
        ("skill", ["NUM.CNT.01"])
    ]


def test_saying_yes_adds_that_one_skill_as_the_machines_link_naming_the_offer_and_nothing_else(conn):
    t, staff = made(conn)
    (offer,) = so.waiting(conn, t)
    so.answer(conn, t, staff, offer["id"], True, "yes, shells are counted")
    rows = conn.execute(
        "select skill_code, source, proposal_id::text as pid from activity_skill where activity_code = %s",
        (CODE,),
    ).fetchall()
    assert [(r["skill_code"], r["source"], r["pid"]) for r in rows] == [
        ("NUM.CNT.02", "machine", offer["id"])
    ]
    assert so.waiting(conn, t) == []


def test_saying_no_adds_nothing_and_the_offer_is_closed_with_the_persons_id(conn):
    t, staff = made(conn)
    (offer,) = so.waiting(conn, t)
    so.answer(conn, t, staff, offer["id"], False, "not this activity")
    assert (
        conn.execute("select count(*) as n from activity_skill where activity_code = %s", (CODE,)).fetchone()[
            "n"
        ]
        == 0
    )
    row = conn.execute(
        "select status, staff_id from curriculum_proposal where about = %s::uuid", (offer["id"],)
    ).fetchone()
    assert (row["status"], row["staff_id"]) == ("rejected", staff)
    assert so.waiting(conn, t) == []


def test_only_what_is_waiting_can_be_answered_and_a_second_answer_is_refused(conn):
    t, staff = made(conn)
    (offer,) = so.waiting(conn, t)
    with pytest.raises(ValueError, match="not waiting"):
        so.answer(conn, t, staff, str(uuid.uuid4()), True, "")
    so.answer(conn, t, staff, offer["id"], True, "")
    with pytest.raises(ValueError, match="not waiting"):
        so.answer(conn, t, staff, offer["id"], True, "")


def test_saying_yes_to_an_offer_does_not_apply_anything_else_that_is_waiting_to_be_applied(conn):
    t, staff = made(conn)
    (offer,) = so.waiting(conn, t)
    so.answer(conn, t, staff, offer["id"], True, "")
    assert (
        conn.execute(
            "select count(*) as n from activity_skill where skill_code = 'NUM.CNT.01' and activity_code = %s",
            (CODE,),
        ).fetchone()["n"]
        == 0
    ), "the shown skill passed on its own but is applied by `engine curriculum apply`, not by this answer"


def test_a_rerun_never_offers_a_skill_that_is_still_waiting_or_was_refused(conn):
    t, staff = made(conn, confidence=0.6)  # the shown skill under the bar waits, and so does the offer
    assert [p.kind for p in proposals(conn, t, confidence=0.6, asked=map_ledger.asked(conn, t))] == [
        "skill"
    ], "a waiting offer is not offered twice (the shown skill is the activity's own proposal, still waiting)"
    for w in so.waiting(conn, t):
        so.answer(conn, t, staff, w["id"], False, "no")
    asked = map_ledger.asked(conn, t)
    assert (CODE, "NUM.CNT.02") in asked and (CODE, "NUM.CNT.01") in asked, "both were refused"
    assert proposals(conn, t, confidence=0.6, asked=asked) == [], "a no is never asked again"


def test_a_skill_the_person_added_is_not_offered_again_either(conn):
    t, staff = made(conn)
    (offer,) = so.waiting(conn, t)
    so.answer(conn, t, staff, offer["id"], True, "")
    again = proposals(conn, t, asked=map_ledger.asked(conn, t))
    assert [p.proposal["skills"] for p in again] == [["NUM.CNT.01"]], (
        "only the skill the examples showed comes back"
    )


def test_the_asked_pairs_are_what_was_offered_whatever_became_of_it_and_what_a_person_refused(conn):
    t, staff = made(conn)
    assert map_ledger.asked(conn, t) == {(CODE, "NUM.CNT.02")}, (
        "an offer waiting is asked; a passed proposal is not"
    )
