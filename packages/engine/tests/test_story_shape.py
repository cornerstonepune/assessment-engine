"""A story in anyone's words → its shape, case, place and one-step answer (goals/j3-story-shape.yaml,
`w1_bank/story_shape.py`). Jev is stood in for; the database is the local copy, rolled back."""

import os

import pytest

from engine.adapters import jev
from engine.w1_bank import story_shape as S

DB = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    from engine.core import db

    with db.connect() as c:
        yield c
        c.rollback()


def _saying(best, p=0.9):
    asked = []

    def ask(conn, purpose, state, options):
        asked.append((purpose, state, set(options)))
        rest = [o for o in options if o != best]
        return {"choice": best, "ranked": [(best, p)] + [(o, (1 - p) / len(rest)) for o in rest]}

    return ask, asked


def test_every_one_step_story_in_the_gold_has_the_answer_its_shapes_operation_gives():
    """The gold checks itself before any model is held to it: a story filed under a shape of the wrong operation, or
    with a number code cannot read, fails here."""
    for g in S.gold():
        if "answer" in g:
            assert S.answer(g["shape"], g["text"]) == g["answer"], g["text"]
        else:
            assert S.one_step_op(g["shape"]) is None, (
                f"{g['shape']} is one step and needs its answer: {g['text']}"
            )


def test_numbers_are_read_from_the_words_and_a_class_name_is_not_one():
    assert S.numbers("A cycle costs ₹2,350. Class 2A has 34 children; 5400 g.") == [2350, 34, 5400]
    assert (
        S.answer("COMPARE_SMALLER", "Class 3A made 63 kites; 3B made 18 fewer. How many did 3B make?") == 45
    )
    assert S.answer("JOIN_RESULT", "Five birds sat; 3 more came.") is None, "a number in words is a person's"


@DB
def test_a_story_in_an_educators_words_is_named_by_jev_and_the_rest_is_code(conn):
    """Nimish: "You should really deep dive into Jev and potentially figure out all the use cases that we can
    integrate and start doing that." Jev chooses among the taxonomy's own story shapes; the case, the skill set and
    level that hold it, and the answer are code's."""
    ask, asked = _saying("COMPARE_SMALLER")
    got = S.name(
        conn, "Leela scored 87 in the quiz. Omar scored 12 less than Leela. What was Omar's score?", ask
    )
    purpose, state, options = asked[0]
    assert purpose == "story_shape" and "Leela" in state["story"]
    assert {"JOIN_RESULT", "SUB_SUB", "CONSTRAINT"} <= options and len(options) == len(S.shapes(conn))
    assert (got["shape"], got["case"], got["how"], got["answer"]) == ("COMPARE_SMALLER", "W11", "jev", 75)
    assert got["placed"], "a case some level names sits on that skill set and level"


@DB
def test_the_engines_own_story_is_named_by_its_template_and_jev_is_not_asked(conn):
    ask, asked = _saying("JOIN_RESULT")
    got = S.name(
        conn, "There were 40 birds on a tree. 15 flew away. How many birds are still on the tree?", ask
    )
    assert asked == [] and (got["shape"], got["how"], got["answer"]) == ("SEPARATE_RESULT", "template", 25)


@DB
def test_a_shape_jev_is_not_sure_of_and_jev_unreachable_are_left_for_a_person(conn):
    ask, _ = _saying("JOIN_CHANGE", p=0.4)
    unsure = S.name(conn, "Zoya had 28 bangles and now has 45. How many did she get?", ask)
    assert (
        unsure["shape"] is None and unsure["answer"] is None and "a person names the shape" in unsure["why"]
    )
    assert unsure["ranked"][0][0] == "JOIN_CHANGE", "the person sees what Jev leaned to"

    def down(*a):
        raise jev.JevError("no TYPESAFE_API_KEY in the engine's environment")

    off = S.name(conn, "Zoya had 28 bangles and now has 45. How many did she get?", down)
    assert off["shape"] is None and "TYPESAFE_API_KEY" in off["why"]


@DB
def test_the_eval_counts_shapes_keys_and_what_is_left(conn):
    stories = [
        {"shape": "JOIN_RESULT", "text": "Dev read 57 pages, then 26 more. How many in all?", "answer": 83},
        {"shape": "PPW_WHOLE", "text": "57 mango trees and 26 chikoo trees. How many trees?", "answer": 83},
        {"shape": "SUB_SUB", "text": "₹600; spent ₹240 and ₹175. How much is left?"},
    ]
    ask, _ = _saying("JOIN_RESULT")
    got = S.evaluate(conn, stories, ask)
    assert (got["n"], got["named"], got["right"], got["keyed"], got["wrong_answer"]) == (3, 3, 1, 2, 0)
    assert [m["want"] for m in got["misses"]] == ["PPW_WHOLE", "SUB_SUB"]


@DB
def test_the_storys_numbers_hold_jev_to_account(conn):
    """Measured 2026-09-28: Jev called "Aisha is 8 years old. She has 34 red beads and 27 blue beads" two parts and a
    whole, 0.9 sure. A one-step question over three numbers is extra information by definition, and code counts
    numbers; a shape whose stories print two numbers is never taken for a story that prints four."""
    ask, _ = _saying("PPW_WHOLE", p=0.9)
    extra = S.name(conn, "Aisha is 8 years old. She has 34 red beads and 27 blue beads. How many beads?", ask)
    assert (extra["shape"], extra["how"], extra["answer"]) == ("EXTRA_INFORMATION", "jev+code", None)
    four = S.name(conn, "12 boys, 14 girls, 3 teachers and 2 cooks. How many children?", ask)
    assert four["shape"] is None and "prints 4" in four["why"]


@DB
def test_a_key_computed_for_a_story_that_is_not_one_step_is_counted_wrong(conn):
    """Measured 2026-09-28: Jev took "90 stickers between them; one has 20 more" for a compare, and code keyed it 70
    (it is 35). The eval had counted only stories whose gold has an answer, and said 0 wrong."""
    stories = [
        {
            "shape": "CONSTRAINT",
            "text": "Two friends have 90 stickers between them. One has 20 more. The fewer?",
        }
    ]
    ask, _ = _saying("COMPARE_SMALLER")
    got = S.evaluate(conn, stories, ask)
    assert (got["keyed"], got["wrong_answer"]) == (1, 1)


@DB
def test_each_shape_is_shown_with_every_one_of_the_engines_stories_of_it(conn):
    constraint = S.shapes(conn)["CONSTRAINT"][1]
    assert "I think of a number" in constraint and "Two numbers add up to" in constraint
