"""Sending the materials list, the reminders and the inbox (goals/m1-10-materials-list.yaml; task M1-10; D-070, D-071,
D-072). Placeholder rows inside the test's own transaction, rolled back."""

import datetime as dt
import json
import os
from urllib.parse import parse_qs, urlsplit

import psycopg
import pytest

from engine.core import db
from engine.w2_print import materials_list as ml
from engine.w2_print import materials_remind as rem
from engine.w2_print import materials_send as send
from tests import materials_rows as m

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

D1 = m.MON
END = m.MON + dt.timedelta(days=13)
LONG_BEFORE = dt.date(2031, 9, 1)


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _set(conn, s, key, value):
    conn.execute(
        "insert into config (tenant_id, key, value, description) values (%s, %s, %s, 'test')"
        " on conflict (tenant_id, key) do update set value = excluded.value",
        (s["tenant"], key, json.dumps(value)),
    )


def _list(conn, s, qty=2):
    """A list with two lines: Clay (qty, needed Mon D1) and Bells (no quantity given, needed D1 + 2)."""
    a, b = s["acts"][:2]
    clay, bell = m.item(conn, s, "Clay", "packet"), m.item(conn, s, "Bells", "piece")
    m.needs(conn, s, a, clay, qty)
    m.needs(conn, s, b, bell, None)
    m.planned(conn, s, D1, a)
    m.planned(conn, s, D1 + dt.timedelta(days=2), b)
    return ml.build(conn, s["class"], "fortnight", m.MON, END)


@pytest.fixture
def s(conn):
    return m.school(conn)


def test_the_flag_is_off_until_the_school_turns_it_on(conn, s):
    assert ml.enabled(conn) is False
    _set(conn, s, "educator.timetable_enabled", True)
    assert ml.enabled(conn) is True


def test_whatsapp_send_writes_the_checklist_records_it_and_returns_a_link_to_nobody_until_a_number_is_set(
    conn, s
):
    lid = _list(conn, s)
    out = send.send(conn, lid, "whatsapp", s["staff"])
    lines = out["text"].splitlines()
    assert lines[0].startswith("K2") and "materials" in lines[0]
    assert len(lines) == 3 and lines[1].startswith("[ ] Clay") and ": 2 packet, needed Mon 3 Nov" in lines[1]
    assert "quantity to confirm (piece)" in lines[2]
    parts = urlsplit(out["wa_link"])
    assert parts.netloc == "wa.me" and parts.path == "/" and parse_qs(parts.query)["text"] == [out["text"]]
    row = conn.execute("select * from materials_send where id = %s", (out["send_id"],)).fetchone()
    assert (row["route"], row["status"], row["who"], row["text"]) == (
        "whatsapp",
        "opened",
        s["staff"],
        out["text"],
    )
    assert (
        conn.execute("select state from materials_list where id = %s", (lid,)).fetchone()["state"] == "sent"
    )


def test_the_link_chooses_the_number_the_school_has_named(conn, s):
    lid = _list(conn, s)
    _set(conn, s, "materials.whatsapp_to", "+91 98765 43210")
    assert urlsplit(send.send(conn, lid, "whatsapp", s["staff"])["wa_link"]).path == "/919876543210"


def test_what_was_sent_is_what_the_list_said_then_not_what_it_says_now(conn, s):
    lid = _list(conn, s)
    out = send.send(conn, lid, "whatsapp", s["staff"])
    [line] = [
        x for g in ml.read(conn, lid, "day")["groups"] for x in g["lines"] if x["item"].startswith("Clay")
    ]
    ml.set_quantity(conn, line["line_id"], 9, s["staff"])
    assert (
        conn.execute("select text from materials_send where id = %s", (out["send_id"],)).fetchone()["text"]
        == out["text"]
    )
    with pytest.raises(psycopg.Error):
        conn.execute("update materials_send set text = 'other'")


def test_email_has_no_sender_so_it_is_recorded_as_not_configured_and_the_list_stays_a_draft(conn, s):
    lid = _list(conn, s)
    out = send.send(conn, lid, "email", s["staff"])
    assert out["status"] == "not configured" and out["wa_link"] is None
    assert (
        conn.execute("select status from materials_send where id = %s", (out["send_id"],)).fetchone()[
            "status"
        ]
        == "not configured"
    )
    assert (
        conn.execute("select state from materials_list where id = %s", (lid,)).fetchone()["state"] == "draft"
    )


def test_an_empty_list_is_not_sent(conn, s):
    lid = ml.build(conn, s["class"], "fortnight", m.MON, END)
    with pytest.raises(send.NothingToSend):
        send.send(conn, lid, "whatsapp", s["staff"])


def test_the_team_has_it_is_one_tick_by_the_educator_and_is_not_doubled(conn, s):
    out = send.send(conn, _list(conn, s), "whatsapp", s["staff"])
    send.team_has_it(conn, out["send_id"], s["staff"])
    send.team_has_it(conn, out["send_id"], s["staff"])
    assert (
        conn.execute(
            "select count(*) as n from materials_send_ack where send_id = %s", (out["send_id"],)
        ).fetchone()["n"]
        == 1
    )


def test_reminders_follow_the_first_day_a_material_is_needed_for_the_educator_and_the_team(conn, s):
    lid = _list(conn, s)
    rem.sync(conn, lid, today=LONG_BEFORE)
    got = conn.execute(
        "select weeks_before, audience, due_on, at_once from reminder where list_id = %s", (lid,)
    ).fetchall()
    assert {(r["weeks_before"], r["audience"], r["due_on"]) for r in got} == {
        (w, a, D1 - dt.timedelta(weeks=w)) for w in (2, 1) for a in ("educator", "team")
    }
    assert not any(r["at_once"] for r in got)


def test_the_lead_times_are_read_from_the_setting(conn, s):
    lid = _list(conn, s)
    _set(conn, s, "materials.reminder_weeks", [3])
    rem.sync(conn, lid, today=LONG_BEFORE)
    assert {
        r["weeks_before"]
        for r in conn.execute("select weeks_before from reminder where list_id = %s", (lid,))
    } == {3}


def test_a_vacation_moves_the_day_and_a_day_gone_by_is_sent_at_once(conn, s):
    lid = _list(conn, s)
    conn.execute(
        "insert into fortnight (tenant_id, academic_year_id, number, kind, starts_on, ends_on)"
        " select tenant_id, academic_year_id, null, 'vacation', %s, %s from fortnight where id = %s",
        (D1 - dt.timedelta(days=20), D1 - dt.timedelta(days=1), s["fortnight"]),
    )
    rem.sync(conn, lid, today=LONG_BEFORE)
    due = {
        r["weeks_before"]: r["due_on"]
        for r in conn.execute(
            "select weeks_before, due_on from reminder where list_id = %s and audience = 'educator'", (lid,)
        )
    }
    assert due == {
        2: D1 - dt.timedelta(days=21),
        1: D1 - dt.timedelta(days=21),
    }  # the last working day before the break
    rem.sync(conn, lid, today=D1 - dt.timedelta(days=3))
    late = conn.execute("select due_on, at_once from reminder where list_id = %s", (lid,)).fetchall()
    assert {(r["due_on"], r["at_once"]) for r in late} == {(D1 - dt.timedelta(days=3), True)}


def test_after_the_list_is_sent_nothing_is_reminded_and_a_rebuild_makes_no_new_reminder(conn, s):
    lid = _list(conn, s)
    rem.sync(conn, lid, today=LONG_BEFORE)
    send.send(conn, lid, "whatsapp", s["staff"])
    states = {r["state"] for r in conn.execute("select state from reminder where list_id = %s", (lid,))}
    assert states == {"cancelled"}
    ml.build(conn, s["class"], "fortnight", m.MON, END)
    rem.sync(conn, lid, today=LONG_BEFORE)
    assert {r["state"] for r in conn.execute("select state from reminder where list_id = %s", (lid,))} == {
        "cancelled"
    }


def test_the_inbox_holds_one_message_for_a_list_whatever_number_of_reminders_are_due(conn, s):
    lid = _list(conn, s)
    today = D1 - dt.timedelta(days=3)
    rem.sync(conn, lid, today=today)  # both lead times have passed: both go today, together
    [one] = [x for x in rem.inbox(conn, today, s["class"])]
    assert (one["list_id"], one["due_on"], one["weeks_before"], one["at_once"]) == (lid, today, [2, 1], True)
    assert one["first_needed"] == D1


def test_the_inbox_holds_nothing_before_the_day_and_nothing_after_a_send(conn, s):
    lid = _list(conn, s)
    rem.sync(conn, lid, today=LONG_BEFORE)
    assert rem.inbox(conn, LONG_BEFORE, s["class"]) == []
    day = D1 - dt.timedelta(weeks=1)
    assert len(rem.inbox(conn, day, s["class"])) == 1
    send.send(conn, lid, "whatsapp", s["staff"])
    assert rem.inbox(conn, day, s["class"]) == []


def test_the_command_counts_what_is_due_and_changes_nothing(conn, s):
    lid = _list(conn, s)
    rem.sync(conn, lid, today=LONG_BEFORE)
    before = conn.execute("select count(*) as n, max(updated_at) as t from reminder").fetchone()
    got = rem.due_counts(conn, D1 - dt.timedelta(weeks=1), s["tenant"])
    assert (got["reminders"], got["lists"], got["educator"], got["team"]) == (4, 1, 2, 2)
    assert conn.execute("select count(*) as n, max(updated_at) as t from reminder").fetchone() == before


def test_reminders_start_again_when_a_list_that_was_emptied_has_a_line_again(conn, s):
    lid = _list(conn, s)
    rem.sync(conn, lid, today=LONG_BEFORE)
    for g in ml.read(conn, lid)["groups"]:
        for ln in g["lines"]:
            ml.remove(conn, ln["line_id"], s["staff"])
    rem.sync(conn, lid, today=LONG_BEFORE)
    assert {r["state"] for r in conn.execute("select state from reminder where list_id = %s", (lid,))} == {
        "cancelled"
    }
    code = m.item(conn, s, "Chalk")
    ml.add(conn, lid, code, 1, D1, None, s["staff"])
    rem.sync(conn, lid, today=LONG_BEFORE)
    assert {r["state"] for r in conn.execute("select state from reminder where list_id = %s", (lid,))} == {
        "pending"
    }


def test_the_inbox_shows_a_member_of_staff_only_the_classes_she_holds(conn, s):
    lid = _list(conn, s)
    today = D1 - dt.timedelta(days=3)
    rem.sync(conn, lid, today=today)
    other = conn.execute(
        "insert into staff (tenant_id, campus_id) values (%s, %s) returning id", (s["tenant"], s["campus"])
    ).fetchone()["id"]
    assert len(rem.inbox(conn, today, None, s["staff"])) == 1
    assert rem.inbox(conn, today, None, other) == []


def test_an_email_that_could_not_be_sent_is_not_a_send_the_team_can_have(conn, s):
    lid = _list(conn, s)
    out = send.send(conn, lid, "email", s["staff"])
    assert ml.read(conn, lid)["last_send"] is None
    with pytest.raises(send.NotSent):
        send.team_has_it(conn, out["send_id"], s["staff"])
