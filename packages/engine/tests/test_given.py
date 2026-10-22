"""An assessment given out, and a child away (`w2_print/given.py`, goals/s2-the-assessment-card.yaml).

The scope Nimish locked on 2026-10-22: "Given (an educator presses "Given on"; an upload without it is still
accepted)" and "an absent child's paper carried". Each is the person's word, kept as a row of its own; a later word
is a new row. Against the real schema, rolled back."""

import os
from datetime import date, timedelta

import pytest

from engine.core import db
from engine.w2_print import given

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _a_paper(conn, qr):
    t = conn.execute("select id from tenant limit 1").fetchone()["id"]
    template = conn.execute("select id from sheet_template order by code limit 1").fetchone()["id"]
    conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, section, week, kind, print_status)"
        " values (%s, %s, %s, 'GIVEN-TEST', '2026-W43', 'practice', 'new')",
        (t, qr, template),
    )
    return t


def _runs(conn, flow):
    return conn.execute(
        "select request from flow_run where flow = %s and request ->> 'by' = 'educator@school' order by started_at, id",
        (flow,),
    ).fetchall()


def test_given_on_is_the_educators_word_kept_with_its_day(conn):
    t = _a_paper(conn, "CSGE0001")
    out = given.given(conn, t, ["CSGE0001", "CSNOPE01"], date.today(), "educator@school")
    assert out["papers"] == 1
    [run] = _runs(conn, given.GIVEN)
    assert run["request"] == {"qrs": ["CSGE0001"], "on": date.today().isoformat(), "by": "educator@school"}
    # the paper itself is not changed: an upload without "Given on" is read the same
    assert (
        conn.execute("select print_status from sheet_instance where qr_code = 'CSGE0001'").fetchone()[
            "print_status"
        ]
        == "new"
    )


def test_a_day_to_come_no_person_or_no_paper_is_refused_in_words(conn):
    t = _a_paper(conn, "CSGE0002")
    pune = conn.execute("select (now() at time zone 'Asia/Kolkata')::date as d").fetchone()["d"]
    given.given(
        conn, t, ["CSGE0002"], pune, "educator@school"
    )  # today in Pune, whatever the server's clock says
    with pytest.raises(ValueError, match="still to come"):
        given.given(conn, t, ["CSGE0002"], pune + timedelta(days=1), "educator@school")
    with pytest.raises(ValueError, match="who gave"):
        given.given(conn, t, ["CSGE0002"], date.today(), "")
    with pytest.raises(LookupError, match="none of these codes"):
        given.given(conn, t, ["CSNOPE01"], date.today(), "educator@school")


def test_a_child_away_and_back_is_two_words_the_newest_standing(conn):
    t = _a_paper(conn, "CSGE0003")
    given.absent(conn, t, "CSGE0003", True, "educator@school")
    given.absent(conn, t, "CSGE0003", False, "educator@school")
    assert [r["request"]["away"] for r in _runs(conn, given.ABSENT)] == [True, False]
    with pytest.raises(LookupError):
        given.absent(conn, t, "CSNOPE01", True, "educator@school")
