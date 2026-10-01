"""/health (no key, no auth — a container or n8n polls it before anything is configured) and
/runs/{id} (a coordinator's or n8n's window into what one flow_run actually did). Both are pure
reads, tested against a real row rather than a mock — there is no domain function to fake here."""

import os

import pytest
from fastapi.testclient import TestClient

from engine.api import deps
from engine.api.app import app
from engine.api.routes import runs
from engine.core import db

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

KEY = "test-engine-key"
HEADERS = {"X-Engine-Key": KEY}


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def tenant(conn):
    return conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]


@pytest.fixture
def client(conn, monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", KEY)
    app.dependency_overrides[deps.get_conn] = lambda: (yield conn)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health_needs_no_key_and_confirms_real_database_connectivity(client):
    r = client.get("/health")
    assert r.status_code == 200 and r.json() == {"ok": True}


def test_a_known_run_is_returned_with_its_cost_and_status(client, conn, tenant):
    row = conn.execute(
        "insert into flow_run (tenant_id, flow, trigger, status, tokens, cost_inr)"
        " values (%s,'read_cells','engine','ok',1234,0.5432) returning id",
        (tenant,),
    ).fetchone()
    r = client.get(f"/runs/{row['id']}", headers=HEADERS)
    assert r.status_code == 200
    body = r.json()
    assert body["flow"] == "read_cells" and body["status"] == "ok"
    assert body["tokens"] == 1234 and body["cost_inr"] == 0.5432


def test_an_unknown_run_is_a_404(client):
    r = client.get("/runs/00000000-0000-0000-0000-000000000000", headers=HEADERS)
    assert r.status_code == 404


def test_runs_refuses_without_the_engine_key(client, conn, tenant):
    row = conn.execute(
        "insert into flow_run (tenant_id, flow, trigger, status) values (%s,'x','engine','ok') returning id",
        (tenant,),
    ).fetchone()
    r = client.get(f"/runs/{row['id']}")
    assert r.status_code == 401


def test_a_run_the_engine_was_killed_under_says_so_when_it_starts_again(monkeypatch):
    """2026-09-25 and 26: two readings died under a deploy and said "running" until someone looked. A parent report
    being written dies the same way, so every flow's runs are marked (goals/p2-live-recovers.yaml)."""
    seen = []

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            pass

        def execute(self, sql, params=None):
            seen.append((sql, params))
            return type("R", (), {"rowcount": 2})()

    monkeypatch.setattr(runs.db, "connect", lambda *a, **k: _Conn())
    assert runs.orphaned() == 2
    [(sql, params)] = seen
    assert "status = 'error'" in sql and sql.endswith("where status = 'running'") and params is None
