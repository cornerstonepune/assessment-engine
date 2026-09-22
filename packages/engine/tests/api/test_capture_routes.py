"""N3/N9 over HTTP: /ingest, /mark, /commit. Each test proves three things a shallow "assert 200"
would miss: the route calls the real engine function with the request's own values (not a typo'd
argument order), a repeat with the same Idempotency-Key does not call it twice, and the route is
actually behind the auth dependency rather than merely defining one nobody attached."""

import os

import pytest
from fastapi.testclient import TestClient

from engine.api import deps
from engine.api.app import app
from engine.core import db
from engine.w3_read import legacy, marking

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
        "select id from tenant where slug = %s", (db.tenant_slug(),)
    ).fetchone()["id"]
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---- /ingest


def test_ingest_calls_import_scan_with_the_requests_own_values(client, monkeypatch):
    seen = []
    monkeypatch.setattr(
        legacy,
        "import_scan",
        lambda conn, path, paper, child, actor, pages=None, masks=None, narrative=False: (
            seen.append((path, paper, child, actor, pages, masks, narrative))
            or {"capture_id": "cap-1", "pages": 2, "results": [1, 2], "unmatched": [], "notes": []}
        ),
    )
    r = client.post(
        "/ingest",
        headers=HEADERS,
        json={
            "path": "/scans/a.pdf",
            "paper_code": "P1",
            "child_id": "c1",
            "actor": "aseem",
            "pages": [1, 2],
            "masks": {"1": 0.2},
            "narrative": True,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body == {
        "capture_id": "cap-1",
        "pages": 2,
        "n_results": 2,
        "n_unmatched": 0,
        "n_notes": 0,
        "already": False,
    }
    assert seen == [("/scans/a.pdf", "P1", "c1", "aseem", [1, 2], {1: 0.2}, True)]


def test_ingest_with_the_same_idempotency_key_does_not_call_import_scan_again(client, monkeypatch):
    calls = []
    monkeypatch.setattr(
        legacy,
        "import_scan",
        lambda conn, *a, **k: (
            calls.append(1)
            or {"capture_id": "cap-2", "pages": 1, "results": [], "unmatched": [], "notes": []}
        ),
    )
    body = {"path": "/scans/b.pdf", "paper_code": "P1", "child_id": "c1", "actor": "aseem"}
    headers = {**HEADERS, "Idempotency-Key": "same-key"}

    first = client.post("/ingest", headers=headers, json=body)
    second = client.post("/ingest", headers=headers, json=body)

    assert len(calls) == 1
    assert first.json()["already"] is False
    assert second.json()["already"] is True
    assert second.json()["capture_id"] == first.json()["capture_id"]


def test_ingest_a_call_already_in_flight_is_a_409_not_an_unhandled_500(client, conn, monkeypatch):
    """test_idempotency.py proves run_idempotent raises InProgress; this proves that exception
    actually reaches the caller as a clean 409 through the real FastAPI exception-handling path,
    not a stack trace — the two are not the same claim, and only one of them was tested before."""
    tenant_id = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    conn.execute(
        "insert into flow_run (tenant_id, flow, trigger, idempotency_key, status)"
        " values (%s,'ingest','http','stuck','running')",
        (tenant_id,),
    )
    monkeypatch.setattr(legacy, "import_scan", lambda *a, **k: pytest.fail("must not be called"))

    r = client.post(
        "/ingest",
        headers={**HEADERS, "Idempotency-Key": "stuck"},
        json={
            "path": "/scans/c.pdf",
            "paper_code": "P1",
            "child_id": "c1",
            "actor": "aseem",
        },
    )

    assert r.status_code == 409
    assert "stuck" in r.json()["detail"]


def test_ingest_refuses_without_the_engine_key(client, monkeypatch):
    monkeypatch.setattr(legacy, "import_scan", lambda *a, **k: pytest.fail("must not be called"))
    r = client.post("/ingest", json={"path": "x", "paper_code": "P1", "child_id": "c1", "actor": "a"})
    assert r.status_code == 401


def test_ingest_rejects_a_malformed_body_before_touching_the_database(client, monkeypatch):
    monkeypatch.setattr(legacy, "import_scan", lambda *a, **k: pytest.fail("must not be called"))
    r = client.post("/ingest", headers=HEADERS, json={"path": "x"})  # missing required fields
    assert r.status_code == 422


# ---- /mark


def test_mark_calls_remark_for_the_requested_child(client, monkeypatch):
    seen = []
    monkeypatch.setattr(marking, "remark", lambda conn, child_id: seen.append(child_id) or 3)
    r = client.post("/mark", headers=HEADERS, json={"child_id": "c9"})
    assert r.status_code == 200 and r.json() == {"changed": 3, "already": False}
    assert seen == ["c9"]


def test_mark_with_the_same_key_does_not_remark_twice(client, monkeypatch):
    calls = []
    monkeypatch.setattr(marking, "remark", lambda conn, child_id: calls.append(1) or len(calls))
    headers = {**HEADERS, "Idempotency-Key": "mk1"}
    client.post("/mark", headers=headers, json={"child_id": "c9"})
    r2 = client.post("/mark", headers=headers, json={"child_id": "c9"})
    assert len(calls) == 1
    assert r2.json()["already"] is True


# ---- /commit


def test_commit_calls_confirm_with_child_and_actor(client, monkeypatch):
    seen = []
    monkeypatch.setattr(marking, "confirm", lambda conn, child_id, by: seen.append((child_id, by)) or 5)
    r = client.post("/commit", headers=HEADERS, json={"child_id": "c1", "by": "aseem"})
    assert r.status_code == 200 and r.json() == {"confirmed": 5, "already": False}
    assert seen == [("c1", "aseem")]


def test_commit_with_the_same_key_does_not_confirm_twice(client, monkeypatch):
    calls = []
    monkeypatch.setattr(marking, "confirm", lambda conn, child_id, by: calls.append(1) or len(calls))
    headers = {**HEADERS, "Idempotency-Key": "cm1"}
    client.post("/commit", headers=headers, json={"child_id": "c1", "by": "aseem"})
    r2 = client.post("/commit", headers=headers, json={"child_id": "c1", "by": "aseem"})
    assert len(calls) == 1
    assert r2.json()["already"] is True


def test_commit_a_different_child_with_the_same_explicit_key_still_only_runs_once_per_key(
    client, monkeypatch
):
    """Documents the actual contract: the key, not the body, is the identity. A caller that reuses
    a key across genuinely different requests gets the first request's result — this is why every
    route derives its default key from the body, and why a caller supplying its own key is
    responsible for making it unique per real event."""
    calls = []
    monkeypatch.setattr(marking, "confirm", lambda conn, child_id, by: calls.append(child_id) or len(calls))
    headers = {**HEADERS, "Idempotency-Key": "reused"}
    r1 = client.post("/commit", headers=headers, json={"child_id": "c1", "by": "aseem"})
    r2 = client.post("/commit", headers=headers, json={"child_id": "c2", "by": "aseem"})
    assert calls == ["c1"]  # c2 never reached confirm()
    assert r1.json()["already"] is False and r2.json()["already"] is True
    assert r2.json()["confirmed"] == r1.json()["confirmed"] == 1  # c2's request got c1's stored result
