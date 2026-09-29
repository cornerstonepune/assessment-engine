"""The equation a group of answer boxes completes (`assess/equation.py`): a box is right when its side comes out at the
total, whatever split the child chose. Nimish, 2026-09-29, of "638 = 600 + [ ] + [ ]": "this question's right answer
is 19 and 19"."""

import json

import pytest

from engine.assess import equation
from engine.core import db


def test_any_split_that_comes_out_at_the_total_is_right():
    assert equation.right("638 = 600 + {5a} + {5b}", {"5a": 19, "5b": 19}) == {"5a": True, "5b": True}
    assert equation.right("638 = 600 + {5a} + {5b}", {"5a": "30", "5b": "8"}) == {"5a": True, "5b": True}
    assert equation.right("638 = 600 + {5a} + {5b}", {"5a": 30, "5b": 9}) == {"5a": False, "5b": False}
    assert (
        equation.right("{a} - 20 = 5", {"a": 25}) == equation.right("{a} − 20 = 5", {"a": 25}) == {"a": True}
    )


def test_each_side_of_a_chained_equation_is_its_own_claim():
    total = "638 + 475 = {5f} + {5g} + {5h} = {5i}"
    assert set(equation.right(total, {"5f": 1000, "5g": 89, "5h": 24, "5i": 1113}).values()) == {True}
    assert equation.right(total, {"5f": 1100, "5g": 0, "5h": 13, "5i": 1112}) == {
        "5f": True,
        "5g": True,
        "5h": True,
        "5i": False,
    }, "a right split beside a wrong total: the split is right, the total is not"


def test_a_side_with_a_box_not_known_decides_nothing():
    assert equation.right("638 = 600 + {5a} + {5b}", {"5a": 19}) == {"5a": None, "5b": None}
    assert equation.right("638 = 600 + {5a} + {5b}", {"5a": 19, "5b": "3?5"}) == {"5a": None, "5b": None}
    assert equation.right("638 + 475 = {5f} + {5g} = {5i}", {"5i": 1113}) == {
        "5f": None,
        "5g": None,
        "5i": True,
    }
    assert equation.refs("638 = 600 + {5a} + {5b}") == ["5a", "5b"]


def test_an_equation_code_cannot_read_is_refused_when_the_paper_is_entered():
    for bad in (
        "638 = 600 * {5a}",
        "638 600 + {5a}",
        "= {5a}",
        "638 = 600 + + {5a}",
        "{a} + {b} = {c}",
        "5 = 6 = {a}",
    ):
        with pytest.raises(ValueError):
            equation.check(bad)


def test_a_paper_whose_own_key_does_not_make_its_equation_true_is_refused():
    def paper(b_answer, holds="638 = 600 + {5a} + {5b}"):
        return {
            "items": [
                {"n": 5, "part": "a", "answer": 30, "holds": holds},
                {"n": 5, "part": "b", "answer": b_answer},
            ]
        }

    assert equation.of(paper(8)["items"][0], paper(8)) == {"holds": "638 = 600 + {5a} + {5b}"}
    assert equation.of({"n": 1, "answer": 3}, paper(8)) == {}, (
        "a question that names no equation is its key's alone"
    )
    with pytest.raises(ValueError, match="not made true"):
        equation.of(paper(9)["items"][0], paper(9))
    with pytest.raises(ValueError, match="not made true"):
        equation.of(paper(None)["items"][0], paper(None))
    with pytest.raises(ValueError, match="its own question's box"):
        equation.of(paper(8, "638 = 600 + {5b} + 30")["items"][0], paper(8, "638 = 600 + {5b} + 30"))
    with pytest.raises(ValueError, match="only boxes of this paper"):
        equation.of(paper(8, "638 = 600 + {5a} + {5z}")["items"][0], paper(8, "638 = 600 + {5a} + {5z}"))


def test_every_equation_the_school_s_papers_name_is_one_their_own_key_makes_true():
    """The papers are the school's: an equation typed wrong would mark a right answer wrong. Each is entered as the
    loader enters it, held to the paper it is on — its boxes that paper's, the key printed with it making it true."""
    named = 0
    for path in sorted((db.REPO_ROOT / "supabase/seed/papers").glob("*.json")):
        paper = json.loads(path.read_text())
        for it in paper["items"]:
            named += bool(equation.of(it, paper))
    assert named >= 26, "question 5 of the G3 and G4 September papers"
