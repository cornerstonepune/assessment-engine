"""The one-activity probe of the proposer (goals/m1-11j-map-probe.yaml).

2026-11-04: proposer v3 hands the reply's shape to the vendor (M1-11e) and nobody has seen that request answered. One
activity, one call, says whether the request is accepted and whether the reply passes the local check, before a full
run is paid for. It prints those two facts and nothing else: a public log must never carry a school's words or a reply.
"""

import re

import pytest

from engine.adapters import llm
from engine.w1_bank import map_probe
from engine.w1_bank.map_agents import PROPOSE, Band
from engine.w1_bank.map_check import Gap, Known

CODE = "ACT-K2-0001"
SECRET = "the school's own sentence about clay"


def band() -> Band:
    return Band(
        known=Known(
            skills={"NUM.CNT.01": "NUM"}, families={"Maths": frozenset({"NUM"})}, objectives=frozenset()
        ),
        gaps={
            CODE: Gap(CODE, "Maths", frozenset(), frozenset(), frozenset()),
            "ACT-K2-0002": Gap("ACT-K2-0002", "Maths", frozenset({"NUM.CNT.01"}), frozenset(), frozenset()),
        },
        words={CODE: {"name": SECRET}, "ACT-K2-0002": {"name": "counting"}},
        person_skills={"ACT-K2-0002": frozenset({"NUM.CNT.01"})},
        objectives={},
        skills={},
        lo_skills=set(),
        names={"NUM.CNT.01": "Counts"},
        pool=frozenset({"ACT-K2-0002"}),
    )


class Asked:
    def __init__(self, answer):
        self.calls, self.answer = [], answer

    def __call__(self, purpose, about, variables):
        self.calls.append((purpose, about, variables))
        if isinstance(self.answer, Exception):
            raise self.answer
        return self.answer


def run(answer):
    ask = Asked(answer)
    return map_probe.probe(band(), CODE, 3, ask), ask


def test_one_question_is_asked_of_the_proposer_about_the_one_activity_and_no_other():
    _, ask = run({"skills": ["NUM.CNT.01"], "confidence": 0.9})
    assert [(p, a) for p, a, _ in ask.calls] == [(PROPOSE, "probe:" + CODE)]
    assert ask.calls[0][2]["gaps"] == ["skill"], "asked as the eval asks it: the activity's links hidden"


def test_a_reply_the_vendor_sent_and_the_local_check_passed_says_so():
    line, _ = run({"skills": ["NUM.CNT.01"], "confidence": 0.9})
    assert line == "HTTP 200; the reply passed the local check"


def test_a_reply_that_broke_the_local_check_says_so_without_the_reason():
    line, _ = run(llm.LLMSchemaError(f"{SECRET!r} was unexpected"))
    assert line == "HTTP 200; the reply broke the local check"
    assert SECRET not in line


@pytest.mark.parametrize("code", [400, 401, 429, 529])
def test_a_refused_request_gives_its_status_and_not_the_vendors_words(code):
    line, _ = run(llm.LLMError(f"claude-sonnet-5-5 returned HTTP {code}: {SECRET} is not a valid schema"))
    assert line == f"HTTP {code}; no reply"


def test_a_call_that_never_reached_the_vendor_has_no_status_to_give():
    line, _ = run(llm.LLMBudgetError(f"campaign spent {SECRET}"))
    assert line == "no HTTP status; the call was not made or did not arrive (LLMBudgetError)"
    assert SECRET not in line


def test_what_is_printed_is_one_line_with_no_words_of_the_school():
    for answer in ({"skills": []}, llm.LLMSchemaError(SECRET), llm.LLMError(f"HTTP 400: {SECRET}")):
        line, _ = run(answer)
        assert "\n" not in line and not re.search(SECRET, line)


def test_the_probes_call_is_labelled_so_a_dev_run_replayed_after_it_does_not_read_it():
    _, ask = run({"skills": []})
    assert ask.calls[0][1].startswith(map_probe.LABEL)
