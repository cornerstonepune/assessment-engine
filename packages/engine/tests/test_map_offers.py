"""A skill passes on its own only if the proposer was shown it in an example; the rest are offered to a person
(goals/m1-12c-skill-offers.yaml, task M1-12c).

The dev run's replay (2026-11-04): a skill the proposer was shown in an example was a skill people also linked in 87 of
110, one it was not shown in 55 of 84, and the model's own confidence told them apart badly. The orchestrator's reading A:
the skills that were shown stay one proposal; each skill that was not is offered on its own, to be added or not by a
person. The bars are rows (`map.skill_min_confidence`, `map.require_examples`, `map.use_checker`), not numbers here."""

import pytest

from engine.w1_bank import map_offers as offers
from engine.w1_bank.map_agents import PROPOSE, VALIDATE, Proposal, Rules, propose
from engine.w1_bank.map_check import decide
from tests.test_map_probe import CODE, band

SHOWN = frozenset({"NUM.CNT.01"})


def rules(**kw):
    base = dict(
        min_confidence=0.8,
        audit_share=0.0,
        examples=3,
        skill_confidence=0.7,
        from_examples=True,
        use_checker=False,
    )
    return Rules(**(base | kw))


def skill(skills, confidence=0.9, status="auto_passed", kind="skill"):
    return Proposal(kind, CODE, {"skills": skills}, confidence, PROPOSE, "", [], "", status, "r")


def test_skills_all_shown_pass_as_they_were_decided():
    p = skill(["NUM.CNT.01"])
    assert offers.split(p, SHOWN, rules()) == [p]


def test_a_skill_not_shown_is_offered_on_its_own_and_the_shown_ones_stay_one_proposal():
    main, offer = offers.split(skill(["NUM.CNT.01", "NUM.CNT.02"]), SHOWN, rules())
    assert (main.kind, main.proposal, main.status) == ("skill", {"skills": ["NUM.CNT.01"]}, "auto_passed")
    assert (offer.kind, offer.status) == ("skill_offer", "needs_person")
    assert offer.proposal == {"skills": ["NUM.CNT.02"], "with": ["NUM.CNT.01"]}
    assert "nearest examples" in offer.reason and offer.confidence == 0.9


def test_each_skill_not_shown_is_its_own_offer_in_the_order_proposed():
    got = offers.split(skill(["NUM.CNT.03", "NUM.CNT.01", "NUM.CNT.02"]), SHOWN, rules())
    assert [p.proposal["skills"] for p in got] == [["NUM.CNT.01"], ["NUM.CNT.03"], ["NUM.CNT.02"]]


def test_with_no_skill_shown_there_is_no_main_proposal_only_the_offers():
    got = offers.split(skill(["NUM.CNT.02"]), SHOWN, rules())
    assert [(p.kind, p.proposal["skills"]) for p in got] == [("skill_offer", ["NUM.CNT.02"])]
    assert got[0].proposal["with"] == []


@pytest.mark.parametrize(
    "p, r",
    [
        (skill(["NUM.CNT.02"], status="rejected"), rules()),
        (skill(["NUM.CNT.02"]), rules(from_examples=False)),
        (skill(["NUM.CNT.02"], kind="lo_skill"), rules()),
        (skill([]), rules()),
    ],
)
def test_a_rejected_proposal_a_rule_that_is_off_another_kind_or_no_skill_is_left_alone(p, r):
    assert offers.split(p, SHOWN, r) == [p]


def test_the_confidence_bar_for_a_skill_is_its_own_row_when_the_rule_is_on():
    assert rules().bar("skill") == 0.7 and rules().bar("objective") == 0.8
    assert rules(from_examples=False).bar("skill") == 0.8
    assert rules(skill_confidence=None).bar("skill") == 0.8


def test_the_validator_decides_only_while_it_is_on():
    kw = dict(min_confidence=0.7, sampled=False)
    assert decide("skill", [], "", 0.9, checker=False, **kw) == "auto_passed"
    assert decide("skill", [], "", 0.9, checker=True, **kw) == "needs_person"
    assert decide("skill", [], "agree", 0.9, checker=True, **kw) == "auto_passed"
    assert decide("skill", [], "", 0.6, checker=False, **kw) == "needs_person"


def run(skills, confidence, **kw):
    b = band()
    b.known.skills["NUM.CNT.02"] = "NUM"
    asked = []

    def ask(purpose, about, variables):
        asked.append(purpose)
        return {
            "skills": skills,
            "objective_code": "",
            "objective_text": "",
            "levels": {},
            "confidence": confidence,
        }

    made = [p for p in propose(b, [CODE], ask, rules(**kw)) if p.kind.startswith("skill")]
    return made, asked


def test_a_run_offers_what_the_examples_did_not_show_and_never_asks_the_checker_when_it_is_off():
    made, asked = run(["NUM.CNT.01", "NUM.CNT.02"], 0.75)
    assert VALIDATE not in asked
    assert [(p.kind, p.proposal["skills"], p.status) for p in made] == [
        ("skill", ["NUM.CNT.01"], "auto_passed"),
        ("skill_offer", ["NUM.CNT.02"], "needs_person"),
    ], "0.75 clears the skill bar of 0.7, though not the general bar of 0.8"


def test_a_confidence_under_the_skill_bar_sends_even_a_shown_skill_to_a_person():
    made, _ = run(["NUM.CNT.01"], 0.65)
    assert [(p.kind, p.status) for p in made] == [("skill", "needs_person")]


def test_with_the_rule_off_a_run_is_as_it_was_one_proposal_decided_by_the_checker():
    made, asked = run(["NUM.CNT.01", "NUM.CNT.02"], 0.9, from_examples=False, use_checker=True)
    assert VALIDATE in asked and [p.kind for p in made] == ["skill"]
