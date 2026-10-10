"""A wrong answer no named mistake explains gets Jev's shortlist (`w1_bank/mistake_guess.py`, goals/j1-jev-mistakes.yaml).
Code names every mistake it can reproduce exactly; Jev is asked only about the rest, and only ever proposes."""

import os

import pytest

from engine.adapters import jev
from engine.core import db
from engine.w1_bank import mistake_guess


@pytest.fixture
def conn():
    """Jev is shown each mistake by its row's name (`mistake_guess.options`), so asking it reads the rows."""
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def test_the_options_are_the_operations_named_mistakes_and_none():
    options = mistake_guess.codes("-")
    assert "M_SMALL_FROM_LARGE" in options and "M_NO_DECREMENT" in options and mistake_guess.NONE in options
    assert not any(c.startswith("M_FACT") for c in options), "an off-by-one is a slip, not a way of thinking"
    assert "M_NOCARRY" not in options, "an addition mistake is not offered for a subtraction"


def test_what_jev_is_shown_is_the_sum_the_right_answer_and_the_childs_never_a_name():
    state = mistake_guess.state({"a": 81, "b": 46, "op": "-"}, "45")
    assert state == {"question": "81 − 46 = ?", "right_answer": 35, "child_answer": "45"}


def test_a_wrong_answer_code_explains_is_never_sent_to_jev():
    asked = []

    def ask(*a):
        asked.append(a)
        return {"ranked": [("M_NO_DECREMENT", 0.9)], "choice": "M_NO_DECREMENT"}

    assert (
        mistake_guess.shortlist(None, {"a": 63, "b": 28, "op": "-"}, "45", ask=ask) is None
    )  # 8−3, 6−2: code's
    assert asked == []


def test_an_unexplained_wrong_answer_gets_three_named_mistakes_or_none_with_their_chances(conn):
    def ask(conn, purpose, state, options):
        assert purpose == mistake_guess.PURPOSE and state["child_answer"] == "395"
        return {
            "ranked": [
                ("NONE", 0.4),
                ("M_EXCHANGE_WRONG_PLACE", 0.3),
                ("M_ZERO_LENDER", 0.2),
                ("M_WRONG_OP", 0.1),
            ]
        }

    # 445 is not asked about: it is exchanging without reducing the tens (M_NO_DECREMENT), which code reproduces
    assert mistake_guess.shortlist(conn, {"a": 502, "b": 167, "op": "-"}, "445", ask=ask) is None
    got = mistake_guess.shortlist(conn, {"a": 502, "b": 167, "op": "-"}, "395", ask=ask)
    assert got == [("NONE", 0.4), ("M_EXCHANGE_WRONG_PLACE", 0.3), ("M_ZERO_LENDER", 0.2)]


def test_a_right_answer_or_a_question_that_is_not_one_sum_is_not_asked_about():
    never = lambda *a: (_ for _ in ()).throw(AssertionError("asked"))  # noqa: E731
    assert mistake_guess.shortlist(None, {"a": 81, "b": 46, "op": "-"}, "35", ask=never) is None
    assert mistake_guess.shortlist(None, {"kind": "word"}, "12", ask=never) is None
    assert mistake_guess.shortlist(None, {"a": 81, "b": 46, "op": "-"}, "", ask=never) is None


def test_the_gold_is_built_from_code_each_case_one_named_mistake_or_a_slip_none_can_make():
    cases = mistake_guess.gold(seed=3, named=40, slips=12)
    assert len(cases) == 52 and sum(c["want"] == mistake_guess.NONE for c in cases) == 12
    for c in cases:
        from engine.assess import misconceptions as M

        made = {code for code, v in M.predict(c["op"], c["a"], c["b"]).items() if v == c["wrote"]}
        assert made == ({c["want"]} if c["want"] != mistake_guess.NONE else set())


def test_an_eval_jev_cannot_answer_says_so_and_scores_nothing(conn):
    """Nimish, 2026-09-29: "The key is already there, but tell me where you want me to put it." Without the key every
    case failed with a traceback; now the eval counts what Jev did not answer and says why, and the command fails."""

    def down(*a):
        raise jev.JevError("no TYPESAFE_API_KEY in the engine's environment: Jev cannot be asked")

    got = mistake_guess.evaluate(conn, mistake_guess.gold(seed=3, named=4, slips=2), ask=down)
    assert (got["cases"], got["unanswered"], got["listed"], got["first"]) == (6, 6, 0, 0)
    assert "TYPESAFE_API_KEY" in got["error"]
