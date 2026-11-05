"""The drafted-pages sheet as a download (engine/api/routes/gold.py): staff only, never anywhere but the browser that asked
(goals/m1-11h-gold-sheet-delivery.yaml). The school's lesson text is on it and this repository's logs are public."""

import csv
import io
import os

import pytest
from fastapi.testclient import TestClient

from engine.api import deps
from engine.api.app import app
from engine.api.routes import gold as gold_route
from engine.w1_bank import map_ledger
from tests import test_k2_draft as base

conn = base.conn
FULL, Scripted, _act, drafted, run, AGREE = (
    base.FULL,
    base.Scripted,
    base._act,
    base.drafted,
    base.run,
    base.AGREE,
)

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
KEY = "test-engine-key"
H = {"X-Engine-Key": KEY}
URL = "/curriculum/gold-sheet.csv"


@pytest.fixture
def client(conn, monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", KEY)
    monkeypatch.setattr(
        gold_route, "config", lambda: {"band": base.BAND}
    )  # the test's own band, not the school's
    app.dependency_overrides[deps.get_conn] = lambda: conn
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.clear()


def _drafted(conn):
    _act(
        conn,
        "KX-1",
        "Activity KX-1",
        strand="Block Room",
        materials="two boxes",
        objective="the school's own",
    )
    run(
        conn,
        Scripted({("k2_page_draft", "KX-1"): [drafted()], ("k2_page_check", "KX-1"): [AGREE]}),
    )


def test_it_needs_the_engines_key(client, conn):
    assert client.get(URL, params={"by": "x@school.invalid"}).status_code == 401


def test_a_sign_in_that_is_not_on_the_staff_list_gets_nothing(client, conn):
    _drafted(conn)
    got = client.get(URL, params={"by": "stranger@elsewhere.invalid"}, headers=H)
    assert got.status_code == 403 and "KX-1" not in got.text and "two boxes" not in got.text


def test_a_member_of_staff_gets_a_csv_to_save_that_is_never_kept_by_a_cache(client, conn):
    _drafted(conn)
    got = client.get(URL, params={"by": "x@school.invalid"}, headers=H)
    assert got.status_code == 200
    assert got.headers["content-type"].startswith("text/csv")
    assert got.headers["content-disposition"].startswith("attachment;")
    assert got.headers["cache-control"] == "no-store"
    (row,) = csv.DictReader(io.StringIO(got.text))
    assert row["code"] == "KX-1" and row["materials"] == "two boxes" and row["steps_by"] == "drafted"
    assert row["verdict"] == "" and row["what_is_wrong"] == ""


def test_what_the_machine_said_of_a_draft_is_not_in_what_is_sent(client, conn):
    _drafted(conn)
    (p,) = map_ledger.standing(conn, conn.t)
    text = client.get(URL, params={"by": "x@school.invalid"}, headers=H).text
    for said in (p["reason"], "describes the activity", "auto_passed", "needs_person", "confidence"):
        assert said not in text, said


def test_how_many_pages_is_bounded(client, conn):
    assert client.get(URL, params={"by": "x@school.invalid", "pages": 0}, headers=H).status_code == 422
    assert client.get(URL, params={"by": "x@school.invalid", "pages": 101}, headers=H).status_code == 422


def test_the_two_checkers_csv_is_staff_only_and_never_cached(client, conn):
    base._two_checkers(conn)
    _act(conn, "KX-1", "Activity KX-1", objective="the school's own", materials="two boxes")
    run(
        conn,
        Scripted(
            {
                ("k2_page_draft", "KX-1"): [drafted()],
                ("k2_page_check", "KX-1"): [AGREE],
                ("k2_page_check_b", "KX-1"): [base.FAULT],
            }
        ),
    )
    url = "/curriculum/checkers.csv"
    assert client.get(url, params={"by": "x@school.invalid"}).status_code == 401
    got = client.get(url, params={"by": "stranger@elsewhere.invalid"}, headers=H)
    assert got.status_code == 403 and "two boxes" not in got.text
    got = client.get(url, params={"by": "x@school.invalid"}, headers=H)
    assert got.status_code == 200 and got.headers["cache-control"] == "no-store"
    (row,) = csv.DictReader(io.StringIO(got.text))
    assert row["school_materials"] == "two boxes" and row["second_verdict"] == "disagree"
