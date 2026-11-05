"""Staff read a K2 page and answer its drafted parts (engine/api/routes/page.py, goals/m1-12b-apply-and-edit.yaml)."""

import os

import pytest
from fastapi.testclient import TestClient

from engine.api import deps
from engine.api.app import app
from tests import test_k2_draft as base
from tests.test_k2_page import SLIPS, STEPS, drafted_page

conn = base.conn
pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
KEY = "test-engine-key"
H = {"X-Engine-Key": KEY}
WHO = {"actor": "x@school.invalid"}


@pytest.fixture
def client(conn, monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", KEY)
    conn.execute(
        "update config set value = 'true'::jsonb where key = 'educator.timetable_enabled'"
    )  # the gate: open
    app.dependency_overrides[deps.get_conn] = lambda: conn
    app.dependency_overrides[deps.get_tenant_id] = lambda: str(conn.t)
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def post(client, path, **body):
    return client.post(f"/curriculum/page/{path}", json={**WHO, "code": "KX-1", **body}, headers=H)


def test_every_route_needs_the_engines_key_and_a_member_of_staff(client, conn):
    drafted_page(conn)
    for path in ("read", "confirm", "revert", "edit"):
        assert (
            client.post(f"/curriculum/page/{path}", json={**WHO, "code": "KX-1", "part": "steps"}).status_code
            == 401
        )
        stranger = {"actor": "stranger@elsewhere.invalid", "code": "KX-1", "part": "steps", "text": "x"}
        got = client.post(f"/curriculum/page/{path}", json=stranger, headers=H)
        assert got.status_code == 403 and "Show ten beads" not in got.text, path


def test_reading_a_page_gives_bullets_slips_materials_and_what_the_maker_and_checker_said(client, conn):
    drafted_page(conn)
    got = post(client, "read")
    assert got.status_code == 200
    page = got.json()
    parts = {p["part"]: p for p in page["parts"]}
    assert (
        parts["steps"]["items"] == STEPS
        and parts["steps"]["source"] == "drafted"
        and parts["steps"]["check_me"]
    )
    assert parts["thinking"]["slips"] == SLIPS and parts["thinking"]["idea"] == "t"
    assert page["materials"]["text"] == "Beads, Rope"
    assert page["draft"]["maker"] == "k2_page_draft v4" and page["draft"]["checker"] == "k2_page_check v1"
    assert page["draft"]["verdict"] == "agree"
    assert post(client, "read", code="NOPE").status_code == 404


def test_confirming_keeps_the_words_and_makes_them_the_persons(client, conn):
    drafted_page(conn)
    got = post(client, "confirm", part="steps").json()
    steps = next(p for p in got["parts"] if p["part"] == "steps")
    assert (steps["source"], steps["check_me"], steps["items"]) == ("person", False, STEPS)


def test_editing_takes_a_list_for_the_steps_and_an_idea_with_slips_for_the_thinking_or_plain_text(
    client, conn
):
    drafted_page(conn)
    steps = post(client, "edit", part="steps", items=["Sit.", "Count."]).json()
    assert next(p for p in steps["parts"] if p["part"] == "steps")["items"] == ["Sit.", "Count."]
    thinking = post(
        client, "edit", part="thinking", idea="New.", slips=[{"keyword": "skips one", "spot": "Gap."}]
    ).json()
    t = next(p for p in thinking["parts"] if p["part"] == "thinking")
    assert (t["idea"], t["slips"], t["source"]) == (
        "New.",
        [{"keyword": "skips one", "spot": "Gap."}],
        "person",
    )
    text = post(client, "edit", part="level_1", text="My level one.").json()
    assert next(p for p in text["parts"] if p["part"] == "level_1")["text"] == "My level one."


def test_reverting_takes_the_draft_back_and_leaves_the_part_empty(client, conn):
    drafted_page(conn)
    got = post(client, "revert", part="steps").json()
    steps = next(p for p in got["parts"] if p["part"] == "steps")
    assert (steps["text"], steps["items"], steps["source"]) == ("", [], "")


def test_the_schools_words_and_a_persons_own_cannot_be_answered_and_a_bad_edit_is_refused(client, conn):
    drafted_page(conn, objective="the school's own")
    for path, extra in (("confirm", {}), ("revert", {}), ("edit", {"text": "x"})):
        got = post(client, path, part="objective", **extra)
        assert got.status_code == 409 and "not a drafted part" in got.json()["detail"], path
    assert (
        next(p for p in post(client, "read").json()["parts"] if p["part"] == "objective")["text"]
        == "the school's own"
    )
    assert post(client, "edit", part="steps", items=[]).status_code == 422
    assert post(client, "edit", part="steps", text="  ").status_code == 422
    post(client, "confirm", part="steps")
    assert post(client, "confirm", part="steps").status_code == 409, (
        "a part a person has made theirs is not a draft"
    )
