"""The two reviewers (W1 gate 4, amended).

The model is faked here on purpose: what these tests must prove is the *shape* of the pass —
that it judges the band's rule once plus a bounded sample, that a verdict lands as a row a
person can act on, and that the eval actually notices disagreement. Whether Haiku has good
taste is what `engine eval pedagogy_review` measures against the gold set, live.
"""

import os

import pytest

from engine import db, review

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

SET, DIFF = "SUB.2D.EXCH", "Hard"


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def fake(verdict="pass", reasons=()):
    def generate(conn, purpose, variables, images=(), subject=None, meta=None):
        if meta is not None:
            meta.update(prompt_id=None, model="fake-model", flow_run_id=None, cost_inr=0)
        return {
            "verdicts": [
                {"ref": s["ref"], "verdict": verdict, "reasons": list(reasons), "note": ""}
                for s in variables["subjects"]
            ]
        }

    return generate


def test_a_unit_is_judged_as_its_rule_plus_a_bounded_sample_not_every_item(conn, monkeypatch):
    seen = {}

    def spy(conn, purpose, variables, images=(), subject=None, meta=None):
        seen.update(variables)
        if meta is not None:
            meta.update(model="fake-model")
        return {
            "verdicts": [{"ref": s["ref"], "verdict": "pass", "reasons": []} for s in variables["subjects"]]
        }

    monkeypatch.setattr(review.llm, "generate", spy)
    live = conn.execute(
        "select count(*) as n from item where status='active' and skill_set_code=%s and difficulty=%s",
        (SET, DIFF),
    ).fetchone()["n"]
    review.review_unit(conn, SET, DIFF, "pedagogy_review", seed=1)
    refs = [s["ref"] for s in seen["subjects"]]
    assert refs[0] == f"template:{SET}:{DIFF}", "the band's own rule is judged, once"
    items = len(refs) - 1
    assert items <= max(1, int(live * review.SAMPLE_FRACTION)), "a sample, not the whole unit"
    assert items < live, "reviewing every item is exactly the cost ADR 0010 removed"


def test_a_verdict_is_stored_as_a_row_a_person_can_act_on(conn, monkeypatch):
    monkeypatch.setattr(review.llm, "generate", fake("reject", ["skill"]))
    verdicts, _ = review.review_unit(conn, SET, DIFF, "pedagogy_review", seed=2)
    row = conn.execute(
        "select reviewer, verdict, reasons, acted_on_by from item_review where ref = %s",
        (verdicts[0]["ref"],),
    ).fetchone()
    assert (row["reviewer"], row["verdict"], row["reasons"]) == ("pedagogy_review", "reject", ["skill"])
    assert row["acted_on_by"] is None, "advisory until a person acts — never auto-applied"


def test_a_review_never_retires_an_item_by_itself(conn, monkeypatch):
    monkeypatch.setattr(review.llm, "generate", fake("reject", ["skill"]))
    before = conn.execute(
        "select count(*) as n from item where status='active' and skill_set_code=%s and difficulty=%s",
        (SET, DIFF),
    ).fetchone()["n"]
    review.review_unit(conn, SET, DIFF, "pedagogy_review", seed=3)
    after = conn.execute(
        "select count(*) as n from item where status='active' and skill_set_code=%s and difficulty=%s",
        (SET, DIFF),
    ).fetchone()["n"]
    assert after == before


def test_an_unknown_reviewer_is_refused(conn):
    with pytest.raises(ValueError, match="reviewer"):
        review.review_unit(conn, SET, DIFF, "vibes_review")


def test_the_eval_counts_agreement_and_names_what_it_disagreed_on(conn, monkeypatch):
    gold = {
        "cases": [
            {
                "ref": "a",
                "reviewer": "pedagogy_review",
                "skill_set": SET,
                "difficulty": DIFF,
                "text": "243 - 18",
                "answer": "225",
                "expected": "pass",
                "expected_reasons": [],
            },
            {
                "ref": "b",
                "reviewer": "pedagogy_review",
                "skill_set": SET,
                "difficulty": DIFF,
                "text": "243 - 18",
                "answer": "999",
                "expected": "reject",
                "expected_reasons": ["answer"],
            },
        ]
    }
    monkeypatch.setattr(review.llm, "generate", fake("pass"))  # agrees on a, misses b
    r = review.evaluate(conn, "pedagogy_review", gold)
    assert (r["cases"], r["agreed"], r["rate"]) == (2, 1, 0.5)
    assert [d["ref"] for d in r["disagreements"]] == ["b"]
    assert r["disagreements"][0]["expected"] == "reject"


def test_the_eval_separates_the_right_verdict_from_the_right_reason(conn, monkeypatch):
    gold = {
        "cases": [
            {
                "ref": "a",
                "reviewer": "language_review",
                "skill_set": SET,
                "difficulty": DIFF,
                "text": "Riya borrows 346 rupees.",
                "expected": "reject",
                "expected_reasons": ["forbidden"],
            },
        ]
    }
    monkeypatch.setattr(review.llm, "generate", fake("reject", ["age"]))  # right call, wrong reason
    r = review.evaluate(conn, "language_review", gold)
    assert r["agreed"] == 1 and r["reason_agreed"] == 0
