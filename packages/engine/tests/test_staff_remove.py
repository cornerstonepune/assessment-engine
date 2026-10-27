"""`engine staff remove EMAIL [EMAIL ...] [--apply]`: a person taken off the staff list (goals/staffrm_remove_a_person.yaml).

Nimish found a placeholder entry on the live list, the text `your-email` with a coordinator's password and every class,
that nothing could remove. Every person here is made up, on an example.test address; the placeholder is made up too,
as the same kind of text (no @).
"""

import copy
import json
import os
import re
import threading
import time

import pytest

from engine.core import db
from tests.test_cli import run

needs_db = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
HASH = "scrypt$16384$00112233445566778899aabbccddeeff$" + "ab" * 64
BOSS = {
    "email": "boss@example.test",
    "name": "Made Up Boss",
    "role": "coordinator",
    "password": HASH,
    "classes": [],
}
TEACHER = {
    "email": "teacher@example.test",
    "name": "Made Up Teacher",
    "role": "educator",
    "password": HASH,
    "classes": ["SL-ONE"],
    "subjects": ["NUM"],
}
SPARE = {**BOSS, "email": "spare@example.test", "name": "Made Up Spare"}
PLACEHOLDER = {**BOSS, "email": "your-email-test", "name": "Placeholder Test"}  # no @, as the one on live
NO_PASSWORD = {**BOSS, "email": "waiting@example.test", "name": "Made Up Waiting", "password": ""}
OTHERS = [BOSS, TEACHER]


def _staff():
    with db.connect() as conn:
        return conn.execute("select value from config where key = 'app.staff'").fetchone()["value"]


def _put(people):
    with db.connect() as conn:
        conn.execute("update config set value = %s where key = 'app.staff'", (json.dumps(people),))
        conn.commit()


@pytest.fixture
def list_of():
    """Sets the staff list for a test and puts back the one it found."""
    was = _staff()
    yield _put
    _put(was)


def _remove(*args):
    return run("staff", "remove", *args)


@needs_db
def test_a_dry_run_changes_nothing_and_says_what_it_would_do_for_each_email(list_of):
    list_of([BOSS, TEACHER, SPARE])
    before = _staff()
    r = _remove("teacher@example.test", "nobody@example.test")
    assert r.exit_code == 0, r.output_plain
    assert "would remove Made Up Teacher (educator)" in r.output_plain
    assert "nobody@example.test" in r.output_plain and "refused" in r.output_plain
    assert "dry run" in r.output_plain.lower() and "--apply" in r.output_plain
    assert _staff() == before, "a dry run wrote to the staff list"


@needs_db
def test_every_refusal_is_said_in_words_and_one_refusal_stops_the_whole_apply(list_of):
    list_of([BOSS, TEACHER, NO_PASSWORD])
    before = _staff()

    unknown = _remove("nobody@example.test").output_plain
    assert "nobody@example.test" in unknown and "is not on the staff list" in unknown

    twice = _remove("teacher@example.test", "TEACHER@example.test").output_plain
    assert twice.count("named more than once") == 2 and "would remove" not in twice

    # the only coordinator who can sign in; the one with no password does not count as one
    last = _remove("boss@example.test").output_plain
    assert "that would leave no coordinator who can sign in" in last and "would remove" not in last

    # case does not matter, nor a space around the address
    cased = _remove("  Teacher@Example.TEST ").output_plain
    assert "would remove Made Up Teacher (educator)" in cased

    # one refused email among fine ones: nothing is applied, not even the fine one
    mixed = _remove("teacher@example.test", "nobody@example.test", "--apply")
    assert mixed.exit_code != 0 and "nothing was applied" in mixed.output_plain
    assert _staff() == before

    # a second coordinator keeps the list able to sign in, so the first may go
    list_of([BOSS, TEACHER, SPARE])
    both = _remove("boss@example.test", "spare@example.test").output_plain
    assert both.count("that would leave no coordinator who can sign in") == 2


@needs_db
def test_the_placeholder_with_no_at_sign_is_removed_by_the_command_and_leaves_everyone_else_as_they_were(
    list_of,
):
    # the case that started this: an entry whose "email" is just text, so the loader's email-shape check must not apply
    list_of([PLACEHOLDER, BOSS, TEACHER])
    others = copy.deepcopy(
        _staff()[1:]
    )  # as the database holds them (it gives each person an id on the way in)
    r = _remove("YOUR-EMAIL-TEST", "--apply")
    assert r.exit_code == 0, r.output_plain
    assert "would remove" not in r.output_plain and "Placeholder Test" in r.output_plain
    assert _staff() == others, "everyone not named must be exactly as they were, in the same order"
    again = _remove("your-email-test", "--apply")
    assert "is not on the staff list" in again.output_plain and again.exit_code != 0


@needs_db
def test_apply_holds_the_staff_list_and_removes_in_one_transaction(list_of, monkeypatch):
    list_of([BOSS, TEACHER, SPARE])
    late = {**TEACHER, "email": "late@example.test", "name": "Made Up Late"}

    # the website saves a new person while the remover is waiting its turn: the remover must read the list after
    # that save, or it writes back the list it read before and the new person vanishes
    result: list = []
    done = threading.Thread(target=lambda: result.append(_remove("teacher@example.test", "--apply")))
    with db.connect() as site:
        site.execute("select 1 from config where key = 'app.staff' for update")
        done.start()
        time.sleep(1.5)
        assert done.is_alive(), "apply did not wait for the lock on the staff list"
        site.execute(
            "update config set value = value || %s::jsonb where key = 'app.staff'", (json.dumps([late]),)
        )
        site.commit()
    done.join(20)
    assert result and result[0].exit_code == 0, result and result[0].output_plain
    assert [s["email"] for s in _staff()] == ["boss@example.test", "spare@example.test", "late@example.test"]

    # and if the write fails, nothing is half done
    list_of([BOSS, TEACHER, SPARE])
    before = _staff()

    def boom(conn, people):
        raise RuntimeError("the database went away")

    monkeypatch.setattr("engine.core.staff_remove.save", boom)
    r = _remove("teacher@example.test", "spare@example.test", "--apply")
    assert r.exit_code != 0
    assert _staff() == before


@needs_db
def test_a_removed_persons_past_sign_offs_are_not_touched(list_of):
    list_of([BOSS, TEACHER])
    with db.connect() as conn:
        tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
        conn.execute(  # a sign-off as the site writes one: the email as free text (assessment_name is append-only)
            "insert into assessment_name (tenant_id, key, name, named_by) values (%s, 'remove-test~key', 'Kept', %s)",
            (tenant, TEACHER["email"]),
        )
        tables = [
            r["table_name"]
            for r in conn.execute(
                "select table_name from information_schema.tables where table_schema = 'public'"
                " and table_type = 'BASE TABLE' and table_name <> 'config' order by 1"
            ).fetchall()
        ]
        snap = {t: conn.execute(f"select count(*) as n from {t}").fetchone()["n"] for t in tables}  # noqa: S608
        sums = conn.execute(
            "select md5(string_agg(e::text, '' order by e.id::text)) as m from evidence_event e"
        ).fetchone()
        r = _remove(
            "teacher@example.test", "--apply"
        )  # its own connection: the row above is not even committed
        assert r.exit_code == 0, r.output_plain
        assert {t: conn.execute(f"select count(*) as n from {t}").fetchone()["n"] for t in tables} == snap  # noqa: S608
        assert (
            conn.execute(
                "select md5(string_agg(e::text, '' order by e.id::text)) as m from evidence_event e"
            ).fetchone()
            == sums
        )
        kept = conn.execute("select named_by from assessment_name where key = 'remove-test~key'").fetchone()
        assert kept["named_by"] == TEACHER["email"], "the old sign-off must still name them"
        conn.rollback()  # nothing of this test is left behind
    assert "past sign-offs" in r.output_plain.lower()


def test_the_website_decides_a_session_by_the_staff_list_on_every_request():
    """The proxy checks only that the cookie is signed; `currentStaff` then looks the email up in the staff list on
    every request, and a person not on it is signed out: `requireStaff` sends them to /login. Read from the source
    (a browser run needs the whole site built; not cheap), so this fails the day that lookup is cached or dropped."""
    from engine.core import db as _db

    web = _db.REPO_ROOT / "apps/web/lib"
    auth = (web / "auth.ts").read_text()
    body = auth.split("export const currentStaff", 1)[1].split("export async function requireStaff", 1)[0]
    assert "staffList()" in body, "currentStaff must read the staff list itself"
    assert re.search(r"if \(!staff\) return null", body), (
        "a person not on the list must come back as signed out"
    )
    cookie = (web / "session-cookie.ts").read_text()
    assert "role" not in cookie.split("export function sessionValue", 1)[1].split("}", 1)[0], (
        "the cookie must carry only who, so nothing in it outlives a removal"
    )
    # the list is read afresh (react's cache() lasts one request); no module-level copy of it anywhere in lib
    queries = (web / "queries.ts").read_text()
    staff_list = queries.split("export async function staffList", 1)[1].split("\n}", 1)[0]
    assert "select value from config where key = 'app.staff'" in staff_list


def test_help_says_what_it_does_and_does_not_do_with_a_made_up_example():
    r = _remove("--help")
    assert r.exit_code == 0
    out = " ".join(r.output_plain.split())
    assert "teacher@example.test" in out and "--apply" in out
    assert "dry run" in out.lower() or "without --apply" in out.lower()
    for plain in ("signs them out", "past", "never deletes", "evidence"):
        assert plain in out.lower(), f"--help should say {plain!r}"
    assert "password" in out.lower() and "classes" in out.lower()
