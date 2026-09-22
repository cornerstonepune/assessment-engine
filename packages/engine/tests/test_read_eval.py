"""How the reader is scored against what a person actually saw on the page.

The one number that matters here is `silently_wrong`: a reading the engine STANDS BEHIND and got
wrong corrupts a child's graph invisibly, where one it flagged costs a teacher a glance.
"""

from engine.w3_read import read_eval

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


def test_a_photograph_a_teacher_corrected_is_read_as_its_own_page_from_its_own_path(tmp_path, monkeypatch):
    """The first teacher correction on a paper outside the seed killed the whole eval: the capture
    names its scan "~/cornerstone/…", and joined to the assessments folder unexpanded that named a
    file that does not exist. And a Grade 3 sitting is one photograph per page, so the second
    photograph is page 2 of the paper — read as page 1 it was scored against the wrong questions."""
    import cv2
    import numpy as np

    from engine.w3_read import read_eval

    monkeypatch.setenv("HOME", str(tmp_path))
    cv2.imwrite(str(tmp_path / "page-two.jpg"), np.full((40, 30, 3), 255, np.uint8))
    got = read_eval.sheet_pages({"file": "~/page-two.jpg", "page": 2}, root=tmp_path / "elsewhere")
    assert [(n, str(f), in_file) for n, f, in_file, _ in got] == [(2, str(tmp_path / "page-two.jpg"), 1)]


def test_a_signed_off_answer_joins_the_gold_set_and_a_correction_on_the_same_answer_wins(monkeypatch):
    """ADR 0032: a sign-off is a person saying the reader's reading is what the child wrote. It joins
    the set the reader is scored against, as a typed correction does — and where both exist for one
    answer, the typed one is the truth."""
    from engine.w3_read import marking, profiles

    row = {
        "paper": "G2-X",
        "path": "~/g2/one.pdf",
        "file_pages": 2,
        "page": 1,
        "item_key": "G2-X/1/4",
        "human_read": "45",
    }
    monkeypatch.setattr(
        profiles, "signed_off", lambda conn: [row, {**row, "item_key": "G2-X/1/5", "human_read": "9"}]
    )
    monkeypatch.setattr(
        marking, "corrections", lambda conn: [{**row, "item_key": "G2-X/1/5", "human_read": "19"}]
    )
    sheets = [s for s in read_eval.gold_sheets(conn=object()) if s["paper"] == "G2-X"]
    assert len(sheets) == 1
    assert sorted((a["n"], a["child_answer"]) for a in sheets[0]["answers"]) == [("4", "45"), ("5", "19")]
