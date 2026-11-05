"""The K2 screens' questions, each answered in one call (task M1-03, goals/m1-03-k2-reads.yaml).

Part A reads what #362 writes: an educator's to-do and the coordinator's list. Part B (the class picture and a child's
page) reads the child's state per skill that M1-02 (#364) will put on main; until then its tests are *contract only*:
they insert fixture rows shaped as docs/notes/m1-02-k2-picture.md proposes, inside the test's own transaction, and the
real table replaces them when it lands. Rows are placeholders (tests/voice_rows.py); no name of a real child or staff.
"""

import datetime as dt
import json
import os
import time

import pytest

from engine.core import db
from engine.w3_read import k2_reads, voice_intake
from tests.voice_rows import a_k2_class, a_note

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

CLEAN = "Activity 12. Above 3."
PROBLEM = "Activity 12. Above 31."  # no child 31 in the class: a problem she must fix before Confirm
BANNED = ("not_willing", "not willing", "Placeholder Educator", "transcript", "audio_key", "email")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


class Counting:
    """The connection, counting every question put to the database."""

    def __init__(self, conn):
        self.conn, self.n = conn, 0

    def execute(self, *a, **k):
        self.n += 1
        return self.conn.execute(*a, **k)

    def __getattr__(self, name):
        return getattr(self.conn, name)


def another_class(conn) -> dict:
    """A second K2 class whose activity has its own number: on the school's list a number names one activity."""
    k = a_k2_class(conn)
    conn.execute("update activity set sheet_no = '13' where code = %s", (k["activity"],))
    return k


def _walk(x):
    """Every key and every string in an answer."""
    if isinstance(x, dict):
        for k, v in x.items():
            yield str(k)
            yield from _walk(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            yield from _walk(v)
    elif isinstance(x, str):
        yield x


def _rows(group):
    return [r["note_id"] for r in group["rows"]]


def test_the_educators_todo_groups_her_notes_with_counts_oldest_first(conn):
    k = a_k2_class(conn)
    old = a_note(conn, k, CLEAN, hours_ago=60)  # past 48 hours, never confirmed
    older = a_note(conn, k, CLEAN, hours_ago=90)
    fresh = a_note(conn, k, CLEAN, hours_ago=1)
    fresher = a_note(conn, k, CLEAN, hours_ago=0.5)
    bad = a_note(conn, k, PROBLEM, hours_ago=2)
    other = another_class(conn)
    a_note(conn, other, CLEAN)  # another educator's: never in hers
    got = k2_reads.todo(conn, k["email"])
    g = got["groups"]
    assert (g["to_confirm"]["count"], g["fix_this"]["count"], g["left_unconfirmed"]["count"]) == (2, 1, 2)
    assert _rows(g["to_confirm"]) == [str(fresh["id"]), str(fresher["id"])], "oldest first"
    assert _rows(g["fix_this"]) == [str(bad["id"])]
    assert _rows(g["left_unconfirmed"]) == [str(older["id"]), str(old["id"])], "oldest first"
    row = g["left_unconfirmed"]["rows"][0]
    assert set(row) == {"note_id", "activity", "activity_name", "received_at", "age_hours", "state"}
    assert (row["state"], row["activity"], row["age_hours"]) == ("left_unconfirmed", k["activity"], 90)


def test_a_note_with_a_problem_is_fix_this_and_a_clean_one_is_to_confirm(conn):
    k = a_k2_class(conn)
    a_note(conn, k, "Activity 99. Above 3.")  # an activity not on the list is a problem too
    a_note(conn, k, "Activity 12. Above 3 and 3.")  # a repeat is read and said, not a problem
    a_note(conn, k, CLEAN)
    g = k2_reads.todo(conn, k["email"])["groups"]
    assert (g["fix_this"]["count"], g["to_confirm"]["count"]) == (1, 2)
    assert g["fix_this"]["rows"][0]["activity"] is None, "an activity not found is not guessed"
    assert [r["state"] for r in g["fix_this"]["rows"] + g["to_confirm"]["rows"]] == [
        "fix_this",
        "to_confirm",
        "to_confirm",
    ]


def test_a_confirmed_note_leaves_the_todo_and_a_sign_in_off_the_staff_list_is_refused(conn):
    k = a_k2_class(conn)
    n = a_note(conn, k, CLEAN)
    conn.execute("update pii.educator_note set status = 'confirmed' where id = %s", (n["id"],))
    g = k2_reads.todo(conn, k["email"])["groups"]
    assert [x["count"] for x in g.values()] == [0, 0, 0, 0]
    with pytest.raises(voice_intake.voice_store.Refused):
        k2_reads.todo(conn, "nobody@example.test")


def _coordinator(conn, k):
    """A coordinator of the same campus, as the people tables hold one (a campus-wide grant)."""
    campus = conn.execute("select campus_id from staff where id = %s", (k["staff"],)).fetchone()["campus_id"]
    staff = conn.execute(
        "insert into staff (tenant_id, campus_id) values (%s, %s) returning id", (k["tenant"], campus)
    ).fetchone()["id"]
    email = f"coordinator.{str(staff)[:6]}@example.test"
    conn.execute(
        "insert into pii.staff (tenant_id, staff_id, name, email) values (%s, %s, 'Placeholder Coordinator', %s)",
        (k["tenant"], staff, email),
    )
    conn.execute(
        "insert into staff_role_grant (tenant_id, staff_id, role_code, valid_from, granted_by)"
        " values (%s, %s, 'coordinator', %s, 'test')",
        (k["tenant"], staff, dt.date(2026, 1, 1)),
    )
    return email


def test_the_coordinator_sees_only_what_needs_a_decision_red_first_and_counts_not_rows(conn):
    k = a_k2_class(conn)
    me = _coordinator(conn, k)
    a_note(conn, k, CLEAN)  # waiting for her educator, nothing for the coordinator to decide
    late = a_note(conn, k, CLEAN, hours_ago=60)
    bad = a_note(conn, k, PROBLEM, hours_ago=2)
    got = k2_reads.coordinator(conn, me)
    assert [(r["note_id"], r["state"]) for r in got["rows"]] == [
        (str(bad["id"]), "fix_this"),
        (str(late["id"]), "left_unconfirmed"),
    ], "red first"
    assert set(got["rows"][0]) == {
        "note_id",
        "class",
        "activity",
        "activity_name",
        "received_at",
        "age_hours",
        "state",
    }
    assert set(got["counts"]) == {
        "late", "unplanned", "unplanned_why", "children_without_notes", "class_days_without_notes",
    }  # fmt: skip
    assert all(
        isinstance(got["counts"][c], int)
        for c in ("late", "children_without_notes", "class_days_without_notes")
    )
    assert got["counts"]["unplanned"] is None and got["counts"]["unplanned_why"], (
        "no plan yet: said, not invented"
    )
    assert got["counts"]["children_without_notes"] >= 5, "this class's five children have no observation yet"


def test_only_a_coordinator_may_ask_for_the_coordinators_list(conn):
    k = a_k2_class(conn)
    with pytest.raises(voice_intake.voice_store.Refused) as no:
        k2_reads.coordinator(conn, k["email"])  # an educator, not a coordinator
    assert no.value.status == 403


def test_late_counts_a_confirmation_made_on_a_later_day_than_the_activity(conn):
    k = a_k2_class(conn)
    me = _coordinator(conn, k)
    zone = conn.execute("select value #>> '{}' z from config where key = 'school.time_zone'").fetchone()["z"]
    assert zone, "the school's time zone is a row"
    before = k2_reads.coordinator(conn, me)["counts"]["late"]
    now = conn.execute("select now() n").fetchone()["n"]
    for taught, sure in ((now - dt.timedelta(days=2), True), (now, False)):
        conn.execute("alter table activity_observation disable trigger activity_observation_clock")
        conn.execute(
            "insert into activity_observation (tenant_id, confirmation_id, activity_code, child_id, class_id,"
            " outcome, entry_mode, route, expected_level, observed_at, stored_at, observed_by, confirmed_by)"
            " values (%s, gen_random_uuid(), %s, %s, %s, 'as_expected', 'individual', 'form', 2, %s, %s, %s, %s)",
            (k["tenant"], k["activity"], k["children"]["1"], k["class"], taught, now, k["staff"], k["staff"]),
        )
        conn.execute("alter table activity_observation enable trigger activity_observation_clock")
    assert k2_reads.coordinator(conn, me)["counts"]["late"] == before + 1


def test_no_name_and_no_internal_label_is_ever_in_an_answer(conn):
    k = a_k2_class(conn)
    me = _coordinator(conn, k)
    a_note(conn, k, "Activity 12. Not willing 2. Absent 4.")
    a_note(conn, k, PROBLEM, hours_ago=60)
    answers = [k2_reads.todo(conn, k["email"]), k2_reads.coordinator(conn, me)]
    seen = " ".join(_walk(json.loads(json.dumps(answers, default=str)))).lower()
    for banned in BANNED:
        assert banned.lower() not in seen, banned
    for child in k["children"].values():
        assert child not in seen, "a child is by Sr. No., never by an id a screen could keep"


def test_each_call_asks_the_database_a_fixed_number_of_times_and_answers_under_a_second(conn):
    k = a_k2_class(conn)
    me = _coordinator(conn, k)

    def asked(call, who):
        c = Counting(conn)
        t = time.perf_counter()
        call(c, who)
        return c.n, time.perf_counter() - t

    for i in range(3):
        a_note(conn, k, CLEAN if i else PROBLEM, hours_ago=i * 30)
    few = [asked(k2_reads.todo, k["email"]), asked(k2_reads.coordinator, me)]
    for i in range(40):
        a_note(conn, k, CLEAN if i % 3 else PROBLEM, hours_ago=i)
    many = [asked(k2_reads.todo, k["email"]), asked(k2_reads.coordinator, me)]
    assert [n for n, _ in many] == [n for n, _ in few], "no query per note: N+1 is a defect"
    assert all(n <= 8 for n, _ in many)
    assert all(s < 1.0 for _, s in many)
