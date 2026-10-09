"""Each service reaches the database as a role of its own (goals/p1-the-roles-hold.yaml).

The privileges are read back from the database itself (`has_table_privilege` and its kin), as the migrations left
them, so a grant wider than a service's code needs fails here whatever a migration's comment says. That a grant is
wide enough is the browser suite's to show: CI runs it with the website and the engine connected as these roles.
"""

import os
import uuid

import psycopg
import pytest

from engine.core import db, roster

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

ROLES = ("app_web", "app_engine")
WRITES = ("INSERT", "UPDATE", "DELETE", "TRUNCATE")
# Every write the website makes (apps/web/app and lib, each `insert into` and `update`): a person's reading or
# judgement, an override of a prescription, a skill set edited or approved, the approved table of mistakes' charges,
# and an error a page raised.
WEB_WRITES = {
    "public.read_correction": {"INSERT"},
    "public.item_result": {"UPDATE"},
    "public.prescription": {"UPDATE"},
    "public.skill_set": {"UPDATE"},
    "public.config": {"UPDATE"},
    # an error a page raised, for the live watcher (goals/p2-live-is-watched.yaml)
    "public.web_error": {"INSERT"},
    # a wrong password for an email, so too many make it wait (goals/p2-live-recovers.yaml)
    "public.sign_in_failure": {"INSERT"},
}
# Every function of ours the website calls: signing a paper off, settling one answer, a roll in its order, a name.
WEB_CALLS = {
    "confirm_results",
    "resolve_result",
    "roll_order",
    "read_child",
    "result_response",
    "result_part",
}


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _names(conn, sql, *args):
    return [r["name"] for r in conn.execute(sql, args).fetchall()]


def _tables(conn, schema):
    return _names(
        conn,
        "select schemaname || '.' || tablename as name from pg_tables where schemaname = %s order by 1",
        schema,
    )


def _ledgers(conn):
    return _names(
        conn,
        "select distinct t.relnamespace::regnamespace || '.' || t.relname as name from pg_trigger g"
        " join pg_class t on t.oid = g.tgrelid where g.tgfoid = 'internal.forbid_change'::regproc order by 1",
    )


def _can(conn, role, table, what):
    return conn.execute("select has_table_privilege(%s, %s, %s) as ok", (role, table, what)).fetchone()["ok"]


def _functions(conn):
    """{name: signature} for every function of ours in `public` and `pii`."""
    rows = conn.execute(
        "select p.proname as name, p.oid::regprocedure::text as sig from pg_proc p"
        " join pg_namespace n on n.oid = p.pronamespace where n.nspname in ('public', 'pii')"
        " and not exists (select 1 from pg_depend d where d.objid = p.oid and d.deptype = 'e')"
    ).fetchall()
    return {r["name"]: r["sig"] for r in rows}


def test_neither_service_can_read_a_name_but_through_its_accessor(conn):
    """`pii.child` is out of reach of both: a name is read through `pii.read_child` and a child found by name through
    `pii.find_child`, and each writes who asked to `access_log`."""
    for role in ROLES:
        assert [w for w in ("SELECT", *WRITES) if _can(conn, role, "pii.child", w)] == [], role
        allowed = conn.execute(
            "select has_function_privilege(%s, 'pii.read_child(uuid, text)', 'execute') as ok", (role,)
        ).fetchone()["ok"]
        assert allowed, f"{role} cannot read a name even through the accessor"
    with conn.transaction():
        conn.execute("set local role app_engine")
        with pytest.raises(psycopg.errors.InsufficientPrivilege), conn.transaction():
            conn.execute("select first_name from pii.child limit 1")


def test_no_service_can_change_remove_or_empty_a_ledger_row(conn):
    """An append-only ledger (a table `internal.forbid_change` guards) is read and added to, never changed, removed or
    emptied — by grant, not by its trigger alone. A ledger made later is held the moment its trigger is."""
    ledgers = _ledgers(conn)
    assert {"public.evidence_event", "public.bank_decision", "public.key_correction"} <= set(ledgers), ledgers
    for role in ROLES:
        held = [
            f"{t} {w}" for t in ledgers for w in ("UPDATE", "DELETE", "TRUNCATE") if _can(conn, role, t, w)
        ]
        assert held == [], role
    assert all(
        _can(conn, "app_engine", t, "INSERT") and _can(conn, "app_engine", t, "SELECT") for t in ledgers
    )


def test_the_website_writes_only_what_a_person_changes_on_it(conn):
    """The website reads every table of `public`, writes the five a person changes on it, and calls only the functions
    its pages call; the engine writes every table but a ledger's rows, and empties none."""
    for t in _tables(conn, "public"):
        assert _can(conn, "app_web", t, "SELECT"), f"the website cannot read {t}"
        writes = {w for w in WRITES if _can(conn, "app_web", t, w)}
        assert writes == WEB_WRITES.get(t, set()), (t, writes)
        assert not _can(conn, "app_engine", t, "TRUNCATE"), t
    calls = {
        name
        for name, sig in _functions(conn).items()
        if conn.execute("select has_function_privilege('app_web', %s, 'execute') as ok", (sig,)).fetchone()[
            "ok"
        ]
    }
    assert calls == WEB_CALLS


def test_every_row_is_in_sight_of_both_services(conn):
    """Row security is forced on every table; a role no policy names would read none of its rows and write none,
    silently. Each table names both."""
    for t in _tables(conn, "public") + _tables(conn, "pii"):
        schema, name = t.split(".")
        roles = conn.execute(
            "select roles::text[] as roles from pg_policies where schemaname = %s and tablename = %s"
            " and policyname = 'app_all'",
            (schema, name),
        ).fetchone()
        assert roles and set(ROLES) <= set(roles["roles"]), t


def test_finding_a_child_by_name_is_logged_like_any_read(conn):
    """The importer finds a child by the first name a paper carries; as the engine's own role, through
    `pii.find_child`, which writes the lookup to `access_log` as a read."""
    tenant = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
    section, actor = f"ROLES-{uuid.uuid4().hex[:6]}", f"test-{uuid.uuid4().hex[:6]}"
    kid = db.one(
        conn,
        "insert into child (tenant_id, roll_no, section, band) values (%s, '1', %s, 'G2') returning id",
        (tenant, section),
    )["id"]
    conn.execute(
        "insert into pii.child (tenant_id, child_id, first_name) values (%s, %s, 'Zoya')", (tenant, kid)
    )
    conn.execute("set local role app_engine")
    assert roster.find(conn, section, "zoya", actor) == kid
    logged = conn.execute(
        "select action from access_log where actor = %s and child_id = %s", (actor, kid)
    ).fetchall()
    assert [r["action"] for r in logged] == ["find_child"]
