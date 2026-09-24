"""N6/N7 — a library worksheet an educator picks, printed for the children they pick: one copy each, each with its
own QR.

Printing the worksheet itself hands out copies no row records: every copy carries the worksheet's code, and whose
copy it is can be read only from the name written on it (the Grade 2 papers of 2026-09-23). A copy printed here is
a sheet instance of its own — the code on the page resolves to the child and the worksheet, the questions the
child saw are recorded (`item_exposure`), and the educator who printed it is its approver — exactly as a paper
from Make papers (`assemble._hand_out`, `assemble.render`), so its scan sorts itself and is read for that child.
"""

from pathlib import Path

from engine.core import db
from engine.w2_print import assemble

KIND = "custom"  # a paper an educator asks for (migration 20261004090000), not the week's practice pack


def _instance(conn, qr):
    return conn.execute(
        "select si.id as instance_id, si.qr_code as qr, si.child_id, st.code, st.band, st.skill_set_code,"
        " st.difficulty, st.item_ids from sheet_instance si join sheet_template st on st.id = si.sheet_template_id"
        " where si.qr_code = %s",
        (qr,),
    ).fetchone()


def for_children(conn, code: str, child_ids: list, week: str, by: str, outdir: Path) -> Path:
    """One copy of worksheet `code` for each child, in roll order, merged into one PDF to print. The same
    worksheet printed again for the same child in the same week is the same copy, not a second one."""
    if not by:
        raise ValueError("a printed paper names the person who printed it")
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    w = conn.execute(
        "select id, code, item_ids, skill_set_code, difficulty, band, retired_at from sheet_template"
        " where source = 'library' and code = %s",
        (code,),
    ).fetchone()
    if not w:
        raise LookupError(f"no worksheet {code}")
    if w["retired_at"]:
        raise ValueError(
            f"{code} is retired: a question on it left the bank — print the worksheet that replaced it"
        )
    kids = conn.execute(
        "select id, roll_no, section from child where id = any(%s) and active"
        " order by section, coalesce(nullif(regexp_replace(roll_no, '\\D', '', 'g'), '')::int, 9999), roll_no",
        (list(child_ids),),
    ).fetchall()
    if len(kids) != len(set(map(str, child_ids))):
        raise LookupError("a child asked for is not on the roll")
    sheets = []
    for c in kids:
        into = {"section": c["section"], "week": week, "kind": KIND}
        p = {"id": None, "child_id": c["id"], "roll_no": c["roll_no"], "band": w["band"],
             "skill_set_code": w["skill_set_code"], "difficulty": w["difficulty"], "rule_fired": "educator"}  # fmt: skip
        qr = assemble._qr(w["id"], c["id"], c["section"], c["roll_no"], week, KIND)
        had = _instance(conn, qr)
        if had:
            rows = {
                r["id"]: r for r in conn.execute("select * from item where id = any(%s)", (had["item_ids"],))
            }
            sheets.append({**had, "roll_no": c["roll_no"], "item_rows": [rows[i] for i in had["item_ids"]]})
        else:
            sheets.append(assemble._hand_out(conn, tenant, into, p, w))
    conn.execute(
        "update sheet_instance set print_status = 'printed', printed_at = now(), approved_by = %s,"
        " approved_at = now(), updated_at = now() where id = any(%s) and print_status = 'new'",
        (by, [s["instance_id"] for s in sheets]),
    )
    out = assemble.render(conn, {"sheets": sheets, "spares": []}, outdir, week, by, KIND)
    return Path(out["pack"])
