"""K2 voice notes, the tables (supabase/migrations/20261226090000_k2_voice_notes.sql, goals/m1-01-voice-intake.yaml).

Every row here is a placeholder made inside the test's own transaction and rolled back: no school data.
"""

import datetime as dt
import os
import uuid

import psycopg
import pytest

from engine.core import db
from tests.rows import a_child, tenant

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _school(conn):
    """A K2 class, its educator and one enrolled child (roll number 7), all placeholders."""
    t = tenant(conn)
    campus = conn.execute("select id from campus where tenant_id = %s limit 1", (t,)).fetchone()["id"]
    year = conn.execute(
        "insert into academic_year (tenant_id, label, starts_on, ends_on) values (%s, '2031-32', '2031-04-01',"
        " '2032-03-31') on conflict (tenant_id, label) do update set label = excluded.label returning id",
        (t,),
    ).fetchone()["id"]
    klass = conn.execute(
        "insert into school_class (tenant_id, campus_id, academic_year_id, grade_code, section)"
        " values (%s, %s, %s, 'K2', %s) returning id",
        (t, campus, year, f"T{uuid.uuid4().hex[:5]}"),
    ).fetchone()["id"]
    staff = conn.execute(
        "insert into staff (tenant_id, campus_id) values (%s, %s) returning id", (t, campus)
    ).fetchone()["id"]
    child = a_child(conn)
    activity = conn.execute("select code from activity where tenant_id = %s limit 1", (t,)).fetchone()["code"]
    return {"tenant": t, "class": klass, "staff": staff, "child": child, "activity": activity}


def _note(conn, s, **over):
    v = {"audio_key": f"voice/{uuid.uuid4().hex}.m4a", "transcript": "Activity 2. Above 7."} | over
    return conn.execute(
        "insert into pii.educator_note (tenant_id, staff_id, class_id, audio_key, transcript)"
        " values (%s, %s, %s, %s, %s) returning *",
        (s["tenant"], s["staff"], s["class"], v["audio_key"], v["transcript"]),
    ).fetchone()


def _observe(conn, s, note=None, **over):
    v = {
        "confirmation_id": uuid.uuid4(),
        "outcome": "above",
        "entry_mode": "individual",
        "route": "voice" if note else "form",
        "expected_level": 2,
        "observed_at": dt.datetime.now(dt.UTC) - dt.timedelta(hours=1),
        "supersedes": None,
        "reason": None,
    } | over
    return conn.execute(
        "insert into activity_observation (tenant_id, confirmation_id, note_id, activity_code, child_id, class_id,"
        " outcome, entry_mode, route, expected_level, observed_at, observed_by, confirmed_by, supersedes, reason)"
        " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) returning *",
        (
            s["tenant"], v["confirmation_id"], note and note["id"], s["activity"], s["child"], s["class"],
            v["outcome"], v["entry_mode"], v["route"], v["expected_level"], v["observed_at"], s["staff"],
            s["staff"], v["supersedes"], v["reason"],
        ),
    ).fetchone()  # fmt: skip


def _refused(conn, error, sql, *args):
    with pytest.raises(error), conn.transaction():
        conn.execute(sql, args)


def test_an_observation_is_never_edited_or_deleted_and_a_correction_names_what_it_replaces(conn):
    s = _school(conn)
    first = _observe(conn, s)
    _refused(
        conn,
        psycopg.errors.RaiseException,
        "update activity_observation set outcome = 'below' where id = %s",
        first["id"],
    )
    _refused(
        conn, psycopg.errors.RaiseException, "delete from activity_observation where id = %s", first["id"]
    )
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        _observe(conn, s, supersedes=first["id"])  # a correction without a reason
    fixed = _observe(conn, s, outcome="below", supersedes=first["id"], reason="misheard the number")
    assert fixed["supersedes"] == first["id"]


def test_the_database_keeps_its_own_clock_and_a_future_teaching_time_is_refused(conn):
    s = _school(conn)
    row = _observe(conn, s, observed_at=dt.datetime(2020, 1, 6, 9, tzinfo=dt.UTC))
    now = conn.execute("select now() as n").fetchone()["n"]
    assert row["stored_at"] == now  # not what the phone said
    assert (
        row["curriculum_version"] is not None
        or conn.execute(
            "select count(*) n from curriculum_version where tenant_id = %s", (s["tenant"],)
        ).fetchone()["n"]
        == 0
    )
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        _observe(conn, s, observed_at=dt.datetime.now(dt.UTC) + dt.timedelta(days=1))


def test_the_rest_did_as_expected_is_only_ever_as_expected_and_a_voice_row_names_its_note(conn):
    s = _school(conn)
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        _observe(conn, s, entry_mode="group_as_expected", outcome="above")
    with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
        _observe(conn, s, route="voice")  # no note
    with pytest.raises(psycopg.errors.ForeignKeyViolation), conn.transaction():
        _observe(conn, s, outcome="secure")  # not a word of the school's
    assert (
        _observe(conn, s, entry_mode="group_as_expected", outcome="as_expected")["entry_mode"]
        == "group_as_expected"
    )
    note = _note(conn, s)
    assert _observe(conn, s, note=note)["note_id"] == note["id"]


def test_a_note_keeps_when_it_reached_us_and_its_status_is_a_word_of_the_school(conn):
    s = _school(conn)
    note = _note(conn, s)
    assert note["status"] == "received"
    conn.execute(
        "update pii.educator_note set received_at = '2020-01-01', audio_key = 'x', status = 'drafted' where id = %s",
        (note["id"],),
    )
    after = conn.execute("select * from pii.educator_note where id = %s", (note["id"],)).fetchone()
    assert (after["received_at"], after["audio_key"], after["status"]) == (
        note["received_at"],
        note["audio_key"],
        "drafted",
    )
    _refused(
        conn,
        psycopg.errors.ForeignKeyViolation,
        "update pii.educator_note set status = 'lost' where id = %s",
        note["id"],
    )


def test_her_decision_on_each_line_is_written_once(conn):
    s = _school(conn)
    note = _note(conn, s)
    claim = conn.execute(
        "insert into pii.note_claim (tenant_id, note_id, section, read_as, words, span_start, span_end, decision,"
        " kept_as, decided_by, decided_at) values (%s, %s, 'above', '7', 'Above 7', 12, 19, 'changed', '17', %s,"
        " '2020-01-01') returning id, decided_at",
        (s["tenant"], note["id"], s["staff"]),
    ).fetchone()
    assert claim["decided_at"] == conn.execute("select now() as n").fetchone()["n"]  # the database's clock
    claim = claim["id"]
    _refused(
        conn,
        psycopg.errors.RaiseException,
        "update pii.note_claim set decision = 'accepted' where id = %s",
        claim,
    )
    _refused(
        conn, psycopg.errors.CheckViolation,
        "insert into pii.note_claim (tenant_id, note_id, section, read_as, words, span_start, span_end, decision,"
        " decided_by) values (%s, %s, 'above', '7', 'Above 7', 12, 19, 'changed', %s)",
        s["tenant"], note["id"], s["staff"],
    )  # fmt: skip


def test_the_engine_writes_and_never_deletes_and_the_website_never_sees_a_note(conn):
    s = _school(conn)
    note = _note(conn, s)
    _observe(conn, s, note=note)
    conn.execute("set local role app_engine")
    assert (
        conn.execute("select count(*) n from pii.educator_note where id = %s", (note["id"],)).fetchone()["n"]
        == 1
    )
    for table in (
        "activity_observation",
        "pii.educator_note",
        "pii.note_claim",
        "observation_outcome",
        "note_status",
    ):
        _refused(conn, psycopg.errors.InsufficientPrivilege, f"delete from {table}")
    conn.rollback()
    s = _school(conn)
    _observe(conn, s)
    conn.execute("set local role app_web")
    assert conn.execute("select count(*) n from activity_observation").fetchone()["n"] >= 1
    assert conn.execute("select count(*) n from observation_outcome").fetchone()["n"] >= 5
    for sql in (
        "select * from pii.educator_note",
        "select * from pii.note_claim",
        "update activity_observation set reason = 'x'",
        "delete from activity_observation",
    ):
        _refused(conn, psycopg.errors.InsufficientPrivilege, sql)  # fmt: skip


def test_the_words_and_the_waiting_time_are_rows_and_audio_is_kept_until_retention_is_decided(conn):
    t = tenant(conn)
    words = lambda table: [  # noqa: E731
        r["code"]
        for r in conn.execute(f"select code from {table} where tenant_id = %s order by ord", (t,)).fetchall()
    ]
    assert words("observation_outcome") == ["above", "as_expected", "below", "not_willing", "absent"]
    assert words("observation_entry_mode") == ["individual", "group_as_expected"]
    assert words("observation_route") == ["voice", "form"]
    assert words("note_status") == ["received", "drafted", "confirmed", "left_unconfirmed"]
    assert words("claim_decision") == ["accepted", "changed", "removed"]
    config = {
        r["key"]: r["value"]
        for r in conn.execute(
            "select key, value from config where tenant_id = %s and key like 'voice.%%'", (t,)
        )
    }
    assert (config["voice.confirm_within_hours"], config["voice.audio_retention_days"]) == (48, None)


def test_a_correction_is_of_the_same_child_and_activity_in_the_same_school_and_happens_once(conn):
    s = _school(conn)
    first = _observe(conn, s)
    other = _school(conn)  # another child, the same school
    fix = {"supersedes": first["id"], "reason": "misheard"}
    other_school = _another_school(conn)
    for wrong in (
        other,  # another child
        s | {"activity": _another_activity(conn, s)},  # another activity
        s
        | {
            "tenant": other_school,
            "activity": _activity_in(conn, other_school, s["activity"]),
        },  # another school
    ):
        with pytest.raises(psycopg.errors.ForeignKeyViolation) as e, conn.transaction():
            _observe(conn, wrong, **fix)
        assert e.value.diag.constraint_name.startswith("activity_observation_supersedes"), (
            e.value.diag.constraint_name
        )
    _observe(conn, s, outcome="below", **fix)
    with pytest.raises(psycopg.errors.UniqueViolation), conn.transaction():
        _observe(conn, s, outcome="as_expected", **fix)  # the same row corrected twice
    mine = uuid.uuid4()
    _refused(
        conn,
        psycopg.errors.CheckViolation,
        "insert into activity_observation (id, tenant_id, confirmation_id, activity_code, child_id, class_id, outcome,"
        " entry_mode, route, expected_level, observed_at, observed_by, confirmed_by, supersedes, reason)"
        " values (%s,%s,%s,%s,%s,%s,'above','individual','form',2,now(),%s,%s,%s,'itself')",
        mine, s["tenant"], uuid.uuid4(), s["activity"], s["child"], s["class"], s["staff"], s["staff"], mine,
    )  # fmt: skip


def test_a_confirmed_note_keeps_its_words_and_class_and_no_note_goes_back(conn):
    s = _school(conn)
    note = _note(conn, s)
    conn.execute("update pii.educator_note set status = 'drafted' where id = %s", (note["id"],))
    _refused(
        conn,
        psycopg.errors.CheckViolation,
        "update pii.educator_note set status = 'received' where id = %s",
        note["id"],
    )
    conn.execute(
        "update pii.educator_note set transcript = 'Activity 3. Above 7.' where id = %s", (note["id"],)
    )
    conn.execute("update pii.educator_note set status = 'confirmed' where id = %s", (note["id"],))
    other = _school(conn)["class"]
    for sql, arg in (
        ("update pii.educator_note set transcript = 'Activity 9.' where id = %s", None),
        ("update pii.educator_note set class_id = %s where id = %s", other),
        ("update pii.educator_note set status = 'left_unconfirmed' where id = %s", None),
    ):
        _refused(conn, psycopg.errors.CheckViolation, sql, *([arg] if arg else []), note["id"])


def _another_activity(conn, s):
    return conn.execute(
        "select code from activity where tenant_id = %s and code <> %s limit 1", (s["tenant"], s["activity"])
    ).fetchone()["code"]


def _another_school(conn):
    return conn.execute(
        "insert into tenant (slug, name) values (%s, 'Placeholder school') returning id",
        (f"t-{uuid.uuid4().hex[:8]}",),
    ).fetchone()["id"]


def _activity_in(conn, tenant, code):
    """The same activity given to a placeholder school, so only the correction's own key can refuse."""
    conn.execute(
        "insert into activity (tenant_id, code, band, strand, name) select %s, code, band, strand, name"
        " from activity where code = %s limit 1",
        (tenant, code),
    )
    return code
