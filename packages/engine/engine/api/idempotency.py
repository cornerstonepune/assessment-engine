"""Runs a route's side-effecting call at most once per (tenant, flow, key). The unique index
`flow_run_idempotency_idx` is the single source of truth for "has this already happened" — this
module never trusts an in-memory check, because n8n or a retried HTTP request can arrive from a
second process at any moment.

Three outcomes for a key already on record:
- `ok`      → the stored result is returned; fn() does not run again.
- `error`   → the previous attempt failed; this call reclaims the row and retries fn().
- `running` → another call is still in flight; this call refuses rather than running twice.
"""
import hashlib
import json


class InProgress(RuntimeError):
    """Another call with the same idempotency key has not finished yet."""


def derive_key(body: dict) -> str:
    """A deterministic key for a caller that sent no Idempotency-Key header — the same body
    produces the same key, so a retry without the header still dedupes."""
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def run_idempotent(conn, tenant_id, flow: str, key: str, request: dict, fn):
    """fn takes no arguments and returns a jsonb-serialisable dict — ids and counts only (rule 6).
    Returns (result, already) where `already` is True when a stored result was returned instead
    of running fn()."""
    claimed = conn.execute(
        "insert into flow_run (tenant_id, flow, trigger, idempotency_key, request, status)"
        " values (%s,%s,'http',%s,%s,'running')"
        " on conflict (tenant_id, flow, idempotency_key) where (idempotency_key is not null) do nothing"
        " returning id",
        (tenant_id, flow, key, json.dumps(request)),
    ).fetchone()

    if claimed is None:
        run_id = _reclaim_or_return(conn, tenant_id, flow, key, request)
        if run_id is None:
            existing = conn.execute(
                "select result from flow_run where tenant_id = %s and flow = %s and idempotency_key = %s",
                (tenant_id, flow, key)).fetchone()
            return existing["result"], True
    else:
        run_id = claimed["id"]

    try:
        result = fn()
    except Exception as e:
        conn.execute(
            "update flow_run set status = 'error', error = %s, finished_at = clock_timestamp() where id = %s",
            (str(e), run_id))
        raise
    conn.execute(
        "update flow_run set status = 'ok', result = %s, finished_at = clock_timestamp() where id = %s",
        (json.dumps(result), run_id))
    return result, False


def _reclaim_or_return(conn, tenant_id, flow, key, request):
    """Called only when our own insert lost the race. Returns a run id to claim and retry
    (the existing row was 'error'), or None (the caller should return its stored 'ok' result —
    or, in the rare case a second retry raced this one and neither reclaimed it, recurse once
    more, which resolves to 'running' → InProgress, never a silent double run)."""
    existing = conn.execute(
        "select id, status from flow_run where tenant_id = %s and flow = %s and idempotency_key = %s",
        (tenant_id, flow, key)).fetchone()
    if existing["status"] == "ok":
        return None
    if existing["status"] == "running":
        raise InProgress(f"{flow} with key {key!r} is already in progress")
    reclaimed = conn.execute(
        "update flow_run set status = 'running', started_at = clock_timestamp(),"
        " finished_at = null, error = null, request = %s"
        " where id = %s and status = 'error' returning id",
        (json.dumps(request), existing["id"])).fetchone()
    if reclaimed is None:
        return _reclaim_or_return(conn, tenant_id, flow, key, request)
    return reclaimed["id"]
