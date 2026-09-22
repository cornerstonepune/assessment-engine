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
    monkeypatch.setenv("ENGINE_KEY", KEY)
    monkeypatch.setattr(library, "PDF_DIR", tmp_path)
    app.dependency_overrides[deps.get_conn] = lambda: (yield conn)
    with TestClient(app, headers={"X-Engine-Key": KEY}) as c:
        yield c
    app.dependency_overrides.clear()


def test_a_worksheet_prints_as_a_pdf_and_is_served_from_disk_the_second_time(client, tmp_path):
    first = client.get("/worksheet/R5-H03.pdf")
    assert first.status_code == 200
    assert first.headers["content-type"] == "application/pdf"
    assert first.content.startswith(b"%PDF")
    assert (tmp_path / "R5-H03.pdf").exists()
    assert client.get("/worksheet/R5-H03.pdf").content == first.content


def test_a_code_that_names_no_worksheet_is_not_found(client):
    assert client.get("/worksheet/R5-H99.pdf").status_code == 404
    assert client.get("/worksheet/..%2Fsecrets.pdf").status_code == 404


def test_a_worksheet_needs_the_engine_key(conn, monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", KEY)
    with TestClient(app) as c:
        assert c.get("/worksheet/R5-H03.pdf").status_code == 401
