"""The parent report's second reader (engine/w4_close/parent_review.py): scored on every bad sentence of the gold set
flagged, and nothing else flagged."""

import json
import os

import pytest

from engine.adapters import jev
from engine.core import db
from engine.w4_close import parent_review as R

GOLD = json.loads((db.REPO_ROOT / R.GOLD).read_text())


def test_the_gold_set_holds_right_drafts_and_wrong_ones_and_no_name():
    cases = GOLD["cases"]
    assert [c for c in cases if not c["bad"]] and [c for c in cases if c["bad"]]
    for c in cases:
        for b in c["bad"]:
            assert b in json.dumps(c["draft"], ensure_ascii=False), (c["ref"], b)
        assert "next" not in c["facts"]
    assert "first_name" not in json.dumps(GOLD)


def test_the_reviewer_is_scored_on_every_bad_sentence_and_on_nothing_else():
    by_draft = {json.dumps(c["draft"], sort_keys=True): c for c in GOLD["cases"]}

    def perfect(conn, purpose, variables, meta=None, version=None):
        c = by_draft[json.dumps(variables["draft"], sort_keys=True)]
        return {"unsupported": [{"quote": b, "why": c["note"]} for b in c["bad"]]}

    r = R.evaluate(None, ask=perfect)
    assert r["caught"] == r["bad"] > 0 and r["false_flags"] == 0 and not r["misses"]

    def fussy(conn, purpose, variables, meta=None, version=None):
        return {"unsupported": [{"quote": variables["draft"]["summary"][:40], "why": "tone"}]}

    r = R.evaluate(None, ask=fussy)
    assert r["false_flags"] > 0 and r["misses"]


def _case(ref):
    return next(c for c in GOLD["cases"] if c["ref"] == ref)


@pytest.fixture
def bars(monkeypatch):
    """The two threshold rows, as seeded: below 0.1 Jev is sure a sentence is wrong, from 0.5 sure it is right."""
    monkeypatch.setattr(R, "_bars", lambda conn: (0.1, 0.5))


def _jev(p_of):
    """Jev, stood in: each sentence's chance it is supported, from `p_of(sentence)`; what it was asked is kept."""
    asked = []

    def ask(conn, purpose, state, asks, version=None):
        asked.append((purpose, state, dict(asks)))
        return {"yes": {k: p_of(s) for k, s in asks.items()}}

    return ask, asked


def test_each_sentence_is_asked_with_only_the_facts_it_is_about():
    """The summary is held to the child's standing; a skill's line to that skill's fact; a mistake's line to what
    happens in that mistake; a home activity to the facts. Every sentence of the draft is asked, once."""
    c = _case("e5")
    asked = R.questions(c["facts"], c["draft"])
    assert {part for part, _, _ in asked} == {"claims", "mistakes", "home"}
    side_by_side = next(
        st for part, st, ss in asked if part == "mistakes" and any("side by side" in s for s in ss)
    )
    assert (
        side_by_side["id"] == "M_NOCARRY" and "what_happens" in side_by_side and "can_do" not in side_by_side
    )
    line = next(st for part, st, ss in asked if part == "claims" and "skill" in st)
    assert set(line) == {"grade", "skill"} and line["skill"]["state"] in ("can_do", "nearly", "improving")
    summary = next(st for part, st, ss in asked if part == "claims" and "skill" not in st)
    assert summary == R.told(c["facts"])
    every = [s for _, _, ss in asked for s in ss]
    assert all(s in json.dumps(c["draft"], ensure_ascii=False) for s in every)
    assert sum(len(R.split(t)) for t in R.texts(c["draft"])) == len(every)


def test_what_jev_is_sure_is_wrong_goes_back_and_what_it_is_sure_is_right_passes(bars):
    """Nimish: "I really want to integrate Jev as much as possible in all the use cases". "Has also improved at
    subtraction" of a child with no subtraction in the facts: Jev is sure it is wrong, and nothing else is asked."""
    c = _case("e7")
    bad = c["bad"][0]
    ask, asked = _jev(lambda s: 0.03 if bad in s else 0.95)

    def model(*a, **k):
        raise AssertionError("the model reads nothing when Jev is sure of every sentence")

    got = R.findings(None, c["facts"], c["draft"], ask=model, version=2, jev_ask=ask, jev_version=1)
    assert [q for q, _ in got] == [bad] and "Jev" in got[0][1]
    assert {p for p, _, _ in asked} == {f"{R.PURPOSE}.{part}" for part in R.PARTS}


def test_only_what_jev_is_unsure_of_is_read_by_the_model(bars):
    """Nimish: "to make it efficient, cost-light". The kite question on a child's report where no question is about
    kites: Jev is unsure (0.23 measured), so the model reads that one sentence, and nothing else of the draft."""
    c = _case("e10")
    bad = c["bad"][0]
    ask, _ = _jev(lambda s: 0.3 if bad in s else 0.95)
    read = []

    def model(conn, purpose, variables, meta=None, version=None):
        read.append(variables["draft"])
        flag = bad in json.dumps(variables["draft"], ensure_ascii=False)
        return {"unsupported": [{"quote": bad, "why": "no question about kites"}] if flag else []}

    seen = {}
    got = R.findings(
        None, c["facts"], c["draft"], ask=model, version=2, jev_ask=ask, jev_version=1, seen=seen
    )
    assert [q for q, _ in got] == [bad]
    shown = [s for d in read for t in R.texts(d) for s in R.split(t)]
    assert len(read) == 1 and len(shown) == 1 and bad in shown[0]
    assert seen["read_by_model"] == 1 and seen["sentences"] > 10


def test_jev_unreachable_the_model_reads_the_whole_draft_as_before(bars):
    c = _case("e10")

    def down(*a, **k):
        raise jev.JevError("no TYPESAFE_API_KEY in the engine's environment: Jev cannot be asked")

    read = []

    def model(conn, purpose, variables, meta=None, version=None):
        read.append(variables["draft"])
        return {"unsupported": []}

    assert R.findings(None, c["facts"], c["draft"], ask=model, version=2, jev_ask=down, jev_version=1) == []
    assert read == [c["draft"]]


def test_the_eval_counts_what_code_catches_first_and_what_the_model_read(bars):
    """As a report is written: code's check first (a draft it sends back is never read), then Jev, then the model. With
    Jev sure every sentence is right and no model, what is caught is what code catches: "mastered", "ready to",
    "secure", and a number the facts do not hold."""
    ask, _ = _jev(lambda s: 0.95)

    def model(*a, **k):
        raise AssertionError("nothing is unsure")

    r = R.evaluate(None, version=2, ask=model, jev_ask=ask, jev_version=1)
    assert r["by_code"] == r["caught"] >= 4 and r["false_flags"] == 0
    assert r["read_by_model"] == 0 and r["sentences"] > 200


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
def test_with_nothing_switched_on_nothing_reads_a_report():
    """Rule 7: a reader is used on a school's reports only once its version is scored and switched on. As seeded, the
    model's two versions and Jev's three questions are all off: nothing is asked."""
    c = _case("e7")

    def boom(*a, **k):
        raise AssertionError("asked while switched off")

    with db.connect() as conn:
        assert R.review(conn, c["facts"], c["draft"], ask=boom, jev_ask=boom) == []


def test_an_eval_that_names_jev_and_cannot_ask_it_says_so(bars):
    """As a report is written, Jev unreachable hands the draft to the model; an eval of Jev must not score that as Jev
    finding nothing (goals/j4-jev-live.yaml)."""

    def down(*a, **k):
        raise jev.JevError("no TYPESAFE_API_KEY in the engine's environment: Jev cannot be asked")

    r = R.evaluate(None, jev_ask=down, jev_version=1)
    assert r["unanswered"] > 0 and "TYPESAFE_API_KEY" in r["error"]
