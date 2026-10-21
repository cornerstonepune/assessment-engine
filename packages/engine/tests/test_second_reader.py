"""ADR 0032 — the second reader: the vision model shown this child's own handwriting proposes what
the first reader gave up on. It only ever proposes; a person confirms."""

import json
import os
from pathlib import Path

import pytest

from engine.adapters import llm
from engine.w3_read import marking, second_reader
from tests.rows import a_read_paper

DOUBT = {
    "child_answer": "",
    "answer_state": "illegible",
    "why": "3 numbers in the region for 2 answers",
    "confidence": 0.0,
}
BOX = [0.1, 0.2, 0.7, 0.35]


def test_doubted_readings_are_grouped_by_the_region_they_share_and_the_rest_left_alone():
    readings = {
        "7a": {**DOUBT, "box": BOX},
        "7b": {**DOUBT, "box": BOX},
        "8": {
            "child_answer": "45",
            "answer_state": "written",
            "why": "",
            "confidence": 96.0,
            "box": [0, 0.4, 0.7, 0.5],
        },
        "9": {**DOUBT, "why": "the answer to this question is not a number", "box": [0, 0.5, 0.7, 0.6]},
        "10": {**DOUBT, "why": "under the confidence floor", "guess": "12", "box": [0, 0.6, 0.7, 0.7]},
        "11": {**DOUBT, "why": "the printed question was not found on the page"},  # no crop to show
    }
    assert second_reader._groups(readings) == {tuple(BOX): ["7a", "7b"]}


def test_the_second_reader_is_shown_the_childs_samples_and_its_answers_become_the_guesses(monkeypatch):
    calls = []
    monkeypatch.setattr(second_reader, "crop_of", lambda path, page, box, cfg: b"target")
    monkeypatch.setattr(
        second_reader,
        "examples",
        lambda conn, notes, cfg, exclude_capture=None: [(b"s1", "45"), (b"s2", "17")],
    )

    def generate(conn, purpose, variables, images=()):
        calls.append((purpose, variables, list(images)))
        return {"answers": ["282", "272"], "sure": 0.8}

    monkeypatch.setattr(llm, "generate", generate)
    readings = {
        "7a": {**DOUBT, "box": BOX},
        "7b": {**DOUBT, "box": BOX},
        "8": {"child_answer": "45", "answer_state": "written", "why": "", "confidence": 96.0},
    }
    got, note = second_reader.propose(
        None, readings, "~/scan.pdf", 1, {"samples": []}, {"reread_dpi": 500, "reread_pad": 0.012}
    )
    assert calls == [
        (
            "read_with_examples",
            {"k": 2, "examples": "Image 1: the child wrote '45'\nImage 2: the child wrote '17'", "n": 2},
            [b"s1", b"s2", b"target"],
        )
    ]
    assert got["7a"]["guess"] == "282" and got["7b"]["guess"] == "272"
    assert got["7a"]["guess_by"] == "read_with_examples with 2 of the child's answers"
    assert (
        got["7a"]["answer_state"] == "illegible" and got["7a"]["child_answer"] == ""
    )  # a proposal, never a reading
    assert got["8"] == readings["8"]
    assert note == "second reader: 1 of 1 questions given a guess, 2 samples shown"


def test_a_short_or_failed_answer_leaves_the_readings_as_they_were(monkeypatch):
    monkeypatch.setattr(second_reader, "crop_of", lambda path, page, box, cfg: b"target")
    monkeypatch.setattr(second_reader, "examples", lambda conn, notes, cfg, exclude_capture=None: [])
    monkeypatch.setattr(
        llm, "generate", lambda conn, purpose, variables, images=(): {"answers": ["282"], "sure": 0.4}
    )
    got, _ = second_reader.propose(
        None, {"7a": {**DOUBT, "box": BOX}, "7b": {**DOUBT, "box": BOX}}, "x", 1, {}, {}
    )
    assert (got["7a"]["guess"], got["7b"]["guess"]) == ("282", "")

    def down(conn, purpose, variables, images=()):
        raise llm.LLMError("all models unavailable")

    monkeypatch.setattr(llm, "generate", down)
    readings = {"7a": {**DOUBT, "box": BOX}}
    got, note = second_reader.propose(None, readings, "x", 1, {}, {})
    assert got == readings and note == "second reader: 0 of 1 questions given a guess, 0 samples shown"


def test_nothing_doubted_means_no_call_at_all(monkeypatch):
    monkeypatch.setattr(llm, "generate", lambda *a, **k: pytest.fail("the model was called"))
    readings = {"8": {"child_answer": "45", "answer_state": "written", "why": "", "confidence": 96.0}}
    assert second_reader.propose(None, readings, "x", 1, {}, {}) == (readings, "")


# ---------------------------------------------------------------- a second opinion on the box reader's guess (ADR 0091)

# a box reader's reading it did not stand behind, with its best reading offered as the guess (`boxes.decide`)
BOXED = {
    "child_answer": "",
    "answer_state": "illegible",
    "why": "under the confidence floor",
    "guess": "47",
    "confidence": 81.0,
    "boxes": 2,
    "inked": 2,
    "box": BOX,
}
SAMPLES = [(b"s1", "45"), (b"s2", "17")]


def _second_reader_says(monkeypatch, answer):
    calls = []
    monkeypatch.setattr(second_reader, "crop_of", lambda path, page, box, cfg: b"target")
    monkeypatch.setattr(second_reader, "examples", lambda conn, notes, cfg, exclude_capture=None: SAMPLES)

    def generate(conn, purpose, variables, images=()):
        calls.append((purpose, variables, list(images)))
        return {"answers": [answer], "sure": 0.7}

    monkeypatch.setattr(llm, "generate", generate)
    return calls


def test_a_box_readers_guess_below_trust_is_read_again_by_the_second_reader_with_the_childs_own_samples(
    monkeypatch,
):
    calls = _second_reader_says(monkeypatch, "47")
    region = {**DOUBT, "guess": "12", "box": [0, 0.6, 0.7, 0.7]}  # Textract's guess on a paper read by region
    second_reader.propose(None, {"5": dict(BOXED), "10": region}, "x", 1, {"samples": []}, {})
    assert (
        calls
        == [
            (
                "read_with_examples",
                {"k": 2, "examples": "Image 1: the child wrote '45'\nImage 2: the child wrote '17'", "n": 1},
                [b"s1", b"s2", b"target"],
            )
        ]
    )  # the box reader's guess only: a guess found in a region is not what Nimish said yes to, and was not measured
    # the backfill of the queue still only turns typing into clicking: it asks about what nobody has guessed yet
    assert second_reader._groups({"5": dict(BOXED)}, second_opinion=False) == {}


def test_when_the_two_readers_agree_the_answer_follows_todays_path_unchanged(monkeypatch):
    _second_reader_says(monkeypatch, "47")
    got, note = second_reader.propose(None, {"5": dict(BOXED)}, "x", 1, {}, {})
    assert got["5"] == BOXED
    assert marking.mark_read({"answer": "47"}, {}, got["5"]) == marking.mark_read({"answer": "47"}, {}, BOXED)
    assert note == "second reader: 1 of 1 questions given a second opinion, 1 agreed, 2 samples shown"


def test_when_the_two_readers_disagree_it_goes_to_a_person_with_both_readings_shown(monkeypatch):
    _second_reader_says(monkeypatch, "41")
    got, note = second_reader.propose(None, {"5": dict(BOXED)}, "x", 1, {}, {})
    r = got["5"]
    assert (r["guess"], r["second_read"]) == (
        "47",
        "41",
    )  # both readings, the box reader's still the one-click guess
    assert (
        r["why"] == "under the confidence floor; the second reader, shown 2 of the child's answers, read 41"
    )
    assert (r["answer_state"], r["child_answer"]) == ("illegible", "")
    status, _, _, read = marking.mark_read({"answer": "47"}, {}, r)
    assert status == "unreadable" and read["second_read"] == "41"  # waits for a person, carrying both
    assert note == "second reader: 1 of 1 questions given a second opinion, 0 agreed, 2 samples shown"
    # a second reader that saw nothing where the box reader saw 47 disagrees too, and says so
    _second_reader_says(monkeypatch, "")
    got, _ = second_reader.propose(None, {"5": dict(BOXED)}, "x", 1, {}, {})
    assert got["5"]["second_read"] == "" and got["5"]["why"].endswith("read nothing")


def test_the_second_reader_never_settles_an_answer_and_is_never_shown_the_question_or_the_right_answer(
    monkeypatch,
):
    import inspect
    import re

    # ADR 0019 / ADR 0032: it is given the child's samples and the crop, and nothing else
    assert list(inspect.signature(second_reader.propose).parameters) == [
        "conn", "readings", "path", "file_page", "notes", "cfg", "exclude_capture", "second_opinion",
    ]  # fmt: skip
    text = (Path(__file__).parents[3] / "supabase/seed/prompts/read_with_examples.v1.txt").read_text()
    assert set(re.findall(r"{{(\w+)}}", text)) == {"k", "examples", "n"}
    for answer in ("47", "41", ""):
        calls = _second_reader_says(monkeypatch, answer)
        readings = {"5": dict(BOXED), "7": {**DOUBT, "box": [0, 0.4, 0.7, 0.5]}}
        got, _ = second_reader.propose(None, readings, "x", 1, {}, {})
        assert all(set(v) == {"k", "examples", "n"} for _, v, _ in calls)
        for r in got.values():  # a proposal at most: never the answer, never settled
            assert (r["answer_state"], r["child_answer"]) == ("illegible", "")
            assert marking.mark_read({"answer": "47"}, {}, r)[0] == "unreadable"


def test_the_second_opinion_is_scored_by_what_it_would_have_caught():
    # (the box reader's guess, the second reader's, what the person typed)
    seen = [("47", "47", "47"), ("47", "41", "41"), ("47", "41", "47"), ("47", "47", "41"), ("3", "8", "5")]
    assert second_reader.opinion_tally(seen) == {
        "n": 5,
        "box_right": 2,
        "second_right": 2,
        "agreed": 2,
        "agreed_right": 1,
        "caught": 2,  # the box reader's guess was wrong and the second reader said otherwise
        "caught_right": 1,  # … and its own reading was what the child wrote
        "false_alarm": 1,  # the box reader was right and the second reader disagreed
        "missed": 1,  # both read the same wrong number
    }


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    from engine.core import db

    with db.connect() as c:
        yield c
        c.rollback()


def test_the_eval_of_the_second_opinion_reads_again_only_what_the_box_reader_guessed(
    conn, tmp_path, monkeypatch
):
    scan = tmp_path / "scan.pdf"
    scan.write_bytes(b"%PDF")
    paper = a_read_paper(
        conn,
        [
            {
                "status": "needs_teacher",
                "read": "",
                "typed": "41",
            },  # the box reader guessed 47; the child wrote 41
            {"status": "needs_teacher", "read": "", "typed": "35"},  # it guessed 35, rightly
            {
                "status": "needs_teacher",
                "read": "",
                "typed": "8",
            },  # ink, no number: nothing of its own to compare
            {"status": "needs_teacher", "read": "", "typed": "12"},  # a region's guess, not the box reader's
        ],
        path=scan,
    )
    readings = [
        {"why": "under the confidence floor", "guess": "47", "boxes": 2},
        {"why": "the reader's readings disagree: 35 / 36", "guess": "35", "boxes": 2},
        {"why": "ink in the box but no number", "guess": "", "boxes": 1},
        {"why": "under the confidence floor", "guess": "12"},
    ]
    for n, (rid, r) in enumerate(zip(paper["results"], readings)):
        raw = {
            **r,
            "child_answer": "",
            "answer_state": "illegible",
            "confidence": 60.0,
            "box": [0, n / 10, 1, 0.1],
        }
        conn.execute("update item_result set raw_read = %s where id = %s", (json.dumps(raw), rid))
    said = {0.0: "41", 0.1: "35", 0.2: "8", 0.3: "12"}  # what the second reader reads in each crop
    monkeypatch.setattr(second_reader, "crop_of", lambda path, page, box, cfg: box[1])
    monkeypatch.setattr(second_reader, "examples", lambda conn, notes, cfg, exclude_capture=None: [])
    asked = []

    def generate(conn, purpose, variables, images=()):
        asked.append(images[-1])
        return {"answers": [said[images[-1]]], "sure": 0.6}

    monkeypatch.setattr(llm, "generate", generate)
    t = second_reader.evaluate(conn, {}, [paper["child"]], second_opinion=True)
    assert sorted(asked) == [0.0, 0.1] and (t["n"], t["right"]) == (2, 2)
    assert t["opinion"] == {
        "n": 2, "box_right": 1, "second_right": 2, "agreed": 1, "agreed_right": 1,
        "caught": 1, "caught_right": 1, "false_alarm": 0, "missed": 0,
    }  # fmt: skip
    # without it, the eval is today's: every answer the first reader did not stand behind, the ink with no number too
    today = second_reader.evaluate(conn, {}, [paper["child"]])
    assert today["n"] == 4 and "opinion" not in today
