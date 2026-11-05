"""Helpers shared by the skill-link tests (goals/m1-15-skill-links.yaml). Staff here are placeholders on the reserved
`.invalid` domain, never a real person."""

import uuid

import psycopg


def refused(conn, sql, params=()):
    """True when the database refuses `sql`; the transaction carries on either way."""
    try:
        with conn.transaction():
            conn.execute(sql, params)
    except (psycopg.errors.IntegrityError, psycopg.errors.RaiseException):
        return True
    return False


def skills(conn, n=5):
    return [r["code"] for r in conn.execute("select code from registry_skill order by code limit %s", (n,))]


def staff(conn, t, email="checker@school.invalid", active=True):
    """A member of staff with an email: a placeholder, never a real person."""
    campus = conn.execute("select id from campus where tenant_id = %s limit 1", (t,)).fetchone()["id"]
    sid = conn.execute(
        "insert into staff (tenant_id, campus_id, active) values (%s, %s, %s) returning id",
        (t, campus, active),
    ).fetchone()["id"]
    conn.execute(
        "insert into pii.staff (tenant_id, staff_id, name, email) values (%s, %s, 'A placeholder', %s)",
        (t, sid, email),
    )
    return sid


ADD = (
    "insert into skill_link (tenant_id, skill_code, before_code, strength, reason, source)"
    " values (%s, %s, %s, %s, %s, %s)"
)


def link(conn, t, after, before, strength="hard", reason="A child counts before they add", source="a list"):
    return conn.execute(ADD + " returning id", (t, after, before, strength, reason, source)).fetchone()["id"]


def csv_of(tmp_path, *rows, header="before_code,after_code,reason,source"):
    p = tmp_path / f"pairs-{uuid.uuid4().hex[:6]}.csv"
    p.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")
    return p
