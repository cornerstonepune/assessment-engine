"""One approval list for everything new (goals/c5-one-approval-list.yaml, slice C5).

BUILD-ORDER, the locked scope of 22 Oct: "one approval list for everything new: draft beside approved, a second
approval before anything reaches a parent; the existing approvals unchanged". The list is `approval_list`; what the
existing approvals could not hold (a sending back with its reason, a second approval) is `approval`, never edited.
"""

import json
import os

import psycopg
import pytest

from engine.core import db
from tests.rows import a_child, tenant

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

MIGRATION = db.REPO_ROOT / "supabase/migrations/20261208090000_one_approval_list.sql"
SEED = json.loads((db.REPO_ROOT / "supabase/seed/vocabulary.json").read_text())


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _decide(conn, kind, target, decision, by, reason=None):
    conn.execute(
        "insert into approval (tenant_id, kind, target, decision, by, reason) values (%s, %s, %s, %s, %s, %s)",
        (tenant(conn), kind, target, decision, by, reason),
    )


def _refused(conn, *args, **kw):
    try:
        with conn.transaction():
            _decide(conn, *args, **kw)
    except psycopg.errors.CheckViolation:
        return True
    return False


def _entry(conn, kind, target):
    return db.one(
        conn,
        "select state, first_by, second_by, sent_back_because from approval_list where kind = %s and target = %s",
        (kind, target),
    )


def _note(conn):
    return db.one(
        conn,
        "insert into parent_note (tenant_id, child_id, week, body) values (%s, %s, 'W1', 'a report') returning id",
        (tenant(conn), a_child(conn)),
    )["id"]


def test_what_is_approved_and_where_it_stands_are_rows(conn):
    kinds = conn.execute("select code, words, reaches_parent from approval_kind order by ord").fetchall()
    assert [tuple(k.values()) for k in kinds] == [
        (k["code"], k["words"], k["reaches_parent"]) for k in SEED["approval_kinds"]
    ]
    states = conn.execute("select code, words from approval_state order by ord").fetchall()
    assert [tuple(s.values()) for s in states] == [(s["code"], s["words"]) for s in SEED["approval_states"]]


def test_draft_beside_approved_in_one_list(conn):
    """A level approved and one not, a way of asking approved and one not, a report: one list, each with its state."""
    level = db.one(conn, "select skill_code, difficulty from skill_level order by 1, 2 limit 1")
    conn.execute(
        "update skill set level_approved = level_approved - %s where code = %s",
        (level["difficulty"], level["skill_code"]),
    )
    conn.execute(
        "insert into question_type (tenant_id, code, fmt, words, marked) values (%s, 'C5.DRAFT', 'C5.DRAFT',"
        " 'a way of asking not yet approved', '{computable}')",
        (tenant(conn),),
    )
    note = _note(conn)
    states = {
        (r["kind"], r["target"]): r["state"]
        for r in conn.execute("select kind, target, state from approval_list").fetchall()
    }
    assert states[("skill_level", f"{level['skill_code']} {level['difficulty']}")] == "draft"
    assert states[("question_type", "C5.DRAFT")] == "draft"
    assert states[("parent_note", str(note))] == "draft"
    assert "approved" in {s for (k, _), s in states.items() if k == "skill_level"}
    assert "approved" in {s for (k, _), s in states.items() if k == "question_type"}


def test_send_back_with_a_reason(conn):
    """A draft is sent back to its writer with the reason; without one it is refused; approved later, it is approved."""
    conn.execute(
        "insert into question_type (tenant_id, code, fmt, words, marked) values (%s, 'C5.BACK', 'C5.BACK', 'w',"
        " '{computable}')",
        (tenant(conn),),
    )
    assert _refused(conn, "question_type", "C5.BACK", "sent_back", "a coordinator")
    _decide(conn, "question_type", "C5.BACK", "sent_back", "a coordinator", "the stem names no number")
    assert dict(_entry(conn, "question_type", "C5.BACK")) == {
        "state": "sent_back",
        "first_by": None,
        "second_by": None,
        "sent_back_because": "the stem names no number",
    }
    conn.execute(
        "insert into question_type_approval (tenant_id, question_type, approved_by, approved_at)"
        " values (%s, 'C5.BACK', 'an educator', clock_timestamp())",
        (tenant(conn),),
    )
    assert _entry(conn, "question_type", "C5.BACK")["state"] == "approved"


def test_a_second_approval_before_anything_reaches_a_parent(conn):
    """A report approved once waits for a second approval, by someone else; it cannot be sent before, and can after."""
    note = _note(conn)
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        conn.execute("update parent_note set sent_at = now() where id = %s", (note,))
    conn.execute("update parent_note set approved_by = 'an educator' where id = %s", (note,))
    assert _entry(conn, "parent_note", str(note))["state"] == "waiting_second"
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        conn.execute("update parent_note set sent_at = now() where id = %s", (note,))
    assert _refused(conn, "parent_note", str(note), "approved", "an educator")  # the same person, twice
    _decide(conn, "parent_note", str(note), "approved", "a coordinator")
    assert dict(_entry(conn, "parent_note", str(note))) == {
        "state": "approved",
        "first_by": "an educator",
        "second_by": "a coordinator",
        "sent_back_because": None,
    }
    conn.execute("update parent_note set sent_at = now() where id = %s", (note,))
    assert _entry(conn, "parent_note", str(note))["state"] == "approved"


def test_the_existing_approvals_are_unchanged(conn):
    """Every level and way of asking approved before is approved in the list, by the same person, and the migration
    run again moves none of them; a decision is never edited."""
    before = (
        conn.execute(
            "select md5(string_agg(code || level_approved::text, ',' order by code)) as s from skill"
        ).fetchone()["s"],
        conn.execute(
            "select md5(string_agg(question_type || approved_by, ',' order by question_type)) as s"
            " from question_type_approval"
        ).fetchone()["s"],
    )
    approved = db.one(
        conn,
        "select count(*) as n from skill_level l join skill s on s.code = l.skill_code and s.tenant_id = l.tenant_id"
        " where s.level_approved ? l.difficulty",
    )["n"]
    assert (
        approved
        == db.one(
            conn, "select count(*) as n from approval_list where kind = 'skill_level' and state = 'approved'"
        )["n"]
    )
    conn.execute(MIGRATION.read_text())
    after = (
        conn.execute(
            "select md5(string_agg(code || level_approved::text, ',' order by code)) as s from skill"
        ).fetchone()["s"],
        conn.execute(
            "select md5(string_agg(question_type || approved_by, ',' order by question_type)) as s"
            " from question_type_approval"
        ).fetchone()["s"],
    )
    assert after == before
    note = _note(conn)
    _decide(conn, "parent_note", str(note), "sent_back", "a coordinator", "a reason")
    with pytest.raises(psycopg.Error), conn.transaction():
        conn.execute("update approval set reason = 'another'")
