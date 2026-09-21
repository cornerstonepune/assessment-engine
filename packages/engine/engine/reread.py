"""Read the corpus again, from the rows the database already holds (goals/s4-validation-queue.yaml).

The reader keeps its best guess for an answer it is unsure of (`raw_read.guess`, never marked from),
but the stored readings predate that: this reads every live scan again so the validation queue can
offer the guess for a one-click confirm. The reader itself is unchanged.

Every live capture already carries its file, its child, the paper it was read against and the pages
of that paper its answers land on — exactly what `legacy.import_scan` takes — so nothing names a
child here (rule 6). A paper a person has signed off or corrected is never read again
(`legacy.worked_on`). Every settled answer whose reading changed is named in the result, so a re-read
that moved anything the engine stood behind cannot pass unnoticed.
"""

from pathlib import Path

from engine import legacy

SETTLED = ("correct", "wrong", "blank")


def _answers(conn):
    rows = conn.execute(
        "select c.sheet_instance_id as paper, r.item_id, r.id, r.status,"
        " r.raw_read::jsonb ->> 'child_answer' as read"
        " from item_result r join capture c on c.id = r.capture_id where c.superseded_by is null"
    ).fetchall()
    return {(r["paper"], r["item_id"]): r for r in rows}


def files(conn, only=None):
    """Every live scan with its child, its paper and the pages its answers land on."""
    rows = conn.execute(
        "select c.path, st.key ->> 'code' as paper, si.child_id,"
        " array_agg(distinct coalesce((i.spec ->> 'page')::int, 1)) as pages"
        " from capture c"
        " join sheet_instance si on si.id = c.sheet_instance_id"
        " join sheet_template st on st.id = si.sheet_template_id"
        " join item_result r on r.capture_id = c.id"
        " join item i on i.id = r.item_id"
        " where c.superseded_by is null"
        " group by c.id, c.path, st.key ->> 'code', si.child_id"
        " order by st.key ->> 'code', c.path"
    ).fetchall()
    return [r for r in rows if not only or r["paper"] in only]


def run(conn, only=None, commit=True):
    before = _answers(conn)
    out = {"read": 0, "missing": 0, "failed": 0, "changed": [], "errors": []}
    for f in files(conn, only):
        path = Path(f["path"]).expanduser()
        if not path.exists():
            out["missing"] += 1
            out["errors"].append(f"{f['paper']} {path.name}: not on this machine")
            continue
        try:
            with conn.transaction():  # a savepoint: one file that fails leaves the others' work intact
                legacy.import_scan(
                    conn,
                    path=str(path),
                    paper_code=f["paper"],
                    child_id=f["child_id"],
                    pages=sorted(f["pages"]),
                    actor="read again",
                    again=True,
                )
            out["read"] += 1
        except Exception as e:  # noqa: BLE001 — one file must not stop the corpus; every failure is reported
            out["failed"] += 1
            out["errors"].append(f"{f['paper']} {path.name}: {type(e).__name__}: {e}")
        if commit:
            conn.commit()
    after = _answers(conn)
    for key, was in before.items():
        now = after.get(key)
        if was["status"] in SETTLED and (
            now is None or (now["status"], now["read"]) != (was["status"], was["read"])
        ):
            out["changed"].append(
                {
                    "item_result": was["id"],
                    "was": was["status"],
                    "now": now["status"] if now else "not read",
                    "read_was": was["read"],
                    "read_now": now["read"] if now else None,
                }
            )
    return out
