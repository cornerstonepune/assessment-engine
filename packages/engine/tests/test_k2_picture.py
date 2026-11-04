"""A K2 child's picture per skill from confirmed voice notes (goals/m1-02-k2-picture.yaml, task M1-02).

The school's rule (decisions D-008, D-051, D-052), worked by hand in each test: a skill is secure only after the child
is named at level 3 on two different school days, and a yes comes at least 14 days after the first of those; "the rest
did as expected" may be that re-check, never opens secure on its own and never moves a state down; a child not
mentioned is not observed and has no row. Each observation and its evidence row are written here as the confirm step
(#362) writes them, placeholders only, inside the test's transaction and rolled back.
"""

import datetime as dt
import os
import uuid

import pytest

from engine.assess import graph
from engine.core import db
from tests.rows import a_child, tenant

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

DAY0 = dt.datetime(2026, 6, 1, 4, 30, tzinfo=dt.UTC)  # a Monday, 10:00 in Pune
MARK = {0: "not_yet", 1: "not_yet", 2: "sometimes", 3: "yes"}  # worked by hand, not read from the rows
MOVE = {"above": 1, "as_expected": 0, "below": -1}


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def k2(conn):
    """A K2 class, one educator, an activity naming one skill; children are made per test."""
    t = tenant(conn)
    campus = conn.execute("select id from campus where tenant_id = %s limit 1", (t,)).fetchone()["id"]
    year = conn.execute(
        "insert into academic_year (tenant_id, label, starts_on, ends_on) values (%s, '2026-27', '2026-04-01',"
        " '2027-03-31') on conflict (tenant_id, label) do update set label = excluded.label returning id",
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
    link = conn.execute(
        "select activity_code, skill_code from activity_skill where tenant_id = %s order by 1, 2 limit 1",
        (t,),
    ).fetchone()
    return {
        "tenant": t,
        "class": klass,
        "staff": staff,
        "activity": link["activity_code"],
        "skill": link["skill_code"],
    }


def seen(conn, s, child, day, outcome, mode="individual", expected=2, supersedes=None):
    """One confirmed observation and, unless not willing or absent, its evidence on the activity's skill."""
    at = DAY0 + dt.timedelta(days=day)
    reached = min(3, max(0, expected + MOVE[outcome])) if outcome in MOVE else None
    obs = conn.execute(
        "insert into activity_observation (tenant_id, confirmation_id, activity_code, child_id, class_id, outcome,"
        " entry_mode, route, expected_level, reached_level, observed_at, observed_by, confirmed_by, supersedes,"
        " reason) values (%s, %s, %s, %s, %s, %s, %s, 'form', %s, %s, %s, %s, %s, %s, %s) returning id",
        (s["tenant"], uuid.uuid4(), s["activity"], child, s["class"], outcome, mode, expected, reached, at,
         s["staff"], s["staff"], supersedes, supersedes and "misheard"),
    ).fetchone()["id"]  # fmt: skip
    if outcome in MOVE:
        mark = MARK[reached]
        conn.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, channel, observed_at, confirmed_by, kind,"
            " mark, seen_by, place, source, observation_id)"
            " values (%s, %s, %s, 'educator', %s, %s, 'observed', %s, %s, 'class', 'voice note', %s)",
            (s["tenant"], child, s["skill"], at, str(s["staff"]), mark, str(s["staff"]), obs),
        )
    return obs


def picture(conn, child):
    graph.rebuild(conn, child)
    return conn.execute(
        "select skill_code, grade_code, state from child_observed_state where child_id = %s", (child,)
    ).fetchall()


def state(conn, s, child):
    rows = picture(conn, child)
    assert [r["skill_code"] for r in rows] == [s["skill"]] and rows[0]["grade_code"] == "K2", rows
    return rows[0]["state"]


def test_secure_needs_level_3_named_on_two_days_and_a_yes_14_days_after_the_first(conn, k2):
    child = a_child(conn)
    seen(conn, k2, child, 0, "above")  # expected 2, above: level 3, yes, named
    assert state(conn, k2, child) == "practising"  # one named day
    seen(conn, k2, child, 0, "above")  # the same school day again
    assert state(conn, k2, child) == "practising"
    seen(conn, k2, child, 1, "above")  # a second school day
    assert state(conn, k2, child) == "secure_to_recheck"  # one adult is enough for K2
    seen(conn, k2, child, 13, "above")  # 13 days after the first: too soon to re-check
    assert state(conn, k2, child) == "secure_to_recheck"
    seen(conn, k2, child, 14, "as_expected", mode="group_as_expected", expected=3)  # the rest, at level 3
    assert state(conn, k2, child) == "secure"


def test_a_second_named_yes_14_days_after_the_first_is_its_own_recheck(conn, k2):
    child = a_child(conn)
    seen(conn, k2, child, 0, "above")
    seen(conn, k2, child, 14, "above")
    assert state(conn, k2, child) == "secure"


def test_the_rest_did_as_expected_is_never_alone_secure(conn, k2):
    child = a_child(conn)
    for day in (0, 1, 15, 30):
        seen(conn, k2, child, day, "as_expected", mode="group_as_expected", expected=3)
    assert state(conn, k2, child) == "not_enough_yet"  # observed with the group, never named
    seen(conn, k2, child, 31, "above")  # one named day, at level 3
    assert state(conn, k2, child) == "practising"  # the group's days never stand in for the second named day


def test_the_rest_did_as_expected_never_lowers_a_state(conn, k2):
    child = a_child(conn)
    seen(conn, k2, child, 0, "above")
    seen(conn, k2, child, 14, "above")
    assert state(conn, k2, child) == "secure"
    seen(conn, k2, child, 20, "as_expected", mode="group_as_expected", expected=2)  # "at least level 2"
    seen(conn, k2, child, 21, "as_expected", mode="group_as_expected", expected=0)  # not yet, as the rest
    assert state(conn, k2, child) == "secure"

    other = a_child(conn)
    seen(conn, k2, other, 0, "as_expected")  # named at level 2: sometimes
    assert state(conn, k2, other) == "practising"
    seen(conn, k2, other, 1, "as_expected", mode="group_as_expected", expected=0)
    assert state(conn, k2, other) == "practising"  # the group's not yet does not make it emerging


def test_a_child_not_mentioned_is_not_observed_and_has_no_row(conn, k2):
    named, quiet, absent = a_child(conn), a_child(conn), a_child(conn)
    seen(conn, k2, named, 0, "above")
    seen(conn, k2, absent, 0, "absent")
    seen(conn, k2, absent, 1, "not_willing")
    assert picture(conn, quiet) == []  # never "not secure"
    assert picture(conn, absent) == []  # absent and not willing are no mark and no evidence


def test_a_corrected_observation_no_longer_counts(conn, k2):
    child = a_child(conn)
    first = seen(conn, k2, child, 0, "above")
    seen(conn, k2, child, 0, "below", supersedes=first)  # she corrected it: level 1, not yet
    seen(conn, k2, child, 14, "above")
    assert state(conn, k2, child) == "practising"  # one named yes day left, not two


def test_a_named_lower_mark_after_secure_resets_the_clock(conn, k2):
    """The orchestrator's answer (D-047, unverified with the school): after a named lower mark, secure needs a fresh
    cycle counted only from marks after it; the old days and the old re-check no longer count."""
    child = a_child(conn)
    seen(conn, k2, child, 0, "above")
    seen(conn, k2, child, 14, "above")
    assert state(conn, k2, child) == "secure"
    seen(conn, k2, child, 20, "below")  # named at level 1: re-opened
    assert state(conn, k2, child) == "practising"
    seen(conn, k2, child, 21, "above")  # a single new yes
    assert state(conn, k2, child) == "practising"
    seen(conn, k2, child, 22, "above")  # a second day after the reset
    assert state(conn, k2, child) == "secure_to_recheck"
    seen(
        conn, k2, child, 34, "as_expected", mode="group_as_expected", expected=3
    )  # 13 days after day 21: too soon
    assert state(conn, k2, child) == "secure_to_recheck"
    seen(conn, k2, child, 35, "as_expected", mode="group_as_expected", expected=3)  # 14 days after day 21
    assert state(conn, k2, child) == "secure"


def test_a_lower_mark_before_secure_does_not_reset_the_clock(conn, k2):
    """D-052: secure is named yes on two days and a yes 14 days after the first; a "sometimes" in between leaves it."""
    child = a_child(conn)
    seen(conn, k2, child, 0, "above")
    seen(conn, k2, child, 1, "as_expected")  # named at level 2: sometimes
    assert state(conn, k2, child) == "practising"
    seen(conn, k2, child, 2, "above")
    assert state(conn, k2, child) == "secure_to_recheck"
    seen(conn, k2, child, 14, "above")  # 14 days after day 0
    assert state(conn, k2, child) == "secure"


def test_secure_then_a_named_lower_mark_and_nothing_more_is_practising(conn, k2):
    child = a_child(conn)
    seen(conn, k2, child, 0, "above")
    seen(conn, k2, child, 14, "above")
    seen(conn, k2, child, 20, "below")  # level 1, not yet: re-opened, shown practising, not emerging
    assert state(conn, k2, child) == "practising"


def test_written_evidence_is_read_exactly_as_before(conn, k2):
    """An observation never reaches the written graph: its table, key and rows are what they were."""
    child = a_child(conn)
    seen(conn, k2, child, 0, "above")
    seen(conn, k2, child, 14, "above")
    graph.rebuild(conn, child)
    assert (
        conn.execute("select count(*) as n from child_skill_state where child_id = %s", (child,)).fetchone()[
            "n"
        ]
        == 0
    )
    assert (
        conn.execute("select count(*) as n from graph_answer where child_id = %s", (child,)).fetchone()["n"]
        == 0
    )


def test_the_rule_is_rows_per_grade_and_way_of_entry(conn, k2):
    rule = conn.execute(
        "select secure_level, secure_days, recheck_days, min_adults from observed_rule"
        " where tenant_id = %s and grade_code = 'K2'",
        (k2["tenant"],),
    ).fetchone()
    assert dict(rule) == {"secure_level": 3, "secure_days": 2, "recheck_days": 14, "min_adults": 1}
    weights = {
        r["entry_mode"]: (r["opens_secure"], r["rechecks"], r["lowers"])
        for r in conn.execute(
            "select entry_mode, opens_secure, rechecks, lowers from observed_weight"
            " where tenant_id = %s and grade_code = 'K2' and kind = 'observed'",
            (k2["tenant"],),
        )
    }
    assert weights == {"individual": (True, True, True), "group_as_expected": (False, True, False)}
    with pytest.raises(Exception), conn.transaction():
        conn.execute("set local role app_engine; delete from observed_weight")


def test_notes_confirmed_by_the_educator_change_the_picture_through_the_confirm_step(conn):
    """The same rule on rows the confirm step itself writes (#362's form Save), not rows written by this file."""
    from engine.w3_read import voice_confirm as vc
    from tests.voice_rows import a_k2_class

    k = a_k2_class(conn)
    for day in (dt.date(2026, 6, 1), dt.date(2026, 6, 15)):  # two school days, the second 14 days on
        vc.save_form(
            conn, k["email"], k["class"], vc.Confirmed(k["activity"], 2, {"above": ["3"]}, True, day)
        )
    named, rest = k["children"]["3"], k["children"]["5"]
    assert {(r["skill_code"], r["state"]) for r in picture(conn, named)} == {
        (s, "secure") for s in k["skills"]
    }
    assert {(r["skill_code"], r["state"]) for r in picture(conn, rest)} == {
        (s, "not_enough_yet") for s in k["skills"]
    }


def test_two_named_marks_at_one_moment_give_the_lower_every_time(conn, k2):
    child = a_child(conn)
    seen(conn, k2, child, 0, "above")
    seen(conn, k2, child, 14, "above")
    seen(conn, k2, child, 20, "above")
    seen(conn, k2, child, 20, "below")  # the same moment, a lower mark
    assert {state(conn, k2, child) for _ in range(3)} == {"practising"}


def test_secure_reads_the_level_reached_and_never_moves_with_the_level_to_mark_setting(conn):
    """A rule that silently moved with a config row would be a defect (rule 11): with level 2 marked yes, a child
    named at level 2 on two days, 14 days apart, has a yes mark each time and is still not secure."""
    from engine.w3_read import voice_confirm as vc
    from tests.voice_rows import a_k2_class

    k = a_k2_class(conn)
    conn.execute(
        "update config set value = %s where tenant_id = %s and key = 'voice.level_mark'",
        ('{"0": "not_yet", "1": "not_yet", "2": "yes", "3": "yes"}', k["tenant"]),
    )
    for day in (dt.date(2026, 6, 1), dt.date(2026, 6, 15)):  # as expected at level 2: reached level 2
        vc.save_form(conn, k["email"], k["class"], vc.Confirmed(k["activity"], 2, {"above": []}, True, day))
    rest = k["children"]["5"]
    assert {
        e["mark"] for e in conn.execute("select mark from evidence_event where child_id = %s", (rest,))
    } == {"yes"}
    named = k["children"]["3"]
    for day in (
        dt.date(2026, 6, 1),
        dt.date(2026, 6, 15),
    ):  # named, as expected at level 2: marked yes, level 2
        vc.save_form(
            conn, k["email"], k["class"], vc.Confirmed(k["activity"], 3, {"below": ["3"]}, False, day)
        )
    assert {r["state"] for r in picture(conn, named)} == {"practising"}
