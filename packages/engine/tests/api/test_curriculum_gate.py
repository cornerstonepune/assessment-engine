"""The curriculum screens answer to the educator gate (goals/m1-13b-curriculum-on-the-shell.yaml; D-076, w2_print/educator_gate.py):
the page and offers routes answer when `educator.timetable_enabled` is on or the member of staff holds a role
`educator.preview_roles` names, and are refused otherwise, before anything is read or changed. A preview only looks
(D-076): the routes that change something need the switch itself."""

import os

import pytest
from fastapi.testclient import TestClient

from engine.api import deps
from engine.api.app import app
from tests import test_k2_draft as base
from tests.test_k2_page import drafted_page

conn = base.conn
pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
KEY = "test-engine-key"
H = {"X-Engine-Key": KEY}
WHO = {"actor": "x@school.invalid"}
OFF = "The curriculum screens are not switched on."
LOOK = "The preview only looks: the curriculum screens are not switched on."
WRITES = ("page/confirm", "page/revert", "page/edit", "offers/answer")


@pytest.fixture
def client(conn, monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", KEY)
    app.dependency_overrides[deps.get_conn] = lambda: conn
    app.dependency_overrides[deps.get_tenant_id] = lambda: str(conn.t)
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def _switch(conn, on: bool):
    conn.execute(
        "update config set value = %s::jsonb where key = 'educator.timetable_enabled'",
        ("true" if on else "false",),
    )


def _grant(conn, role: str):
    conn.execute(
        "insert into staff_role_grant (tenant_id, staff_id, role_code, valid_from, granted_by)"
        " values (%s, %s, %s, current_date - 1, 'test')",
        (conn.t, conn.staff, role),
    )


def calls():
    part = {**WHO, "code": "KX-1", "part": "steps"}
    return {
        "page/read": {**WHO, "code": "KX-1"},
        "page/confirm": part,
        "page/revert": part,
        "page/edit": {**part, "text": "x"},
        "offers/list": WHO,
        "offers/answer": {**WHO, "id": "00000000-0000-0000-0000-000000000000", "yes": False},
    }


def test_switched_off_every_route_is_refused_to_staff_with_no_preview_role_and_nothing_changes(client, conn):
    drafted_page(conn)
    _switch(conn, False)
    before = conn.execute("select steps from activity where code = 'KX-1'").fetchone()["steps"]
    for path, body in calls().items():
        got = client.post(f"/curriculum/{path}", json=body, headers=H)
        assert (got.status_code, got.json()["detail"]) == (403, OFF), path
    assert conn.execute("select steps from activity where code = 'KX-1'").fetchone()["steps"] == before
    assert (
        conn.execute(
            "select source from activity_part_source where activity_code = 'KX-1' and part = 'steps'"
        ).fetchone()["source"]
        == "drafted"
    )


def test_switched_off_a_role_the_preview_names_may_look(client, conn):
    drafted_page(conn)
    _switch(conn, False)
    _grant(conn, "head")
    assert client.post("/curriculum/page/read", json={**WHO, "code": "KX-1"}, headers=H).status_code == 200
    assert client.post("/curriculum/offers/list", json=WHO, headers=H).status_code == 200


def test_switched_off_a_preview_changes_nothing(client, conn):
    drafted_page(conn)
    _switch(conn, False)
    _grant(conn, "head")
    before = conn.execute("select steps from activity where code = 'KX-1'").fetchone()["steps"]
    for path in WRITES:
        got = client.post(f"/curriculum/{path}", json=calls()[path], headers=H)
        assert (got.status_code, got.json()["detail"]) == (403, LOOK), path
    assert conn.execute("select steps from activity where code = 'KX-1'").fetchone()["steps"] == before


def test_a_role_the_preview_does_not_name_gets_nothing(client, conn):
    drafted_page(conn)
    _switch(conn, False)
    _grant(conn, "ops")
    assert client.post("/curriculum/page/read", json={**WHO, "code": "KX-1"}, headers=H).status_code == 403


def test_switched_on_staff_may_look_and_change_and_a_stranger_is_refused(client, conn):
    drafted_page(conn)
    _switch(conn, True)
    assert client.post("/curriculum/page/read", json={**WHO, "code": "KX-1"}, headers=H).status_code == 200
    kept = client.post("/curriculum/page/confirm", json=calls()["page/confirm"], headers=H)
    assert kept.status_code == 200, kept.text
    stranger = {"actor": "stranger@elsewhere.invalid", "code": "KX-1"}
    got = client.post("/curriculum/page/read", json=stranger, headers=H)
    assert got.status_code == 403 and got.json()["detail"] not in (
        OFF,
        LOOK,
    )  # not on the staff list: the old refusal
