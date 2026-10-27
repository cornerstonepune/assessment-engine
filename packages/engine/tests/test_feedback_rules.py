"""A note from staff that becomes a GitHub issue (goals/feed_report_from_the_tool.yaml).

What the website does with a note is shown in a browser (apps/web/tests/u70-report-a-problem.spec.ts) and its rules
without one (apps/web/tests/u70-feedback-rules.spec.ts). What is shown here is what no browser can: that the row holds a
role and classes and no column for a name or an email, that the website may add a note and say how its sending went but
never change or remove what was written, that the limits are rows, and that a note that has not reached GitHub is said
plainly — and with no secret — in the live watch.
"""

import json
import os
import uuid

import psycopg
import pytest

from engine.checks import watch
from engine.core import db

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

SEED = db.REPO_ROOT / "supabase" / "seed"
ROWS = {"feedback.max_per_hour", "feedback.max_chars", "feedback.send_per_try"}


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _note(conn, status="saved", minutes_ago=60):
    """A note of a test's own, rolled back with the fixture."""
    tenant = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
    return db.one(
        conn,
        "insert into staff_note (tenant_id, kind, doing, happened, route, role, classes, reporter, status, created_at)"
        " values (%s, 'bug', 'printing', 'nothing came out', '/papers', 'educator', '3A', %s, %s,"
        " now() - make_interval(mins => %s)) returning id",
        (tenant, uuid.uuid4().hex, status, minutes_ago),
    )["id"]


def test_a_note_keeps_role_and_class_and_never_a_name_or_email(conn):
    columns = {
        r["column_name"]
        for r in conn.execute(
            "select column_name from information_schema.columns"
            " where table_name = 'staff_note' and table_schema = 'public'"
        )
    }
    assert columns == {
        "id", "tenant_id", "kind", "doing", "happened", "how_often", "route", "role", "classes", "browser",
        "reporter", "status", "issue_number", "tried_at", "created_at", "updated_at",
    }, columns  # fmt: skip
    assert not {c for c in columns if "name" in c or "email" in c}
    statuses = db.one(
        conn,
        "select pg_get_constraintdef(oid) as d from pg_constraint"
        " where conrelid = 'public.staff_note'::regclass and pg_get_constraintdef(oid) like '%%status%%'",
    )["d"]
    assert all(f"'{s}'" in statuses for s in ("saved", "sent", "failed")), statuses


def test_the_website_may_add_a_note_and_mark_it_sent_but_never_change_its_words(conn):
    may = {
        r["column_name"]
        for r in conn.execute(
            "select column_name from information_schema.columns where table_name = 'staff_note'"
            " and table_schema = 'public' and has_column_privilege('app_web', 'public.staff_note', column_name, 'UPDATE')"
        )
    }
    assert may == {"status", "issue_number", "tried_at"}, may

    def can(w):
        return db.one(conn, "select has_table_privilege('app_web', 'public.staff_note', %s) as ok", (w,))[
            "ok"
        ]

    assert can("INSERT") and can("SELECT") and not can("DELETE") and not can("TRUNCATE")

    note = _note(conn)
    conn.execute(
        "update staff_note set status = 'sent', issue_number = 7, tried_at = now() where id = %s", (note,)
    )
    # not even the owner of the table changes the words or removes a note: the trigger holds for every role
    for change in (
        "update staff_note set happened = 'edited' where id = %s",
        "delete from staff_note where id = %s",
    ):
        conn.execute("savepoint s")
        with pytest.raises(psycopg.errors.RaiseException):
            conn.execute(change, (note,))
        conn.execute("rollback to savepoint s")
    assert db.one(conn, "select happened, status from staff_note where id = %s", (note,)) == {
        "happened": "nothing came out",
        "status": "sent",
    }


def test_the_limits_are_rows(conn):
    seeded = {r["key"] for r in json.loads((SEED / "thresholds.json").read_text())["thresholds"]}
    assert ROWS <= seeded, ROWS - seeded
    loaded = {r["key"] for r in conn.execute("select key from threshold where key like 'feedback.%%'")}
    assert ROWS <= loaded, ROWS - loaded
    web = db.REPO_ROOT / "apps" / "web" / "lib" / "feedback.ts"
    src = web.read_text()
    assert all(k in src for k in ROWS), "the website reads each limit from its row"


def test_unsent_notes_are_said_in_the_health_check_with_no_secret(conn, monkeypatch):
    monkeypatch.setenv("GITHUB_FEEDBACK_TOKEN", "ghp_not-a-real-token-but-shaped-like-one")
    before = [p for p in watch.problems(conn, 10**12) if "GitHub" in p]
    _note(conn, "saved")
    _note(conn, "saved")
    _note(conn, "failed")
    _note(conn, "saved", minutes_ago=0)  # just written: its first try is still in hand, so not yet said
    _note(conn, "sent")
    said = [p for p in watch.problems(conn, 10**12) if "GitHub" in p]
    assert before == [], before  # the copy holds no note but a test's own
    assert said == [
        "feedback is not connected to GitHub: 2 notes from staff are saved and wait to be sent",
        "GitHub refused 1 notes from staff: they are kept and sent again on the next try",
    ], said
    assert not any("ghp_" in p or "token" in p.lower() for p in said)
