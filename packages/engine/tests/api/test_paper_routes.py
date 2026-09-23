"""Make papers over HTTP: the website asks what a paper would hold, then asks for it in a teacher's name."""

import os

import pytest
from fastapi.testclient import TestClient

from engine.api import deps
from engine.api.app import app
from engine.core import db

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

KEY = "test-engine-key"
HEADERS = {"X-Engine-Key": KEY}
ASK = {"week": "2026-W39", "areas": [{"skill_set": "SUB.2D2D", "level": "Easy", "n": 4}]}


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def client(conn, monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", KEY)
    app.dependency_overrides[deps.get_conn] = lambda: (yield conn)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def child(conn):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    return str(
        conn.execute(
            "insert into child (tenant_id, roll_no, section, band) values (%s,'1','PAPERTEST','G2') returning id",
            (tenant,),
        ).fetchone()["id"]
    )


def test_a_teacher_previews_a_paper_then_it_prints_in_their_name(client, child, conn):
    plan = client.post(f"/child/{child}/paper/plan", headers=HEADERS, json=ASK)
    assert plan.status_code == 200 and plan.json()["n"] == 4
    made = client.post(f"/child/{child}/paper", headers=HEADERS, json={**ASK, "by": "teacher@school.test"})
    assert made.status_code == 200, made.text
    row = conn.execute(
        "select kind, approved_by from sheet_instance where qr_code = %s", (made.json()["qr"],)
    )
    assert dict(row.fetchone()) == {"kind": "custom", "approved_by": "teacher@school.test"}


def test_a_request_the_bank_cannot_fill_says_why(client, child):
    bad = {**ASK, "areas": [{"skill_set": "SUB.1D1D", "level": "Hard", "n": 4}]}
    r = client.post(f"/child/{child}/paper/plan", headers=HEADERS, json=bad)
    assert r.status_code == 409 and "has no level 'Hard'" in r.json()["detail"]
    assert (
        client.post(f"/child/{child}/paper/plan", headers=HEADERS, json={**ASK, "areas": []}).status_code
        == 422
    )
