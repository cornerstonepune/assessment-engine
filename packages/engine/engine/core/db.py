"""The single database entry point. Nothing else in the engine opens a connection."""

import os
from collections.abc import Generator, Iterable
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

import psycopg
from dotenv import load_dotenv
from psycopg import sql
from psycopg.abc import Params, QueryNoTemplate
from psycopg.rows import DictRow, dict_row


def _repo_root_for(this_file: Path) -> Path:
    """Five levels above .../assessment-engine/packages/engine/engine/core/db.py is the monorepo
    root. The Docker image copies only `engine/` (Dockerfile: COPY engine ./engine), so inside a
    container this file has nothing five levels above it — fall back to the folder that holds
    `engine/` rather than crash at import time. There is no repo .env to read in a container either
    way; the platform injects DATABASE_URL etc. directly (compose.yml: env_file)."""
    parents = this_file.resolve().parents
    return parents[4] if len(parents) > 4 else parents[min(2, len(parents) - 1)]


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


Conn = psycopg.Connection[DictRow]
"""The one kind of connection the engine opens: each row a dict by column name."""
Id = UUID | str
"""A row's id: a UUID as psycopg reads one, or its text as a caller sends it; Postgres takes either."""


@contextmanager
def connect(url: str | None = None) -> Generator[Conn, None, None]:
    # `psycopg.connect` is typed for tuple rows whatever factory it is handed; the class named with its row type
    # says what `dict_row` makes, so every `row["id"]` downstream is checked against a dict, not a tuple.
    with Conn.connect(url or dsn(), row_factory=dict_row) as conn:
        yield conn


def one(conn: Conn, query: QueryNoTemplate, params: Params | None = None) -> DictRow:
    """The row a query must return. A query that returns none here is a defect, and says which query it was rather
    than failing later as "None is not subscriptable"."""
    row = conn.execute(query, params).fetchone()
    if row is None:
        raise LookupError(f"no row where one must be: {query!r}")
    return row


def counts(conn: Conn, tables: Iterable[str]) -> dict[str, int]:
    """→ each table's rows; a table named `schema.table` is quoted as two names."""
    each = sql.SQL("select count(*) as n from {}")
    return {t: one(conn, each.format(sql.Identifier(*t.split("."))))["n"] for t in tables}
