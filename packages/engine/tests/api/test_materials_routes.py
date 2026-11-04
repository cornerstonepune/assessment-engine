"""The materials-list routes (engine/api/routes/materials.py): each refuses while educator.timetable_enabled is off and
for anyone who does not hold the class; when on, the educator builds, reads, edits and sends her list. The website's
calls run on the test's own transaction, rolled back; the rows are placeholders (tests/materials_rows.py)."""

import datetime as dt
import json
import os

import pytest
from fastapi.testclient import TestClient

from engine.api import deps
from engine.api.app import app
from engine.core import db
from tests import materials_rows as m

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
KEY = "test-engine-key"
H = {"X-Engine-Key": KEY}
END = m.MON + dt.timedelta(days=13)


@pytest.fixture
def engine(monkeypatch):
    monkeypatch.setenv("ENGINE_KEY", KEY)
    with db.connect() as conn:
        app.dependency_overrides[deps.get_conn] = lambda: conn
        try:
            with TestClient(app) as client:
                yield client, conn, m.school(conn)
        finally:
            app.dependency_overrides.clear()
            conn.rollback()


def _flag(conn, s, on=True):
    conn.execute(
        "insert into config (tenant_id, key, value, description) values (%s, 'educator.timetable_enabled', %s, 't')"
        " on conflict (tenant_id, key) do update set value = excluded.value",
        (s["tenant"], json.dumps(on)),
    )


def _plan(conn, s):
    clay = m.item(conn, s, "Clay", "packet")
    m.needs(conn, s, s["acts"][0], clay, 2)
    m.planned(conn, s, m.MON, s["acts"][0])
    return clay


def _build(client, s, actor=None):
    return client.post(
        "/materials/build",
        headers=H,
        json={
            "actor": actor or s["email"],
            "class_id": str(s["class"]),
            "period": "fortnight",
            "from": str(m.MON),
            "to": str(END),
        },
    )


def test_every_route_refuses_while_the_screens_are_off(engine):
    client, conn, s = engine
    _flag(conn, s, False)
    refused = _build(client, s)
    assert (refused.status_code, refused.json()["detail"]) == (403, "The timetable is not switched on.")
    assert client.post("/materials/reminders", headers=H, json={"actor": s["email"]}).status_code == 403


def test_a_route_needs_the_engine_key(engine):
    client, conn, s = engine
    assert client.post("/materials/build", json={}).status_code in (401, 500)


def test_someone_who_does_not_hold_the_class_is_refused(engine):
    client, conn, s = engine
    _flag(conn, s)
    staff = conn.execute(
        "insert into staff (tenant_id, campus_id) values (%s, %s) returning id", (s["tenant"], s["campus"])
    ).fetchone()["id"]
    conn.execute(
        "insert into pii.staff (tenant_id, staff_id, name, email) values (%s, %s, 'Placeholder Other', 'placeholder.other@example.test')",
        (s["tenant"], staff),
    )
    assert _build(client, s, actor="placeholder.other@example.test").status_code == 403


def test_build_read_edit_and_send_as_the_educator(engine):
    client, conn, s = engine
    _flag(conn, s)
    _plan(conn, s)
    built = _build(client, s)
    assert built.status_code == 200, built.text
    body = built.json()
    [line] = [ln for g in body["groups"] for ln in g["lines"]]
    assert (line["quantity"], line["unit"], line["tracked"]) == (2, "packet", False)
    lid = body["list_id"]
    put = client.post(
        "/materials/line/quantity",
        headers=H,
        json={"actor": s["email"], "line_id": line["line_id"], "quantity": 5},
    )
    assert put.status_code == 200
    got = client.post(
        "/materials/read", headers=H, json={"actor": s["email"], "list_id": lid, "group_by": "week"}
    ).json()
    assert got["groups"][0]["lines"][0]["quantity"] == 5
    sent = client.post(
        "/materials/send", headers=H, json={"actor": s["email"], "list_id": lid, "route": "whatsapp"}
    ).json()
    assert sent["wa_link"].startswith("https://wa.me/?text=") and "5 packet" in sent["text"]
    ack = client.post(
        "/materials/send/ack", headers=H, json={"actor": s["email"], "send_id": str(sent["send_id"])}
    )
    assert ack.status_code == 200


def test_a_new_item_is_proposed_and_a_line_outside_the_catalogue_is_refused(engine):
    client, conn, s = engine
    _flag(conn, s)
    _plan(conn, s)
    lid = _build(client, s).json()["list_id"]
    bad = client.post(
        "/materials/line/add",
        headers=H,
        json={
            "actor": s["email"],
            "list_id": lid,
            "material_code": "MAT-NOPE",
            "quantity": 1,
            "needed_on": str(m.MON),
        },
    )
    assert bad.status_code == 422
    new = client.post(
        "/materials/catalogue/propose",
        headers=H,
        json={"actor": s["email"], "name": "Feather duster", "unit": "piece"},
    ).json()
    ok = client.post(
        "/materials/line/add",
        headers=H,
        json={
            "actor": s["email"],
            "list_id": lid,
            "material_code": new["code"],
            "quantity": 1,
            "needed_on": str(m.MON),
        },
    )
    assert ok.status_code == 200


def test_the_reminder_inbox_lists_only_what_is_due(engine):
    client, conn, s = engine
    _flag(conn, s)
    _plan(conn, s)
    _build(client, s)
    got = client.post("/materials/reminders", headers=H, json={"actor": s["email"]})
    assert got.status_code == 200 and got.json()["reminders"] == []  # 2031 is far off: nothing is due yet


def test_removing_the_first_line_moves_the_reminders_to_the_next_day_a_material_is_needed(engine):
    client, conn, s = engine
    _flag(conn, s)
    first, later = m.item(conn, s, "Clay", "packet"), m.item(conn, s, "Bells")
    m.needs(conn, s, s["acts"][0], first, 1)
    m.needs(conn, s, s["acts"][1], later, 1)
    m.planned(conn, s, m.MON, s["acts"][0])
    m.planned(conn, s, m.MON + dt.timedelta(days=7), s["acts"][1])
    body = _build(client, s).json()

    def due():
        return {
            r["due_on"]
            for r in conn.execute("select due_on from reminder where list_id = %s", (body["list_id"],))
        }

    before = due()
    line = next(ln for g in body["groups"] for ln in g["lines"] if ln["material_code"] == first)
    assert (
        client.post(
            "/materials/line/remove", headers=H, json={"actor": s["email"], "line_id": line["line_id"]}
        ).status_code
        == 200
    )
    assert min(due()) == min(before) + dt.timedelta(days=7)


def test_a_range_that_ends_before_it_starts_is_refused_in_words_not_a_crash(engine):
    client, conn, s = engine
    _flag(conn, s)
    bad = client.post(
        "/materials/build",
        headers=H,
        json={
            "actor": s["email"],
            "class_id": str(s["class"]),
            "period": "week",
            "from": str(END),
            "to": str(m.MON),
        },
    )
    assert bad.status_code == 422 and "before" in bad.json()["detail"]


def test_a_quantity_on_a_removed_line_is_refused(engine):
    client, conn, s = engine
    _flag(conn, s)
    _plan(conn, s)
    body = _build(client, s).json()
    line = body["groups"][0]["lines"][0]["line_id"]
    client.post("/materials/line/remove", headers=H, json={"actor": s["email"], "line_id": line})
    again = client.post(
        "/materials/line/quantity", headers=H, json={"actor": s["email"], "line_id": line, "quantity": 3}
    )
    assert again.status_code == 409
