"""The graph's scenarios: does a child's ledger of papers give the states and the next level worked out by hand?
`engine goal gr1-state-from-recent-evidence`.

A scenario is a ledger: one line per paper, its school day, its level and each answer's mark. Each line is written as
the school's own papers are: a sheet for the child, a capture of it, a question at that level, a signed-off answer and
its evidence. Then the database decides, as on live (`rebuild_child_skill_state`, `child_level_state`,
`next_difficulty`), and the result is compared with what the goal file says. The child is one of a section of its own,
and the caller rolls everything back.
"""

import datetime
import json
import uuid

from engine.core import db

SECTION = "GR1-GOAL"
DAY0 = datetime.date(2026, 9, 1)
MARKS = {"R": ("correct", True), "W": ("wrong", False), "B": ("blank", None)}


def _tenant(conn):
    return db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]


def _paper(conn, t, child, skill, line):
    """One line of a ledger written as a real paper: sheet, capture, and per mark a question at the line's level, a
    signed-off answer and its evidence, sat on day `line.day` at 10:00 in the school's time zone."""
    tag = uuid.uuid4().hex[:8].upper()
    at = db.one(
        conn,
        "select (%s::timestamp + interval '10 hours') at time zone"
        " (select value #>> '{}' from config where tenant_id = %s and key = 'school.time_zone') as at",
        (DAY0 + datetime.timedelta(days=int(line["day"])), t),
    )["at"]
    tpl = conn.execute(
        "insert into sheet_template (tenant_id, band, child_id, week, key, batch_id) values (%s, 'G2', %s, %s, %s, %s)"
        " returning id",
        (t, child, f"GR1-{tag}", json.dumps({"code": tag}), tag),
    ).fetchone()["id"]
    inst = conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status)"
        " values (%s, %s, %s, %s, 'returned') returning id",
        (t, f"CS{tag[:6]}", tpl, child),
    ).fetchone()["id"]
    cap = conn.execute(
        "insert into capture (tenant_id, path, pages, sheet_instance_id, status) values (%s, 'gr1.pdf', 1, %s,"
        " 'processed') returning id",
        (t, inst),
    ).fetchone()["id"]
    for n, mark in enumerate(line["marks"].split()):
        sign, _, code = mark.partition(":")
        status, correct = MARKS[sign]
        item = conn.execute(
            "insert into item (tenant_id, item_key, template, rung_code, skill_codes, skill_set_code, difficulty,"
            " signal, fmt, spec, responses) values (%s, %s, 'gr1', %s, %s, %s, %s, 'Procedural', 'column', %s, %s)"
            " returning id",
            (
                t,
                f"gr1/{tag}/{n}",
                skill["rung_code"],
                [skill["registry"]],
                skill["code"],
                line["level"],
                json.dumps({"op": "+", "a": 34, "b": 25, "page": 1}),
                json.dumps([{"rid": "a", "answer": 59}]),
            ),
        ).fetchone()["id"]
        res = conn.execute(
            "insert into item_result (tenant_id, capture_id, item_id, rid, status, misconception_codes, state,"
            " confirmed_by, confirmed_at) values (%s, %s, %s, 'a', %s, %s, 'confirmed', 'goal@example.org', %s)"
            " returning id",
            (t, cap, item, status, [code] if code else [], at),
        ).fetchone()["id"]
        conn.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes,"
            " channel, item_result_id, observed_at, confirmed_by) values (%s, %s, %s, %s, %s, %s, 'item', %s, %s,"
            " 'goal@example.org')",
            (t, child, skill["registry"], skill["rung_code"], correct, [code] if code else [], res, at),
        )


def ledger(conn, sc):
    """A child of SECTION with the scenario's papers and, when it says so, a prescription at its level. Returns
    (child id, the skill: its code, rung and registry skill)."""
    t = _tenant(conn)
    skill = db.one(
        conn,
        "select s.code, s.rung_code, (select i.skill_codes[1] from item i where i.tenant_id = s.tenant_id"
        " and i.skill_set_code = s.code and cardinality(i.skill_codes) > 0 order by i.item_key limit 1) as registry"
        " from skill s where s.tenant_id = %s and s.code = %s",
        (t, sc["skill"]),
    )
    roll = db.one(
        conn, "select count(*) + 1 as n from child where tenant_id = %s and section = %s", (t, SECTION)
    )["n"]
    child = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s, %s, %s, 'G2') returning id",
        (t, str(roll), SECTION),
    ).fetchone()["id"]
    conn.execute(
        "insert into pii.child (tenant_id, child_id, first_name) values (%s, %s, 'Goal')", (t, child)
    )
    for line in sc["ledger"]:
        _paper(conn, t, child, skill, line)
    if sc.get("prescribed"):
        conn.execute(
            "insert into prescription (tenant_id, child_id, week, kind, skill_set_code, difficulty, rule_fired)"
            " values (%s, %s, 'GR1', 'practice', %s, %s, 'goal')",
            (t, child, sc["skill"], sc["prescribed"]),
        )
    return child, skill


def measure(conn, sc):
    """What the database decides for the scenario's ledger: each level's state, the skill's one state and its
    repeating mistake, and the next paper's level and rule."""
    child, skill = ledger(conn, sc)
    conn.execute("select rebuild_child_skill_state(%s)", (child,))
    levels = {
        r["difficulty"]: r["state"]
        for r in conn.execute(
            "select difficulty, state from child_level_state where child_id = %s and skill_code = %s",
            (child, sc["skill"]),
        )
    }
    row = db.one(
        conn,
        "select state, repeating_misconception from child_skill_state where child_id = %s and skill_code = %s"
        " and rung_code = %s",
        (child, skill["registry"], skill["rung_code"]),
    )
    nxt = db.one(conn, "select difficulty, rule from next_difficulty(%s, %s)", (child, sc["skill"]))
    return {
        "levels": levels,
        "skill": row["state"] if row else None,
        "repeating": row["repeating_misconception"] if row else None,
        "next": nxt["difficulty"],
        "rule": nxt["rule"],
    }


def run(conn, sc):
    """(measurements, failures): every expectation the scenario names, compared with what the database decided."""
    try:
        got = measure(conn, sc)
    finally:
        conn.rollback()  # a scenario proves the rule, it never leaves a child behind
    failures = [
        f"{key}: expected {want!r}, got {got[key]!r}"
        for key, want in sc["expect"].items()
        if got[key] != want
    ]
    return got, failures
