"""A worksheet prints (goals/s3-worksheet-library.yaml): the engine renders it the first time it is
asked for, through the same renderer as a child's paper, and serves it from disk after that."""

import os

import pytest
from fastapi.testclient import TestClient

from engine.api import deps
from engine.api.app import app
from engine.core import db
from engine.w2_print import library

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

KEY = "test-engine-key"


@pytest.fixture
def conn():
    with db.connect() as c:
        library.build(c)
        yield c
        c.rollback()


@pytest.fixture
def client(conn, monkeypatch, tmp_path):
    from engine.api.routes import library as route

    monkeypatch.setenv("ENGINE_KEY", KEY)
    monkeypatch.setattr(library, "PDF_DIR", tmp_path)
    monkeypatch.setattr(route, "PRINTS", tmp_path / "prints")
    app.dependency_overrides[deps.get_conn] = lambda: (yield conn)
    with TestClient(app, headers={"X-Engine-Key": KEY}) as c:
        yield c
    app.dependency_overrides.clear()


def test_a_worksheet_prints_as_a_pdf_and_is_served_from_disk_the_second_time(client, tmp_path):
    first = client.get("/worksheet/R22-H03.pdf")
    assert first.status_code == 200
    assert first.headers["content-type"] == "application/pdf"
    assert first.content.startswith(b"%PDF")
    assert (tmp_path / "R22-H03.pdf").exists()
    assert client.get("/worksheet/R22-H03.pdf").content == first.content


def test_a_code_that_names_no_worksheet_is_not_found(client):
    assert client.get("/worksheet/R22-H99.pdf").status_code == 404
    assert client.get("/worksheet/..%2Fsecrets.pdf").status_code == 404


def test_a_worksheet_needs_the_engine_key(conn, monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", KEY)
    with TestClient(app) as c:
        assert c.get("/worksheet/R22-H03.pdf").status_code == 401


def test_a_worksheet_printed_for_two_children_is_one_pdf_of_two_copies_each_with_its_own_code(
    client, conn, tmp_path
):
    from engine.w2_print import handout

    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    kids = [
        str(conn.execute(
            "insert into child (tenant_id, roll_no, section, band) values (%s,%s,'PRINTTEST','G2') returning id",
            (tenant, roll),
        ).fetchone()["id"])
        for roll in ("1", "2")
    ]  # fmt: skip
    for k in kids:
        conn.execute(
            "insert into pii.child (tenant_id, child_id, first_name) values (%s,%s,'Test')", (tenant, k)
        )
    code = conn.execute(
        "select code from sheet_template where source = 'library' and retired_at is null order by code limit 1"
    ).fetchone()["code"]
    got = client.post(
        f"/worksheet/{code}/for.pdf", json={"children": kids, "week": "2026-W39", "by": "e@school"}
    )
    assert got.status_code == 200 and got.content.startswith(b"%PDF")
    codes = conn.execute(
        "select distinct qr_code from sheet_instance where child_id = any(%s::uuid[])", (kids,)
    ).fetchall()
    assert len(codes) == 2
    none = client.post(
        f"/worksheet/{code}/for.pdf", json={"children": [], "week": "2026-W39", "by": "e@school"}
    )
    assert none.status_code == 404
    assert handout.KIND == "custom"
