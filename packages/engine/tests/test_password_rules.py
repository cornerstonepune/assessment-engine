"""A password a member of staff sets themselves (goals/auth-email-password.yaml).

What the website does with a link is shown in a browser (apps/web/tests/gate-password.spec.ts). What is shown here is
what no browser can: that the token is kept as a hash and nothing else, that the website may spend a link but not
rewrite one, that the limits and the list of common passwords are rows and seed files rather than numbers in code, and
that a link whose email never left is said plainly — and with no secret — in the live watch.
"""

import json
import os
import re
import uuid

import pytest

from engine.checks import watch
from engine.core import db

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

WEB = db.REPO_ROOT / "apps" / "web"
SEED = db.REPO_ROOT / "supabase" / "seed"
# Every limit this flow stands on, and what it is for.
ROWS = {
    "password.min_length",
    "password.scrypt_n",
    "password_link.reset_minutes",
    "password_link.first_days",
    "password_ask.max_per_email",
    "password_ask.max_per_ip",
    "password_ask.window_minutes",
}


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _link(conn, mail=None, **more):
    """A link row of a test's own, rolled back with the fixture."""
    tenant = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
    fields = {"purpose": "reset", "expires_at": "now() + interval '1 hour'", **more}
    return db.one(
        conn,
        "insert into password_link (tenant_id, email, token_hash, purpose, expires_at, mail)"
        f" values (%s, %s, %s, %s, {fields.pop('expires_at')}, %s) returning id, token_hash",
        (tenant, f"{uuid.uuid4().hex[:8]}@test.invalid", uuid.uuid4().hex * 2, fields["purpose"], mail),
    )


def test_a_link_is_kept_as_a_hash_and_the_website_may_only_spend_one(conn):
    """The row holds a sha-256 of the token and no column that could hold the token itself; the website may add a row
    and mark it used, closed or sent, and may not touch the email, the hash or when it runs out — so a link cannot be
    moved to another person or given more time from a page."""
    columns = {
        r["column_name"]: r["data_type"]
        for r in conn.execute(
            "select column_name, data_type from information_schema.columns"
            " where table_name = 'password_link' and table_schema = 'public'"
        )
    }
    assert set(columns) == {
        "id", "tenant_id", "email", "token_hash", "purpose", "created_at",
        "expires_at", "used_at", "closed_at", "mail", "updated_at",
    }, columns  # fmt: skip
    assert "token" not in columns

    may = {
        c
        for c in columns
        if conn.execute(
            "select has_column_privilege('app_web', 'public.password_link', %s, 'UPDATE') as ok", (c,)
        ).fetchone()["ok"]
    }
    assert may == {"used_at", "closed_at", "mail"}, may
    assert conn.execute(
        "select has_table_privilege('app_web', 'public.password_link', 'INSERT') as ok"
    ).fetchone()["ok"]
    for what in ("DELETE", "TRUNCATE"):
        assert not conn.execute(
            "select has_table_privilege('app_web', 'public.password_link', %s) as ok", (what,)
        ).fetchone()["ok"], what

    # the hash is unique, so two rows cannot answer one token
    assert (
        conn.execute(
            "select count(*) as n from pg_indexes where tablename = 'password_link'"
            " and indexdef like '%UNIQUE%token_hash%'"
        ).fetchone()["n"]
        == 1
    )


def test_the_forgot_form_counts_what_was_asked_for_per_email_and_per_address(conn):
    """Each ask is a row, and the address is kept as a mark of itself, never as an address: the website writes an HMAC
    of it (`addressMark`), and the column holds nothing that reads as an address."""
    tenant = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
    email = f"{uuid.uuid4().hex[:8]}@test.invalid"
    for _ in range(3):
        conn.execute(
            "insert into password_ask (tenant_id, email, ip) values (%s, %s, %s)",
            (tenant, email, "a" * 32),
        )
    asked = conn.execute(
        "select count(*) as n from password_ask where email = %s and created_at > now() - interval '1 hour'",
        (email,),
    ).fetchone()["n"]
    assert asked == 3
    source = (WEB / "lib" / "password-links.ts").read_text()
    assert "createHmac" in source and "addressMark" in source
    assert "password_ask.max_per_email" in source and "password_ask.max_per_ip" in source
    assert not conn.execute(
        "select has_table_privilege('app_web', 'public.password_ask', 'UPDATE') as ok"
    ).fetchone()["ok"]


def test_mail_that_is_not_configured_is_said_in_the_health_check_with_no_secret(conn):
    """`engine live watch` says how many set-password links of the last day never reached anyone, and why in the
    plainest words: no email, no token, no link, no reason from the sender (rule 6)."""
    _link(conn, mail="not configured")
    _link(conn, mail="failed")
    said = watch.problems(conn, free_bytes=10**12)
    lines = [line for line in said if "set-password" in line or "mail is not configured" in line]
    assert any("mail is not configured" in line for line in lines), said
    assert any("refused" in line for line in lines), said
    tokens = {r["token_hash"] for r in conn.execute("select token_hash from password_link")}
    for line in lines:
        assert "@" not in line, line
        assert not any(t in line for t in tokens), line
        assert "http" not in line


def test_every_number_and_the_common_list_are_rows_and_seed_files(conn):
    """Rule 1: the shortest password, how hard it is hashed, how long a link lasts and how often it may be asked for
    are threshold rows; the commonest passwords are a seed file. None of them is a number in the website's code."""
    have = {r["key"] for r in conn.execute("select key from threshold where key like 'password%'").fetchall()}
    assert ROWS <= have, ROWS - have

    common = json.loads((SEED / "common_passwords.json").read_text())["passwords"]
    assert len(common) > 50 and "password123" in common
    assert len(common) == len(set(p.lower() for p in common)), "the list says a password twice"

    source = (WEB / "lib" / "password.ts").read_text() + (WEB / "lib" / "password-links.ts").read_text()
    assert "password.min_length" in source and "password_link.reset_minutes" in source
    # no list of passwords and no length written into the code: both are read from the rows above
    assert "const COMMON = new Set(common.passwords" in source
    assert not re.search(r"length\s*<\s*\d", source), "the shortest password is a row, not a number here"


def test_nothing_was_added_but_a_password(conn):
    """Nimish, 26 Oct 2026: "No 2FA needed for now, keep it simple." No second factor, no social sign-in, no
    magic-link-only way in, no "remember me": the only new way to reach the site is a password its owner set."""
    pages = {p.name for p in (WEB / "app" / "login").rglob("*") if p.is_dir()}
    assert pages == {"forgot", "link", "new-password"}, pages
    source = "\n".join(
        p.read_text()
        for p in (WEB / "lib").glob("*.ts")
        if p.name.startswith(("auth", "password", "session"))
    )
    for never in ("totp", "otp", "two.factor", "2fa", "oauth", "google", "remember.me"):
        assert not re.search(rf"\b{never}\b", source, re.I), never
    tables = {
        r["table_name"]
        for r in conn.execute(
            "select table_name from information_schema.tables where table_schema = 'public'"
            " and table_name like 'password%'"
        )
    }
    assert tables == {"password_link", "password_ask"}, tables
