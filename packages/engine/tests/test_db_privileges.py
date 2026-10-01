"""Our functions answer only their owner (goals/p0-the-database-answers-only-its-own.yaml).

Supabase exposes `public` through its REST API, and Postgres lets everyone run a new function unless a grant says
otherwise. On 2026-09-30 a copy built from the migrations let `anon` run all seven of our SECURITY DEFINER functions,
the ones that sign off, correct and write a child's evidence among them. These hold every function we own closed to
the API's roles, and every function made later closed too.
"""

import pytest

from engine.core import db

API_ROLES = ("anon", "authenticated")
OURS = """
    select p.oid, p.oid::regprocedure::text as sig
    from pg_proc p
    join pg_namespace n on n.oid = p.pronamespace
    where n.nspname in ('public', 'pii', 'internal')
      and p.proowner = (select oid from pg_roles where rolname = current_user)
      and not exists (select 1 from pg_depend d where d.objid = p.oid and d.deptype = 'e')
"""


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def test_the_api_roles_exist_so_this_check_reads_something(conn):
    roles = {r["rolname"] for r in conn.execute("select rolname from pg_roles").fetchall()}
    assert set(API_ROLES) <= roles


def _runs(conn, role, func):
    """Can `role` execute `func` (an oid or a signature)?"""
    return conn.execute("select has_function_privilege(%s, %s, 'execute') as x", (role, func)).fetchone()["x"]


def test_no_function_of_ours_runs_for_the_api_roles(conn):
    funcs = conn.execute(OURS).fetchall()
    assert any(f["sig"].startswith("confirm_results(") for f in funcs), "the sign-off function is not ours?"
    assert [(f["sig"], r) for f in funcs for r in API_ROLES if _runs(conn, r, f["oid"])] == []


def test_a_function_made_later_is_closed_to_them_too(conn):
    conn.execute("create function public._made_later() returns int language sql as 'select 1'")
    for role in API_ROLES:
        assert not _runs(conn, role, "public._made_later()"), (
            f"{role} runs a function made after the migration"
        )
