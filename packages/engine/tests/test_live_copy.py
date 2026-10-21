"""`engine live copy`: live's counts are read in the snapshot the dump came from, so educators making papers while the
rehearsal copies live cannot fail it (run 39562277664: `sheet_template` 7982 → 7995 between the dump and the count),
and a copy short of a row, or holding one too many, still fails. Two scratch databases on the test server stand in
for live and its copy."""

import os
import uuid
from urllib.parse import urlparse, urlunparse

import psycopg
import pytest

from engine.checks import live_copy

ROWS = 5


def _url(name):
    return urlunparse(urlparse(os.environ["DATABASE_URL"])._replace(path=f"/{name}"))


@pytest.fixture
def pair():
    names = [f"live_copy_{w}_{uuid.uuid4().hex[:8]}" for w in ("live", "copy")]
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as admin:
        for n in names:
            admin.execute(f"create database {n}")
    urls = [_url(n) for n in names]
    for i, u in enumerate(urls):
        with psycopg.connect(u, autocommit=True) as c:
            c.execute("create schema pii; create table public.sheet_template (id int primary key)")
            c.execute("create table pii.child_name (id int primary key)")
            if i == 0:
                c.execute(f"insert into public.sheet_template select generate_series(1, {ROWS})")
                c.execute("insert into pii.child_name values (1)")
    yield urls
    with psycopg.connect(os.environ["DATABASE_URL"], autocommit=True) as admin:
        for n in names:
            admin.execute(f"drop database {n} with (force)")


def _sql(url, statement):
    with psycopg.connect(url, autocommit=True) as c:
        c.execute(statement)


def _restore_then(monkeypatch, before=None, after=None):
    """Run `before` and `after` around the real restore: the gap between live's dump and the comparison."""
    real = live_copy.restore

    def restore(url, path):
        if before:
            before()
        real(url, path)
        if after:
            after()

    monkeypatch.setattr(live_copy, "restore", restore)


def _count(url):
    with psycopg.connect(url) as c:
        return c.execute("select count(*) from sheet_template").fetchone()[0]


def test_a_paper_made_while_the_copy_is_made_does_not_fail_it(pair, monkeypatch):
    live, copy = pair
    _restore_then(monkeypatch, before=lambda: _sql(live, "insert into sheet_template values (99)"))
    counts, wrong = live_copy.copy(live, copy)
    assert _count(live) == ROWS + 1, "an educator's new paper reached live after the dump"
    assert counts["public.sheet_template"] == ROWS == _count(copy), "live counted as the dump saw it"
    assert counts["pii.child_name"] == 1
    assert wrong == []


def test_a_row_missing_from_the_copy_still_fails(pair, monkeypatch):
    live, copy = pair
    _restore_then(monkeypatch, after=lambda: _sql(copy, "delete from sheet_template where id = 1"))
    _, wrong = live_copy.copy(live, copy)
    assert wrong == [f"public.sheet_template: live {ROWS}, copy {ROWS - 1}"]


def test_an_extra_row_on_the_copy_still_fails(pair, monkeypatch):
    live, copy = pair
    _restore_then(monkeypatch, after=lambda: _sql(copy, "insert into sheet_template values (99)"))
    _, wrong = live_copy.copy(live, copy)
    assert wrong == [f"public.sheet_template: live {ROWS}, copy {ROWS + 1}"]


def test_live_is_only_read(pair):
    live, _ = pair
    with live_copy.snapshot(live) as (conn, _snap), pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        conn.execute("insert into sheet_template values (100)")
