"""N10 over HTTP: /graph/rebuild."""
import os

import pytest
from fastapi.testclient import TestClient

from engine import db
from engine.api import deps
from engine.api.app import app
from engine.api.routes import graph as graph_route

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
    app.dependency_overrides[deps.get_tenant_id] = lambda: conn.execute(
        "select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_rebuild_calls_skill_graph_rebuild_with_the_requested_child(client, monkeypatch):
    seen = []
    monkeypatch.setattr(graph_route.skill_graph, "rebuild", lambda conn, child_id: seen.append(child_id) or 4)
    r = client.post("/graph/rebuild", headers=HEADERS, json={"child_id": "c1"})
    assert r.status_code == 200 and r.json() == {"states": 4, "already": False}
    assert seen == ["c1"]


def test_rebuild_with_no_child_id_rebuilds_everyone(client, monkeypatch):
    seen = []
    monkeypatch.setattr(graph_route.skill_graph, "rebuild", lambda conn, child_id: seen.append(child_id) or 26)
    # An explicit key, not derive_key's default from the (empty) body: an empty body is exactly
    # what a real "rebuild everyone" nightly call looks like, so relying on the derived key here
    # risks colliding with a real flow_run row already on record for this tenant — as it did once,
    # against a manually-run smoke test during this session.
    r = client.post("/graph/rebuild", headers={**HEADERS, "Idempotency-Key": "test-rebuild-everyone"}, json={})
    assert r.status_code == 200 and r.json()["states"] == 26
    assert seen == [None]


def test_two_calls_with_the_same_body_and_no_explicit_key_dedupe(client, monkeypatch):
    """No Idempotency-Key header: the fallback key is derived from the body, so an identical
    request (same or absent child_id) is treated as a retry, not a second event."""
    calls = []
    monkeypatch.setattr(graph_route.skill_graph, "rebuild", lambda conn, child_id: calls.append(1) or len(calls))
    r1 = client.post("/graph/rebuild", headers=HEADERS, json={"child_id": "c1"})
    r2 = client.post("/graph/rebuild", headers=HEADERS, json={"child_id": "c1"})
    assert len(calls) == 1
    assert r1.json()["already"] is False and r2.json()["already"] is True


def test_a_different_body_with_no_explicit_key_runs_independently(client, monkeypatch):
    calls = []
    monkeypatch.setattr(graph_route.skill_graph, "rebuild", lambda conn, child_id: calls.append(child_id) or 1)
    client.post("/graph/rebuild", headers=HEADERS, json={"child_id": "c1"})
    client.post("/graph/rebuild", headers=HEADERS, json={"child_id": "c2"})
    assert calls == ["c1", "c2"]


def test_rebuild_refuses_without_the_engine_key(client, monkeypatch):
    monkeypatch.setattr(graph_route.skill_graph, "rebuild", lambda *a, **k: pytest.fail("must not be called"))
    r = client.post("/graph/rebuild", json={"child_id": "c1"})
    assert r.status_code == 401
