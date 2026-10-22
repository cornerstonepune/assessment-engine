"""FastAPI dependencies every route shares: who is calling, and a database connection scoped to
the request. One request is one transaction — every write a route and its idempotency wrapper
make lands together on success, and unwinds together on any error, exactly like `db.connect()`'s
existing commit-on-exit / rollback-on-exception behaviour already used everywhere else."""

import base64
import hashlib
import hmac
import os
import time

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


UPLOAD_LIFE_S = (
    3600  # the longest a token the site signs may live: a class's scan on a slow phone line, with room
)


def require_upload_token(x_upload_token: str = Header("")) -> str:
    """Who is putting a scan in, from the token the site signed for them (apps/web/lib/engine.ts `uploadTicket`, ADR 0092) → their
    email. The browser sends the file straight here, past Vercel's 4.5 MB limit, and must never hold ENGINE_KEY: the
    token is `<email, base64url>.<expiry, ms>.<HMAC-SHA256 of "upload." + both, keyed by ENGINE_KEY>`, so only the
    site can sign one, and it is worth nothing after its hour, and nothing as a key to any other route."""
    configured = os.environ.get("ENGINE_KEY")
    if not configured:
        raise HTTPException(status_code=500, detail="ENGINE_KEY is not configured")
    body, _, mac = x_upload_token.rpartition(".")
    who, _, expiry = body.partition(".")
    want = hmac.new(configured.encode(), f"upload.{body}".encode(), hashlib.sha256).hexdigest()
    if not (who and expiry.isdigit() and hmac.compare_digest(mac, want)):
        raise HTTPException(status_code=401, detail="this page's permission to send a scan is not the site's")
    if not 0 < int(expiry) / 1000 - time.time() <= UPLOAD_LIFE_S:
        raise HTTPException(
            status_code=401, detail="this page's permission to send a scan has run out: reload it"
        )
    return base64.urlsafe_b64decode(who + "=" * (-len(who) % 4)).decode()


def _pool_for(dsn: str) -> ConnectionPool:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(dsn, min_size=1, max_size=8, kwargs={"row_factory": dict_row})
    return _pool


def get_conn():
    """A serverless-style short-lived pool when ENGINE_POOL=1 (behind a real process manager,
    per ADR 0008); a plain connection otherwise (dev, tests) — the same serverless-vs-not split
    `engine/db.py` already makes for the app's own Postgres client. Always `Depends(get_conn, scope="function")`: it
    commits as the route returns, before the answer is sent. FastAPI closes a request-scoped one after sending, and
    the website, reading back what it had just asked for, sometimes read the row before the commit."""
    if os.environ.get("ENGINE_POOL") == "1":
        with _pool_for(db.dsn()).connection() as conn:
            yield conn
    else:
        with db.connect() as conn:
            yield conn


def get_tenant_id(conn=Depends(get_conn, scope="function")) -> str:
    return conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]


def tenant_now() -> str:
    """The tenant, on a connection held only for the question: a route that first takes minutes of upload in (ADR
    0092) must not hold one of the pool's eight connections while a phone sends a class's scan."""
    with db.connect() as conn:
        return get_tenant_id(conn)
