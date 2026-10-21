"""Every live row onto the rehearsal's copy, counted in the snapshot it was dumped from. `engine live copy`.

The rehearsal (`.github/workflows/rehearse-update-live.yml`) once dumped live, then counted live a few minutes later
with fresh queries: on 2026-10-21 educators made 13 papers in that gap (`sheet_template` 7982 → 7995, run 39562277664)
and the rehearsal failed before testing anything. Here one read-only, repeatable-read transaction on live exports
its snapshot, `pg_dump --snapshot` dumps exactly that snapshot, and live's counts are read in the same transaction,
so they are the dump's own counts whatever is written meanwhile. The copy is then counted and every table must
match: a row missing from the copy, or one too many, still fails. Live is only read; no address is printed.
"""

import subprocess
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

import psycopg
from psycopg import sql

TABLES = "select schemaname || '.' || tablename as t from pg_tables where schemaname in ('public', 'pii') order by 1"


def _tables(conn: psycopg.Connection) -> list[str]:
    return [r[0] for r in conn.execute(TABLES)]


def counts(conn: psycopg.Connection, tables: list[str]) -> dict[str, int]:
    """Each table's row count, as `conn`'s transaction sees it."""
    out = {}
    for t in tables:
        query = sql.SQL("select count(*) from {}").format(sql.Identifier(*t.split(".", 1)))
        out[t] = conn.execute(query).fetchall()[0][0]
    return out


@contextmanager
def snapshot(url: str) -> Generator[tuple[psycopg.Connection, str], None, None]:
    """A read-only, repeatable-read transaction on `url`, held open, and the id of its exported snapshot."""
    with psycopg.connect(url) as conn:
        conn.isolation_level = psycopg.IsolationLevel.REPEATABLE_READ
        conn.read_only = True
        snap = conn.execute("select pg_export_snapshot()").fetchall()[0][0]
        try:
            yield conn, snap
        finally:
            conn.rollback()


def _run(argv: list[str], what: str) -> None:
    # The command line holds an address: on failure say which step and pg's own words, never the argv.
    done = subprocess.run(argv, capture_output=True, text=True, check=False)
    if done.returncode:
        raise RuntimeError(f"{what} failed ({done.returncode}): {done.stderr.strip()}")


def dump(url: str, snap: str, tables: list[str], path: Path) -> None:
    """Every row of `tables` exactly as snapshot `snap` holds them."""
    argv = [
        "pg_dump",
        "--dbname",
        url,
        "--snapshot",
        snap,
        "--format=custom",
        "--data-only",
        "--no-owner",
        "--no-privileges",
        f"--file={path}",
        *(f"--table={t}" for t in tables),
    ]
    _run(argv, "pg_dump")


def restore(url: str, path: Path) -> None:
    _run(
        [
            "pg_restore",
            "--data-only",
            "--disable-triggers",
            "--no-owner",
            "--no-privileges",
            "--exit-on-error",
            f"--dbname={url}",
            str(path),
        ],
        "pg_restore",
    )


def differences(live: dict[str, int], copy: dict[str, int]) -> list[str]:
    """Each table whose count on the copy is not live's, in words."""
    return [f"{t}: live {live[t]}, copy {copy.get(t)}" for t in live if copy.get(t) != live[t]]


def copy(live_url: str, copy_url: str) -> tuple[dict[str, int], list[str]]:
    """Empty the copy's tables that live also has, fill them from one snapshot of live, and compare every count with
    that snapshot's. Returns live's counts and the tables that differ (none, when the copy is whole)."""
    with psycopg.connect(copy_url, autocommit=True) as c:
        here = _tables(c)
        c.execute(
            sql.SQL("truncate table {} cascade").format(
                sql.SQL(", ").join(sql.Identifier(*t.split(".", 1)) for t in here)
            )
        )
    with snapshot(live_url) as (conn, snap), tempfile.TemporaryDirectory() as tmp:
        tables = [t for t in _tables(conn) if t in set(here)]
        path = Path(tmp) / "live.dump"
        dump(live_url, snap, tables, path)
        live = counts(conn, tables)
        restore(copy_url, path)
    with psycopg.connect(copy_url) as c:
        return live, differences(live, counts(c, tables))
