"""M1-14 part a: the timetable's rules as rows a person edits (goals/m1-14a-timetable-rules.yaml, `/timetable/rules/*`).
The world is the school's own Fortnight 10 text loaded into a K2 class made for the test (placeholder educator, no child
read); the database is the local copy, rolled back. The educator switch is OFF throughout: these are staff screens."""

import os

import psycopg
import pytest

from tests.test_k2_day import (  # noqa: F401  (the fixtures: a loaded K2 class, the app wired to it)
    conn,
    world,
)

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def rules(world):  # noqa: F811
    world["conn"].execute("update config set value = 'false' where key = 'educator.timetable_enabled'")
    return world


def ask(w, what, **body):
    body.setdefault("actor", w["k"]["email"])
    body.setdefault("class_id", w["k"]["class"])
    return w["client"].post(f"/timetable/rules/{what}", json=body)


def period_at(w, hhmm):
    return next(p for p in ask(w, "read").json()["periods"] if p["starts_at"] == hhmm)


def test_the_rules_are_read_with_the_switch_off_and_hold_the_schools_periods_and_fixed_slots(rules):
    r = ask(rules, "read").json()
    assert len(r["periods"]) == 15 and r["periods"][0]["starts_at"] == "08:30"
    assert r["blocks"] == [] and r["limits"] == []
    fixed = {(f["label"], f["weekday"], f["week"]) for f in r["fixed"]}
    assert any(label.lower().startswith("lunch") for label, _, _ in fixed)
    assert {"math", "english", "art"} <= {s["code"] for s in r["subjects"]}
    assert rules["k"]["class"] in {c["id"] for c in r["classes"]} and r["class"]["grade"] == "K2"


def test_someone_not_on_the_staff_list_changes_nothing(rules):
    r = ask(
        rules,
        "change",
        actor="nobody@example.test",
        rule="block",
        action="set",
        on_date="2026-11-25",
        reason="x",
    )
    assert r.status_code == 403


def test_a_day_is_blocked_with_its_reason_and_who_made_it_is_kept(rules):
    r = ask(rules, "change", rule="block", action="set", on_date="2026-11-25", reason="Sports day")
    assert r.status_code == 200, r.text
    got = ask(rules, "read").json()
    assert [(b["on_date"], b["reason"], b["period_id"]) for b in got["blocks"]] == [
        ("2026-11-25", "Sports day", None)
    ]
    edit = got["history"][0]
    assert edit["rule"] == "block" and edit["action"] == "set" and edit["after"]["on_date"] == "2026-11-25"
    assert edit["who"] == "You" and edit["before"] is None  # a name is never read: it stays in pii


def test_one_period_of_a_weekday_in_one_week_can_be_blocked_and_the_same_block_twice_is_refused(rules):
    pid = period_at(rules, "09:40")["id"]
    one = {
        "rule": "block",
        "action": "set",
        "weekday": 3,
        "week_code": "A",
        "period_id": pid,
        "reason": "Assembly",
    }
    assert ask(rules, "change", **one).status_code == 200
    again = ask(rules, "change", **one)
    assert again.status_code == 409 and "already" in again.json()["detail"].lower()


@pytest.mark.parametrize(
    "bad",
    [
        {"on_date": "2026-11-28", "reason": "x"},  # a Saturday
        {"on_date": "2026-11-25", "weekday": 3, "reason": "x"},  # a date and a weekday
        {"reason": "x"},  # neither
        {"on_date": "2026-11-25", "reason": "  "},  # no reason
        {"weekday": 6, "reason": "x"},
    ],
)
def test_a_block_that_makes_no_sense_is_refused_before_anything_is_written(rules, bad):
    assert ask(rules, "change", rule="block", action="set", **bad).status_code == 422
    assert ask(rules, "read").json()["blocks"] == []


def test_a_block_is_removed_and_the_removal_is_kept_too(rules):
    ask(rules, "change", rule="block", action="set", on_date="2026-11-25", reason="Sports day")
    block = ask(rules, "read").json()["blocks"][0]
    assert ask(rules, "change", rule="block", action="remove", id=block["id"]).status_code == 200
    got = ask(rules, "read").json()
    assert got["blocks"] == [] and [
        (h["action"], (h["before"] or {}).get("reason")) for h in got["history"][:2]
    ] == [
        ("remove", "Sports day"),
        ("set", None),
    ]


def test_a_subjects_limit_is_set_changed_and_each_change_keeps_what_it_was(rules):
    one = {"rule": "limit", "subject_code": "math", "span": "week"}
    assert ask(rules, "change", action="set", fewest=3, most=5, **one).status_code == 200
    assert ask(rules, "change", action="set", fewest=4, most=4, **one).status_code == 200
    got = ask(rules, "read").json()
    assert [(x["subject_code"], x["span"], x["fewest"], x["most"]) for x in got["limits"]] == [
        ("math", "week", 4, 4)
    ]
    last = got["history"][0]
    assert (
        last["before"]["fewest"],
        last["before"]["most"],
        last["after"]["fewest"],
        last["after"]["most"],
    ) == (3, 5, 4, 4)
    assert set(got["placed"]["math"]) == {"A", "B"} and got["placed"]["math"]["A"] > 0


@pytest.mark.parametrize(
    "bad",
    [
        {"fewest": 5, "most": 3},
        {"fewest": -1},
        {},
        {"fewest": 1, "span": "month"},
        {"fewest": 1, "subject_code": "underwater_basket_weaving"},
    ],
)
def test_a_limit_that_cannot_be_met_by_its_own_words_is_refused(rules, bad):
    body = {"rule": "limit", "action": "set", "subject_code": "math", "span": "week", **bad}
    assert ask(rules, "change", **body).status_code == 422
    assert ask(rules, "read").json()["limits"] == []


def test_a_limit_is_removed(rules):
    ask(rules, "change", rule="limit", action="set", subject_code="art", span="fortnight", most=2)
    lim = ask(rules, "read").json()["limits"][0]
    assert ask(rules, "change", rule="limit", action="remove", id=lim["id"]).status_code == 200
    assert ask(rules, "read").json()["limits"] == []


def test_a_period_is_given_new_times_and_a_clash_with_its_neighbour_is_refused(rules):
    p = period_at(rules, "09:40")
    nxt = next(x for x in ask(rules, "read").json()["periods"] if x["ord"] == p["ord"] + 1)
    ok = ask(
        rules,
        "change",
        rule="period",
        action="set",
        id=p["id"],
        starts_at="09:40",
        ends_at=nxt["starts_at"],
        label=p["label"],
    )
    assert ok.status_code == 200, ok.text
    over = ask(
        rules,
        "change",
        rule="period",
        action="set",
        id=p["id"],
        starts_at="09:40",
        ends_at="23:00",
        label=p["label"],
    )
    assert over.status_code == 422 and "overlap" in over.json()["detail"].lower()
    backwards = ask(
        rules,
        "change",
        rule="period",
        action="set",
        id=p["id"],
        starts_at="10:00",
        ends_at="09:00",
        label=p["label"],
    )
    assert backwards.status_code == 422


def test_a_fixed_slot_is_pinned_then_released_and_the_slot_it_replaced_is_in_the_history(rules):
    p = period_at(rules, "09:40")
    pin = ask(
        rules,
        "change",
        rule="fixed",
        action="set",
        period_id=p["id"],
        week_code="A",
        weekday=2,
        text="Library visit",
    )
    assert pin.status_code == 200, pin.text
    got = ask(rules, "read").json()
    mine = [f for f in got["fixed"] if f["text"] == "Library visit"]
    assert len(mine) == 1 and (mine[0]["weekday"], mine[0]["week"]) == (2, "A")
    assert got["history"][0]["before"] is not None  # the lesson that was there is not lost
    assert ask(rules, "change", rule="fixed", action="remove", id=mine[0]["id"]).status_code == 200
    assert not [f for f in ask(rules, "read").json()["fixed"] if f["text"] == "Library visit"]


def test_the_history_cannot_be_rewritten(rules):
    ask(rules, "change", rule="block", action="set", on_date="2026-11-25", reason="Sports day")
    with pytest.raises(psycopg.errors.Error):
        rules["conn"].execute("delete from timetable_rule_edit")


def test_a_period_with_no_end_keeps_none_and_is_not_given_one(rules):
    last = ask(rules, "read").json()["periods"][-1]
    assert last["ends_at"] is None
    ok = ask(
        rules,
        "change",
        rule="period",
        action="set",
        id=last["id"],
        starts_at=last["starts_at"],
        label="Boarding",
    )
    assert ok.status_code == 200 and ok.json()["periods"][-1]["ends_at"] is None


def test_a_period_may_not_start_when_another_does_and_the_change_is_kept_for_the_grade(rules):
    ps = ask(rules, "read").json()["periods"]
    clash = ask(
        rules, "change", rule="period", action="set", id=ps[1]["id"], starts_at=ps[0]["starts_at"], label="x"
    )
    assert clash.status_code == 422 and "overlap" in clash.json()["detail"].lower()
    ok = ask(
        rules,
        "change",
        rule="period",
        action="set",
        id=ps[1]["id"],
        starts_at=ps[1]["starts_at"],
        ends_at=ps[1]["ends_at"],
        label="Renamed",
    )
    assert ok.status_code == 200 and ok.json()["history"][0]["rule"] == "period"
