"""/children/find: the one lookup a workflow needs before it can call /ingest."""

import os

import pytest
from fastapi.testclient import TestClient

from engine import db, roster
from engine.api import deps
from engine.api.app import app

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

KEY = "test-engine-key"
HEADERS = {"X-Engine-Key": KEY}


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def client(conn, monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", KEY)
    app.dependency_overrides[deps.get_conn] = lambda: (yield conn)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_find_returns_the_child_id(client, monkeypatch):
    monkeypatch.setattr(roster, "find", lambda conn, section, name, actor: "child-123")
    r = client.post(
        "/children/find", headers=HEADERS, json={"section": "G2", "first_name": "Advika", "actor": "n8n"}
    )
    assert r.status_code == 200 and r.json() == {"child_id": "child-123"}


def test_a_name_that_does_not_resolve_uniquely_is_a_404_not_a_500(client, monkeypatch):
    def boom(conn, section, name, actor):
        raise ValueError("2 children called 'Advika' in G2")

    monkeypatch.setattr(roster, "find", boom)
    r = client.post(
        "/children/find", headers=HEADERS, json={"section": "G2", "first_name": "Advika", "actor": "n8n"}
    )
    assert r.status_code == 404
    assert "2 children" in r.json()["detail"]


def test_two_identical_lookups_both_run_and_both_log(client, monkeypatch):
    """No idempotency wrapper here on purpose: a lookup is a read, and running it twice writing
    two access_log rows is the honest, correct behaviour, not a bug to suppress."""
    calls = []
    monkeypatch.setattr(roster, "find", lambda conn, section, name, actor: calls.append(1) or "c1")
    client.post(
        "/children/find", headers=HEADERS, json={"section": "G2", "first_name": "Advika", "actor": "n8n"}
    )
    client.post(
        "/children/find", headers=HEADERS, json={"section": "G2", "first_name": "Advika", "actor": "n8n"}
    )
    assert len(calls) == 2


def test_find_refuses_without_the_engine_key(client, monkeypatch):
    monkeypatch.setattr(roster, "find", lambda *a, **k: pytest.fail("must not be called"))
    r = client.post("/children/find", json={"section": "G2", "first_name": "Advika", "actor": "n8n"})
    assert r.status_code == 401
