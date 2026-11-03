"""A K2 note confirmed, or the form saved: observations, then evidence, by code (engine/w3_read/voice_confirm.py).

Placeholder class, educator and children (tests/voice_rows.py), inside a rolled-back transaction: no school data.
"""

import os

import psycopg
import pytest

from engine.core import db
from engine.w3_read import voice_confirm as vc
from engine.w3_read import voice_store
from tests.voice_rows import a_k2_class, a_note

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _rows(conn, confirmation):
    return {
        str(r["child_id"]): r
        for r in conn.execute(
            "select * from activity_observation where confirmation_id = %s", (confirmation,)
        ).fetchall()
    }


def _evidence(conn, child):
    return conn.execute(
        "select skill_code, mark, kind, observation_id from evidence_event where child_id = %s order by skill_code",
        (child,),
    ).fetchall()


def test_a_confirmed_note_gives_one_row_a_child_and_evidence_on_each_skill_only_where_it_is_evidence(conn):
    k = a_k2_class(conn)
    note = a_note(
        conn, k, "Activity 12, level 2. Above 3. Below 1. Not willing 2. Absent 4. The rest did as expected."
    )
    final = vc.Confirmed(
        k["activity"], 2, {"above": ["3"], "below": ["1"], "not_willing": ["2"], "absent": ["4"]}, True
    )
    rows = _rows(conn, vc.confirm_note(conn, str(note["id"]), k["email"], final))
    c = k["children"]
    assert {str(r["child_id"]): (r["outcome"], r["entry_mode"]) for r in rows.values()} == {
        c["3"]: ("above", "individual"), c["1"]: ("below", "individual"), c["2"]: ("not_willing", "individual"),
        c["4"]: ("absent", "individual"), c["5"]: ("as_expected", "group_as_expected"),
    }  # fmt: skip
    assert all(r["route"] == "voice" and r["note_id"] == note["id"] for r in rows.values())
    marks = {child: {e["mark"] for e in _evidence(conn, child)} for child in c.values()}
    # level 2 expected: above reaches 3 (yes), as expected stays 2 (sometimes), below falls to 1 (not yet)
    assert marks == {
        c["3"]: {"yes"},
        c["5"]: {"sometimes"},
        c["1"]: {"not_yet"},
        c["2"]: set(),
        c["4"]: set(),
    }
    assert all(len(_evidence(conn, child)) == len(k["skills"]) for child in (c["3"], c["5"], c["1"]))
    assert all(
        e["kind"] == "observed" and e["observation_id"] == rows[c["3"]]["id"] for e in _evidence(conn, c["3"])
    )
    status = conn.execute("select status from pii.educator_note where id = %s", (note["id"],)).fetchone()[
        "status"
    ]
    assert status == "confirmed"


def test_without_the_rest_did_as_expected_a_child_not_named_gets_no_row(conn):
    k = a_k2_class(conn)
    note = a_note(conn, k, "Activity 12. Above 3.")
    rows = _rows(
        conn,
        vc.confirm_note(conn, str(note["id"]), k["email"], vc.Confirmed(k["activity"], 2, {"above": ["3"]})),
    )
    assert list(rows) == [k["children"]["3"]]


def test_her_decision_on_each_line_is_kept_beside_what_code_read(conn):
    k = a_k2_class(conn)
    note = a_note(conn, k, "Activity 12. Above 3. Below 31. Absent 4.")
    final = vc.Confirmed(k["activity"], 2, {"above": ["3"], "below": ["1"]})  # 31 was 1; absent removed
    vc.confirm_note(conn, str(note["id"]), k["email"], final)
    claims = {
        r["section"]: (r["read_as"], r["decision"], r["kept_as"])
        for r in conn.execute("select * from pii.note_claim where note_id = %s", (note["id"],)).fetchall()
    }
    assert claims == {
        "activity": (k["activity"], "accepted", None), "above": ("3", "accepted", None),
        "below": ("31", "changed", "1"), "absent": ("4", "removed", None),
    }  # fmt: skip


def test_a_number_not_in_the_class_or_a_child_in_two_lists_is_refused_and_writes_nothing(conn):
    k = a_k2_class(conn)
    note = a_note(conn, k, "Activity 12. Above 3.")
    for lists, words in (
        ({"above": ["31"]}, "not in this class"),
        ({"above": ["3"], "below": ["3"]}, "two lists"),
    ):
        with pytest.raises(voice_store.Refused, match=words), conn.transaction():
            vc.confirm_note(conn, str(note["id"]), k["email"], vc.Confirmed(k["activity"], 2, lists))
    assert (
        conn.execute(
            "select count(*) n from activity_observation where note_id = %s", (note["id"],)
        ).fetchone()["n"]
        == 0
    )


def test_an_incident_a_confirmed_note_and_someone_elses_note_are_never_confirmed(conn):
    k = a_k2_class(conn)
    incident = a_note(conn, k, "Incident. 10:30, 5 fell near the slide; the coordinator was told.")
    with pytest.raises(voice_store.Refused, match="incident"), conn.transaction():
        vc.confirm_note(conn, str(incident["id"]), k["email"], vc.Confirmed(k["activity"], 2, {}))
    note = a_note(conn, k, "Activity 12. Above 3.")
    vc.confirm_note(conn, str(note["id"]), k["email"], vc.Confirmed(k["activity"], 2, {"above": ["3"]}))
    with pytest.raises(voice_store.Refused, match="not waiting"), conn.transaction():
        vc.confirm_note(conn, str(note["id"]), k["email"], vc.Confirmed(k["activity"], 2, {"above": ["3"]}))
    other = a_k2_class(conn)
    theirs = a_note(conn, other, "Activity 12. Above 3.")
    with pytest.raises(voice_store.Refused, match="not one of your notes"), conn.transaction():
        vc.confirm_note(conn, str(theirs["id"]), k["email"], vc.Confirmed(k["activity"], 2, {"above": ["3"]}))


def test_a_note_about_an_earlier_day_is_taught_then_and_never_later_than_now(conn):
    k = a_k2_class(conn)
    note = a_note(conn, k, "Yesterday. Activity 12. Above 3.")
    rows = _rows(
        conn,
        vc.confirm_note(conn, str(note["id"]), k["email"], vc.Confirmed(k["activity"], 2, {"above": ["3"]})),
    )
    (row,) = rows.values()
    assert row["observed_at"] < note["received_at"] and row["observed_at"] <= row["stored_at"]


def test_the_form_saves_the_same_rows_without_a_note(conn):
    k = a_k2_class(conn)
    rows = _rows(
        conn,
        vc.save_form(conn, k["email"], k["class"], vc.Confirmed(k["activity"], 1, {"below": ["2"]}, True)),
    )
    assert len(rows) == 5 and all(r["route"] == "form" and r["note_id"] is None for r in rows.values())


def test_a_correction_is_a_new_row_naming_the_old_and_carries_its_own_evidence(conn):
    k = a_k2_class(conn)
    rows = _rows(
        conn, vc.save_form(conn, k["email"], k["class"], vc.Confirmed(k["activity"], 2, {"above": ["3"]}))
    )
    (old,) = rows.values()
    new = vc.correct(conn, str(old["id"]), k["email"], "below", "it was 3 below, misheard")
    row = conn.execute("select * from activity_observation where id = %s", (new,)).fetchone()
    assert (row["supersedes"], row["outcome"], row["reason"]) == (
        old["id"],
        "below",
        "it was 3 below, misheard",
    )
    assert {e["mark"] for e in _evidence(conn, k["children"]["3"]) if e["observation_id"] == new} == {
        "not_yet"
    }


def test_a_note_past_its_48_hours_is_never_confirmed_even_before_the_job_runs(conn):
    k = a_k2_class(conn)
    note = a_note(conn, k, "Activity 12. Above 3.", hours_ago=49)
    with pytest.raises(voice_store.Refused, match="kept as unconfirmed"), conn.transaction():
        vc.confirm_note(conn, str(note["id"]), k["email"], vc.Confirmed(k["activity"], 2, {"above": ["3"]}))


def test_only_her_own_observation_is_corrected_and_only_once(conn):
    k, other = a_k2_class(conn), a_k2_class(conn)
    rows = _rows(
        conn, vc.save_form(conn, k["email"], k["class"], vc.Confirmed(k["activity"], 2, {"above": ["3"]}))
    )
    (old,) = rows.values()
    with pytest.raises(voice_store.Refused, match="not one of your observations"), conn.transaction():
        vc.correct(conn, str(old["id"]), other["email"], "below", "not mine")
    vc.correct(conn, str(old["id"]), k["email"], "below", "misheard")
    with pytest.raises(voice_store.Refused, match="already corrected"), conn.transaction():
        vc.correct(conn, str(old["id"]), k["email"], "as_expected", "again")
    with pytest.raises(voice_store.Refused, match="Not found"), conn.transaction():
        vc.correct(conn, "not-an-id", k["email"], "below", "x")


def test_the_database_refuses_evidence_from_a_note_not_confirmed(conn):
    """Not only the engine: a record written straight into the table for a drafted note is refused (D-051)."""
    k = a_k2_class(conn)
    note = a_note(conn, k, "Activity 12. Above 3.")
    obs = conn.execute(
        "insert into activity_observation (tenant_id, confirmation_id, note_id, activity_code, child_id, class_id,"
        " outcome, entry_mode, route, expected_level, observed_at, observed_by, confirmed_by)"
        " values (%s, gen_random_uuid(), %s, %s, %s, %s, 'above', 'individual', 'voice', 2, now(), %s, %s) returning id",
        (k["tenant"], note["id"], k["activity"], k["children"]["3"], k["class"], k["staff"], k["staff"]),
    ).fetchone()["id"]
    with pytest.raises(psycopg.errors.CheckViolation, match="confirmed note"), conn.transaction():
        conn.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, channel, observed_at, confirmed_by, kind,"
            " mark, seen_by, place, source, observation_id) values (%s, %s, %s, 'educator', now(), 'x', 'observed',"
            " 'yes', 'x', 'class', 'test', %s)",
            (k["tenant"], k["children"]["3"], k["skills"][0], obs),
        )


def test_only_an_educator_who_holds_the_class_records_confirms_or_corrects_for_it(conn):
    k = a_k2_class(conn)
    other = a_k2_class(conn)  # an educator of another class, with no grant on this one
    note = a_note(
        conn, k | {"staff": other["staff"]}, "Activity 12. Above 3."
    )  # hers, about a class she does not hold
    for call in (
        lambda: vc.save_form(
            conn, other["email"], k["class"], vc.Confirmed(k["activity"], 2, {"above": ["3"]})
        ),
        lambda: vc.confirm_note(
            conn, str(note["id"]), other["email"], vc.Confirmed(k["activity"], 2, {"above": ["3"]})
        ),
    ):
        with pytest.raises(voice_store.Refused, match="do not hold this class"), conn.transaction():
            call()
    conn.execute(
        "update config set value = '[]'::jsonb where key = 'voice.roles_that_record'"
    )  # no role records: even her own class is refused
    with pytest.raises(voice_store.Refused, match="do not hold this class"), conn.transaction():
        vc.save_form(conn, k["email"], k["class"], vc.Confirmed(k["activity"], 2, {"above": ["3"]}))


def test_the_mark_and_the_level_reached_come_from_the_rows_and_the_level_is_kept(conn):
    k = a_k2_class(conn)
    rows = _rows(
        conn,
        vc.save_form(conn, k["email"], k["class"], vc.Confirmed(k["activity"], 2, {"above": ["3"]}, True)),
    )
    c = k["children"]
    assert rows[c["3"]]["reached_level"] == 3 and rows[c["5"]]["reached_level"] == 2
    assert {e["mark"] for e in _evidence(conn, c["3"])} == {"yes"}
    conn.execute("""update config set value = '{"0": "not_yet", "1": "not_yet", "2": "not_yet", "3": "sometimes"}'::jsonb
                    where key = 'voice.level_mark'""")
    conn.execute("""update config set value = '{"above": 0, "as_expected": 0, "below": -2}'::jsonb
                    where key = 'voice.outcome_moves_level'""")
    again = _rows(
        conn, vc.save_form(conn, k["email"], k["class"], vc.Confirmed(k["activity"], 2, {"below": ["4"]}))
    )
    assert again[c["4"]]["reached_level"] == 0
    assert {e["mark"] for e in _evidence(conn, c["4"]) if e["observation_id"] == again[c["4"]]["id"]} == {
        "not_yet"
    }
    third = _rows(
        conn, vc.save_form(conn, k["email"], k["class"], vc.Confirmed(k["activity"], 3, {"above": ["2"]}))
    )
    assert {e["mark"] for e in _evidence(conn, c["2"]) if e["observation_id"] == third[c["2"]]["id"]} == {
        "sometimes"
    }
