"""The materials_read eval (rule 7: no prompt is active before it meets a bar). It scores what code did with the model's
readings against cases a person marked. The model is replaced by a fake, so no call is made and nothing is spent."""

import pytest

from engine.w2_print import materials_read_eval as ev

CATALOGUE = [
    {"code": "MAT-0001", "name": "Pen", "unit": "piece"},
    {"code": "MAT-0002", "name": "Clay", "unit": "packet"},
]


def _case(note, *expect):
    return {"note": note, "expect": [{"item_code": c, "quantity": q, "unit": u} for c, q, u in expect]}


def _ask(answers):
    return lambda note, catalogue: answers[note]


def _reading(code, q, unit, text="x"):
    return {"text": text, "item_code": code, "quantity": q, "unit": unit}


def test_an_empty_gold_set_is_refused_before_any_model_call():
    with pytest.raises(ev.NoGold):
        ev.score([], CATALOGUE, _ask({}))


def test_the_scores_count_what_was_confirmed_wrongly_what_was_found_and_what_was_held_back():
    cases = [
        _case("20 pens", ("MAT-0001", 20, "piece")),
        _case("3 clay", ("MAT-0002", 3, "packet")),
        _case("some ribbon"),
    ]
    answers = {
        "20 pens": {"people_visible": False, "readings": [_reading("MAT-0001", 20, "piece", "20 pens")]},
        "3 clay": {
            "people_visible": False,
            "readings": [_reading("MAT-0001", 3, "piece", "3 clay")],
        },  # wrong item, confirmed
        "some ribbon": {"people_visible": False, "readings": [_reading(None, None, None, "some ribbon")]},
    }
    got = ev.score(cases, CATALOGUE, _ask(answers))
    assert (
        got["confirmed_wrong"] == 1
    )  # a count: one of the two confirmed readings is not what the person marked
    assert got["found"] == 1 / 2  # of the two marked items, one was found
    assert got["held_back_right"] == 1.0  # the case that should go to a person did
