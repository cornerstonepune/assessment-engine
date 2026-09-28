"""The Jev adapter (`adapters/jev.py`, ADR 0036): one typed decision per call, from a prompt row, never text.
The service is stood in for; what is tested is the request the adapter builds and what it makes of the reply."""

import pytest

from engine.adapters import jev

ROW = {
    "id": "p1",
    "text": "Which named mistake produces exactly {answer}?",
    "model": "jev-latest",
    "json_schema": {"type": "choice"},
}


def _reply(probabilities):
    best = max(probabilities, key=probabilities.get)
    return {
        "model": "jev-1.13.0",
        "answers": {
            "decision": {"type": "choice", "choice": best, "confidence": 0.5, "probabilities": probabilities}
        },
        "usage": {"input_tokens": 400, "output_tokens": 60},
    }


def test_a_choice_is_asked_with_the_rows_words_and_comes_back_ranked():
    sent = {}

    def post(body):
        sent.update(body)
        return _reply({"M_NOCARRY": 0.7, "M_CONCAT": 0.2, "NONE": 0.1})

    options = {"M_NOCARRY": "Forgets to carry", "M_CONCAT": "Writes the column sum", "NONE": "None of these"}
    out = jev.ask(ROW, {"answer": "75"}, options, post)
    assert sent["model"] == "jev-latest" and sent["state"] == {"answer": "75"}
    q = sent["questions"]["decision"]
    assert q["type"] == "choice" and q["instructions"] == "Which named mistake produces exactly 75?"
    assert set(q["criteria"]) == {"M_NOCARRY", "M_CONCAT", "NONE"}
    assert out["choice"] == "M_NOCARRY" and [c for c, _ in out["ranked"]] == ["M_NOCARRY", "M_CONCAT", "NONE"]
    assert out["tokens_in"] == 400 and out["model"] == "jev-1.13.0"


def test_a_choice_outside_the_options_is_refused_never_passed_on():
    with pytest.raises(jev.JevError, match="not one of"):
        jev.ask(
            ROW, {"answer": "75"}, {"M_NOCARRY": "Forgets to carry"}, lambda body: _reply({"M_OTHER": 1.0})
        )


def test_more_options_than_the_service_takes_are_refused_before_anything_is_sent():
    options = {f"O{i}": "x" for i in range(jev.MAX_OPTIONS + 1)}
    with pytest.raises(jev.JevError, match="at most"):
        jev.ask(ROW, {}, options, lambda body: pytest.fail("sent"))


def test_no_key_says_so_in_words():
    with pytest.raises(jev.JevError, match="TYPESAFE_API_KEY"):
        jev._post({}, key="")


YES_NO = {
    "id": "p2",
    "text": "Did the class work on this skill this week: {subject}?",
    "model": "jev-latest",
    "json_schema": {"type": "noul", "criteria": {"true": "it did", "false": "it did not"}},
}


def test_many_yes_no_questions_go_in_one_call_and_come_back_as_probabilities():
    sent = {}

    def post(body):
        sent.update(body)
        return {"model": "jev-1.13.0", "answers": {k: {"type": "noul", "noul": p} for k, p in (("A", 0.9), ("B", 0.1))},
                "usage": {"input_tokens": 300, "output_tokens": 4}}  # fmt: skip

    out = jev.yes_no(YES_NO, {"educator_note": "sums"}, {"A": "adding", "B": "taking away"}, post)
    assert set(sent["questions"]) == {"A", "B"} and sent["state"] == {"educator_note": "sums"}
    assert sent["questions"]["A"] == {
        "type": "noul",
        "instructions": "Did the class work on this skill this week: adding?",
        "criteria": {"true": "it did", "false": "it did not"},
    }
    assert out["yes"] == {"A": 0.9, "B": 0.1} and out["tokens_in"] == 300


def test_a_yes_no_answer_that_is_not_a_probability_or_not_asked_is_refused():
    asks = {"A": "adding"}
    with pytest.raises(jev.JevError, match="not the questions"):
        jev.yes_no(YES_NO, {}, asks, lambda b: {"answers": {"Z": {"type": "noul", "noul": 0.5}}})
    with pytest.raises(jev.JevError, match="not a probability"):
        jev.yes_no(YES_NO, {}, asks, lambda b: {"answers": {"A": {"type": "noul", "noul": 1.7}}})
