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
