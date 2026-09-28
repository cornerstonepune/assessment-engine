"""N11 — Friday's class card (goals/w4a-class-card.yaml, `w4_close/card.py`). The graph is written directly — it is
Ring B, a pure function of the evidence, and what the card reads; the database is the local copy, rolled back."""

import os
import uuid

import pytest

from engine.assess import focus
from engine.core import db
from engine.w4_close import card

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def section(conn):
    """Five children in one Grade 2 section; the fifth has no checked paper."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    name = f"T{uuid.uuid4().hex[:5]}"
    kids = [
        conn.execute(
            "insert into child (tenant_id, roll_no, section, band) values (%s,%s,%s,'G2') returning id",
            (tenant, str(i), name),
        ).fetchone()["id"]
        for i in range(1, 6)
    ]

    def state(child, skill, rung, st, n, right, mistake=None):
        conn.execute(
            "insert into child_skill_state (tenant_id, child_id, skill_code, rung_code, state, n_events, n_correct,"
            " repeating_misconception) values (%s,%s,%s,%s,%s,%s,%s,%s)",
            (tenant, child, skill, rung, st, n, right, mistake),
        )

    a, b, c, d, _ = kids
    state(a, "NUM.OPS.02", "R24", "stretch_ready", 8, 8)
    state(b, "NUM.OPS.02", "R24", "patterned_error", 6, 2, "M_SMALL_FROM_LARGE")
    state(c, "NUM.OPS.02", "R24", "patterned_error", 5, 2, "M_SMALL_FROM_LARGE")
    state(d, "NUM.OPS.02", "R24", "emerging", 4, 1)
    state(d, "NUM.OPS.01", "R24", "secure", 5, 5)  # the same rung twice: the child sits where weakest
    state(a, "NUM.OPS.01", "R22", "not_enough_yet", 2, 2)
    return name, [str(k) for k in kids]


def test_the_card_groups_every_child_on_every_skill_from_the_graph_alone(conn, section):
    """Nimish: "After 34 evaluations, the system is able to see that there are certain areas where the child lags."
    The card is those areas for a whole class: every child on every skill set they have evidence on, in the graph's
    own groups, the reteach groups by the named mistake they repeat, and a child with no checked paper named."""
    name, (a, b, c, d, e) = section
    got = card.build(conn, name)
    sub = next(s for s in got["skills"] if s["rung"] == "R24")
    assert sub["skill_set"] == "SUB.2D2D"
    g = sub["groups"]
    assert g["move_up"] == [a] and g["emerging"] == [d] and g["secure"] == [], "d sits once, where weakest"
    assert set(g["reteach"]["M_SMALL_FROM_LARGE"]["children"]) == {b, c}
    assert g["reteach"]["M_SMALL_FROM_LARGE"]["name"], "a mistake is shown by its name"
    add = next(s for s in got["skills"] if s["rung"] == "R22")
    assert add["groups"]["not_enough_yet"] == [a]
    fifth = next(ch for ch in got["children"] if ch["child_id"] == e)
    assert fifth["home"] is None and fifth["why"] == "no checked paper yet"
    assert len(got["children"]) == 5
    with pytest.raises(ValueError, match="no class"):
        card.build(conn, "NOSUCH")


def test_the_card_names_each_childs_home_area_as_w2_would_make_it(conn, section, monkeypatch):
    """Nimish: "based on the skill set evaluation, the system should be able to create an assessment that's very
    specific to the child". The card names the one area that child's home paper works on — W2's own choice
    (`focus_paper.home_area`), never a second rule written here."""
    name, (a, b, c, d, e) = section
    asked = []

    def home_area(conn, child_id, states):
        asked.append(str(child_id))
        if str(child_id) == b:
            return [
                focus.Area("SUB.2D2D", "NUM.OPS.02", "Easy", 2, 6, "M_SMALL_FROM_LARGE", "patterned_error")
            ]
        return []

    monkeypatch.setattr(card.focus_paper, "home_area", home_area)
    got = {ch["child_id"]: ch for ch in card.build(conn, name)["children"]}
    assert sorted(asked) == sorted([a, b, c, d]), "asked for every child with evidence, not for one without"
    assert got[b]["home"]["skill_set"] == "SUB.2D2D" and got[b]["home"]["level"] == "Easy"
    assert got[b]["home"]["mistake_name"], "the mistake the paper is aimed at, by its name"
    assert got[a]["home"] is None and got[a]["why"]


def test_the_card_is_kept_as_the_weeks_rows_and_confirmed_once_by_name(conn, section):
    name, (a, b, c, d, e) = section
    built = card.build(conn, name)
    assert card.store(conn, name, "2026-W40", built) == 2
    assert card.store(conn, name, "2026-W40", built) == 2, "rebuilding replaces the week's rows"
    rows = conn.execute(
        "select rung_code, move_up, reteach, groups from class_card where section = %s and week = '2026-W40'",
        (name,),
    ).fetchall()
    r24 = next(r for r in rows if r["rung_code"] == "R24")
    assert [str(x) for x in r24["move_up"]] == [a] and set(r24["reteach"]["M_SMALL_FROM_LARGE"]) == {b, c}
    assert len(rows) == 2 and r24["groups"]["emerging"] == [d]

    with pytest.raises(ValueError, match="names the educator"):
        card.confirm(conn, name, "2026-W40", "", built)
    card.confirm(conn, name, "2026-W40", "neha", built)
    assert card.confirmed(conn, name, "2026-W40")["by"] == "neha"
    import psycopg

    with pytest.raises(psycopg.errors.RaiseException):
        conn.execute("update class_card_confirmation set by = 'x' where section = %s", (name,))


def test_the_card_over_http_is_the_cards_and_its_confirmation_names_the_educator(conn, section, monkeypatch):
    from fastapi.testclient import TestClient

    from engine.api import deps
    from engine.api.app import app

    monkeypatch.setenv("ENGINE_KEY", "k")
    app.dependency_overrides[deps.get_conn] = lambda: (yield conn)
    name, (a, *_) = section
    try:
        with TestClient(app, headers={"X-Engine-Key": "k"}) as client:
            r = client.get(f"/card/{name}/2026-W40")
            assert r.status_code == 200, r.text
            assert r.json()["confirmed"] is None and len(r.json()["children"]) == 5
            assert client.post(f"/card/{name}/2026-W40/confirm", json={"by": "neha"}).status_code == 200
            assert client.get(f"/card/{name}/2026-W40").json()["confirmed"]["by"] == "neha"
            assert client.get("/card/NOSUCH/2026-W40").status_code == 404
            assert client.post(f"/card/{name}/2026-W40/confirm", json={"by": ""}).status_code == 422
    finally:
        app.dependency_overrides.clear()
