"""A wrong answer no named mistake explains becomes a mistake the system knows (goals/s22-learned-mistakes.yaml,
`w1_bank/learned.py`). Runs on the local copy of the database in a transaction that is rolled back.

The children here write the larger digit of each column: 47 + 38 → 48, 52 + 36 → 56. No named mistake gives either."""

import json
import os
import uuid

import pytest

from engine.assess import learned_rules as L
from engine.assess import misconceptions as M
from engine.core import db
from engine.w1_bank import learn, learned
from engine.w3_read import marking
from tests.test_learn import _question, _tenant

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _sum(conn, tenant, a, b, op="+"):
    """A question `a op b` in the bank, its key and its named mistakes' answers as the generator stores them."""
    key = _question(conn, tenant)
    right = M.compute(op, a, b)
    responses = [{"rid": "ans", "kind": "digits", "answer": str(right), "cells": len(str(right)),
                  "misconceptions": M.predict(op, a, b)}]  # fmt: skip
    conn.execute(
        "update item set spec = spec || %s::jsonb, responses = %s where item_key = %s",
        (json.dumps({"a": a, "b": b, "op": op}), json.dumps(responses), key),
    )
    return key


def _written(conn, tenant, key, wrote, state="confirmed"):
    """One child's answer `wrote` to `key`, read and — `state` confirmed — checked by a person. → the result's id."""
    item = conn.execute("select id from item where item_key = %s", (key,)).fetchone()["id"]
    child = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s,%s,'TLEARN','G2') returning id",
        (tenant, uuid.uuid4().hex[:6]),
    ).fetchone()["id"]
    t = conn.execute(
        "insert into sheet_template (tenant_id, band, week) values (%s, 'G2', 'W1') returning id", (tenant,)
    ).fetchone()["id"]
    si = conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id) values (%s,%s,%s,%s) returning id",
        (tenant, f"CS{uuid.uuid4().hex[:6]}", t, child),
    ).fetchone()["id"]
    cap = conn.execute(
        "insert into capture (tenant_id, path, sheet_instance_id) values (%s,'~/x.pdf',%s) returning id",
        (tenant, si),
    ).fetchone()["id"]
    return conn.execute(
        "insert into item_result (tenant_id, capture_id, item_id, rid, status, state, raw_read)"
        " values (%s,%s,%s,'ans','wrong',%s,%s) returning id",
        (tenant, cap, item, state, json.dumps({"child_answer": str(wrote), "answer_state": "written"})),
    ).fetchone()["id"]


def _mine(conn):
    return [p for p in learn.refresh(conn) if p["kind"] == "new_mistake"]


def test_a_rule_seen_on_two_questions_is_proposed_once_with_its_examples_and_words(conn):
    """Nimish: "Whenever there is an answer that the student writes which is not found in the answer list, the system
    should create that as a mistake". Seen on one question it could be anything; on two different questions the same
    rule is a way of working — proposed once, with its examples and what it does in words."""
    tenant = _tenant(conn)
    one, two = _sum(conn, tenant, 47, 38), _sum(conn, tenant, 52, 36)
    assert 48 not in M.predict("+", 47, 38).values() and 56 not in M.predict("+", 52, 36).values()
    _written(conn, tenant, one, 48)
    assert _mine(conn) == [], "one question is not enough to call it a way of working"
    _written(conn, tenant, two, 56)
    _written(conn, tenant, two, 57, state="candidate")  # not yet checked by a person: not evidence

    proposed = _mine(conn)
    assert len(proposed) == 1
    p = proposed[0]
    rule = p["evidence"]["rule"]
    assert L.predict(rule, 47, 38) == 48 and L.predict(rule, 52, 36) == 56
    assert {(e["a"], e["b"], e["wrote"]) for e in p["evidence"]["examples"]} == {(47, 38, 48), (52, 36, 56)}
    assert p["evidence"]["words"] == L.words(rule) and "larger digit" in p["evidence"]["words"]
    assert len(_mine(conn)) == 1, "proposed once, not on every refresh"


def test_an_adopted_mistake_is_recognised_on_a_question_it_was_never_seen_on(conn):
    """Nimish: "so that next time, when a child does that, that is found." A person names the rule and adopts it; a
    third child who writes 64 for 63 + 24 — a question no child had got wrong this way — is recognised."""
    tenant = _tenant(conn)
    _written(conn, tenant, _sum(conn, tenant, 47, 38), 48)
    _written(conn, tenant, _sum(conn, tenant, 52, 36), 56)
    p = _mine(conn)[0]

    with pytest.raises(ValueError, match="named"):
        learn.decide(conn, p["id"], "adopt", "neha", "  ")
    with pytest.raises(ValueError, match="adopt or reject"):
        learn.decide(conn, p["id"], "remove", "neha")
    got = learn.decide(conn, p["id"], "adopt", "neha", "Writes the bigger digit in each column")
    code = got["code"]
    assert code == learned.code_for(p["evidence"]["rule"]) and code.startswith("L_")
    row = conn.execute(
        "select name, op, detectable_by from misconception where code = %s", (code,)
    ).fetchone()
    assert (row["name"], row["op"], row["detectable_by"]) == (
        "Writes the bigger digit in each column",
        "+",
        "answer_lookup",
    )
    assert _mine(conn) == [], "an adopted mistake is not proposed again"

    third = _sum(conn, tenant, 63, 24)
    result = _written(conn, tenant, third, 0, state="candidate")
    assert marking.correct(conn, result, "64", "achal")["codes"] == [code]
    assert marking.correct(conn, result, "65", "achal")["codes"] == [], "only the answer the rule gives"


def test_a_rejected_rule_is_not_proposed_again_and_recognises_nothing(conn):
    tenant = _tenant(conn)
    _written(conn, tenant, _sum(conn, tenant, 47, 38), 48)
    _written(conn, tenant, _sum(conn, tenant, 52, 36), 56)
    p = _mine(conn)[0]
    assert learn.decide(conn, p["id"], "reject", "neha", "a copying slip")["code"] is None
    assert _mine(conn) == [] and learned.rules(conn) == []
