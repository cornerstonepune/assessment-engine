"""The K2 class picture and a child's page (task M1-03 part B, goals/m1-03-k2-reads.yaml).

They read `child_observed_state` (#364, M1-02), which the graph rebuilds from confirmed voice observations. A class of
22 children and 20 skills is made here with real observations and evidence rows (placeholders, inside the test's
transaction), the graph rebuilt by the engine's own function, and each answer is held to a table worked out by hand
from the scenario's rules, and to counts taken straight from the database. A child is by Sr. No.; nothing here names a
child, a child's id, "not willing" or an internal label.
"""

import datetime as dt
import json
import os
import time
import uuid
from zoneinfo import ZoneInfo

import pytest

from engine.assess import graph
from engine.core import db
from engine.w3_read import k2_picture_reads as reads
from engine.w3_read.voice_store import Refused
from tests.rows import a_child
from tests.test_k2_reads import BANNED, Counting, _coordinator, _walk
from tests.voice_rows import a_k2_class, a_note

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

MARK = {0: "not_yet", 1: "not_yet", 2: "sometimes", 3: "yes"}  # worked by hand, not read from the rows
MOVE = {"above": 1, "as_expected": 0, "below": -1}
TODAY = dt.datetime.now(dt.UTC)
ZONE = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _observe(conn, s, child, skill, day, outcome, mode="individual", expected=2, note=None):
    """One confirmed observation `day` days before 30 days ago... i.e. taught `30 - day` days ago, and its evidence."""
    at = TODAY - dt.timedelta(days=30 - day)
    reached = min(3, max(0, expected + MOVE[outcome])) if outcome in MOVE else None
    obs = conn.execute(
        "insert into activity_observation (tenant_id, confirmation_id, note_id, activity_code, child_id, class_id,"
        " outcome, entry_mode, route, expected_level, reached_level, observed_at, observed_by, confirmed_by)"
        " values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) returning id",
        (s["tenant"], uuid.uuid4(), note, s["acts"][skill], child, s["class"], outcome, mode,
         "voice" if note else "form", expected, reached, at, s["staff"], s["staff"]),
    ).fetchone()["id"]  # fmt: skip
    if outcome in MOVE:
        conn.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, channel, observed_at, confirmed_by, kind,"
            " mark, seen_by, place, source, observation_id)"
            " values (%s, %s, %s, 'educator', %s, %s, 'observed', %s, %s, 'class', 'voice note', %s)",
            (s["tenant"], child, skill, at, str(s["staff"]), MARK[reached], str(s["staff"]), obs),
        )
    return obs


def scene(conn, skills=20, observed=19):
    """A K2 class of 22, `skills` skills each with its own activity, `observed` of them seen by someone. Each child's
    rule, by Sr. No.: 1 named at level 3 on two days; 2 the same and a re-check 20 days on; 3 as expected on 5 skills;
    4 below on 5; 5 only 'the rest' on 3; 6 nothing; 7 not willing; 8 to 22 as expected on the skills that share their
    number's remainder on 4."""
    k = a_k2_class(conn)
    t = k["tenant"]
    for roll in range(6, 23):
        child = a_child(conn)
        conn.execute(
            "insert into enrolment (tenant_id, child_id, class_id, roll_no, from_date, recorded_by)"
            " values (%s, %s, %s, %s, %s, 'test')",
            (t, child, k["class"], str(roll), dt.date(2026, 1, 1)),
        )
        k["children"][str(roll)] = str(child)
    names = conn.execute(
        "select code, name from registry_skill where tenant_id = %s order by code limit %s", (t, skills)
    ).fetchall()
    k["skills"] = [r["code"] for r in names]
    k["skill_names"] = {r["code"]: r["name"] for r in names}
    k["acts"] = {}
    for i, skill in enumerate(k["skills"]):
        code = f"ACT-K2-P{uuid.uuid4().hex[:6]}"
        conn.execute(
            "insert into activity (tenant_id, code, band, strand, name) values (%s, %s, 'K2', 'Maths', 'Placeholder')",
            (t, code),
        )
        conn.execute(
            "insert into activity_skill (tenant_id, activity_code, skill_code) values (%s, %s, %s)",
            (t, code, skill),
        )
        k["acts"][skill] = code
    live = k["skills"][:observed]
    c = k["children"]
    expect = {}  # (roll, skill) -> (state, level, day last seen); what each rule above must come to, by hand
    for j, sk in enumerate(live):
        _observe(conn, k, c["1"], sk, 10, "above")
        _observe(conn, k, c["1"], sk, 11, "above")
        expect[("1", sk)] = ("secure_to_recheck", 3, 11)
        if j < 10:
            _observe(conn, k, c["2"], sk, 1, "above")
            _observe(conn, k, c["2"], sk, 2, "above")
            _observe(conn, k, c["2"], sk, 20, "as_expected", expected=3)
            expect[("2", sk)] = ("secure", 3, 20)
        if j < 5:
            _observe(conn, k, c["3"], sk, 5, "as_expected")
            _observe(conn, k, c["4"], sk, 5, "below", expected=1)
            expect[("3", sk)] = ("practising", 2, 5)
            expect[("4", sk)] = ("emerging", 0, 5)
        if j < 3:
            _observe(conn, k, c["5"], sk, 5, "as_expected", mode="group_as_expected")
            expect[("5", sk)] = ("not_enough_yet", None, 5)
        for roll in range(8, 23):
            if j % 4 == roll % 4:
                _observe(conn, k, c[str(roll)], sk, 3, "as_expected")
                expect[(str(roll), sk)] = ("practising", 2, 3)
    _observe(conn, k, c["7"], live[0], 4, "not_willing")  # an observation, never evidence, never shown
    for child in c.values():
        graph.rebuild(conn, child)
    k["expect"] = expect
    k["live"] = live
    return k


def _day(days_ago):
    return (TODAY - dt.timedelta(days=30 - days_ago)).astimezone(ZONE).date().isoformat()


def test_the_class_picture_is_children_by_number_by_skill_and_equals_the_database(conn):
    k = scene(conn)
    got = reads.class_picture(conn, k["email"], k["class"])
    assert [r["roll_no"] for r in got["children"]] == [str(n) for n in range(1, 23)], "by Sr. No., in order"
    assert [s["code"] for s in got["skills"]] == sorted(k["live"]), (
        "only skills the class has any observation on"
    )
    assert {s["code"]: s["name"] for s in got["skills"]} == {c: k["skill_names"][c] for c in k["live"]}
    cells = {(r["roll_no"], code): cell for r in got["children"] for code, cell in r["cells"].items()}
    assert set(cells) == set(k["expect"]), "a cell exactly where the child was seen on the skill"
    for key, (state, level, day) in k["expect"].items():
        cell = cells[key]
        assert (cell["state"], cell["level"], cell["last_seen"]) == (state, level, _day(day)), key
    states = conn.execute(
        "select cs.words, cs.colour, s.state from child_observed_state s join child_state cs on cs.code = s.state"
        " and cs.tenant_id = s.tenant_id where s.child_id = any(%s::uuid[])",
        (list(k["children"].values()),),
    ).fetchall()
    assert len(cells) == len(states), "as many cells as the database holds rows"
    for r in states:
        assert any(c["state"] == r["state"] and c["words"] == r["words"] and c["colour"] == r["colour"]
                   for c in cells.values())  # fmt: skip
    for state in {r["state"] for r in states}:
        assert sum(c["state"] == state for c in cells.values()) == sum(r["state"] == state for r in states), (
            state
        )


def test_a_cell_nobody_filled_is_empty_and_never_a_failure_and_the_colours_are_the_rows(conn):
    k = scene(conn)
    got = {r["roll_no"]: r["cells"] for r in reads.class_picture(conn, k["email"], k["class"])["children"]}
    assert got["6"] == {}, "a child not seen has no cell: not seen is not 'not secure' (D-008)"
    assert got["7"] == {}, "not willing is an observation only: nothing about it is shown"
    assert {c["state"] for c in got["5"].values()} == {"not_enough_yet"}
    assert all(c["level"] is None for c in got["5"].values()), "'the rest did as expected' shows no level"
    assert set(got["1"]) == set(k["live"]) and "unobserved" not in json.dumps(got)
    other = conn.execute(
        "select code from state_colour where tenant_id = %s and code <> 'green' order by code limit 1",
        (k["tenant"],),
    ).fetchone()["code"]
    conn.execute(
        "update child_state set colour = %s where code = 'secure' and tenant_id = %s", (other, k["tenant"])
    )
    again = {r["roll_no"]: r["cells"] for r in reads.class_picture(conn, k["email"], k["class"])["children"]}
    assert {c["colour"] for c in again["2"].values()} == {other}, "the colour is the row's, never a copy"


def test_a_childs_page_lists_her_skills_newest_first_with_the_sentence_she_said(conn):
    k = scene(conn)
    child, sk = (
        k["children"]["9"],
        k["skills"][1],
    )  # roll 9 shares the remainder 1 with skills 1, 5, 9, 13, 17
    note = a_note(conn, k, "Activity 12. Above 9. The rest did as expected. She counted to twenty today.")
    conn.execute("update pii.educator_note set status = 'confirmed' where id = %s", (note["id"],))
    _observe(conn, k, child, k["skills"][5], 15, "above", note=note["id"])
    graph.rebuild(conn, child)
    page = reads.child_page(conn, k["email"], k["class"], "9")
    assert page["roll_no"] == "9" and set(page) == {"class", "roll_no", "skills", "growth", "ready_next"}
    assert [s["code"] for s in page["skills"]][0] == k["skills"][5], (
        "newest first: the day-15 note comes first"
    )
    first = page["skills"][0]
    assert (first["state"], first["level"], first["last_seen"]) == ("practising", 3, _day(15))
    assert "counted to twenty" in first["sentence"]
    assert first["name"] == k["skill_names"][k["skills"][5]]
    rest = page["skills"][1:]
    assert all(s["sentence"] is None for s in rest), "no note, no sentence"
    assert [s["last_seen"] for s in page["skills"]] == sorted(
        (s["last_seen"] for s in page["skills"]), reverse=True
    )
    assert sk in {s["code"] for s in rest}
    with pytest.raises(Refused) as no:
        reads.child_page(conn, k["email"], k["class"], "99")
    assert no.value.status == 404


def test_only_staff_of_the_class_or_a_coordinator_may_see_it_and_a_stranger_may_not(conn):
    k, other = scene(conn, skills=3, observed=3), a_k2_class(conn)
    with pytest.raises(Refused) as no:
        reads.class_picture(conn, other["email"], k["class"])  # an educator of another class
    assert no.value.status == 403
    with pytest.raises(Refused):
        reads.child_page(conn, other["email"], k["class"], "1")
    assert reads.class_picture(conn, _coordinator(conn, k), k["class"])["children"], (
        "a coordinator of the campus may"
    )
    with pytest.raises(Refused) as no:
        reads.class_picture(conn, "nobody@example.test", k["class"])
    assert no.value.status == 403


def test_no_name_no_child_id_and_no_internal_label_is_ever_in_an_answer(conn):
    k = scene(conn)
    picture = reads.class_picture(conn, k["email"], k["class"])
    page = reads.child_page(conn, k["email"], k["class"], "7")  # the child who was not willing
    seen = " ".join(_walk(json.loads(json.dumps([picture, page], default=str)))).lower()
    for banned in BANNED:
        assert banned.lower() not in seen, banned
    for child in k["children"].values():
        assert child not in seen, "a child is by Sr. No."
    assert page["skills"] == [], "not willing shows nothing at all"


def test_each_call_asks_the_database_a_fixed_number_of_times_and_answers_under_a_second(conn):
    k = scene(conn, skills=20, observed=20)
    small = scene(conn, skills=2, observed=2)

    def asked(call, *args):
        c = Counting(conn)
        t = time.perf_counter()
        call(c, *args)
        return c.n, time.perf_counter() - t

    full = [
        asked(reads.class_picture, k["email"], k["class"]),
        asked(reads.child_page, k["email"], k["class"], "1"),
    ]
    less = [
        asked(reads.class_picture, small["email"], small["class"]),
        asked(reads.child_page, small["email"], small["class"], "1"),
    ]
    assert [n for n, _ in full] == [n for n, _ in less], (
        "no query per child, per skill or per cell: N+1 is a defect"
    )
    assert all(n <= 8 for n, _ in full)
    assert all(s < 1.0 for _, s in full), full
    cells = sum(len(r["cells"]) for r in reads.class_picture(conn, k["email"], k["class"])["children"])
    assert cells >= 20 * 3, "a class of 22 and 20 skills, with real cells in it"


def test_the_pictures_query_is_planned_as_what_it_reads_and_never_compiled(conn):
    k = scene(conn, skills=3, observed=3)
    plan = conn.execute(
        "explain (format json) " + reads.CELLS_SQL, reads.cells_params(conn, k["class"], "Asia/Kolkata")
    ).fetchone()["QUERY PLAN"][0]["Plan"]
    jit_above = float(conn.execute("select current_setting('jit_above_cost') as v").fetchone()["v"])
    assert plan["Total Cost"] < jit_above, "Postgres runs it rather than compiling it first"


# --- the free sentence is a note's own words: it may name a child, so a code check stands before it is returned --------

HELD = "sentence held back: it may name a child"
SAID = "Activity 12. Above 9. The rest did as expected. {}"


def _with_sentence(conn, sentence):
    """A class where roll 9's latest observation came from a confirmed note whose free sentence is `sentence`; the
    class's children carry placeholder names (invented here, in the test database only)."""
    k = scene(conn, skills=6, observed=6)
    names = {
        "9": ("Zorbak", "Quillfeather"),
        "10": ("आरव", ""),
        "11": ("Mx", ""),
    }  # a Latin name, a Devanagari one, an initial
    for roll, (first, last) in names.items():
        conn.execute(
            "update pii.child set first_name = %s, last_name = %s where child_id = %s",
            (first, last, k["children"][roll]),
        )
    note = a_note(conn, k, SAID.format(sentence))
    conn.execute("update pii.educator_note set status = 'confirmed' where id = %s", (note["id"],))
    _observe(conn, k, k["children"]["9"], k["skills"][5], 15, "above", note=note["id"])
    graph.rebuild(conn, k["children"]["9"])
    return k


def _sentence(conn, k, email=None):
    page = reads.child_page(conn, email or k["email"], k["class"], "9")
    return page["skills"][0]["sentence"], page["skills"][0]["sentence_note"]


@pytest.mark.parametrize(
    "said",
    ["Zorbak counted to twenty today.", "zORBAK counted to twenty.", "She sat with Quillfeather's group.",
     "आरव ने बीस तक गिना।", "It was Quillfeather, again."],
)  # fmt: skip
def test_a_sentence_that_names_a_child_of_the_class_is_held_back(conn, said):
    k = _with_sentence(conn, said)
    assert _sentence(conn, k) == (None, HELD), said


@pytest.mark.parametrize(
    "said", ["She counted to twenty today.", "Zorbakian rhymes were fun.", "आरवी ने बीस तक गिना।", "Mixed Mxs of blocks."]
)  # fmt: skip
def test_a_name_inside_a_longer_word_is_not_a_name_and_the_sentence_is_shown(conn, said):
    k = _with_sentence(conn, said)
    assert _sentence(conn, k) == (said.rstrip(".।"), None), (
        "shown as the reader gave it, without its full stop"
    )


def test_when_the_check_cannot_run_no_sentence_is_returned(conn, monkeypatch):
    k = _with_sentence(conn, "She counted to twenty today.")

    def broken(*a, **kw):
        raise RuntimeError("the names could not be read")

    monkeypatch.setattr(reads, "names_of_class", broken)
    assert _sentence(conn, k) == (None, HELD)


def test_the_sentence_is_for_the_educator_who_recorded_it_and_for_coordinators_only(conn):
    k = _with_sentence(conn, "She counted to twenty today.")
    assistant = conn.execute(
        "insert into staff (tenant_id, campus_id) select %s, campus_id from staff where id = %s returning id",
        (k["tenant"], k["staff"]),
    ).fetchone()["id"]
    conn.execute(
        "insert into pii.staff (tenant_id, staff_id, name, email) values (%s, %s, 'Placeholder Assistant', %s)",
        (k["tenant"], assistant, f"assistant.{str(assistant)[:6]}@example.test"),
    )
    email = conn.execute("select email from pii.staff where staff_id = %s", (assistant,)).fetchone()["email"]
    conn.execute(
        "insert into staff_role_grant (tenant_id, staff_id, role_code, school_class_id, valid_from, granted_by)"
        " values (%s, %s, 'assistant', %s, %s, 'test')",
        (k["tenant"], assistant, k["class"], dt.date(2026, 1, 1)),
    )
    assert _sentence(conn, k) == ("She counted to twenty today", None), "who recorded it"
    assert _sentence(conn, k, _coordinator(conn, k)) == ("She counted to twenty today", None), "a coordinator"
    got, note = _sentence(conn, k, email)
    assert got is None and note != HELD, "another educator of the class sees the skill, not the sentence"
    assert reads.child_page(conn, email, k["class"], "9")["skills"], "the rest of the page is hers to see"


def test_the_names_are_read_through_the_logged_read_in_one_query_for_the_class(conn):
    k = _with_sentence(conn, "She counted to twenty today.")
    c = Counting(conn)
    page = reads.child_page(c, k["email"], k["class"], "9")
    assert page["skills"][0]["sentence"]
    assert c.n <= 9, c.n  # was 8: M1-17 adds two reads (growth, links) and drops one (names ride the cells)
    logged = conn.execute(
        "select count(*) n from access_log where action = 'read_pii_child' and actor = %s",
        (reads.NAME_CHECK,),
    ).fetchone()["n"]
    assert logged == 22, "each of the class's 22 names read is logged, with who asked"
