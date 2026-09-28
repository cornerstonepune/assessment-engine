"""The space of column rules a new mistake is found in (`assess/learned_rules.py`, goals/s22-learned-mistakes.yaml).
Pure: numbers in, numbers out."""

from engine.assess import learned_rules as L
from engine.assess import misconceptions as M


def test_the_right_method_is_the_one_rule_that_is_no_mistake():
    right = L.RIGHT["+"]
    assert L.answer(right, 47, 38) == 85 and L.predict(right, 47, 38) is None
    assert L.predict(L.RIGHT["-"], 502, 167) is None


def test_the_rule_space_reproduces_named_mistakes_it_was_never_told_about():
    """Nimish: "systems that become smarter with every other iteration" — the space the system learns in holds the
    mistakes people named by hand, found from their answers alone: forgets to carry, writes the whole column sum,
    drops the last carry, smaller from larger, exchanges without reducing the lender."""
    cases = [
        ("+", 47, 38, "M_NOCARRY"),
        ("+", 47, 38, "M_CONCAT"),
        ("+", 76, 54, "M_DROP_CARRYOUT"),
        ("-", 52, 27, "M_SMALL_FROM_LARGE"),
        ("-", 52, 27, "M_NO_DECREMENT"),
    ]
    for op, a, b, code in cases:
        wrote = M.predict(op, a, b)[code]
        found = L.explaining(op, a, b, wrote)
        assert found, f"{code}: {a} {op} {b} written {wrote} is in no rule"
        assert all(L.predict(r, a, b) == wrote for r in found)


def test_every_rule_found_for_an_answer_reproduces_it_and_the_simplest_comes_first():
    wrote = 75  # 47 + 38, forgetting to carry
    found = L.explaining("+", 47, 38, wrote)
    assert [L.cost(r) for r in found] == sorted(L.cost(r) for r in found)
    assert L.words(found[0])  # every rule says what it does in the school's words
    assert L.explaining("+", 47, 38, 85) == [], "the right answer is no mistake"


def test_a_rule_has_one_id_and_comes_back_from_it():
    for r in L.rules("+")[:20] + L.rules("-")[:20]:
        assert L.from_id(L.rule_id(r)) == r


def test_every_named_mistake_that_is_a_way_of_working_lies_in_the_space():
    """The space is the right one when the mistakes people named by hand are all in it — every procedural one (a slip
    of a fact, ±1 or ±10, or the other operation is a slip, not a column rule): 20,267 of 20,267 on 6,000 sums when
    written (2026-09-28); here 400 sums, up to four digits."""
    import random

    rng, missed = random.Random(2), []
    for op in "+-":
        for _ in range(200):
            a, b = rng.randint(10, 9999), rng.randint(10, 999)
            if op == "-" and a < b:
                a, b = b, a
            for code, wrote in M.predict(op, a, b).items():
                if (
                    not code.startswith("M_FACT")
                    and code != "M_WRONG_OP"
                    and not L.explaining(op, a, b, wrote)
                ):
                    missed.append((code, a, op, b, wrote))
    assert missed == []
