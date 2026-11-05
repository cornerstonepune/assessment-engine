"""The consolidated list goes to the one inventory person by WhatsApp (task M1-16; D-071, D-074: "the inventory person
gets a proper final list"). A structured checklist, the link recorded with what was sent and when; delivery cannot be
known. Written before the code."""

import datetime as dt
import os
from urllib.parse import parse_qs, urlsplit

import pytest

from engine.core import db
from engine.w2_print import materials_consolidate as mc
from engine.w2_print import materials_inventory as inv
from engine.w2_print import materials_list as ml
from tests import materials_rows as m

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
LO, HI = m.MON, m.MON + dt.timedelta(days=27)


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _consolidated(conn):
    s = m.school(conn)
    a = s["acts"][0]
    clay = m.item(conn, s, "Clay", "packet")
    m.needs(conn, s, a, clay, 2)
    m.planned(conn, s, LO, a)
    ml.build(conn, s["class"], "fortnight", LO, HI)
    return s, mc.build(conn, s["tenant"], LO, HI)


def test_the_inventory_person_gets_one_checklist_and_what_was_sent_is_recorded(conn):
    s, cid = _consolidated(conn)
    conn.execute(
        "insert into config (tenant_id, key, value, description) values (%s, 'materials.inventory_whatsapp_to', '\"+91 98765 43210\"', 't')"
        " on conflict (tenant_id, key) do update set value = excluded.value",
        (s["tenant"],),
    )
    out = inv.send(conn, cid, s["staff"])
    first, *lines = out["text"].splitlines()
    assert (
        "materials" in first
        and len(lines) == 1
        and lines[0].startswith("[ ] Clay")
        and ": 2 packet" in lines[0]
    )
    parts = urlsplit(out["wa_link"])
    assert parts.path == "/919876543210" and parse_qs(parts.query)["text"] == [out["text"]]
    row = conn.execute(
        "select * from materials_consolidated_send where id = %s", (out["send_id"],)
    ).fetchone()
    assert (row["text"], row["who"], row["status"]) == (out["text"], s["staff"], "opened")
    assert row["at"] is not None


def test_a_line_whose_total_is_not_known_is_sent_as_to_confirm_never_as_a_number(conn):
    s = m.school(conn)
    a = s["acts"][0]
    glue = m.item(conn, s, "Glue", "bottle")
    m.needs(conn, s, a, glue, None)
    m.planned(conn, s, LO, a)
    ml.build(conn, s["class"], "fortnight", LO, HI)
    out = inv.send(conn, mc.build(conn, s["tenant"], LO, HI), s["staff"])
    assert "quantity to confirm (bottle)" in out["text"]


def test_a_second_send_after_a_change_marks_what_changed(conn):
    s = m.school(conn)
    a = s["acts"][0]
    clay = m.item(conn, s, "Clay", "packet")
    m.needs(conn, s, a, clay, 2)
    m.planned(conn, s, LO, a)
    lid = ml.build(conn, s["class"], "fortnight", LO, HI)
    inv.send(conn, mc.build(conn, s["tenant"], LO, HI), s["staff"])
    [line] = [ln for g in ml.read(conn, lid)["groups"] for ln in g["lines"]]
    ml.set_quantity(conn, line["line_id"], 6, s["staff"])
    out = inv.send(conn, mc.build(conn, s["tenant"], LO, HI), s["staff"])
    assert any("changed: was 2, now 6" in ln for ln in out["text"].splitlines())
