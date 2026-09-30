"""The maker over HTTP (goal m3-the-maker): see the papers, make them in an educator's name — once, however often
the form is sent — and print them as one."""

import os

import pytest
from fastapi.testclient import TestClient

from engine.api import deps
from engine.api.app import app
from engine.core import db

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

KEY = "test-engine-key"
HEADERS = {"X-Engine-Key": KEY}
SECTION = "MAKERROUTES"


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
def kids(conn):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    return [
        str(
            conn.execute(
                "insert into child (tenant_id, roll_no, section, band) values (%s,%s,%s,'G2') returning id",
                (tenant, roll, SECTION),
            ).fetchone()["id"]
        )
        for roll in ("1", "2")
    ]


def _batch(kids, **more):
    return {
        "section": SECTION,
        "week": "2026-W40",
        "kind": "practice",
        "way": "same",
        "children": kids,
        "areas": [{"skill_set": "SUB.2D2D", "level": "Easy", "n": 3}],
        **more,
    }


def test_an_educator_sees_the_papers_makes_them_once_and_prints_them_as_one(client, kids, conn):
    plan = client.post("/papers/plan", headers=HEADERS, json=_batch(kids))
    assert plan.status_code == 200, plan.text
    assert [p["n"] for p in plan.json()["papers"]] == [3, 3] and plan.json()["refused"] == []

    sent = _batch(kids, by="educator@school.test", once="form-1")
    made = client.post("/papers/make", headers=HEADERS, json=sent)
    assert made.status_code == 200, made.text
    assert made.json()["papers"] == 2 and made.json()["already"] is False
    again = client.post("/papers/make", headers=HEADERS, json=sent)
    assert again.json()["qrs"] == made.json()["qrs"] and again.json()["already"] is True, (
        "sent twice, made once"
    )
    n = conn.execute(
        "select count(*) as n from sheet_instance si join child c on c.id = si.child_id where c.section = %s",
        (SECTION,),
    ).fetchone()["n"]
    assert n == 2

    pdf = client.get("/papers/pack.pdf", headers=HEADERS, params={"qr": made.json()["qrs"]})
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    assert client.get("/papers/pack.pdf", headers=HEADERS, params={"qr": ["CS000000"]}).status_code == 404


def test_a_batch_that_cannot_be_made_says_why(client, kids):
    bad = client.post("/papers/plan", headers=HEADERS, json=_batch(kids, kind="homework"))
    assert bad.status_code == 409 and "class practice" in bad.json()["detail"]
    nothing = client.post(
        "/papers/make", headers=HEADERS, json=_batch(kids, way="own", areas=[], by="e", once="f")
    )
    assert nothing.status_code == 409 and "roll 1" in nothing.json()["detail"], (
        "a child with nothing to work on"
    )
