"""The single database entry point. Nothing else in the engine opens a connection."""
import os
from contextlib import contextmanager
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

REPO_ROOT = Path(__file__).resolve().parents[3]
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


@contextmanager
def connect():
    with psycopg.connect(dsn(), row_factory=dict_row) as conn:
        yield conn


def counts(conn, tables) -> dict[str, int]:
    return {t: conn.execute(f"select count(*) as n from {t}").fetchone()["n"] for t in tables}
