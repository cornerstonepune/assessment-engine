"""ADR 0032 — the reader keeps a notebook per child, rebuilt from every check, and reads with it open.

The loop counts as built only when a check changes a LATER read (goals/w3-read-and-graph.yaml,
`correction_must_change_a_later_read`): these tests build a notebook from checks and read with it.
"""

import os

import pytest

from engine import profiles


def checked(**kw):
    """One answer a person has settled, as `profiles.checked_rows` returns it."""
    base = {
        "fmt": "legacy_bare",
        "model_read": "45",
        "human_read": "45",
        "confidence": 95.0,
        "why": "",
        "answer_state": "written",
        "guess": "",
        "capture_id": "c1",
        "page": 1,
        "box": [0.1, 0.1, 0.3, 0.2],
        "corrected": False,
    }
    return {**base, **kw}


def reading(text, confidence=90.0, **kw):
    return {"child_answer": text, "answer_state": "written", "why": "", "confidence": confidence, **kw}


# ---------------------------------------------------------------- the notebook


def test_the_floor_rises_to_where_this_childs_readings_are_right():
    sure = [checked(confidence=96) for _ in range(12)]
    # half the readings at 70–89 were wrong for this child: 70 is not her floor, 90 is
    shaky = [checked(confidence=80, model_read="17", human_read="47") for _ in range(6)]
    shaky += [checked(confidence=80) for _ in range(6)]
    assert profiles.build(sure + shaky)["floor"] == 90
    assert profiles.build(sure)["floor"] == 70  # nothing below 90 was ever wrong


def test_the_floor_is_the_default_until_ten_checks_and_95_when_nothing_qualifies():
    assert profiles.build([checked(confidence=96, model_read="1", human_read="7")] * 5)["floor"] == 70
    wrong_everywhere = [
        checked(confidence=c, model_read="1", human_read="7")
        for c in (96, 96, 96, 85, 85, 85, 75, 75, 75, 96)
    ]
    assert profiles.build(wrong_everywhere)["floor"] == 95


def test_a_kind_overturned_more_than_a_quarter_of_the_time_is_routed_to_a_person():
    words = [checked(fmt="legacy_word", model_read="12", human_read="21") for _ in range(3)]
    words += [checked(fmt="legacy_word") for _ in range(5)]
    sums = [checked(model_read="9", human_read="4")] + [checked() for _ in range(9)]
    notes = profiles.build(words + sums, route_above=0.25)
    assert notes["route"] == ["legacy_word"]
    assert notes["by_kind"]["legacy_word"] == {"checked": 8, "right": 5, "stood_behind": 8, "overturned": 3}
    # five readings of a kind are too few to route on
    assert profiles.build(words[:5], route_above=0.25)["route"] == []


def test_digit_confusions_are_tallied_from_corrections_one_digit_apart():
    rows = [checked(model_read="17", human_read="47")] * 3 + [checked(model_read="282", human_read="272")]
    rows += [checked(model_read="5", human_read="500")]  # not one digit apart: not a confusion
    assert profiles.build(rows)["confusions"] == {"1>4": 3, "8>7": 1}


def test_samples_are_the_last_eight_distinct_confirmed_readings_with_a_crop():
    rows = [checked(model_read=str(n), human_read=str(n), box=[0, 0, 0.1, n / 100]) for n in range(1, 12)]
    rows += [checked(model_read="", human_read="", answer_state="blank")]  # nothing to show
    rows += [checked(model_read="99", human_read="99", box=None)]  # no crop to show
    got = profiles.build(rows)["samples"]
    assert [s["text"] for s in got] == [str(n) for n in range(4, 12)]
    assert got[0] == {"capture_id": "c1", "page": 1, "box": [0, 0, 0.1, 0.04], "text": "4"}


def test_what_the_reader_gave_up_on_is_counted_with_whether_its_guess_was_right():
    rows = [
        checked(
            model_read="",
            answer_state="illegible",
            why="under the confidence floor",
            guess="45",
            human_read="45",
        )
    ]
    rows += [
        checked(
            model_read="",
            answer_state="illegible",
            why="3 numbers in the region for 2 answers",
            human_read="45",
        )
    ]
    notes = profiles.build(rows)
    assert notes["gave_up"] == {"n": 2, "guess_right": 1}
    assert notes["checked"] == 2 and notes["right"] == 0


# ---------------------------------------------------------------- the next read


def test_a_reading_holding_a_digit_this_child_has_had_confused_twice_is_flagged_with_the_reading_as_the_guess():
    notes = profiles.build([checked(model_read="17", human_read="47")] * 2)
    got = profiles.apply(
        {"3": reading("17", 88.0), "4": reading("45", 88.0)}, notes, lambda slot: "legacy_bare"
    )
    assert got["3"] == {
        "child_answer": "",
        "answer_state": "illegible",
        "why": "this child's 1 has been read for a 4 before",
        "guess": "17",
        "confidence": 88.0,
    }
    assert got["4"] == reading("45", 88.0)  # nothing this child confuses in it


def test_a_routed_kind_goes_to_a_person_whatever_the_confidence():
    notes = profiles.build(
        [checked(fmt="legacy_word", model_read="12", human_read="21")] * 3 + [checked(fmt="legacy_word")] * 5
    )
    got = profiles.apply({"7": reading("30", 99.0)}, notes, lambda slot: "legacy_word")
    assert got["7"]["answer_state"] == "illegible" and got["7"]["guess"] == "30"
    assert (
        got["7"]["why"]
        == "this child's word-problem answers were read wrong 3 times in 8; a person checks them"
    )


def test_an_empty_notebook_changes_nothing_and_a_doubt_is_never_overwritten():
    doubt = {
        "child_answer": "",
        "answer_state": "illegible",
        "why": "under the confidence floor",
        "guess": "17",
        "confidence": 60.0,
    }
    fresh = {"3": reading("17"), "5": doubt}
    assert profiles.apply(fresh, {}, lambda slot: "legacy_bare") == fresh
    notes = profiles.build([checked(model_read="17", human_read="47")] * 2)
    assert profiles.apply({"5": doubt}, notes, lambda slot: "legacy_bare")["5"] == doubt


def test_a_blank_is_never_flagged_by_the_notebook():
    notes = profiles.build([checked(model_read="17", human_read="47")] * 2)
    blank = {"child_answer": "", "answer_state": "blank", "why": "", "confidence": 0.0}
    assert profiles.apply({"1": blank}, notes, lambda slot: "legacy_bare")["1"] == blank


# ---------------------------------------------------------------- on the copy


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    from engine import db

    with db.connect() as c:
        yield c
        c.rollback()


def test_rebuild_writes_a_notebook_for_every_checked_child_and_reads_it_back(conn):
    n = profiles.rebuild(conn)
    assert n == conn.execute("select count(*) as n from child_reading_profile").fetchone()["n"] > 0
    child = conn.execute("select child_id from read_correction limit 1").fetchone()["child_id"]
    notes = profiles.for_child(conn, child)
    assert notes["checked"] > 0 and notes["floor"] in (70, 80, 90, 95)
    assert set(notes) >= {
        "checked",
        "right",
        "by_kind",
        "by_confidence",
        "floor",
        "route",
        "confusions",
        "samples",
        "gave_up",
    }
    # a second rebuild is the same notebook: a pure function of the checks
    profiles.rebuild(conn)
    assert profiles.for_child(conn, child) == notes


def test_a_signed_off_answer_counts_as_the_reader_being_right(conn):
    row = conn.execute(
        "select r.id from item_result r join capture c on c.id = r.capture_id"
        " where c.superseded_by is null and r.state = 'confirmed' and r.raw_read::jsonb ->> 'answer_state' = 'written'"
        " and not exists (select 1 from read_correction rc where rc.item_result_id = r.id) limit 1"
    ).fetchone()
    if not row:
        pytest.skip("no signed-off answer without a correction on the copy")
    rows = [r for r in profiles.checked_rows(conn) if str(r["item_result_id"]) == str(row["id"])]
    assert (
        len(rows) == 1 and not rows[0]["corrected"] and rows[0]["human_read"] == rows[0]["model_read"] != ""
    )
