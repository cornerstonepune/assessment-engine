"""N12 — every parent report that is due, written at once (goals/w4d-every-report-written.yaml).
- `due` finds each child a report can be written for whose newest one is missing or out of date.
- `write_each` writes them one after another, each exactly as the page's button does (`parent_report.start` and
  `.write`), and reads back whether it was kept.
Nimish, 2026-09-30: "the reports havent been generated for grade 3; please go ahead and generate all the reports".
Until now a report was written only when someone opened a child's page and pressed its button."""

from engine.core import db
from engine.w4_close import parent_report


def due(conn, band=None):
    """Every child, or every child of one band, whose parent report is due → [{child_id, band, section, roll_no, why}],
    by band, section and roll. A child with nothing signed off has nothing to report yet, and a report still true of the
    child's answers, approved or not, is left as it is."""
    kids = conn.execute(
        "select c.id, c.band, c.section, c.roll_no from child c where c.active"
        " and (%(b)s::text is null or c.band = %(b)s)"
        " and exists (select 1 from evidence_event e where e.child_id = c.id and e.confirmed_by is not null)"
        " order by c.band, c.section, roll_order(c.roll_no), c.roll_no",
        {"b": band},
    ).fetchall()
    out = []
    for k in kids:
        if parent_report.facts(conn, k["id"]) is None:
            continue  # its signed-off answers are all on papers read again since
        note = parent_report.latest(conn, k["id"])
        if note and not note["stale"]:
            continue
        why = (
            "no report yet"
            if note is None
            else "its facts changed since it was written: answers signed off, or the child's grade"
        )
        out.append(
            {"child_id": str(k["id"]), "band": k["band"], "section": k["section"], "roll_no": k["roll_no"]}
            | {"why": why}
        )
    return out


def write_each(by, kids):
    """`parent_report.write` for each child in turn, in `by`'s name → each child as given with `kept`, and `error`
    saying why not. Each is a run of its own, as the page's button starts one, so `/runs/{id}` shows it too."""
    done = []
    for k in kids:
        run = parent_report.start(k["child_id"], by)
        parent_report.write(run, k["child_id"])
        with db.connect() as conn:
            r = conn.execute("select status, error from flow_run where id = %s", (run,)).fetchone()
        done.append({**k, "kept": r["status"] == "ok", "error": r["error"]})
    return done
