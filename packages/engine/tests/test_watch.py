"""What is wrong on live, in words a public issue can carry (goals/p2-live-is-watched.yaml).

Each test adds rows of its own, under a flow or a page pattern no other row has, inside a transaction it rolls back,
and looks for its own line: the copy is shared, so another test's runs may be there too.
"""

import os
import re
import uuid

import pytest

from engine.checks import watch
from engine.core import db

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

PLENTY = 50 * 10**9  # bytes free: no disk line


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _tenant(conn):
    return db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]


def _run(conn, flow, status, started, finished=None):
    conn.execute(
        "insert into flow_run (tenant_id, flow, status, started_at, finished_at)"
        " values (%s, %s, %s, now() - %s::interval, now() - %s::interval)",
        (_tenant(conn), flow, status, started, finished),
    )


def _mine(lines, name):
    return [ln for ln in lines if name in ln]


def test_a_run_stuck_past_its_limit_is_a_problem(conn):
    """A reading still running past `watch.stuck_minutes` died or hangs; one inside the limit is working."""
    stuck, busy = f"stuck-{uuid.uuid4().hex[:6]}", f"busy-{uuid.uuid4().hex[:6]}"
    _run(conn, stuck, "running", "45 minutes")
    _run(conn, stuck, "running", "50 minutes")
    _run(conn, busy, "running", "2 minutes")
    lines = watch.problems(conn, PLENTY)
    assert _mine(lines, stuck) == [f"{stuck} runs still running after 30 minutes: 2"]
    assert _mine(lines, busy) == []


def test_a_run_that_failed_in_the_window_is_a_problem(conn):
    """A run that failed in the last `watch.window_minutes` is said once per watch; one that failed before is old news."""
    failed, old = f"failed-{uuid.uuid4().hex[:6]}", f"old-{uuid.uuid4().hex[:6]}"
    _run(conn, failed, "error", "6 minutes", "5 minutes")
    _run(conn, old, "error", "3 hours", "3 hours")
    lines = watch.problems(conn, PLENTY)
    assert _mine(lines, failed) == [f"{failed} runs failed in the last 30 minutes: 1"]
    assert _mine(lines, old) == []


def test_a_website_error_is_a_problem_named_by_its_page_pattern(conn):
    """The website records an error a page raised by the page's pattern (apps/web/instrumentation.ts); the watch counts
    them per page."""
    page = f"/watch-{uuid.uuid4().hex[:6]}/[id]"
    for _ in range(3):
        conn.execute(
            "insert into web_error (tenant_id, route, kind) values (%s, %s, 'render')", (_tenant(conn), page)
        )
    assert _mine(watch.problems(conn, PLENTY), page) == [
        f"website errors on {page} in the last 30 minutes: 3"
    ]


def test_a_nearly_full_disk_is_a_problem(conn):
    """The server's disk holds every scan and paper; below `watch.disk_free_gb` free, the next deploy or scan fails."""
    assert _mine(watch.problems(conn, int(1.5 * 10**9)), "disk") == [
        "the server's disk has 1.5 GB free, less than 2 GB"
    ]
    assert _mine(watch.problems(conn, PLENTY), "disk") == []


def test_no_problem_names_a_child_an_id_or_an_address(conn):
    """The watcher posts these lines to an issue on a public repository: a run's error text can carry a child's name,
    so it is never quoted, and no line holds an id or an address."""
    flow = f"named-{uuid.uuid4().hex[:6]}"
    conn.execute(
        "insert into flow_run (tenant_id, flow, status, started_at, finished_at, error)"
        " values (%s, %s, 'error', now(), now(), 'Zoya''s paper at 10.0.0.7 failed')",
        (_tenant(conn), flow),
    )
    lines = watch.problems(conn, int(0.5 * 10**9))
    assert _mine(lines, flow), lines
    text = "\n".join(lines)
    assert "Zoya" not in text
    assert not re.search(r"[0-9a-f]{8}-[0-9a-f]{4}-", text)
    assert not re.search(r"\b\d{1,3}(\.\d{1,3}){3}\b", text)
