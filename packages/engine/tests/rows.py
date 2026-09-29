"""Rows a database test builds for itself, inside its own transaction, so it proves the same thing on a database
built from the repository (`bin/testdb fresh`, what CI runs) as on a copy of live — never "whatever live holds".
"""

import json
import uuid

from engine.core import db


def tenant(conn):
    return conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]


def a_child(conn, section=None):
    """A Grade 2 child in a section of its own, on the roster as every child is: `child` and its `pii` row."""
    t = tenant(conn)
    section = section or f"ROWS-{uuid.uuid4().hex[:6].upper()}"
    child = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s, '1', %s, 'G2') returning id",
        (t, section),
    ).fetchone()["id"]
    conn.execute(
        "insert into pii.child (tenant_id, child_id, first_name) values (%s, %s, 'Rowstest')", (t, child)
    )
    return child


def a_read_paper(conn, answers, path="scan.pdf", paper="TEST-P1", fmt="column"):
    """One child's paper, read: a child, the worksheet it was printed from, its copy, the scan and one answer per
    entry of `answers`. Each entry is a dict of `status` (correct / wrong / blank / needs_teacher), `read` (what
    the reader took the child to have written), and optionally `state` (candidate / confirmed) and `typed` (a
    person's correction of the reading). → {"child", "capture", "results": [item_result ids, in order]}."""
    t = tenant(conn)
    tag = uuid.uuid4().hex[:6].upper()
    child = a_child(conn, f"ROWS-{tag}")
    tpl = conn.execute(
        "insert into sheet_template (tenant_id, band, child_id, week, key, batch_id) values (%s, 'G2', %s, %s, %s, %s)"
        " returning id",
        (t, child, f"ROWS-{tag}", json.dumps({"code": paper}), paper),
    ).fetchone()["id"]
    inst = conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, print_status)"
        " values (%s, %s, %s, %s, 'returned') returning id",
        (t, f"CS{tag}", tpl, child),
    ).fetchone()["id"]
    cap = conn.execute(
        "insert into capture (tenant_id, path, pages, sheet_instance_id, status) values (%s, %s, 1, %s, 'processed')"
        " returning id",
        (t, str(path), inst),
    ).fetchone()["id"]
    results = []
    for n, a in enumerate(answers, start=1):
        item = conn.execute(
            "insert into item (tenant_id, item_key, template, rung_code, skill_codes, signal, fmt, spec, responses)"
            " values (%s, %s, 'rows', 'R24', '{NUM.OPS.02}', 'Procedural', %s, %s, %s) returning id",
            (
                t,
                f"rows/{tag}/{n}",
                fmt,
                json.dumps({"op": "-", "a": 62, "b": 27, "page": 1}),
                json.dumps([{"rid": "a", "answer": 35}]),
            ),
        ).fetchone()["id"]
        state = "blank" if a["status"] == "blank" else "written"
        raw = {"child_answer": a["read"], "answer_state": state, "confidence": 95.0, "why": ""}
        res = conn.execute(
            "insert into item_result (tenant_id, capture_id, item_id, rid, raw_read, status, state)"
            " values (%s, %s, %s, 'a', %s, %s, %s) returning id",
            (t, cap, item, json.dumps(raw), a["status"], a.get("state", "candidate")),
        ).fetchone()["id"]
        if "typed" in a:
            conn.execute(
                "insert into read_correction (tenant_id, child_id, capture_id, item_result_id, model_read, human_read, by)"
                " values (%s, %s, %s, %s, %s, %s, 'tester@example.org')",
                (t, child, cap, res, a["read"], a["typed"]),
            )
        results.append(res)
    return {"child": child, "capture": cap, "results": results}
