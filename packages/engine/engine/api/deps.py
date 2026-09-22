"""FastAPI dependencies every route shares: who is calling, and a database connection scoped to
the request. One request is one transaction — every write a route and its idempotency wrapper
make lands together on success, and unwinds together on any error, exactly like `db.connect()`'s
existing commit-on-exit / rollback-on-exception behaviour already used everywhere else."""

import os

from fastapi import Depends, Header, HTTPException
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from engine.core import db

_pool: ConnectionPool | None = None


def require_engine_key(x_engine_key: str | None = Header(None)) -> None:
    """The whole boundary between an unauthenticated caller and the database. A misconfigured
    (unset or empty) ENGINE_KEY must refuse every request, never accept one by an unset header
    matching an unset secret."""
    configured = os.environ.get("ENGINE_KEY")
    if not configured:
        raise HTTPException(status_code=500, detail="ENGINE_KEY is not configured")
    if x_engine_key != configured:
        raise HTTPException(status_code=401, detail="missing or wrong X-Engine-Key")


def _pool_for(dsn: str) -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(dsn, min_size=1, max_size=8, kwargs={"row_factory": dict_row})
    return _pool


def get_conn():
    """A serverless-style short-lived pool when ENGINE_POOL=1 (behind a real process manager,
    per ADR 0008); a plain connection otherwise (dev, tests) — the same serverless-vs-not split
    `engine/db.py` already makes for the app's own Postgres client."""
    if os.environ.get("ENGINE_POOL") == "1":
        with _pool_for(db.dsn()).connection() as conn:
            yield conn
    else:
        with db.connect() as conn:
            yield conn


def get_tenant_id(conn=Depends(get_conn)) -> str:
    return conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
