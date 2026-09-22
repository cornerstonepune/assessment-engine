"""The skill-set spec: ratification, and the mistake list's two halves.

The model is replaced by a fake throughout. What is tested here is the half code owns — which
named mistakes a band's own numbers can reach — and the checks every model proposal passes through
before anything is stored.
"""

import os

import pytest

from engine import db, spec
from engine.assess import bands
from engine.assess import misconceptions as M

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

SET = "SUB.2D.EXCH"
PREDICTOR_CODES = {c for table in (M.ADD_PREDICTORS, M.SUB_PREDICTORS, M.MULTI_PREDICTORS) for c in table}


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def fake_mistakes(mistakes):
    def generate(conn, purpose, variables, images=(), subject=None, meta=None):
        assert purpose == "misconception_list" and variables["bands"]["Hard"]
        assert variables["already_covered"], "the prompt is told what code has already covered"
        if meta is not None:
            meta.update(prompt_id=None, model="fake-model", cost_inr=0)
        return {"mistakes": mistakes}

    return generate


def mistake(name, a, b, writes, visible="answer_lookup", correct=None):
    return {
        "name": name,
        "how_it_goes": "the child follows this rule every time",
        "example": {
            "numbers": [a, b],
            "op": "-",
            "child_writes": writes,
            "correct_answer": a - b if correct is None else correct,
        },
        "repair_hint": "rods",
        "visible_in": visible,
    }


# ── the half code owns ────────────────────────────────────────────────────────────────────────


def test_a_bands_numbers_obey_its_rule(conn):
    check = {"op": "-", "digits": [3, 2], "regroups": [1]}  # SUB.2D.EXCH Hard's rule before step 8h
    pairs = bands.pairs(check, 30)
    assert len(pairs) == 30
    assert all(op == "-" and a > b and len(str(a)) == 3 and len(str(b)) == 2 for op, a, b in pairs)


def test_code_finds_every_computable_mistake_a_curated_list_names(conn):
    """The recall a prompt was being scored on is a property of arithmetic, so code owns it: for
    every skill set whose bands have numbers, what the predictors reach must include every code a
    person curated that a predictor can produce at all."""
    rows = conn.execute("select code, misconception_codes as curated from skill_set order by code").fetchall()
    checked = 0
    for r in rows:
        covered = set(c for cs in spec.known_misconceptions(conn, r["code"], 40).values() for c in cs)
        if not covered:
            continue  # a native-generator set: no numbers to sample, nothing for code to claim
        checked += 1
        want = set(r["curated"]) & PREDICTOR_CODES
        assert want <= covered, f"{r['code']}: code missed {sorted(want - covered)}"
    assert checked >= 10, "most of the ladder has numbers; if not, this test stopped testing anything"


def test_a_band_that_forbids_exchange_reaches_no_exchange_mistake(conn):
    no_reg = {"op": "-", "digits": [2, 2], "regroups": [0]}
    assert "M_NO_DECREMENT" not in M.applicable(bands.pairs(no_reg, 40))
    with_reg = {"op": "-", "digits": [2, 2], "regroups": [1]}
    assert "M_NO_DECREMENT" in M.applicable(bands.pairs(with_reg, 40))


# ── the checks every proposal passes ──────────────────────────────────────────────────────────


def test_a_proposal_an_existing_predictor_reproduces_is_that_misconception(conn, monkeypatch):
    """The vocabulary must not grow a second name for a wrong path it already has: 62 - 27 written
    as 45 is what the predictors compute, whatever the model chose to call it. Two structural
    methods land there and both are kept — the answer alone cannot separate them, the working does.
    A fact slip lands there too and is left out."""
    monkeypatch.setattr(
        spec.llm, "generate", fake_mistakes([mistake("Takes the small digit from the big one", 62, 27, 45)])
    )
    (p,) = spec.propose_misconceptions(conn, SET, apply=True)["proposals"]
    assert p["matches"] == ["M_NO_DECREMENT", "M_SMALL_FROM_LARGE"]
    assert (
        conn.execute("select count(*) as n from misconception where code = %s", (p["code"],)).fetchone()["n"]
        == 0
    ), "nothing new was invented"


def test_a_proposal_whose_own_arithmetic_is_wrong_is_dropped(conn, monkeypatch):
    monkeypatch.setattr(
        spec.llm, "generate", fake_mistakes([mistake("Cannot subtract", 62, 27, 45, correct=34)])
    )
    (p,) = spec.propose_misconceptions(conn, SET, apply=True)["proposals"]
    assert p["dropped"] and "is 35" in p["dropped"]
    assert (
        conn.execute("select count(*) as n from misconception where code = %s", (p["code"],)).fetchone()["n"]
        == 0
    )


def test_a_proposal_whose_example_is_the_right_answer_is_dropped(conn, monkeypatch):
    monkeypatch.setattr(spec.llm, "generate", fake_mistakes([mistake("Not a mistake at all", 62, 27, 35)]))
    (p,) = spec.propose_misconceptions(conn, SET, apply=True)["proposals"]
    assert p["dropped"] == "its example's wrong answer is the right answer"


def test_an_answer_only_claim_code_cannot_reproduce_is_downgraded_not_trusted(conn, monkeypatch):
    """A wrong answer nothing computes cannot be marked from the answer alone, whatever the model
    claims — so the claim drops to the written working instead of being stored as if a marker
    could act on it."""
    monkeypatch.setattr(
        spec.llm, "generate", fake_mistakes([mistake("Writes the answer backwards", 62, 27, 53)])
    )
    (p,) = spec.propose_misconceptions(conn, SET, apply=True)["proposals"]
    assert p["matches"] == [] and p["downgraded"] and p["visible_in"] == "working"
    row = conn.execute(
        "select op, detectable_by, source, description from misconception where code = %s", (p["code"],)
    ).fetchone()
    assert (row["op"], row["detectable_by"]) == ("-", "working")
    assert "misconception_list" in row["source"] and "fake-model" in row["source"]
    assert p["downgraded"] in row["description"], "why it was downgraded is stored with it"


def test_applying_unions_and_withdraws_the_signature(conn, monkeypatch):
    conn.execute("update skill_set set status = 'ratified', ratified_by = 'a test' where code = %s", (SET,))
    before = set(
        conn.execute("select misconception_codes as c from skill_set where code = %s", (SET,)).fetchone()["c"]
    )
    monkeypatch.setattr(
        spec.llm, "generate", fake_mistakes([mistake("Only in the working", 62, 27, 53, "working")])
    )
    r = spec.propose_misconceptions(conn, SET, apply=True)
    after = set(
        conn.execute("select misconception_codes as c from skill_set where code = %s", (SET,)).fetchone()["c"]
    )
    assert before <= after, "a curated code can never be dropped by a model's omission"
    assert set(r["covered"]) <= after, "what code computed is attached too"
    row = conn.execute("select status, ratified_by from skill_set where code = %s", (SET,)).fetchone()
    assert (row["status"], row["ratified_by"]) == ("draft", None), "a changed list needs a new signature"


def test_ratify_signs_every_draft_with_a_name_and_never_signs_one_twice(conn):
    """W1 gate 1. Only this one row is put back to draft: the all-drafts branch is proved by it
    being the only row the bulk call returns, never by rewriting the live ratifications."""
    conn.execute("update skill_set set status = 'draft', ratified_by = null where code = %s", (SET,))
    assert SET in [r["code"] for r in spec.ratify(conn, "a test")], "the bulk call takes every draft"
    assert conn.execute("select count(*) as n from skill_set where status = 'draft'").fetchone()["n"] == 0
    assert spec.ratify(conn, "a test") == [], "and an already-ratified row is not signed again"
    row = conn.execute("select status, ratified_by from skill_set where code = %s", (SET,)).fetchone()
    assert (row["status"], row["ratified_by"]) == ("ratified", "a test")


def test_a_reasoning_mistake_needs_no_arithmetic_and_is_not_asked_for_any(conn, monkeypatch):
    """A mistake in how a child justifies a claim has no wrong number. Earlier prompt versions had
    to invent one and three in five were thrown away for arithmetic that was never the point."""
    monkeypatch.setattr(
        spec.llm,
        "generate",
        fake_mistakes(
            [
                {
                    "name": "Checks one case and calls the claim proved",
                    "how_it_goes": "one example is a proof",
                    "family": "F",
                    "repair_hint": "ask for a counter-example",
                    "visible_in": "answer_lookup",
                }
            ]
        ),
    )
    (p,) = spec.propose_misconceptions(conn, SET, apply=True)["proposals"]
    assert p["dropped"] is None and p["matches"] == []
    assert p["visible_in"] == "explanation" and p["downgraded"], "an answer-only claim with no answer"
    row = conn.execute("select op, detectable_by from misconception where code = %s", (p["code"],)).fetchone()
    assert (row["op"], row["detectable_by"]) == ("any", "explanation")


# ---- a skill is stated as what the child can do (goals/s2-skill-map-outcomes.yaml)


def test_an_outcome_that_starts_with_what_the_child_does_passes():
    assert (
        spec.outcome_problems(
            "Adds numbers in columns, regrouping ten ones into a ten exactly when a column adds up to ten or more."
        )
        == []
    )


def test_a_topic_label_is_not_an_outcome():
    problems = spec.outcome_problems("2-digit addition with regrouping")
    assert any("what the child does" in p for p in problems)
    assert any("words" in p for p in problems)


def test_an_outcome_is_one_sentence_without_codes_or_jargon():
    assert any("one sentence" in p for p in spec.outcome_problems("Adds within 10. Reads = as balance."))
    assert any(
        "code" in p
        for p in spec.outcome_problems("Adds two numbers as rung R5 of ADD.2D.REG requires them to.")
    )
    assert any(
        "planted" in p
        for p in spec.outcome_problems(
            "Reads a worked column calculation with one planted, named misconception and writes the correct answer."
        )
    )
    assert any(
        "borrow" in p
        for p in spec.outcome_problems("Subtracts two numbers in columns and will borrow a ten when needed.")
    )
