"""N3 — a paper entered once follows its file (goals/l2-live-audit-clean.yaml): its template holds the questions the
file has, in order, and a question of the paper the file no longer has leaves it. The file is what was printed; a
corrected file updates the rows (`legacy.load_paper`), and before 2026-10-12 a question it dropped stayed: G2-CAM-A's
question 5, stored whole on the old ladder's R9 before the file split it into 5a–5c on R31, kept R9 alive."""

import json
import re

import psycopg

ACTOR = "engine (legacy paper)"


def follow(conn, tenant, paper, ids, keys):
    """The paper's template set to the file's questions, and the questions it no longer has gone: removed when nothing
    points at one; retired when an answer or a correction does, so what points at it keeps it, and moved to the rung
    its number has in the file, as an old paper's sum moves to its skill, so it keeps no other rung alive. `keys` is
    (key, number, rung) for each question the file has. Returns the template id."""
    prefix = f"legacy/{paper['code']}/"
    rungs = {}
    for _, n, rung in keys:
        rungs.setdefault(n, set()).add(rung)
    for r in conn.execute(
        "select id, item_key from item where tenant_id = %s and source = 'legacy' and left(item_key, %s) = %s"
        " and not (item_key = any(%s))",
        (tenant, len(prefix), prefix, [k for k, _, _ in keys]),
    ).fetchall():
        try:
            with conn.transaction():
                conn.execute("delete from item where id = %s", (r["id"],))
            continue
        except psycopg.errors.ForeignKeyViolation:
            pass
        conn.execute(
            "insert into item_feedback (tenant_id, item_id, actor, verdict, note)"
            " select %s, %s, %s, 'retire', %s where exists (select 1 from item where id = %s and status = 'active')",
            (tenant, r["id"], ACTOR, f"no longer a question of {paper['code']} as its file says", r["id"]),
        )
        home = rungs.get(re.sub(r"\D+$", "", r["item_key"][len(prefix) :]), set())
        if len(home) == 1:
            conn.execute("update item set rung_code = %s where id = %s", (home.pop(), r["id"]))
    existing = conn.execute(
        "select id from sheet_template where tenant_id = %s and source = 'legacy' and batch_id = %s",
        (tenant, paper["code"]),
    ).fetchone()
    if existing:
        conn.execute(
            "update sheet_template set band = %s, week = %s, item_ids = %s, key = %s, updated_at = now()"
            " where id = %s",
            (paper["band"], paper["week"], ids, json.dumps(paper), existing["id"]),
        )
        return existing["id"]
    return conn.execute(
        "insert into sheet_template (tenant_id, band, week, variant, batch_id, item_ids, key, source)"
        " values (%s,%s,%s,1,%s,%s,%s,'legacy') returning id",
        (tenant, paper["band"], paper["week"], paper["code"], ids, json.dumps(paper)),
    ).fetchone()["id"]
