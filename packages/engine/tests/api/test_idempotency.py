"""The idempotency wrapper is the one piece every HTTP route depends on. It must:
- never run a side-effecting call twice for the same (tenant, flow, key)
- not get permanently stuck after a failure — a retry with the same key must actually retry
- refuse rather than double-run when a duplicate request arrives while the first is still in
  flight (a genuine concurrent duplicate, simulated by a row left `running`)
- dedupe even when the caller sent no Idempotency-Key header, by deriving one from the body

All of it is tested against the real database: the partial unique index this leans on
(`flow_run_idempotency_idx`) is Postgres behaviour a fake connection cannot stand in for.
"""
import os

import pytest

from engine import db
from engine.api.idempotency import InProgress, derive_key, run_idempotent

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def tenant(conn):
    return conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]


def counter():
    calls = []
    return calls, lambda: (calls.append(1), {"n": len(calls)})[1]


def test_the_first_call_runs_the_function_once_and_stores_the_result(conn, tenant):
    calls, fn = counter()
    result, already = run_idempotent(conn, tenant, "test_flow", "k1", {"a": 1}, fn)
    assert result == {"n": 1} and already is False
    assert len(calls) == 1


def test_a_repeat_of_the_same_key_returns_the_stored_result_without_running_again(conn, tenant):
    calls, fn = counter()
    first, _ = run_idempotent(conn, tenant, "test_flow", "k2", {}, fn)
    second, already = run_idempotent(conn, tenant, "test_flow", "k2", {}, fn)
    assert len(calls) == 1  # fn ran exactly once
    assert second == first == {"n": 1}
    assert already is True


def test_a_different_key_runs_independently(conn, tenant):
    calls, fn = counter()
    run_idempotent(conn, tenant, "test_flow", "k3a", {}, fn)
    run_idempotent(conn, tenant, "test_flow", "k3b", {}, fn)
    assert len(calls) == 2


def test_the_same_key_under_a_different_flow_runs_independently(conn, tenant):
    """A key is scoped to its flow: /ingest and /mark reusing the same derived key (same ids)
    must not collide."""
    calls, fn = counter()
    run_idempotent(conn, tenant, "flow_a", "same_key", {}, fn)
    run_idempotent(conn, tenant, "flow_b", "same_key", {}, fn)
    assert len(calls) == 2


def test_an_exception_marks_the_row_error_and_is_reraised(conn, tenant):
    def boom():
        raise ValueError("model is down")

    with pytest.raises(ValueError, match="model is down"):
        run_idempotent(conn, tenant, "test_flow", "k4", {}, boom)

    row = conn.execute(
        "select status, error from flow_run where tenant_id = %s and flow = 'test_flow'"
        " and idempotency_key = 'k4'", (tenant,)).fetchone()
    assert row["status"] == "error"
    assert "model is down" in row["error"]


def test_a_failed_call_can_be_retried_with_the_same_key(conn, tenant):
    attempts = []

    def flaky():
        attempts.append(1)
        if len(attempts) == 1:
            raise ValueError("transient")
        return {"ok": True}

    with pytest.raises(ValueError):
        run_idempotent(conn, tenant, "test_flow", "k5", {}, flaky)

    result, already = run_idempotent(conn, tenant, "test_flow", "k5", {}, flaky)

    assert len(attempts) == 2  # the retry actually ran fn again — not permanently poisoned
    assert result == {"ok": True} and already is False


def test_a_call_still_in_flight_refuses_rather_than_running_twice(conn, tenant):
    # Simulates a concurrent duplicate request: a row already claimed and still 'running'.
    conn.execute(
        "insert into flow_run (tenant_id, flow, trigger, idempotency_key, status)"
        " values (%s,'test_flow','http','k6','running')", (tenant,))
    calls, fn = counter()

    with pytest.raises(InProgress, match="k6"):
        run_idempotent(conn, tenant, "test_flow", "k6", {}, fn)

    assert calls == []  # fn was never called


def test_no_header_key_is_derived_deterministically_from_the_request_body(conn, tenant):
    key_a = derive_key({"child_id": "c1", "paper": "P1"})
    key_b = derive_key({"paper": "P1", "child_id": "c1"})  # field order must not matter
    key_c = derive_key({"child_id": "c2", "paper": "P1"})  # different content, different key
    assert key_a == key_b
    assert key_a != key_c

    calls, fn = counter()
    run_idempotent(conn, tenant, "test_flow", key_a, {}, fn)
    run_idempotent(conn, tenant, "test_flow", key_b, {}, fn)  # same derived key: same effect
    assert len(calls) == 1
