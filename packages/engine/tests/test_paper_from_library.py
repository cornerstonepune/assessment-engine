"""Step 7 (goals/s7-paper-from-library.yaml): a child's paper for the week is a worksheet from the
library, not questions drawn afresh. Against the real schema and the real library on the copy,
inside one rolled-back transaction."""

import json
import os

import pytest

from engine.core import db
from engine.w2_print import assemble, prescribe

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

SET, SECTION = "SUB.2D2D", "TESTSEC"


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytest.fixture
def children(conn):
    """Three children in a section of their own, so the real roster is never touched."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    ids = []
    for roll, name in (("1", "Aarav"), ("2", "Riya"), ("3", "Meera")):
        cid = conn.execute(
            "insert into child (tenant_id, roll_no, section, band) values (%s,%s,%s,'G2') returning id",
            (tenant, roll, SECTION),
        ).fetchone()["id"]
        conn.execute(
            "insert into pii.child (tenant_id, child_id, first_name) values (%s,%s,%s)", (tenant, cid, name)
        )
        ids.append(cid)
    return ids


def _week(conn, week, difficulty="Hard"):
    rows = prescribe.for_class(conn, SECTION, week, SET)
    conn.execute(
        "update prescription set difficulty = %s where id = any(%s)",
        (difficulty, [r["prescription_id"] for r in rows]),
    )
    return assemble.for_week(conn, SECTION, week)


def _worksheet(conn, instance_id):
    return conn.execute(
        "select t.source, t.code, t.item_ids from sheet_instance si join sheet_template t on t.id = si.sheet_template_id"
        " where si.id = %s",
        (instance_id,),
    ).fetchone()


def test_every_paper_is_one_library_worksheet_whole(conn, children):
    built = _week(conn, "S7-W1")
    assert len(built["sheets"]) == 3, built["short"]
    for s in built["sheets"] + built["spares"]:
        t = _worksheet(conn, s["instance_id"])
        assert t["source"] == "library" and t["code"] == s["code"]
        assert [r["id"] for r in s["item_rows"]] == list(t["item_ids"])


def test_one_level_in_one_week_never_repeats_a_worksheet_and_spares_are_ones_nobody_was_given(conn, children):
    built = _week(conn, "S7-W1")
    given = [s["code"] for s in built["sheets"]]
    spares = [s["code"] for s in built["spares"]]
    assert len(set(given)) == len(given) == 3
    assert spares and not set(given) & set(spares)


def test_no_child_is_given_a_worksheet_they_sat(conn, children):
    first = {s["child_id"]: s["code"] for s in _week(conn, "S7-W1")["sheets"]}
    second = {s["child_id"]: s["code"] for s in _week(conn, "S7-W2")["sheets"]}
    assert first.keys() == second.keys()
    assert all(first[c] != second[c] for c in first)


def test_a_retired_worksheet_is_never_handed_out_again_and_a_printed_paper_keeps_its_questions(
    conn, children
):
    s = _week(conn, "S7-W1")["sheets"][0]
    conn.execute(
        "update sheet_template set retired_at = now() where source = 'library' and code = %s", (s["code"],)
    )
    assert list(_worksheet(conn, s["instance_id"])["item_ids"]) == [r["id"] for r in s["item_rows"]]
    again = _week(conn, "S7-W2")
    assert s["code"] not in {x["code"] for x in again["sheets"] + again["spares"]}


def test_a_worksheet_holding_a_question_no_longer_in_the_bank_is_never_handed_out(conn, children):
    # retired by hand, as a flag does, without the library being rebuilt yet
    first = conn.execute(
        "select code, item_ids from sheet_template where source = 'library' and retired_at is null"
        " and skill_set_code = %s and difficulty = 'Hard' order by code limit 1",
        (SET,),
    ).fetchone()
    conn.execute("update item set status = 'retired' where id = %s", (first["item_ids"][0],))
    built = _week(conn, "S7-W1")
    assert first["code"] not in {s["code"] for s in built["sheets"] + built["spares"]}


def test_a_child_who_has_sat_every_worksheet_at_a_level_is_named_not_handed_a_repeat(conn, children):
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    kid = children[0]
    for t in conn.execute(
        "select id from sheet_template where source = 'library' and skill_set_code = %s and difficulty = 'Hard'",
        (SET,),
    ).fetchall():
        conn.execute(
            "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id) values (%s,%s,%s,%s)",
            (tenant, assemble._qr(t["id"], kid, "an earlier term", "practice"), t["id"], kid),
        )
    built = _week(conn, "S7-W1")
    assert kid not in {s["child_id"] for s in built["sheets"]}
    (named,) = [x for x in built["short"] if x["child_id"] == kid]
    assert "every worksheet" in named["why"] and {"had", "needed"} <= named.keys()


def test_the_printed_paper_names_its_worksheet(conn, children):
    s = _week(conn, "S7-W1")["sheets"][0]
    assert s["code"] in assemble.label("Aarav", s, "practice")
    json.dumps(assemble.label("Aarav", s, "practice"))  # a plain string, printed as it is
