"""Who signs in to the website (goals/ui4a-staff-and-search.yaml).

Nimish, 2026-10-11: "Maybe we can simply add a user ID/password for them: simple user ID/password, nothing complex."
`engine staff add` puts an educator on the staff list in the database — their email, name and role, and a password
typed where only the person running it sees it, hashed as the website checks it. The list is the database's alone:
the seed in the public repository holds no one's email, so Achal's and Neha's never pass through it.
"""

import json
import os
import pathlib

import pytest
from typer.testing import CliRunner

from engine.cli import app
from engine.core import db
from engine.core.staff import staff_hash

SEED = pathlib.Path(__file__).resolve().parents[3] / "supabase" / "seed" / "config.json"
EMAIL = "new-educator@cornerstone.test"
PASSWORD = "a-long-test-password"
needs_db = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


def _staff():
    with db.connect() as conn:
        return conn.execute("select value from config where key = 'app.staff'").fetchone()["value"]


def _add(monkeypatch, *args, typed=(PASSWORD, PASSWORD)):
    said = iter(typed)
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(said))
    return CliRunner().invoke(app, ["staff", "add", *args], env={"NO_COLOR": "1", "COLUMNS": "200"})


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
def test_a_person_is_put_on_the_staff_list_with_a_password_the_sign_in_accepts(monkeypatch, clean):
    before = _staff()
    r = _add(monkeypatch, EMAIL.upper(), "--name", "Test Educator")
    assert r.exit_code == 0, r.output
    assert "Test Educator (educator)" in r.output and PASSWORD not in r.output
    after = _staff()
    assert after[: len(before)] == before, "no one already on the list is changed"
    [me] = [s for s in after if s["email"] == EMAIL]
    assert (me["name"], me["role"]) == ("Test Educator", "educator")
    scheme, salt, _ = me["password"].split("$")
    assert scheme == "scrypt" and me["password"] == staff_hash(PASSWORD, salt), "the hash the website checks"


@needs_db
def test_a_person_already_on_the_list_a_role_no_one_holds_or_a_short_password_is_refused(monkeypatch, clean):
    assert _add(monkeypatch, EMAIL, "--name", "Test Educator").exit_code == 0
    again = _add(monkeypatch, EMAIL, "--name", "Someone Else")
    assert again.exit_code != 0 and "already on the staff list" in again.output
    assert [s["name"] for s in _staff() if s["email"] == EMAIL] == ["Test Educator"]

    # a role is one the school's decisions name (people.decides) or one someone on the list already holds
    odd = _add(monkeypatch, "odd@cornerstone.test", "--name", "Odd", "--role", "headmaster")
    assert odd.exit_code != 0 and "headmaster" in odd.output
    short = _add(monkeypatch, "short@cornerstone.test", "--name", "Short", typed=("short", "short"))
    assert short.exit_code != 0 and "10" in short.output
    differ = _add(
        monkeypatch, "differ@cornerstone.test", "--name", "Differ", typed=(PASSWORD, PASSWORD + "x")
    )
    assert differ.exit_code != 0
    emails = {s["email"] for s in _staff()}
    assert not emails & {"odd@cornerstone.test", "short@cornerstone.test", "differ@cornerstone.test"}


def test_the_staff_list_is_not_in_the_public_repository():
    """The seed's staff list is empty: who signs in is the database's to hold, put there by `engine staff add`, so an
    educator's email never enters the repository."""
    rows = {r["key"]: r for r in json.loads(SEED.read_text())["config"]}
    assert rows["app.staff"]["value"] == []
    assert rows["app.staff"]["seed_once"] is True, "a list the app owns is seeded once and then left alone"
