"""Judging an answer without working it out (taxonomy §8–§9).

"Which is closest?" was always answered by the middle option, so a child who ticked the middle one every
time scored full marks, and a sum ending in 50 sat exactly between two options, so it had two right
answers. These hold both shut.
"""

import random
from collections import Counter

from engine.assess import reasoning as RS
from engine.assess.rounding import half_up


def _closest(n, seed=11):
    rng, made = random.Random(seed), []
    while len(made) < n:
        try:
            made.append(RS.choose_estimate(rng, "R18", "Conceptual", op=rng.choice("+-")))
        except RuntimeError:
            continue
    return made


def test_the_right_option_is_the_one_nearest_the_exact_answer_and_no_other_is_as_near():
    for item in _closest(300):
        s, pick = item.spec, item.responses[0]
        exact = s["a"] + s["b"] if s["op"] == "+" else s["a"] - s["b"]
        distances = sorted(abs(o - exact) for o in s["options"])
        assert distances[0] < distances[1], (s, "two options are equally close: the question has two answers")
        assert int(pick.answer) == half_up(exact, 100), s
        assert pick.options == [str(o) for o in s["options"]]


def test_the_right_option_is_first_middle_and_last_in_turn_not_always_the_middle():
    places = Counter(item.spec["options"].index(int(item.responses[0].answer)) for item in _closest(300))
    assert set(places) == {0, 1, 2}, places
    assert max(places.values()) / 300 < 0.45, places
