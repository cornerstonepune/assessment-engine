"""Which readings no longer match the paper they were read against.

A capture is idempotent on the file's bytes (`capture.file_sha256`), which is right: reading the
same scan twice must not make two sets of candidates. But a capture is a reading of **two** things —
the scan *and* the paper's answer slots — and only one of them was in the key. When `G2-CAM-A` was
corrected from 24 slots to the 27 its page actually holds, the ten readings taken against the old
shape stayed live and `legacy import` reported "nothing to do", because the file had not changed.

So a reading is stale when the paper has more answer slots than it found, and nothing else detects
that: the rows look complete, the counts look plausible, and three answers per child are simply
absent. This is the same class as the defect it followed — a missing row is invisible.

Nothing here supersedes anything. It reports, and a person re-reads (rule: engine prepares, person
approves). Superseding a capture discards evidence a teacher may already have confirmed, and that is
not a call code makes on its own.
"""

from engine.core import db


def stale_captures(conn, paper_code=None):
    """Live captures that hold fewer answers than their paper now has slots for."""
    return conn.execute(
        "select t.batch_id, c.id as capture_id, c.path,"
        "       array_length(t.item_ids, 1) as slots,"
        "       (select count(*) from item_result r where r.capture_id = c.id) as answers"
        "  from capture c"
        "  join sheet_instance si on si.id = c.sheet_instance_id"
        "  join sheet_template t on t.id = si.sheet_template_id"
        " where c.superseded_by is null and t.source = 'legacy' and c.status = 'processed'"
        "   and (%s::text is null or t.batch_id = %s::text)"
        "   and (select count(*) from item_result r where r.capture_id = c.id)"
        "       < array_length(t.item_ids, 1)"
        " order by t.batch_id, c.path",
        (paper_code, paper_code),
    ).fetchall()


def report(conn, paper_code=None):
    rows = stale_captures(conn, paper_code)
    return [
        {
            "paper": r["batch_id"],
            "file": r["path"],
            "found": r["answers"],
            "slots": r["slots"],
            "missing": r["slots"] - r["answers"],
        }
        for r in rows
    ]


def demo():
    """`python -m engine.w3_read.stale` — the check against the live database, exit 1 if anything is stale."""
    with db.connect() as conn:
        rows = report(conn)
    for r in rows:
        print(
            f"  {r['paper']:<14} {r['found']:>3} of {r['slots']:<3} answers  ({r['missing']} missing)  {r['file']}"
        )
    print(f"  {len(rows)} stale reading(s)")
    return 1 if rows else 0


if __name__ == "__main__":
    raise SystemExit(demo())
