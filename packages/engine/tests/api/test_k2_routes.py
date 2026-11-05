"""The K2 read routes (engine/api/routes/k2.py): the same keyed, actor-named, switched-off-means-403 pattern as the voice
routes. The website's calls run on the test's own transaction, rolled back; the rows are placeholders."""

import json
import os

import pytest
from fastapi.testclient import TestClient

from engine.api import deps
from engine.api.app import app
from engine.core import db
from tests.test_k2_reads import CLEAN, _coordinator, another_class
from tests.voice_rows import a_k2_class, a_note

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
KEY = "test-engine-key"
ROUTES = ("/k2/todo", "/k2/coordinator", "/k2/picture", "/k2/child")


@pytest.fixture
def engine(monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", KEY)
    with db.connect() as conn:
        app.dependency_overrides[deps.get_conn] = lambda: conn
        try:
            with TestClient(app) as client:
                yield client, conn
        finally:
            app.dependency_overrides.clear()
            conn.rollback()


def _switch(conn, on: bool):
    conn.execute(
        "update config set value = %s::jsonb where key = 'voice.screens_enabled'",
        ("true" if on else "false",),
    )


def _body(path, k):
    return (
        {"actor": k["email"], "class_id": k["class"], "roll_no": "1"}
        if path in ROUTES[2:]
        else {"actor": k["email"]}
    )


def _post(client, path, body, key=KEY):
    return client.post(path, json=body, headers={"X-Engine-Key": key})


def test_every_k2_read_refuses_while_voice_notes_are_switched_off(engine):
    client, conn = engine
    k = a_k2_class(conn)
    _switch(conn, False)
    for path in ROUTES:
        r = _post(client, path, _body(path, k))
        assert (r.status_code, r.json()["detail"]) == (403, "Voice notes are not switched on."), path


def test_every_k2_read_needs_the_engines_key(engine):
    client, conn = engine
    k = a_k2_class(conn)
    _switch(conn, True)
    for path in ROUTES:
        assert _post(client, path, _body(path, k), key="wrong").status_code == 401, path


def test_the_todo_is_only_the_signed_in_educators_own(engine):
    client, conn = engine
    mine, theirs = a_k2_class(conn), another_class(conn)
    _switch(conn, True)
    a_note(conn, mine, CLEAN)
    a_note(conn, theirs, CLEAN)
    r = _post(client, "/k2/todo", {"actor": mine["email"]})
    assert r.status_code == 200, r.text
    assert r.json()["groups"]["to_confirm"]["count"] == 1
    assert _post(client, "/k2/todo", {"actor": "nobody@example.test"}).status_code == 403


def test_the_coordinators_list_is_refused_to_an_educator_and_given_to_a_coordinator(engine):
    client, conn = engine
    k = a_k2_class(conn)
    me = _coordinator(conn, k)
    _switch(conn, True)
    assert _post(client, "/k2/coordinator", {"actor": k["email"]}).status_code == 403
    r = _post(client, "/k2/coordinator", {"actor": me})
    assert r.status_code == 200, r.text
    assert set(r.json()) == {"rows", "counts"}


def test_the_answers_have_no_field_a_parent_could_be_shown_that_is_not_theirs(engine):
    """There is no parent role yet. The schema of every K2 answer has no field for a name, 'not willing' or an
    internal label, so a parent role added later cannot reach one through these calls."""
    client, _ = engine
    schema = client.get("/openapi.json").json()
    text = json.dumps({p: v for p, v in schema["paths"].items() if p.startswith("/k2/")}).lower()
    assert "/k2/todo" in text and "/k2/picture" in text and "/k2/child" in text
    for banned in ("not_willing", "not willing", "first_name", "last_name", "email_address", "transcript"):
        assert banned not in text, banned


def test_the_picture_and_a_childs_page_reach_only_staff_of_that_class(engine):
    client, conn = engine
    k, other = a_k2_class(conn), a_k2_class(conn)
    _switch(conn, True)
    r = _post(client, "/k2/picture", {"actor": k["email"], "class_id": k["class"]})
    assert r.status_code == 200, r.text
    assert [c["roll_no"] for c in r.json()["children"]] == ["1", "2", "3", "4", "5"] and r.json()[
        "skills"
    ] == []
    assert _post(client, "/k2/picture", {"actor": other["email"], "class_id": k["class"]}).status_code == 403
    one = _post(client, "/k2/child", {"actor": k["email"], "class_id": k["class"], "roll_no": "3"})
    assert (one.status_code, one.json()["roll_no"], one.json()["skills"]) == (200, "3", [])
    assert (one.json()["growth"], one.json()["ready_next"]) == ([], []), "the route carries M1-17's two lists"
    assert (
        _post(client, "/k2/child", {"actor": k["email"], "class_id": k["class"], "roll_no": "99"}).status_code
        == 404
    )


# ---- M1-17: the picture and a child's page answer the staff preview while the switch is off (D-076, educator_gate) ----


def test_the_staff_preview_sees_the_picture_and_a_child_while_the_switch_is_off_and_nobody_else_does(engine):
    client, conn = engine
    k = a_k2_class(conn)
    preview = _coordinator(conn, k)  # a coordinator: a role `educator.preview_roles` names
    _switch(conn, False)
    for path, body in (
        ("/k2/picture", {"actor": preview, "class_id": k["class"]}),
        ("/k2/child", {"actor": preview, "class_id": k["class"], "roll_no": "1"}),
    ):
        assert _post(client, path, body).status_code == 200, path
    # her own class teacher is not the preview: switched off still means no
    for path in ROUTES[2:]:
        r = _post(client, path, _body(path, k))
        assert (r.status_code, r.json()["detail"]) == (403, "Voice notes are not switched on."), path
    # a sign-in not on the staff list is not the preview either
    r = _post(client, "/k2/picture", {"actor": "nobody@example.test", "class_id": k["class"]})
    assert (r.status_code, r.json()["detail"]) == (403, "Voice notes are not switched on.")


def test_the_preview_changes_nothing_else_the_to_do_and_the_coordinator_list_still_wait_for_the_switch(
    engine,
):
    client, conn = engine
    k = a_k2_class(conn)
    preview = _coordinator(conn, k)
    _switch(conn, False)
    for path in ROUTES[:2]:
        assert _post(client, path, {"actor": preview}).status_code == 403, path


def test_a_preview_role_that_is_not_named_is_not_the_preview(engine):
    client, conn = engine
    k = a_k2_class(conn)
    who = _coordinator(conn, k)
    conn.execute("update config set value = '[\"head\"]'::jsonb where key = 'educator.preview_roles'")
    _switch(conn, False)
    assert _post(client, "/k2/picture", {"actor": who, "class_id": k["class"]}).status_code == 403
