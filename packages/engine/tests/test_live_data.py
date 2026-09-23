"""`engine live data`: each check finds the disagreement it names, and the whole run cannot write."""

import os
import uuid

import psycopg
import pytest

from engine.checks import live_data
from engine.core import db


def test_a_migration_is_unapplied_until_its_version_is_recorded():
    files = ["20260917090000_ring_a.sql", "20261006090000_only_what_is_taught.sql"]
    assert live_data.unapplied(files, ["20260917090000"]) == ["20261006090000_only_what_is_taught.sql"]
    assert live_data.unapplied(files, ["20260917090000", "20261006090000"]) == []


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs the local copy (bin/testdb)")
    with db.connect(db.dsn()) as c:
        yield c
        c.rollback()


def _answer_on(conn, rung):
    tenant = conn.execute(
        "insert into tenant (slug, name) values (%s, 't') returning id", (f"t-{uuid.uuid4()}",)
    )
    tenant = tenant.fetchone()["id"]
    child = conn.execute(
        "insert into child (tenant_id, roll_no, band, section) values (%s, '1', 'G2', 'G2') returning id",
        (tenant,),
    ).fetchone()["id"]
    conn.execute(
        "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, channel, observed_at,"
        " confirmed_by) values (%s, %s, 'NUM.OPS.01', %s, true, 'teacher_override', now(), 'a person')",
        (tenant, child, rung),
    )
    return child


def test_a_signed_off_answer_on_a_rung_no_skill_holds_fails_and_names_the_rung(conn):
    _answer_on(conn, "R_NOWHERE")
    assert any("R_NOWHERE" in p for p in live_data._off_the_map(conn))


def test_an_answer_on_a_skill_whose_topic_is_not_taught_is_kept_and_noted_not_failed(conn):
    """Multiplication (M1) and explaining a method (X1) are hidden on purpose; their answers are kept."""
    row = conn.execute(
        "select ss.tenant_id, ss.rung_code, ss.code from skill_set ss join topic t"
        " on t.tenant_id = ss.tenant_id and t.code = ss.topic_code where not t.taught limit 1"
    ).fetchone()
    if not row:
        pytest.skip("needs the seed loaded on the copy")
    child = conn.execute(
        "insert into child (tenant_id, roll_no, band, section) values (%s, '1', 'G2', 'HIDDENTEST') returning id",
        (row["tenant_id"],),
    ).fetchone()["id"]
    conn.execute(
        "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, channel, observed_at,"
        " confirmed_by) values (%s, %s, 'NUM.OPS.03', %s, true, 'teacher_override', now(), 'a person')",
        (row["tenant_id"], child, row["rung_code"]),
    )
    assert not any(row["rung_code"] in p for p in live_data._off_the_map(conn))
    assert live_data.hidden(conn).get(row["code"], 0) >= 1


def test_an_answer_the_graph_has_not_read_fails_until_the_graph_is_rebuilt(conn):
    _answer_on(conn, "R_NOWHERE")
    assert live_data._stale_graph(conn)
    conn.execute("select rebuild_child_skill_state(id) from child")
    assert not live_data._stale_graph(conn)


def test_a_paper_with_one_question_counted_twice_fails_and_names_the_paper(conn):
    tenant = conn.execute(
        "insert into tenant (slug, name) values (%s, 't') returning id", (f"t-{uuid.uuid4()}",)
    )
    tenant = tenant.fetchone()["id"]
    conn.execute(
        "insert into rung (tenant_id, code, band, descriptor) values (%s, 'R1', 'G2', 'd')", (tenant,)
    )
    item = conn.execute(
        "insert into item (tenant_id, item_key, template, rung_code, signal, fmt, spec, responses)"
        " values (%s, 'K', 'T', 'R1', 'Procedural', 'bare_sum', '{}', '[]') returning id",
        (tenant,),
    ).fetchone()["id"]
    template = conn.execute(
        "insert into sheet_template (tenant_id, band, level, week, item_ids) values (%s, 'G2', 'L0', 'w', %s)"
        " returning id",
        (tenant, [item]),
    ).fetchone()["id"]
    sheet = conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id) values (%s, 'CS00ffee', %s)"
        " returning id",
        (tenant, template),
    ).fetchone()["id"]
    file = "insert into capture (tenant_id, path, sheet_instance_id) values (%s, 'p', %s) returning id"
    one = "insert into item_result (tenant_id, capture_id, item_id, rid, status) values (%s, %s, %s, 'ans', 'correct')"
    conn.execute(one, (tenant, conn.execute(file, (tenant, sheet)).fetchone()["id"], item))
    assert not [p for p in live_data._marking(conn) if "CS00ffee" in p]
    # the same page scanned again and neither file marked as replacing the other
    conn.execute(one, (tenant, conn.execute(file, (tenant, sheet)).fetchone()["id"], item))
    assert [p for p in live_data._marking(conn) if "CS00ffee" in p] == [
        "paper CS00ffee: 2 answers counted for 1 questions printed, 1 counted twice"
    ]


def test_the_run_is_read_only(conn, monkeypatch):
    def write(c):
        c.execute("insert into tenant (slug, name) values ('never', 'never')")
        return []

    monkeypatch.setattr(live_data, "CHECKS", (("a write", write),))
    with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
        live_data.check(db.dsn())
