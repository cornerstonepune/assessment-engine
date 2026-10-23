"""One evidence record for every kind (goals/c2-one-evidence-record-for-every-kind.yaml, slice C2).

BUILD-ORDER, the locked scope of 22 Oct: "one evidence record for every kind (written, observed, voice, project,
performance): who saw it, where, which registry skill, its scale (right/wrong/blank or yes/sometimes/not yet) and its
source; past rows untouched (rule 4)". The record is `evidence_event`; its kinds, scales and marks are rows.
"""

import json
import os

import psycopg
import pytest

from engine.checks import past
from engine.core import db
from tests import rows

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

MIGRATION = db.REPO_ROOT / "supabase/migrations/20261205090000_one_evidence_record_for_every_kind.sql"
SEED = json.loads((db.REPO_ROOT / "supabase/seed/vocabulary.json").read_text())


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _skill(conn):
    return db.one(conn, "select code from registry_skill order by code limit 1")["code"]


def _record(conn, child, **kw):
    """One record as an educator writes it: an observation unless told otherwise."""
    r = {
        "kind": "observed",
        "mark": "sometimes",
        "correct": None,
        "seen_by": "an educator",
        "place": "Grade 2 classroom",
        "source": "seen in class",
        "skill_code": _skill(conn),
        "rung_code": None,
        "channel": "educator",
    } | kw
    return conn.execute(
        "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, channel, observed_at,"
        " kind, mark, seen_by, place, source)"
        " values (%(t)s, %(child)s, %(skill_code)s, %(rung_code)s, %(correct)s, %(channel)s, now(), %(kind)s,"
        " %(mark)s, %(seen_by)s, %(place)s, %(source)s) returning *",
        r | {"t": rows.tenant(conn), "child": child},
    ).fetchone()


def _refused(conn, child, **kw):
    try:
        with conn.transaction():
            _record(conn, child, **kw)
    except (psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation):
        return True
    return False


def test_every_kind_is_a_row_with_its_scale(conn):
    """Written, observed, voice, project and performance; right/wrong/blank and yes/sometimes/not yet; the
    migration's rows are the seed's, so a new school gets the same."""
    kinds = conn.execute("select code, scale from evidence_kind order by ord").fetchall()
    assert [(k["code"], k["scale"]) for k in kinds] == [
        (k["code"], k["scale"]) for k in SEED["evidence_kinds"]
    ]
    assert {k["code"] for k in kinds} == {"written", "observed", "voice", "project", "performance"}
    marks = conn.execute(
        "select scale, code, words, correct from evidence_mark order by scale, ord"
    ).fetchall()
    assert [(m["scale"], m["code"], m["words"], m["correct"]) for m in marks] == [
        (s["code"], m["code"], m["words"], m["correct"])
        for s in sorted(SEED["evidence_scales"], key=lambda s: s["code"])
        for m in s["marks"]
    ]
    assert [m["code"] for m in marks if m["scale"] == "answer"] == ["right", "wrong", "blank"]
    assert [m["code"] for m in marks if m["scale"] == "seen"] == ["yes", "sometimes", "not_yet"]


def test_a_record_of_every_kind_says_who_where_which_skill_its_mark_and_source(conn):
    """One record for each kind other than written, read back with everything the scope names."""
    child = rows.a_child(conn)
    for kind, mark in [
        ("observed", "yes"),
        ("voice", "wrong"),
        ("project", "not_yet"),
        ("performance", "sometimes"),
    ]:
        r = _record(conn, child, kind=kind, mark=mark)
        assert (r["kind"], r["mark"], r["seen_by"], r["place"], r["source"]) == (
            kind,
            mark,
            "an educator",
            "Grade 2 classroom",
            "seen in class",
        )
        assert db.one(conn, "select count(*) as n from registry_skill where code = %s", (r["skill_code"],))[
            "n"
        ]


def test_a_record_missing_who_where_source_or_a_registry_skill_is_refused(conn):
    child = rows.a_child(conn)
    assert _refused(conn, child, seen_by=None)
    assert _refused(conn, child, place=None)
    assert _refused(conn, child, source=None)
    assert _refused(conn, child, skill_code="NOT.A.SKILL")
    assert _refused(conn, child, kind="drawing")
    assert not _refused(conn, child)


def test_a_mark_is_on_its_kinds_scale(conn):
    """An observation is yes, sometimes or not yet, never right or wrong; a voice answer is right, wrong or blank."""
    child = rows.a_child(conn)
    assert _refused(conn, child, kind="observed", mark="right")
    assert _refused(conn, child, kind="observed", mark=None)
    assert _refused(conn, child, kind="observed", mark="yes", correct=True)
    assert _refused(conn, child, kind="voice", mark="sometimes")
    assert _record(conn, child, kind="voice", mark="wrong")["correct"] is False


def test_three_signals_never_two(conn):
    """A written answer's mark follows `correct` by itself: right, wrong and blank stay three; a mark that disagrees
    with `correct` is refused."""
    child = rows.a_child(conn)
    rung = db.one(conn, "select rung_code from skill where rung_code is not null limit 1")["rung_code"]
    written = {"kind": "written", "mark": None, "seen_by": None, "place": None, "source": None}
    written |= {"rung_code": rung, "channel": "teacher_override"}
    assert [_record(conn, child, **written, correct=c)["mark"] for c in (True, False, None)] == [
        "right",
        "wrong",
        "blank",
    ]
    assert _refused(conn, child, **(written | {"mark": "right"}), correct=False)
    assert _refused(conn, child, **(written | {"rung_code": None}), correct=True)


def test_the_maths_graph_reads_written_answers_alone(conn):
    """An observation is kept, and waits for the observation engine; the graph's reading is unchanged."""
    child = rows.a_child(conn)
    r = _record(conn, child, kind="observed", mark="yes")
    assert db.one(conn, "select count(*) as n from evidence_placed where id = %s", (r["id"],))["n"] == 0


def test_past_rows_are_untouched(conn):
    """Rule 4 and Nimish's "nothing will change for any of the past assessments": the evidence, every child's states
    and every scored answer are the same after the migration runs again, and a record is still never edited."""
    before = past.fingerprint(conn)
    conn.execute(MIGRATION.read_text())
    assert past.fingerprint(conn) == before
    child = rows.a_child(conn)
    r = _record(conn, child)
    with pytest.raises(psycopg.Error), conn.transaction():
        conn.execute("update evidence_event set mark = 'yes' where id = %s", (r["id"],))
