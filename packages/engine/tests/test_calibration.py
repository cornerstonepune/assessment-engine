"""Levels to review: when most of a grade or class is secure at a level, the level may be too easy
(goals/cal_levels_to_review.yaml).

Nimish, 2026-10-26: "If 8 out of 10 people in the class are able to solve the advanced level for that particular grade
or school, then that's not actually advanced." His decisions: the system only suggests, the threshold is 80 percent,
the minimum is 8 children. Every test builds its own children in classes of its own and rolls back, so it proves the
same on a database built from the repository as on a copy of live.
"""

import json
import re
import uuid
from pathlib import Path

import psycopg
import pytest

from engine.core import db
from tests.rows import a_registry_skill, tenant

REPO = Path(__file__).resolve().parents[3]
GRADE = "G10"  # a grade no school class is in, so a grade's count here is the test's own
LEVEL = "Advance"


def _a_skill(c) -> dict:
    return db.one(
        c,
        "select s.code, s.rung_code from skill s join skill_level l on l.tenant_id = s.tenant_id and l.skill_code = s.code"
        " where s.tenant_id = %s and l.difficulty = %s order by s.code limit 1",
        (tenant(c), LEVEL),
    )


def _a_paper(c, child, skill, level, marks, section, confirmed=True):
    """One paper of `child`'s: a capture, and one signed-off answer at `level` for each of `marks` ('right', 'wrong',
    'blank') — the evidence the graph reads."""
    t = tenant(c)
    tag = uuid.uuid4().hex[:8].upper()
    tpl = c.execute(
        "insert into sheet_template (tenant_id, band, child_id, week, key, batch_id) values (%s, %s, %s, %s, %s, %s)"
        " returning id",
        (t, GRADE, child, f"CAL-{tag}", json.dumps({"code": tag}), tag),
    ).fetchone()["id"]
    inst = c.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status)"
        " values (%s, %s, %s, %s, 'returned') returning id",
        (t, f"CS{tag[:6]}", tpl, child),
    ).fetchone()["id"]
    cap = c.execute(
        "insert into capture (tenant_id, path, pages, sheet_instance_id, status) values (%s, 'cal.pdf', 1, %s, 'processed')"
        " returning id",
        (t, inst),
    ).fetchone()["id"]
    registry = a_registry_skill(c, t)
    for n, mark in enumerate(marks):
        item = c.execute(
            "insert into item (tenant_id, item_key, template, rung_code, skill_codes, skill_set_code, difficulty, signal,"
            " fmt, spec, responses) values (%s, %s, 'cal', %s, %s, %s, %s, 'Procedural', 'column', %s, %s) returning id",
            (
                t,
                f"cal/{tag}/{n}",
                skill["rung_code"],
                [registry],
                skill["code"],
                level,
                json.dumps({"op": "-", "a": 62, "b": 27, "page": 1}),
                json.dumps([{"rid": "a", "answer": 35}]),
            ),
        ).fetchone()["id"]
        status = {"right": "correct", "wrong": "wrong", "blank": "blank"}[mark]
        res = c.execute(
            "insert into item_result (tenant_id, capture_id, item_id, rid, status, state, confirmed_by, confirmed_at)"
            " values (%s, %s, %s, 'a', %s, 'confirmed', 'tester@example.org', now()) returning id",
            (t, cap, item, status),
        ).fetchone()["id"]
        c.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, channel, item_result_id,"
            " observed_at, confirmed_by) values (%s, %s, %s, %s, %s, 'item', %s, now(), %s)",
            (
                t,
                child,
                registry,
                skill["rung_code"],
                {"right": True, "wrong": False, "blank": None}[mark],
                res,
                "tester@example.org" if confirmed else None,
            ),
        )
    return cap


def _a_child_in(c, section):
    """The next child on the roll of `section`, in grade GRADE, as every child is: `child` and its `pii` row."""
    t = tenant(c)
    roll = db.one(
        c, "select count(*) + 1 as n from child where tenant_id = %s and section = %s", (t, section)
    )["n"]
    child = c.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s, %s, %s, %s) returning id",
        (t, str(roll), section, GRADE),
    ).fetchone()["id"]
    c.execute(
        "insert into pii.child (tenant_id, child_id, first_name) values (%s, %s, 'Caltest')", (t, child)
    )
    return child


def _a_child_at(c, section, skill, level, papers, confirmed=True):
    """A child of `section` (grade GRADE) with `papers`, each a list of marks, at `level`."""
    child = _a_child_in(c, section)
    for marks in papers:
        _a_paper(c, child, skill, level, marks, section, confirmed)
    return child


SECURE = [["right", "right"], ["right", "right"]]  # two papers, four right: the graph's "secure"
PRACTISING = [["right", "wrong"], ["right", "wrong"]]  # half right: practising
BLANK = [["blank", "blank"], ["blank", "blank"]]  # on two papers, nothing written


def _a_class(c, skill, secure, others=(), level=LEVEL, confirmed=True):
    """A class of its own: `secure` children secure at `level`, then one child for each paper set in `others`."""
    section = f"CAL-{uuid.uuid4().hex[:6].upper()}"
    for _ in range(secure):
        _a_child_at(c, section, skill, level, SECURE, confirmed)
    for papers in others:
        _a_child_at(c, section, skill, level, papers, confirmed)
    return section


def _row(c, kind, value, skill, level=LEVEL):
    return c.execute(
        "select * from level_calibration where scope_kind = %s and scope_value = %s and skill_code = %s and difficulty = %s",
        (kind, value, skill["code"], level),
    ).fetchone()


def test_eight_of_ten_secure_at_a_level_is_suggested_with_its_counts():
    with db.connect() as c:
        skill = _a_skill(c)
        eight = _a_class(c, skill, 8, others=[PRACTISING] * 2)
        seven = _a_class(c, skill, 7, others=[PRACTISING] * 3)
        got = _row(c, "class", eight, skill)
        assert (got["secure"], got["assessed"], got["verdict"]) == (8, 10, "review")
        got = _row(c, "class", seven, skill)
        assert (got["secure"], got["assessed"], got["verdict"]) == (7, 10, "fine")
        c.rollback()


def test_secure_at_a_level_is_the_graphs_own_rule_applied_to_that_levels_answers():
    with db.connect() as c:
        skill = _a_skill(c)
        section = f"CAL-{uuid.uuid4().hex[:6].upper()}"
        # secure at Medium, half right at Advance: a skill-wide state would blend the two; a level's state does not
        child = _a_child_at(c, section, skill, "Medium", SECURE)
        for marks in PRACTISING:
            _a_paper(c, child, skill, "Advance", marks, section)
        states = {
            r["difficulty"]: r["state"]
            for r in c.execute(
                "select difficulty, state from child_level_state where child_id = %s", (child,)
            )
        }
        assert states == {"Medium": "secure", "Advance": "practising"}
        # the graph's own rule gives the same state on the answers at one level
        only_advance = _a_child_at(c, section, skill, "Advance", SECURE)
        c.execute("select rebuild_child_skill_state(%s)", (only_advance,))
        graph = db.one(c, "select state from child_skill_state where child_id = %s", (only_advance,))["state"]
        level = db.one(c, "select state from child_level_state where child_id = %s", (only_advance,))["state"]
        assert graph == level
        # and it is one rule, not a copy: the graph and the level both call it
        for definition in (
            "select pg_get_functiondef('rebuild_child_skill_state(uuid)'::regprocedure) as d",
            "select pg_get_viewdef('child_level_state'::regclass) as d",
        ):
            assert "graph_state_of" in db.one(c, definition)["d"]
        c.rollback()


def test_a_blank_is_not_a_success_and_only_confirmed_answers_count():
    with db.connect() as c:
        skill = _a_skill(c)
        # eight children who wrote nothing on two papers, and two who were secure: a blank was assessed, not secure
        blanks = _a_class(c, skill, 2, others=[BLANK] * 8)
        got = _row(c, "class", blanks, skill)
        assert (got["secure"], got["assessed"], got["verdict"]) == (2, 10, "fine")
        # eight secure, none of whose answers a person has confirmed: nobody has been assessed yet (rule 4)
        unconfirmed = _a_class(c, skill, 8, confirmed=False)
        assert _row(c, "class", unconfirmed, skill) is None
        c.rollback()


def test_a_grade_and_a_class_are_counted_separately():
    with db.connect() as c:
        skill = _a_skill(c)
        # other classes of the grade may already hold answers (a browser spec's are kept): the grade moves by this test's own
        was = _row(c, "grade", GRADE, skill) or {"assessed": 0, "secure": 0}
        first = _a_class(c, skill, 5)
        second = _a_class(c, skill, 4, others=[PRACTISING])
        one, two = _row(c, "class", first, skill), _row(c, "class", second, skill)
        assert (one["assessed"], one["verdict"]) == (5, "too_few")
        assert (two["assessed"], two["verdict"]) == (5, "too_few")
        grade = _row(c, "grade", GRADE, skill)
        assert (grade["assessed"] - was["assessed"], grade["secure"] - was["secure"]) == (10, 9)
        assert grade["verdict"] in (
            "review",
            "fine",
        )  # a grade of 8 or more is judged, whatever the classes alone were
        c.rollback()


def test_the_system_only_suggests_no_level_is_changed():
    watched = ("skill_level", "skill_level_version", "skill")
    with db.connect() as c:
        skill = _a_skill(c)

        def snapshot():
            return {
                t: c.execute(
                    f"select md5(string_agg(x::text, '|' order by x::text)) as m from {t} x"
                ).fetchone()["m"]
                for t in watched
            }

        before = snapshot()
        section = _a_class(c, skill, 9)
        got = _row(c, "class", section, skill)
        assert got["verdict"] == "review"
        c.execute(
            "insert into calibration_review (tenant_id, skill_code, difficulty, scope_kind, scope_value, assessed, secure,"
            " reviewed_by) values (%s, %s, %s, 'class', %s, %s, %s, 'tester@example.org')",
            (tenant(c), skill["code"], LEVEL, section, got["assessed"], got["secure"]),
        )
        assert snapshot() == before
        c.rollback()


def test_the_threshold_is_80_percent_and_is_a_row():
    seed = {
        t["key"]: t["value"]
        for t in json.loads((REPO / "supabase/seed/thresholds.json").read_text())["thresholds"]
    }
    assert seed["calibration.too_easy_share"] == 0.8
    with db.connect() as c:
        assert (
            float(db.one(c, "select value from threshold where key = 'calibration.too_easy_share'")["value"])
            == 0.8
        )
        skill = _a_skill(c)
        section = _a_class(c, skill, 7, others=[PRACTISING] * 3)
        assert _row(c, "class", section, skill)["verdict"] == "fine"
        c.execute("update threshold set value = 0.7 where key = 'calibration.too_easy_share'")
        assert _row(c, "class", section, skill)["verdict"] == "review"  # a row moved it; no deploy
        c.rollback()


def test_under_eight_children_say_not_enough_and_suggest_nothing():
    with db.connect() as c:
        skill = _a_skill(c)
        section = _a_class(c, skill, 7)  # all seven secure
        got = _row(c, "class", section, skill)
        assert (got["secure"], got["assessed"], got["min_children"], got["verdict"]) == (7, 7, 8, "too_few")
        c.rollback()


def test_the_minimum_is_a_row():
    seed = {
        t["key"]: t["value"]
        for t in json.loads((REPO / "supabase/seed/thresholds.json").read_text())["thresholds"]
    }
    assert seed["calibration.min_children"] == 8
    with db.connect() as c:
        assert (
            float(db.one(c, "select value from threshold where key = 'calibration.min_children'")["value"])
            == 8
        )
        skill = _a_skill(c)
        section = _a_class(c, skill, 7)
        c.execute("update threshold set value = 7 where key = 'calibration.min_children'")
        assert _row(c, "class", section, skill)["verdict"] == "review"
        c.rollback()


def test_a_review_hides_a_suggestion_until_the_numbers_move_and_is_only_ever_added_to():
    with db.connect() as c:
        skill = _a_skill(c)
        section = _a_class(c, skill, 9)
        got = _row(c, "class", section, skill)
        assert got["looked_at"] is None
        c.execute(
            "insert into calibration_review (tenant_id, skill_code, difficulty, scope_kind, scope_value, assessed, secure,"
            " reviewed_by) values (%s, %s, %s, 'class', %s, %s, %s, 'tester@example.org')",
            (tenant(c), skill["code"], LEVEL, section, got["assessed"], got["secure"]),
        )
        assert _row(c, "class", section, skill)["looked_at"] is not None  # hidden: nothing has moved
        for _ in range(
            int(
                db.one(c, "select value from threshold where key = 'calibration.review_again_children'")[
                    "value"
                ]
            )
        ):
            _a_child_at(c, section, skill, LEVEL, SECURE)
        assert _row(c, "class", section, skill)["looked_at"] is None  # the numbers moved: it is asked again
        for change in ("update calibration_review set reviewed_by = 'x'", "delete from calibration_review"):
            with pytest.raises(psycopg.Error):
                with c.transaction():
                    c.execute(change)
        c.rollback()


def test_no_python_or_web_file_holds_the_numbers():
    """Rule 1: the 80 percent and the 8 are rows, not constants in code."""
    for path in [
        *(REPO / "packages/engine/engine").rglob("*.py"),
        *(REPO / "apps/web/lib").glob("*calibration*.ts"),
    ]:
        text = path.read_text()
        assert not re.search(r"too_easy_share\s*[=:]\s*0?\.8|min_children\s*[=:]\s*8", text), path


def _the_case_before_cal(n, share, observers, repeating, min_events=3, min_obs=2, promote=0.8, demote=0.5):
    """`rebuild_child_skill_state`'s case as it was written until 20261214090000 (20261023090000), in Python."""
    if n < min_events:
        return "not_enough_yet"
    if repeating is not None:
        return "patterned_error"
    if share < demote:
        return "emerging"
    if share < promote or observers < min_obs:
        return "practising"
    return "stretch_ready" if n >= 2 * min_events else "secure"


def test_the_shared_rule_gives_the_state_the_graph_always_gave():
    """Moving the case into one function must change no child's state: every combination, against the old case."""
    with db.connect() as c:
        t = tenant(c)
        for n in range(0, 10):
            for right in range(0, n + 1):
                share = None if n == 0 else right / n
                for observers in (1, 2, 3):
                    for repeating in (None, "M_X"):
                        got = db.one(
                            c,
                            "select public.graph_state_of(%s, %s::numeric, %s::numeric, %s::numeric, %s::text) as state",
                            (t, n, share, observers, repeating),
                        )["state"]
                        want = _the_case_before_cal(n, share, observers, repeating)
                        assert got == want, (n, right, observers, repeating)
        c.rollback()
