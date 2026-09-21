"""The single database entry point. Nothing else in the engine opens a connection."""

import os
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


def _repo_root_for(this_file: Path) -> Path:
    """Four levels above .../assessment-engine/packages/engine/engine/db.py is the monorepo
    root. The Docker image copies only `engine/` (Dockerfile: COPY engine ./engine), so inside a
    container this file has nothing four levels above it — fall back to its grandparent rather
    than crash at import time. There is no repo .env to read in a container either way; the
    platform injects DATABASE_URL etc. directly (compose.yml: env_file)."""
    parents = this_file.resolve().parents
    return parents[3] if len(parents) > 3 else this_file.resolve().parent.parent


REPO_ROOT = _repo_root_for(Path(__file__))
if (REPO_ROOT / ".env").exists():
    load_dotenv(REPO_ROOT / ".env")


def dsn() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set — copy .env.example to .env and fill it in")
    return url


def tenant_slug() -> str:
    return os.getenv("TENANT_SLUG", "cornerstone-pune")


def env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} is not set — see .env.example")
    return value


def local_copy() -> str:
    """The copy of the live database on this Mac that every test and goal scenario uses (ADR 0025,
    `bin/testdb`). An address anywhere else is refused: a test must never write to live rows."""
    url = env("TEST_DATABASE_URL")
    if urlparse(url).hostname not in ("127.0.0.1", "localhost"):
        raise RuntimeError(
            "refusing to run tests against a database that is not on this machine — "
            "TEST_DATABASE_URL must name the local copy (bin/testdb)"
        )
    return url


@contextmanager
def connect(url: str | None = None):
    with psycopg.connect(url or dsn(), row_factory=dict_row) as conn:
        yield conn


def counts(conn, tables) -> dict[str, int]:
    return {t: conn.execute(f"select count(*) as n from {t}").fetchone()["n"] for t in tables}
