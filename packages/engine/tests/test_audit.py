"""`engine audit`'s invariants that are pure enough to hold without a database."""

from collections import Counter

from engine.checks.audit import lopsided

RULE = {"share": 0.75, "min_questions": 40}


def test_a_level_whose_right_answers_all_sit_in_one_place_is_named():
    places = {("ESTIMATE.HUNDRED", "Hard", "choose_estimate", "pick"): Counter({1: 54})}
    assert lopsided(places, RULE) == [
        "ESTIMATE.HUNDRED Hard choose_estimate (pick): 54 of 54 right answers are option 2"
    ]


def test_answers_spread_fairly_or_too_few_to_judge_are_not():
    places = {
        ("EQUALITY.INVERSE", "Medium", "equation", "tf"): Counter({0: 28, 1: 26}),
        ("ESTIMATE.HUNDRED", "Easy", "possible_answer", "could"): Counter({1: 30, 0: 24}),
        ("MISSING.DIGIT", "Easy", "equation", "s1"): Counter({0: 12}),
    }
    assert lopsided(places, RULE) == []
