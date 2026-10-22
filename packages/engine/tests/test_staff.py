"""Who signs in to the website (goals/ui4a-staff-and-search.yaml).

Nimish, 2026-10-11: "Maybe we can simply add a user ID/password for them: simple user ID/password, nothing complex."
Since 2026-10-22 everyone signs in with their school Google account (goals/a1-sign-in-with-google.yaml); `engine staff
add` puts a person on the staff list in the database first — their email, name and role — when they must hold another
role than a first sign-in gives. The list is the database's alone: the seed in the public repository holds no one's
email, so Achal's and Neha's never pass through it.
"""

import json
import os
import pathlib

import pytest

from engine.core import db
from tests.test_cli import run

SEED = pathlib.Path(__file__).resolve().parents[3] / "supabase" / "seed" / "config.json"
EMAIL = "new-educator@cornerstone.test"
needs_db = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


def _staff():
    with db.connect() as conn:
        return conn.execute("select value from config where key = 'app.staff'").fetchone()["value"]


def _add(*args):
    return run("staff", "add", *args)


@pytest.fixture
def clean():
    """The staff list as it was: whatever a test added is taken off again."""
    yield
    with db.connect() as conn:
        conn.execute(
            "update config set value = (select coalesce(jsonb_agg(s), '[]'::jsonb) from jsonb_array_elements(value) s"
            " where s ->> 'email' <> %s) where key = 'app.staff'",
            (EMAIL,),
        )
        conn.commit()


@needs_db
def test_a_person_is_put_on_the_staff_list_by_one_command(clean):
    before = _staff()
    r = _add(EMAIL.upper(), "--name", "Test Educator", "--role", "coordinator")
    assert r.exit_code == 0, r.output_plain
    assert "Test Educator (coordinator) can sign in with Google" in r.output_plain
    after = _staff()
    assert after[: len(before)] == before, "no one already on the list is changed"
    [me] = [s for s in after if s["email"] == EMAIL]
    assert (me["name"], me["role"]) == ("Test Educator", "coordinator")
    assert "password" not in me, "no password: Google proves who signs in"


@needs_db
def test_a_person_already_on_the_list_or_a_role_no_one_holds_is_refused(clean):
    assert _add(EMAIL, "--name", "Test Educator").exit_code == 0
    again = _add(EMAIL, "--name", "Someone Else")
    assert again.exit_code != 0 and "already on the staff list" in again.output_plain
    assert [s["name"] for s in _staff() if s["email"] == EMAIL] == ["Test Educator"]

    # a role is one the school's decisions name (people.decides) or one someone on the list already holds
    odd = _add("odd@cornerstone.test", "--name", "Odd", "--role", "headmaster")
    assert odd.exit_code != 0 and "headmaster" in odd.output_plain
    assert "odd@cornerstone.test" not in {s["email"] for s in _staff()}


def test_the_staff_list_is_not_in_the_public_repository():
    """The seed's staff list is empty: who signs in is the database's to hold, put there by `engine staff add`, so an
    educator's email never enters the repository."""
    rows = {r["key"]: r for r in json.loads(SEED.read_text())["config"]}
    assert rows["app.staff"]["value"] == []
    assert rows["app.staff"]["seed_once"] is True, "a list the app owns is seeded once and then left alone"


# ---- F1a: each educator names the classes they teach (goals/f1a-each-educator-has-classes.yaml, ADR 0073 D1)

CLASSES = ("F1A-ONE", "F1A-TWO")


@pytest.fixture
def two_classes():
    """Two classes with a child in each, as a class exists on the site: a section a child still in school is in. A child
    is never deleted (their answers are append-only), so the classes' children leave school after, as a child does."""
    with db.connect() as conn:
        tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
        for section in CLASSES:
            conn.execute(
                "insert into child (tenant_id, roll_no, section, band) values (%s, '1', %s, 'G2')"
                " on conflict (tenant_id, section, roll_no) do update set active = true",
                (tenant, section),
            )
        conn.commit()
    yield CLASSES
    with db.connect() as conn:
        conn.execute("update child set active = false where section = any(%s)", (list(CLASSES),))
        conn.commit()


def _staff_cli(*args):
    return run("staff", *args)


@needs_db
def test_a_person_is_put_on_the_list_with_the_classes_they_teach(clean, two_classes):
    r = _add(EMAIL, "--name", "Test Educator", "--class", "F1A-TWO", "--class", "F1A-ONE")
    assert r.exit_code == 0, r.output_plain
    assert "F1A-ONE, F1A-TWO" in r.output_plain, "the command says the classes it put them on"
    [me] = [s for s in _staff() if s["email"] == EMAIL]
    assert me["classes"] == ["F1A-ONE", "F1A-TWO"], "in class order, each once"
    listed = _staff_cli("list")
    assert listed.exit_code == 0 and "F1A-ONE, F1A-TWO" in listed.output_plain


@needs_db
def test_a_class_with_no_child_in_it_is_refused_and_nothing_changes(clean, two_classes):
    before = _staff()
    r = _add(EMAIL, "--name", "Test Educator", "--class", "F1A-ONE", "--class", "F1A-NOBODY")
    assert r.exit_code != 0 and "F1A-NOBODY" in r.output_plain and "no child" in r.output_plain
    assert _staff() == before, "a typed class that is no class puts no one on the list"


@needs_db
def test_an_educators_classes_are_changed_by_one_command(clean, two_classes):
    assert _add(EMAIL, "--name", "Test Educator", "--class", "F1A-ONE").exit_code == 0
    others = [s for s in _staff() if s["email"] != EMAIL]

    moved = _staff_cli("classes", EMAIL.upper(), "F1A-TWO")
    assert moved.exit_code == 0, moved.output_plain
    assert "F1A-TWO" in moved.output_plain
    assert [s["classes"] for s in _staff() if s["email"] == EMAIL] == [["F1A-TWO"]]
    assert [s for s in _staff() if s["email"] != EMAIL] == others, "no one else on the list is changed"

    # no classes at all is said on purpose, never by leaving the classes out
    bare = _staff_cli("classes", EMAIL)
    assert bare.exit_code != 0 and "--none" in bare.output_plain
    assert _staff_cli("classes", EMAIL, "--none").exit_code == 0
    assert [s["classes"] for s in _staff() if s["email"] == EMAIL] == [[]]

    assert _staff_cli("classes", EMAIL, "F1A-NOBODY").exit_code != 0
    nobody = _staff_cli("classes", "nobody@cornerstone.test", "F1A-ONE")
    assert nobody.exit_code != 0 and "not on the staff list" in nobody.output_plain
