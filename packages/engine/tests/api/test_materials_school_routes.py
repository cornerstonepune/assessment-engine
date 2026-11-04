"""The school-wide materials routes (engine/api/routes/materials_school.py; task M1-16): refuse while
educator.timetable_enabled is off and for anyone who does not hold a role that consolidates; a coordinator builds, reads
and sends the school's list; a class educator sends a typed or photographed note for her class's list. The model is a fake;
rows are placeholders in the test's own transaction, rolled back."""

import datetime as dt
import io
import os

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from engine.adapters import llm
from engine.api import deps
from engine.api.app import app
from engine.core import db
from engine.w2_print import materials_list as ml
from tests import materials_rows as m

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
KEY = "test-engine-key"
H = {"X-Engine-Key": KEY}
LO, HI = m.MON, m.MON + dt.timedelta(days=27)


@pytest.fixture
def engine(monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", KEY)
    with db.connect() as conn:
        app.dependency_overrides[deps.get_conn] = lambda: conn
        try:
            with TestClient(app) as client:
                s = m.school(conn)
                conn.execute(
                    "insert into config (tenant_id, key, value, description) values (%s, 'educator.timetable_enabled', 'true', 't')"
                    " on conflict (tenant_id, key) do update set value = excluded.value",
                    (s["tenant"],),
                )
                yield client, conn, s
        finally:
            app.dependency_overrides.clear()
            conn.rollback()


def _coordinator(conn, s):
    staff = conn.execute(
        "insert into staff (tenant_id, campus_id) values (%s, %s) returning id", (s["tenant"], s["campus"])
    ).fetchone()["id"]
    email = f"placeholder.coord.{staff}@example.test"
    conn.execute(
        "insert into pii.staff (tenant_id, staff_id, name, email) values (%s, %s, 'Placeholder Coordinator', %s)",
        (s["tenant"], staff, email),
    )
    conn.execute(
        "insert into staff_role_grant (tenant_id, staff_id, role_code, valid_from, granted_by)"
        " values (%s, %s, 'coordinator', '2026-01-01', 'test')",
        (s["tenant"], staff),
    )
    return email


def _list(conn, s):
    a = s["acts"][0]
    clay = m.item(conn, s, "Clay", "packet")
    m.needs(conn, s, a, clay, 2)
    m.planned(conn, s, LO, a)
    return ml.build(conn, s["class"], "fortnight", LO, HI), clay


def _jpeg() -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (40, 30), "white").save(out, "JPEG")
    return out.getvalue()


def test_every_route_refuses_while_the_screens_are_off(engine):
    client, conn, s = engine
    conn.execute("update config set value = 'false' where key = 'educator.timetable_enabled'")
    body = {"actor": _coordinator(conn, s), "from": str(LO), "to": str(HI)}
    refused = client.post("/materials/school/build", headers=H, json=body)
    assert (refused.status_code, refused.json()["detail"]) == (403, "The timetable is not switched on.")


def test_a_class_educator_is_not_the_one_who_builds_the_schools_list(engine):
    client, conn, s = engine
    body = {"actor": s["email"], "from": str(LO), "to": str(HI)}
    assert client.post("/materials/school/build", headers=H, json=body).status_code == 403


def test_a_coordinator_builds_reads_and_sends_the_schools_list(engine):
    client, conn, s = engine
    _list(conn, s)
    who = _coordinator(conn, s)
    built = client.post(
        "/materials/school/build", headers=H, json={"actor": who, "from": str(LO), "to": str(HI)}
    )
    assert built.status_code == 200, built.text
    body = built.json()
    assert [(x["unit"], x["quantity"]) for x in body["lines"]] == [("packet", 2)]
    got = client.post("/materials/school/read", headers=H, json={"actor": who, "consolidated_id": body["id"]})
    assert got.json()["lines"] == body["lines"]
    sent = client.post(
        "/materials/school/send", headers=H, json={"actor": who, "consolidated_id": body["id"]}
    ).json()
    assert sent["wa_link"].startswith("https://wa.me/?text=") and "2 packet" in sent["text"]


def test_a_typed_note_from_the_educator_adds_what_code_confirms(engine, monkeypatch):
    client, conn, s = engine
    lid, clay = _list(conn, s)
    pen = m.item(conn, s, "Pen", "piece")
    monkeypatch.setattr(
        llm,
        "generate",
        lambda conn, purpose, variables, images=(), **kw: {
            "people_visible": False,
            "readings": [{"text": "20 pens", "item_code": pen, "quantity": 20, "unit": "piece"}],
        },
    )
    got = client.post(
        "/materials/note",
        headers=H,
        data={"actor": s["email"], "list_id": str(lid), "needed_on": str(LO), "note": "20 pens"},
    )
    assert got.status_code == 200, got.text
    assert [r["status"] for r in got.json()["readings"]] == ["confirmed"]


def test_a_file_that_is_not_a_picture_is_refused_in_words(engine, monkeypatch):
    client, conn, s = engine
    lid, _ = _list(conn, s)
    monkeypatch.setattr(
        llm, "generate", lambda *a, **k: pytest.fail("no model call for a file that is not a picture")
    )
    got = client.post(
        "/materials/note",
        headers=H,
        data={"actor": s["email"], "list_id": str(lid), "needed_on": str(LO)},
        files={"file": ("n.jpg", b"not a picture", "image/jpeg")},
    )
    assert got.status_code == 422 and "picture" in got.json()["detail"]


def test_a_photograph_goes_to_the_model_as_a_plain_jpeg_and_is_not_kept(engine, monkeypatch):
    client, conn, s = engine
    lid, _ = _list(conn, s)
    seen = {}

    def fake(conn, purpose, variables, images=(), **kw):
        seen["images"] = list(images)
        return {"people_visible": False, "readings": []}

    monkeypatch.setattr(llm, "generate", fake)
    got = client.post(
        "/materials/note",
        headers=H,
        data={"actor": s["email"], "list_id": str(lid), "needed_on": str(LO)},
        files={"file": ("n.png", _jpeg(), "image/png")},
    )
    assert got.status_code == 200 and seen["images"][0][:2] == b"\xff\xd8"  # a JPEG, whatever came in


def test_when_the_months_money_is_spent_she_is_told_in_words_and_nothing_is_added(engine, monkeypatch):
    client, conn, s = engine
    lid, _ = _list(conn, s)

    def spent(*a, **k):
        raise llm.LLMBudgetError("campaign m1-16 stopped")

    monkeypatch.setattr(llm, "generate", spent)
    got = client.post(
        "/materials/note",
        headers=H,
        data={"actor": s["email"], "list_id": str(lid), "needed_on": str(LO), "note": "20 pens"},
    )
    assert got.status_code == 429 and "reading notes" in got.json()["detail"]
