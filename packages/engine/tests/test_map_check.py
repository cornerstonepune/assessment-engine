"""The code half of the curriculum mapping validator (goals/m1-05-mapping-agents.yaml, engine/w1_bank/map_check.py).

Pure code, no database and no model: every activity, skill and objective here is a placeholder.
"""

from engine.w1_bank.map_check import Gap, Known, decide, problems

KNOWN = Known(
    skills={"NUM.CNT.01": "NUM", "NUM.CNT.02": "NUM", "MOT.FMS.01": "MOT", "ART.CLR.01": "ART"},
    families={"Maths": frozenset({"NUM", "MOT"}), "Clay": frozenset({"ART", "MOT"})},
    objectives=frozenset({"LO-K2-0001-1", "LO-K2-0002-1"}),
)


def gap(**kw) -> Gap:
    base = dict(
        activity="ACT-K2-9001", strand="Maths", skills=frozenset(), objectives=frozenset(), levels=frozenset()
    )
    return Gap(**(base | kw))


def test_a_skill_code_the_registry_does_not_hold_is_named_as_invented_and_never_passes():
    out = problems("skill", {"skills": ["NUM.CNT.01", "NUM.CNT.99"]}, gap(), KNOWN)
    assert out == ["invented code NUM.CNT.99: not a skill of this band"]
    assert decide("skill", out, "agree", 0.99, min_confidence=0.8, sampled=False) == "rejected"


def test_a_skill_from_a_family_people_never_used_for_that_subject_is_refused():
    out = problems("skill", {"skills": ["ART.CLR.01"]}, gap(strand="Maths"), KNOWN)
    assert out == ["ART.CLR.01 is ART, a family people never linked to a Maths activity"]


def test_a_subject_people_never_mapped_has_no_family_that_fits():
    out = problems("skill", {"skills": ["NUM.CNT.01"]}, gap(strand="Yoga"), KNOWN)
    assert out == ["NUM.CNT.01 is NUM, a family people never linked to a Yoga activity"]


def test_a_duplicate_or_an_existing_link_is_a_problem():
    assert problems("skill", {"skills": ["NUM.CNT.01", "NUM.CNT.01"]}, gap(), KNOWN) == [
        "NUM.CNT.01 named twice"
    ]
    assert problems("skill", {"skills": ["NUM.CNT.01"]}, gap(skills=frozenset({"NUM.CNT.01"})), KNOWN) == [
        "NUM.CNT.01 is already linked"
    ]


def test_no_skill_at_all_is_an_answer_and_a_person_confirms_it():
    """Many activities are coverage only (art, clay, circle time): "none" may be right, but a person says so."""
    assert problems("skill", {"skills": []}, gap(), KNOWN) == []
    assert decide("skill", [], "agree", 0.99, min_confidence=0.8, sampled=False, none=True) == "needs_person"


def test_an_objective_is_an_existing_code_or_new_words_never_both_and_a_code_must_exist():
    assert problems("objective", {"objective_code": "LO-K2-0001-1"}, gap(), KNOWN) == []
    assert problems("objective", {"objective_text": "Counts objects to 10"}, gap(), KNOWN) == []
    assert problems("objective", {"objective_code": "LO-K2-7777-1"}, gap(), KNOWN) == [
        "invented code LO-K2-7777-1: not an objective of this band"
    ]
    assert problems("objective", {"objective_code": "LO-K2-0001-1", "objective_text": "x"}, gap(), KNOWN) == [
        "an existing objective or new words, not both"
    ]
    assert problems("objective", {}, gap(), KNOWN) == ["no objective proposed"]
    assert problems(
        "objective", {"objective_code": "LO-K2-0001-1"}, gap(objectives=frozenset({"LO-K2-0001-1"})), KNOWN
    ) == ["LO-K2-0001-1 is already linked"]


def test_level_words_only_where_the_sheet_gives_none():
    filled = gap(levels=frozenset({"level_1"}))
    assert (
        problems("levels", {"levels": {"level_0": "Watches", "level_2": "Does it with help"}}, filled, KNOWN)
        == []
    )
    assert problems("levels", {"levels": {"level_1": "Tries"}}, filled, KNOWN) == [
        "level_1 already has the sheet's words"
    ]
    assert problems("levels", {"levels": {"level_9": "x"}}, gap(), KNOWN) == ["level_9 is not a level"]
    assert problems("levels", {"levels": {"level_0": "  "}}, gap(), KNOWN) == ["level_0 is empty"]
    assert problems("levels", {"levels": {}}, gap(), KNOWN) == ["no level words proposed"]


def test_only_a_confident_agreed_unsampled_skill_from_a_known_code_passes_on_its_own():
    assert decide("skill", [], "agree", 0.9, min_confidence=0.8, sampled=False) == "auto_passed"
    assert decide("skill", [], "disagree", 0.9, min_confidence=0.8, sampled=False) == "needs_person"
    assert decide("skill", [], "agree", 0.7, min_confidence=0.8, sampled=False) == "needs_person"
    assert decide("skill", [], "agree", 0.9, min_confidence=0.8, sampled=True) == "needs_person"
    assert decide("lo_skill", [], "agree", 1.0, min_confidence=0.8, sampled=False) == "auto_passed"


def test_new_words_always_go_to_a_person_because_nothing_scores_them():
    assert decide("levels", [], "agree", 1.0, min_confidence=0.8, sampled=False) == "needs_person"
    assert (
        decide("objective", [], "agree", 1.0, min_confidence=0.8, sampled=False, new_words=True)
        == "needs_person"
    )
    assert decide("objective", [], "agree", 1.0, min_confidence=0.8, sampled=False) == "auto_passed"


def test_a_kind_whose_audit_failed_never_passes_on_its_own():
    assert (
        decide("skill", [], "agree", 1.0, min_confidence=0.8, sampled=False, kind_stopped=True)
        == "needs_person"
    )
