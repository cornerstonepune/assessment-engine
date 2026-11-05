"""M1-17 brick B: a K2 child's page gains growth (levels by month, a trend) and what is ready next (confirmed links
only). Built on the class of 22 from test_k2_picture_reads.scene; the dates are the scene's known days, worked by hand.
Nothing here names a child; a child is by Sr. No."""

import json
import os
import uuid

import pytest

from engine.core import db
from engine.w3_read import k2_picture_reads as reads
from tests.test_k2_picture_reads import MARK, TODAY, _day, scene
from tests.test_k2_reads import BANNED

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _set(conn, key, value):
    conn.execute("update config set value = %s::jsonb where key = %s", (json.dumps(value), key))


def _link(conn, k, skill, before, status, strength="hard"):
    conn.execute(
        "insert into skill_link (tenant_id, skill_code, before_code, strength, reason, source, status, confirmed_by,"
        " confirmed_at) values (%s, %s, %s, %s, 'a test reason', 'test', %s, %s, %s)",
        (k["tenant"], skill, before, strength, status,
         k["staff"] if status == "confirmed" else None, TODAY if status == "confirmed" else None),
    )  # fmt: skip


def _page(conn, k, roll):
    return reads.child_page(conn, k["email"], k["class"], roll)


def _growth(page, skill):
    return next((g for g in page["growth"] if g["skill"]["code"] == skill), None)


def test_the_page_keeps_what_it_had_and_gains_growth_and_ready_next(conn):
    k = scene(conn)
    page = _page(conn, k, "2")
    assert {"class", "roll_no", "skills", "growth", "ready_next"} <= set(page)
    assert len(page["skills"]) == 10, "the plan is the skills she was seen on, as before"


def test_growth_is_the_days_seen_with_the_highest_level_and_nothing_summed(conn):
    k = scene(conn)
    sk = k["live"][0]
    g = _growth(_page(conn, k, "2"), sk)  # seen on three days, level 3 each, by the scene's rule
    assert g["skill"] == {"code": sk, "name": k["skill_names"][sk]}
    assert (g["first_seen"], g["last_seen"]) == (_day(1), _day(20))
    assert sum(m["days"] for m in g["by_month"]) == 3
    assert {m["level"] for m in g["by_month"]} == {3}
    assert not {"score", "total", "average"} & set(g), "a trend, never a score"
    one = _growth(_page(conn, k, "3"), sk)  # as expected once, at level 2
    assert one["by_month"] == [{"month": _day(5)[:7], "level": 2, "days": 1}]
    assert one["trend"] == "too_few"


def test_growth_skips_the_rest_did_as_expected_and_not_willing(conn):
    k = scene(conn)
    group_only = _page(conn, k, "5")
    assert group_only["skills"], "the child is seen, as 'not enough yet'"
    assert group_only["growth"] == [], "but no level was named, so there is no growth"
    assert _page(conn, k, "7")["growth"] == [], "not willing is an observation, never growth"


def test_a_corrected_observation_counts_once_at_its_corrected_level(conn):
    k = scene(conn)
    sk, child = k["live"][0], k["children"]["3"]
    first = conn.execute(
        "select id from activity_observation where child_id = %s and activity_code = %s",
        (child, k["acts"][sk]),
    ).fetchone()["id"]
    fixed = conn.execute(
        "insert into activity_observation (tenant_id, confirmation_id, activity_code, child_id, class_id, outcome,"
        " entry_mode, route, expected_level, reached_level, observed_at, observed_by, confirmed_by, supersedes, reason)"
        " select tenant_id, %s, activity_code, child_id, class_id, 'above', 'individual', 'form', 2, 3, observed_at,"
        " observed_by, confirmed_by, id, 'a test correction' from activity_observation where id = %s returning id",
        (uuid.uuid4(), first),
    ).fetchone()["id"]
    conn.execute(
        "insert into evidence_event (tenant_id, child_id, skill_code, channel, observed_at, confirmed_by, kind, mark,"
        " seen_by, place, source, observation_id) select tenant_id, child_id, skill_code, channel, observed_at,"
        " confirmed_by, kind, %s, seen_by, place, source, %s from evidence_event where observation_id = %s",
        (MARK[3], fixed, first),
    )
    g = _growth(_page(conn, k, "3"), sk)
    assert g["by_month"] == [{"month": _day(5)[:7], "level": 3, "days": 1}]


def test_the_number_of_months_a_trend_needs_is_a_config_row(conn):
    k = scene(conn)
    _set(conn, "k2.child_page", {"growth_min_months": 99, "done_states": ["secure"]})
    assert {g["trend"] for g in _page(conn, k, "2")["growth"]} == {"too_few"}
    _set(conn, "k2.child_page", {"growth_min_months": 2, "done_states": ["secure"]})
    for g in _page(conn, k, "2")["growth"]:
        assert (g["trend"] == "too_few") == (len(g["by_month"]) < 2)


def test_ready_next_reads_confirmed_links_only(conn):
    k = scene(conn)
    a, b, c = k["live"][0], k["live"][10], k["live"][11]
    _link(conn, k, b, a, "confirmed")
    _link(conn, k, c, a, "proposed")  # nobody confirmed it: nothing reads it
    got = _page(conn, k, "2")["ready_next"]  # child 2 is secure on the first ten skills
    assert got == [{
        "skill": {"code": b, "name": k["skill_names"][b]},
        "because": [{"before": {"code": a, "name": k["skill_names"][a]}, "strength": "hard"}],
    }]  # fmt: skip


def test_secure_to_recheck_is_not_done_and_a_skill_not_seen_is_not_called_not_ready(conn):
    k = scene(conn)
    a, b, far = k["live"][0], k["live"][10], k["live"][15]
    _link(conn, k, b, a, "confirmed")  # child 1 is only secure_to_recheck on a
    assert _page(conn, k, "1")["ready_next"] == []
    _link(conn, k, k["live"][12], k["live"][1], "confirmed")
    _link(conn, k, k["live"][12], far, "confirmed")  # child 2 was never seen on `far`
    page = _page(conn, k, "2")
    assert [r["skill"]["code"] for r in page["ready_next"]] == [b]
    assert "not ready" not in json.dumps(page).lower() and "not_ready" not in json.dumps(page)


def test_which_states_are_done_is_a_config_row(conn):
    k = scene(conn)
    _link(conn, k, k["live"][10], k["live"][0], "confirmed")
    _set(conn, "k2.child_page", {"growth_min_months": 2, "done_states": []})
    assert _page(conn, k, "2")["ready_next"] == []


def test_the_page_names_no_child_and_no_internal_label(conn):
    k = scene(conn)
    _link(conn, k, k["live"][10], k["live"][0], "confirmed")
    text = json.dumps(_page(conn, k, "2"), default=str)
    for banned in (*BANNED, *k["children"].values()):
        assert banned not in text
