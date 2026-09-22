"""ADR 0032 — the second reader: the vision model shown this child's own handwriting proposes what
the first reader gave up on. It only ever proposes; a person confirms."""

import pytest

from engine.adapters import llm
from engine.w3_read import second_reader

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
