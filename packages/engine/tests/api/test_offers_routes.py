"""Staff list and answer the skills waiting for a person (engine/api/routes/offers.py, goals/m1-12c-skill-offers.yaml)."""

import os

import pytest
from fastapi.testclient import TestClient

from engine.api import deps
from engine.api.app import app
from tests.test_skill_offers import CODE, made
from tests.test_skill_offers import conn as conn  # noqa: PLC0414

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
KEY = "test-engine-key"
H = {"X-Engine-Key": KEY}


@pytest.fixture
def client(conn, monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", KEY)
    conn.execute(
        "update config set value = 'true'::jsonb where key = 'educator.timetable_enabled'"
    )  # the gate: open
    t, _ = made(conn)
    app.dependency_overrides[deps.get_conn] = lambda: conn
    app.dependency_overrides[deps.get_tenant_id] = lambda: str(t)
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


WHO = {"actor": "lead@school.invalid"}


def test_it_needs_the_key_and_a_member_of_staff(client):
    assert client.post("/curriculum/offers/list", json=WHO).status_code == 401
    got = client.post("/curriculum/offers/list", json={"actor": "stranger@elsewhere.invalid"}, headers=H)
    assert got.status_code == 403 and CODE not in got.text


def test_the_list_is_what_the_screen_reads(client):
    (offer,) = client.post("/curriculum/offers/list", json=WHO, headers=H).json()["offers"]
    assert set(offer) == {"id", "kind", "activity", "skills", "also", "confidence", "reason"}
    assert offer["kind"] == "offer" and offer["activity"]["code"] == CODE
    assert [s["code"] for s in offer["skills"]] == ["NUM.CNT.02"] and [s["code"] for s in offer["also"]] == [
        "NUM.CNT.01"
    ]


def test_yes_adds_the_skill_and_the_list_that_is_left_comes_back(client, conn):
    (offer,) = client.post("/curriculum/offers/list", json=WHO, headers=H).json()["offers"]
    got = client.post("/curriculum/offers/answer", json={**WHO, "id": offer["id"], "yes": True}, headers=H)
    assert got.status_code == 200 and got.json() == {"offers": []}
    rows = conn.execute(
        "select skill_code, source from activity_skill where activity_code = %s", (CODE,)
    ).fetchall()
    assert [(r["skill_code"], r["source"]) for r in rows] == [("NUM.CNT.02", "machine")]


def test_no_adds_nothing_and_an_answer_to_what_is_not_waiting_is_refused(client, conn):
    (offer,) = client.post("/curriculum/offers/list", json=WHO, headers=H).json()["offers"]
    assert (
        client.post(
            "/curriculum/offers/answer", json={**WHO, "id": offer["id"], "yes": False}, headers=H
        ).status_code
        == 200
    )
    assert (
        conn.execute("select count(*) as n from activity_skill where activity_code = %s", (CODE,)).fetchone()[
            "n"
        ]
        == 0
    )
    again = client.post("/curriculum/offers/answer", json={**WHO, "id": offer["id"], "yes": True}, headers=H)
    assert again.status_code == 409 and "not waiting" in again.json()["detail"]
