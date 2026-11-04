"""Rows a database test builds for itself, inside its own transaction, so it proves the same thing on a database
built from the repository (`bin/testdb fresh`, what CI runs) as on a copy of live — never "whatever live holds".
"""

import json
import re
import uuid

from engine.core import db


def drawn(make):
    """A question drawn as the bank draws one: a maker's "draw again" (numbers no story of its shape holds, a fact
    family 7 × 7 cannot make) is drawn again, as `draw._paired` and `bank.fill` always have."""
    for _ in range(200):
        try:
            return make()
        except RuntimeError:
            continue
    raise AssertionError("nothing drawn in 200 tries")


def tenant(conn):
    return conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]


def a_registry_skill(conn, tenant, code="NUM.OPS.01"):
    """The school's registry skill `code` given to a school a test made for itself: a question names one (C1)."""
    conn.execute(
        "insert into registry_skill (tenant_id, code, domain, strand, name)"
        " select %s, code, domain, strand, name from registry_skill where code = %s limit 1"
        " on conflict do nothing",
        (tenant, code),
    )
    return code


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


WAITED = {
    "correct": "read as a right answer; a person checks every answer of this kind until the reader is trusted on it",
    "wrong": "read as a wrong answer; a person checks every wrong answer before it counts",
    "blank": "read as blank; a person checks every blank before it counts",
}


def a_read_paper(conn, answers, path="scan.pdf", paper="TEST-P1", fmt="column"):
    """One child's paper, read: a child, the worksheet it was printed from, its copy, the scan and one answer per
    entry of `answers`. Each entry is a dict of `status` (correct / wrong / blank / needs_teacher), `read` (what
    the reader took the child to have written), and optionally `state` (candidate / confirmed), `typed` (a
    person's correction of the reading) and `why` (the reason it waited; a confirmed answer's is marking's hold). → {"child", "capture", "results": [item_result ids, in order]}."""
    t = tenant(conn)
    tag = uuid.uuid4().hex.upper()  # all of it: six digits of it collided on a unique column (M0-04)
    child = a_child(conn, f"ROWS-{tag[:8]}")
    tpl = conn.execute(
        "insert into sheet_template (tenant_id, band, child_id, week, key, batch_id) values (%s, 'G2', %s, %s, %s, %s)"
        " returning id",
        (t, child, f"ROWS-{tag[:8]}", json.dumps({"code": paper}), paper),
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
        # an answer a person signed off had waited for them, as marking holds every answer until its kind is trusted
        why = a.get("why", WAITED.get(a["status"], "") if a.get("state") == "confirmed" else "")
        raw = {"child_answer": a["read"], "answer_state": state, "confidence": 95.0, "why": why}
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


def data_steps(migration):
    """A migration's data steps (its `do $$ … end $$;` blocks and its top-level update, insert and delete statements),
    to run again on today's schema and functions. A later migration can make an earlier one's DDL impossible to repeat
    (B4 dropped the `rung` table B1 and B3 put triggers on; B4b made `skill_set` a view, which C1 dropped, so a step
    naming it names today's `skill`); what those tests prove — running the migration's rows again changes nothing — is
    these steps, in their order."""
    step = r"^do \$\$.*?^end \$\$;|^(?:update|insert into|delete from)\b.*?;[ \t]*$"
    steps = "\n".join(m.group(0) for m in re.finditer(step, migration.read_text(), re.S | re.M))
    return re.sub(r"\bskill_set\b", "skill", steps)


def forget_paper(conn, paper):
    """Take away what `a_read_paper` wrote and what reading it wrote after, for a test that had to commit it (a second
    connection reads it) and so must put the database back as it found it (M0-04c). `paper` is what `a_read_paper`
    returned. Some of what a reading writes is append-only by trigger, so the triggers are off for this transaction
    (`session_replication_role`, the tests' own role may), and every row that names the paper's capture, child, copy or
    items is deleted by that name, whatever table it is in. The caller commits."""
    items = [
        r["item_id"]
        for r in conn.execute("select item_id from item_result where capture_id = %s", (paper["capture"],))
    ]
    sheet = conn.execute(
        "select c.sheet_instance_id as i, s.sheet_template_id as t from capture c"
        " join sheet_instance s on s.id = c.sheet_instance_id where c.id = %s",
        (paper["capture"],),
    ).fetchone()
    conn.execute("set local session_replication_role = replica")
    named = {
        "capture_id": [paper["capture"]],
        "item_id": items,
        "sheet_instance_id": [sheet["i"]],
        "child_id": [paper["child"]],
    }
    for column, ids in named.items():
        for r in conn.execute(
            "select table_schema as s, table_name as t from information_schema.columns c"
            " where column_name = %s and table_schema in ('public', 'pii')"
            " and (select table_type from information_schema.tables x where x.table_schema = c.table_schema"
            "      and x.table_name = c.table_name) = 'BASE TABLE'",
            (column,),
        ).fetchall():
            conn.execute(f'delete from {r["s"]}."{r["t"]}" where {column} = any(%s)', (ids,))
    conn.execute("delete from capture where id = %s", (paper["capture"],))
    conn.execute("delete from sheet_instance where id = %s", (sheet["i"],))
    conn.execute("delete from sheet_template where id = %s", (sheet["t"],))
    conn.execute("delete from item where id = any(%s)", (items,))
    conn.execute("delete from child where id = %s", (paper["child"],))
    conn.execute("set local session_replication_role = origin")
