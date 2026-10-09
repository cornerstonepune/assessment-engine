"""What the copies read from one scanned file came to (N8): each copy's score by its child's class and roll number,
and every answer as the reader left it — for a person on the site, or a session through the engine's API, without the
database and never with a name (rule 6). Reading the copies is `copies.read`'s; this only reports on it.
"""

from pathlib import Path

from engine.w3_read import copies


def tally(conn, capture_id) -> dict:
    """What the engine made of one copy's answers: settled right, and waiting for a person as read right,
    read wrong, read blank or not read at all — the reason each waits is its own (`marking.mark_read`)."""
    return conn.execute(
        "select count(*) filter (where status = 'correct') as right,"
        " count(*) filter (where status <> 'correct' and raw_read::jsonb ->> 'why' like 'read as a right%%')"
        "   as right_waiting,"
        " count(*) filter (where raw_read::jsonb ->> 'why' like 'read as a wrong%%') as wrong,"
        " count(*) filter (where raw_read::jsonb ->> 'why' like 'read as blank%%') as blank,"
        " count(*) filter (where status <> 'correct') as waiting"
        " from item_result where capture_id = %s",
        (capture_id,),
    ).fetchone()


def of_scan(conn, name: str) -> list[dict]:
    """Every copy read from one scanned file, in file order, as its child's class and roll number (never a name,
    rule 6), the worksheet, and what the engine made of its answers (`tally`): the per-child score of a scan, for
    whoever needs it without the database — a person on the site, or a session through the engine's API."""
    stem = Path(name).stem
    rows = conn.execute(
        "select c.id as capture_id, c.path, ch.section, ch.roll_no, coalesce(t.code, t.batch_id) as code,"
        " (select count(*) from item_result r where r.capture_id = c.id) as answers"
        " from capture c join sheet_instance si on si.id = c.sheet_instance_id"
        " join sheet_template t on t.id = si.sheet_template_id left join child ch on ch.id = si.child_id"
        " where c.superseded_by is null and (c.path like %s or c.path like %s) order by c.path",
        (copies._home(copies.CUT / stem) + "/%", copies._home(copies.WAS_CUT / stem) + "/%"),
    ).fetchall()
    out = []
    for r in rows:
        t = tally(conn, r["capture_id"])
        unclear = t["waiting"] - t["right_waiting"] - t["wrong"] - t["blank"]
        out.append({"copy": Path(r["path"]).name.split("-")[0], "section": r["section"], "roll_no": r["roll_no"],
                    "code": r["code"], "capture_id": str(r["capture_id"]), "answers": r["answers"],
                    "right": t["right"] + t["right_waiting"], "wrong": t["wrong"], "blank": t["blank"],
                    "unclear": max(0, unclear), "waiting": t["waiting"]})  # fmt: skip
    return out


def readings(conn, capture_id) -> list[dict]:
    """Every answer on one read copy as the reader left it — its state, why it waits, how many boxes the paper
    printed and how many held ink, what the reader saw — with no name and no image: what someone improving the
    reader needs to see why answers came back unclear, through the engine's API."""
    rows = conn.execute(
        "select i.item_key, r.rid, r.status, r.raw_read::jsonb as raw"
        " from item_result r join item i on i.id = r.item_id where r.capture_id = %s order by i.item_key, r.rid",
        (capture_id,),
    ).fetchall()
    keep = (
        "page",
        "file_page",
        "answer_state",
        "why",
        "child_answer",
        "guess",
        "confidence",
        "boxes",
        "inked",
        "seen",
        "working_shown",
    )
    return [
        {
            "item": r["item_key"],
            "answer": r["rid"],
            "status": r["status"],
            **{k: (r["raw"] or {}).get(k) for k in keep},
        }
        for r in rows
    ]
