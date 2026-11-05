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
    # with no staff preview (D-076): a previewing coordinator is answered the list worked out and not kept, which
    # tests/test_educator_gate.py holds; here the switch alone decides
    conn.execute("update config set value = '[]' where key = 'educator.preview_roles'")
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


def test_a_list_that_is_not_there_is_not_found_not_a_crash(engine):
    client, conn, s = engine
    who = _coordinator(conn, s)
    ghost = "00000000-0000-4000-8000-000000000000"
    for route in ("read", "send"):
        got = client.post(
            f"/materials/school/{route}", headers=H, json={"actor": who, "consolidated_id": ghost}
        )
        assert got.status_code == 404, route


def test_a_bad_date_or_id_on_a_note_is_refused_before_any_model_call(engine, monkeypatch):
    client, conn, s = engine
    lid, _ = _list(conn, s)
    monkeypatch.setattr(
        llm, "generate", lambda *a, **k: pytest.fail("no model call for a note that cannot be filed")
    )
    for bad in ({"list_id": "nope", "needed_on": str(LO)}, {"list_id": str(lid), "needed_on": "31/12/2026"}):
        got = client.post("/materials/note", headers=H, data={"actor": s["email"], "note": "20 pens"} | bad)
        assert got.status_code == 422, bad


def test_the_coordinators_build_makes_every_class_list_and_names_the_classes_it_is_short_of(engine):
    client, conn, s = engine
    _list(conn, s)
    bare = m.another_class(conn, s, "T-bare")
    who = _coordinator(conn, s)
    got = client.post(
        "/materials/school/build", headers=H, json={"actor": who, "from": str(LO), "to": str(HI)}
    )
    assert got.status_code == 200, got.text
    body = got.json()
    assert [r["class_id"] for r in body["built"]] == [str(s["class"])]
    assert str(bare) in {r["class_id"] for r in body["no_plan"]}
    assert (
        body["no_materials"] == [] and body["no_fortnight"] == []
    )  # every shortness the build knows is returned


def _waiting_note(conn, s, lid, text="some pens"):
    return conn.execute(
        "insert into materials_note_review (tenant_id, list_id, text, reason, who) values (%s, %s, %s, 'no quantity', %s)"
        " returning id",
        (s["tenant"], lid, text, s["staff"]),
    ).fetchone()["id"]


def test_the_review_routes_are_for_the_coordinator_only(engine):
    client, conn, s = engine
    lid, _ = _list(conn, s)
    nid = _waiting_note(conn, s, lid)
    body = {
        "actor": s["email"],
        "note_id": str(nid),
        "material_code": "MAT-1",
        "quantity": 3,
        "needed_on": str(LO),
    }
    for path in ("/materials/review/list", "/materials/review/resolve", "/materials/review/dismiss"):
        assert client.post(path, headers=H, json=body | {"why": "x"}).status_code == 403, path


def test_a_coordinator_sees_the_waiting_notes_clears_one_and_sets_one_aside(engine):
    client, conn, s = engine
    lid, _ = _list(conn, s)
    pen = m.item(conn, s, "Pen", "piece")
    first, second = _waiting_note(conn, s, lid, "some pens"), _waiting_note(conn, s, lid, "a thing")
    who = _coordinator(conn, s)
    seen = client.post("/materials/review/list", headers=H, json={"actor": who}).json()["notes"]
    assert [n["text"] for n in seen] == ["some pens", "a thing"]
    done = client.post(
        "/materials/review/resolve",
        headers=H,
        json={
            "actor": who,
            "note_id": str(first),
            "material_code": pen,
            "quantity": 30,
            "needed_on": str(LO),
        },
    )
    assert done.status_code == 200, done.text
    again = client.post(
        "/materials/review/resolve",
        headers=H,
        json={
            "actor": who,
            "note_id": str(first),
            "material_code": pen,
            "quantity": 30,
            "needed_on": str(LO),
        },
    )
    assert again.status_code == 409
    set_aside = client.post(
        "/materials/review/dismiss",
        headers=H,
        json={"actor": who, "note_id": str(second), "why": "not a material"},
    )
    assert set_aside.status_code == 200, set_aside.text
    assert client.post("/materials/review/list", headers=H, json={"actor": who}).json()["notes"] == []


def test_a_review_that_cannot_be_done_says_why_in_words(engine):
    client, conn, s = engine
    lid, clay = _list(conn, s)
    nid = _waiting_note(conn, s, lid)
    who = _coordinator(conn, s)
    base = {"actor": who, "note_id": str(nid), "needed_on": str(LO)}
    cases = [
        ({"material_code": "MAT-9999", "quantity": 3}, 422),
        ({"material_code": clay, "quantity": 0}, 422),
        ({"material_code": clay, "quantity": 3, "needed_on": "31/12/2026"}, 422),
    ]
    for extra, want in cases:
        got = client.post("/materials/review/resolve", headers=H, json=base | extra)
        assert got.status_code == want, (extra, got.text)
    assert client.post("/materials/review/dismiss", headers=H, json=base | {"why": " "}).status_code == 422
    unknown = base | {"note_id": "00000000-0000-0000-0000-000000000000", "why": "x"}
    assert client.post("/materials/review/dismiss", headers=H, json=unknown).status_code == 404


def test_a_coordinator_approves_a_word_and_a_unit_and_a_clash_is_said_in_words(engine):
    client, conn, s = engine
    pen, pencil = m.item(conn, s, "Pen", "piece"), m.item(conn, s, "Pencil", "piece")
    who = _coordinator(conn, s)
    ok = client.post(
        "/materials/review/alias", headers=H, json={"actor": who, "word": "Ball Pen", "material_code": pen}
    )
    assert ok.status_code == 200, ok.text
    clash = client.post(
        "/materials/review/alias", headers=H, json={"actor": who, "word": "ball pen", "material_code": pencil}
    )
    assert clash.status_code == 409
    conv = {"actor": who, "material_code": pen, "unit": "dozen", "factor": 12}
    assert client.post("/materials/review/convert", headers=H, json=conv).status_code == 200
    for bad in ({"factor": 0}, {"unit": "piece"}, {"material_code": "MAT-9999"}):
        assert client.post("/materials/review/convert", headers=H, json=conv | bad).status_code == 422, bad
    assert (
        client.post(
            "/materials/review/alias",
            headers=H,
            json={"actor": s["email"], "word": "x", "material_code": pen},
        ).status_code
        == 403
    )
