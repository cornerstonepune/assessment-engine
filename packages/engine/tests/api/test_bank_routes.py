"""W1/N2 over HTTP: /bank/fill. Unlike /ingest, bank.fill is NOT naturally idempotent — a fresh
model call generates different items each time, so a retried HTTP request without this wrapper
would silently double-spend model tokens and double the bank. That is the one thing these tests
must prove beyond the generic pattern the other route tests already cover."""

import os
from collections import namedtuple

import pytest
from fastapi.testclient import TestClient

from engine import bank, db
from engine.api import deps
from engine.api.app import app

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

KEY = "test-engine-key"
HEADERS = {"X-Engine-Key": KEY}
Item = namedtuple("Item", "item_id")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def client(conn, monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", KEY)
    app.dependency_overrides[deps.get_conn] = lambda: (yield conn)
    app.dependency_overrides[deps.get_tenant_id] = lambda: conn.execute(
        "select id from tenant where slug = %s", (db.tenant_slug(),)
    ).fetchone()["id"]
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_fill_calls_bank_fill_with_the_requests_own_values(client, monkeypatch):
    seen = []
    monkeypatch.setattr(
        bank,
        "fill",
        lambda conn, code, difficulty, n: (
            seen.append((code, difficulty, n)) or ({"asked": 5, "accepted": 5}, {}, [Item("k1"), Item("k2")])
        ),
    )
    r = client.post(
        "/bank/fill", headers=HEADERS, json={"skill_set": "ADD.2D.REG", "difficulty": "Hard", "count": 5}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["accepted_item_keys"] == ["k1", "k2"]
    assert body["counts"] == {"asked": 5, "accepted": 5}
    assert seen == [("ADD.2D.REG", "Hard", 5)]


def test_a_retried_call_with_the_same_key_does_not_ask_the_model_again(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        bank, "fill", lambda conn, code, difficulty, n: calls.append(1) or ({"accepted": len(calls)}, {}, [])
    )
    body = {"skill_set": "ADD.2D.REG", "difficulty": "Hard", "count": 5}
    headers = {**HEADERS, "Idempotency-Key": "fill-1"}
    r1 = client.post("/bank/fill", headers=headers, json=body)
    r2 = client.post("/bank/fill", headers=headers, json=body)
    assert len(calls) == 1  # the model was asked once, not twice
    assert r1.json()["counts"]["accepted"] == r2.json()["counts"]["accepted"] == 1
    assert r2.json()["already"] is True


def test_a_count_of_zero_is_rejected_before_touching_the_model(client, monkeypatch):
    monkeypatch.setattr(bank, "fill", lambda *a, **k: pytest.fail("must not be called"))
    r = client.post("/bank/fill", headers=HEADERS, json={"skill_set": "X", "difficulty": "Hard", "count": 0})
    assert r.status_code == 422


def test_an_excessive_count_is_rejected_before_touching_the_model(client, monkeypatch):
    """A cap exists so a typo (or a compromised caller) can't ask for an unbounded, expensive fill
    in one call — matches the daily budget row's own spirit of a machine-checkable ceiling."""
    monkeypatch.setattr(bank, "fill", lambda *a, **k: pytest.fail("must not be called"))
    r = client.post(
        "/bank/fill", headers=HEADERS, json={"skill_set": "X", "difficulty": "Hard", "count": 10_000}
    )
    assert r.status_code == 422


def test_fill_refuses_without_the_engine_key(client, monkeypatch):
    monkeypatch.setattr(bank, "fill", lambda *a, **k: pytest.fail("must not be called"))
    r = client.post("/bank/fill", json={"skill_set": "X", "difficulty": "Hard", "count": 5})
    assert r.status_code == 401


def test_coverage_returns_every_unit_and_short_only_returns_just_the_gaps(client):
    """n8n asks the engine which units are short; the engine decides what short means, so the
    orchestrator never has to know about targets or floors (CLAUDE.md rule 3)."""
    all_rows = client.get("/bank/coverage", headers=HEADERS).json()
    short = client.get("/bank/coverage", headers=HEADERS, params={"short_only": "true"}).json()
    assert all_rows and all({"code", "difficulty", "n", "target", "shortfall"} <= r.keys() for r in all_rows)
    assert all(r["shortfall"] > 0 for r in short)
    assert len(short) <= len(all_rows)
    assert all(r["shortfall"] == max(0, r["target"] - r["n"]) for r in all_rows)


def test_coverage_refuses_without_the_engine_key(client):
    assert client.get("/bank/coverage").status_code == 401


def test_review_reports_what_a_person_must_look_at_without_retiring_anything(client, conn, monkeypatch):
    from engine import review

    monkeypatch.setattr(
        review,
        "review_unit",
        lambda conn, code, diff, reviewer: (
            [
                {"ref": "template:X:Hard", "verdict": "pass", "reasons": []},
                {"ref": "item-1", "verdict": "reject", "reasons": ["skill"]},
            ],
            {"model": "fake-model", "cost_inr": 0.1},
        ),
    )
    before = conn.execute("select count(*) as n from item where status='active'").fetchone()["n"]
    r = client.post(
        "/bank/review",
        headers=HEADERS,
        json={"skill_set": "SUB.2D.EXCH", "difficulty": "Hard", "reviewer": "pedagogy_review"},
    )
    assert r.status_code == 200
    assert (r.json()["judged"], r.json()["not_passed"]) == (2, 1)
    assert conn.execute("select count(*) as n from item where status='active'").fetchone()["n"] == before


def test_review_rejects_an_unknown_reviewer_before_spending_anything(client, monkeypatch):
    from engine import review

    monkeypatch.setattr(review, "review_unit", lambda *a, **k: pytest.fail("must not be called"))
    r = client.post(
        "/bank/review",
        headers=HEADERS,
        json={"skill_set": "SUB.2D.EXCH", "difficulty": "Hard", "reviewer": "vibes"},
    )
    assert r.status_code == 422
