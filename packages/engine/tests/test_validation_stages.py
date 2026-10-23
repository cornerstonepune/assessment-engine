"""Validation rules per subject and kind (goals/c4-validation-rules-per-subject-and-kind.yaml, slice C4).

BUILD-ORDER, the locked scope of 22 Oct: "validation rules per subject and kind: New (every answer to a person),
Learning, Trusted, Falls back; every number a row, grown from `kind_trust` (ADR 0060); each subject's page shows each
kind's stage". The stages are `validation_stage` rows, the numbers `validation_rule` rows, the answer `kind_stage`.
"""

import json
import os

import psycopg
import pytest

from engine.checks import past
from engine.core import db
from tests.rows import a_read_paper, tenant

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

MIGRATION = db.REPO_ROOT / "supabase/migrations/20261207090000_each_kind_has_its_validation_stage.sql"
SEED = json.loads((db.REPO_ROOT / "supabase/seed/vocabulary.json").read_text())
KIND = "c4_kind"  # a kind of question of the test's own, so no other check is in its window
RIGHT = {"status": "correct", "read": "35", "state": "confirmed"}
MISREAD = {"status": "wrong", "read": "17", "typed": "35", "state": "confirmed"}  # the reader was wrong


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _papers(conn, *answers):
    """One paper a minute, oldest first, each with its answers, all of the test's own kind."""
    for k, a in enumerate(answers):
        p = a_read_paper(conn, a, fmt=KIND)
        conn.execute(
            "update capture set created_at = now() + %s * interval '1 minute' where id = %s",
            (k, p["capture"]),
        )


def _rule(conn, window, bar=0.95, kind=KIND):
    conn.execute(
        "insert into validation_rule (tenant_id, subject_code, kind, window_size, bar) values (%s, 'NUM', %s, %s, %s)"
        " on conflict (tenant_id, subject_code, coalesce(kind, '')) do update set window_size = excluded.window_size,"
        " bar = excluded.bar",
        (tenant(conn), kind, window, bar),
    )


def _stage(conn):
    return db.one(conn, 'select stage, checks, n, "right" from kind_stage where kind = %s', (KIND,))


def test_the_four_stages_are_rows(conn):
    rows = conn.execute(
        "select code, words, every_answer_to_person from validation_stage order by ord"
    ).fetchall()
    assert [(r["code"], r["words"], r["every_answer_to_person"]) for r in rows] == [
        (v["code"], v["words"], v["every_answer_to_person"]) for v in SEED["validation_stages"]
    ]
    assert [r["code"] for r in rows] == ["new", "learning", "trusted", "falls_back"]
    assert rows[0]["words"].startswith("New") and rows[0]["every_answer_to_person"]


def test_every_subject_starts_with_the_numbers_kind_trust_reads(conn):
    """Grown from `kind_trust`: each subject's rule is today's window and bar, and a subject added later gets it."""
    window = db.one(conn, "select value::int as v from threshold where key = 'marking.agreement_window'")["v"]
    bar = db.one(conn, "select value as v from threshold where key = 'marking.agreement_gate'")["v"]
    rules = conn.execute(
        "select subject_code, window_size, bar from validation_rule where kind is null"
    ).fetchall()
    subjects = {r["code"] for r in conn.execute("select code from subject").fetchall()}
    assert {r["subject_code"] for r in rules} == subjects
    assert {(r["window_size"], r["bar"]) for r in rules} == {(window, bar)}
    conn.execute(
        "insert into subject (tenant_id, code, name) values (%s, 'C4TEST', 'a subject')", (tenant(conn),)
    )
    assert db.one(conn, "select count(*) as n from validation_rule where subject_code = 'C4TEST'")["n"] == 1


def test_a_kind_goes_new_learning_trusted_and_falls_back(conn):
    """With three checks counted, all three to match: never checked, New; one right, Learning; three right, Trusted;
    then a misread, Falls back, and every answer of it to a person again."""
    _rule(conn, 3, 1.0)
    a_read_paper(conn, [{"status": "correct", "read": "35"}], fmt=KIND)  # read, not yet checked by a person
    assert _stage(conn)["stage"] == "new"
    _papers(conn, [RIGHT])
    assert _stage(conn)["stage"] == "learning"
    _papers(conn, [RIGHT], [RIGHT], [RIGHT])
    assert dict(_stage(conn)) == {"stage": "trusted", "checks": 4, "n": 3, "right": 3}
    _papers(conn, [RIGHT], [RIGHT], [RIGHT], [MISREAD])
    assert _stage(conn)["stage"] == "falls_back"
    assert db.one(conn, "select every_answer_to_person as p from validation_stage where code = 'falls_back'")[
        "p"
    ]


def test_every_number_is_a_row(conn):
    """The same checks, held to a longer window, are still learning: the stage follows the rule's row."""
    _papers(conn, [RIGHT], [RIGHT], [RIGHT])
    _rule(conn, 3, 1.0)
    assert _stage(conn)["stage"] == "trusted"
    _rule(conn, 4, 1.0)
    assert _stage(conn)["stage"] == "learning"
    _rule(conn, 3, 0.5)
    assert _stage(conn)["stage"] == "trusted"


def test_a_stage_agrees_with_kind_trust_under_the_same_numbers(conn):
    conn.execute("update threshold set value = 3 where key = 'marking.agreement_window'")
    conn.execute("update validation_rule set window_size = 3 where kind is null")
    _papers(conn, [RIGHT], [MISREAD], [RIGHT], [RIGHT])
    trust = db.one(conn, 'select n, "right", trusted from kind_trust where fmt = %s', (KIND,))
    stage = db.one(conn, 'select n, "right", trusted from kind_stage where kind = %s', (KIND,))
    assert dict(stage) == dict(trust)
    _papers(conn, [RIGHT], [RIGHT], [RIGHT])
    trust = db.one(conn, 'select n, "right", trusted from kind_trust where fmt = %s', (KIND,))
    stage = db.one(conn, 'select n, "right", trusted from kind_stage where kind = %s', (KIND,))
    assert dict(stage) == dict(trust)


def test_a_subject_taken_away_takes_its_rules_with_it(conn):
    """A subject's rules are made when the subject is (above), so they go when it does: a subject can still be removed
    (tests/s43-across-classes.spec.ts adds one and takes it away)."""
    conn.execute(
        "insert into subject (tenant_id, code, name) values (%s, 'C4GONE', 'a subject')", (tenant(conn),)
    )
    conn.execute("delete from subject where code = 'C4GONE'")
    assert db.one(conn, "select count(*) as n from validation_rule where subject_code = 'C4GONE'")["n"] == 0


def test_a_rule_out_of_range_is_refused(conn):
    for window, bar in ((0, 0.9), (3, 0), (3, 1.5)):
        with pytest.raises(psycopg.errors.CheckViolation), conn.transaction():
            _rule(conn, window, bar)


def test_past_results_are_the_same_before_and_after(conn):
    """Nimish: "nothing will change for any of the past assessments, scoring etc. right?"."""
    before = past.fingerprint(conn) | past.fingerprint(conn, past.CURRICULUM)
    conn.execute(MIGRATION.read_text())
    assert past.fingerprint(conn) | past.fingerprint(conn, past.CURRICULUM) == before
