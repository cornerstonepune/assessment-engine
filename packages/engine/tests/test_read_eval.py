"""How the reader is scored against what a person actually saw on the page.

The one number that matters here is `silently_wrong`: a reading the engine STANDS BEHIND and got
wrong corrupts a child's graph invisibly, where one it flagged costs a teacher a glance.
"""

from engine import read_eval

GOLD = [
    {"n": 1, "part": "", "child_answer": "763", "answer_state": "written"},
    {"n": 2, "part": "", "child_answer": "<", "answer_state": "written"},
    {"n": 3, "part": "", "child_answer": "", "answer_state": "blank"},
]


def test_a_confident_wrong_value_is_a_silent_error():
    read = {"1": {"child_answer": "363", "answer_state": "written"}}
    s = read_eval.score(GOLD[:1], read)
    assert (s["exact"], s["silently_wrong"]) == (0, 1)


def test_a_false_blank_is_a_silent_error_too():
    """`blank` is not a flag. It is the engine asserting the child did not attempt this skill, and
    it lands in the graph as exactly that. The Grade 3 baseline is where it showed: the comparison
    question is answered with "<", the transcriber reads numbers only, and the region came back
    blank at full confidence on a question the child got right."""
    s = read_eval.score(GOLD[1:2], {"2": {"child_answer": "", "answer_state": "blank"}})
    assert (s["exact"], s["silently_wrong"]) == (0, 1)


def test_a_flagged_answer_is_not_a_silent_error():
    """It reached a person. That is the whole difference the bar rests on."""
    s = read_eval.score(GOLD[1:2], {"2": {"child_answer": "", "answer_state": "illegible"}})
    assert (s["wrong_value"], s["silently_wrong"]) == (1, 0)


def test_a_blank_the_child_really_left_is_read_right():
    s = read_eval.score(GOLD[2:], {"3": {"child_answer": "", "answer_state": "blank"}})
    assert (s["exact"], s["silently_wrong"]) == (1, 0)


def test_a_response_with_no_row_at_all_is_counted_as_missing():
    """Nobody corrects what they were never shown."""
    s = read_eval.score(GOLD, {})
    assert (s["missing"], s["responses_given_a_row"]) == (3, 0.0)


def test_a_sitting_can_be_several_photographs():
    """A Grade 2 sitting is one scanned PDF; a Grade 3 sitting is one photograph per page."""
    assert read_eval.sheet_name({"file": "a.pdf"}) == "a.pdf"
    assert read_eval.sheet_name({"files": ["p1.jpg", "p2.jpg"]}) == "p1.jpg"
