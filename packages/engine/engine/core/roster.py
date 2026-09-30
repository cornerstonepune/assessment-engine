"""The class list.

A child's name is the one piece of this system that is genuinely sensitive, so it lives in the
`pii` schema and nowhere else: `child` carries a roll number, a band and a section, and every
other table joins to that. The roster file itself stays outside the repository — it has names in
it — and is read by path.
"""

import json
from pathlib import Path

from engine.core import db


def load(path: Path) -> dict:
    """Upsert children from a roster file → how many were added, how many already existed, and each child whose
    grade it changed, by class and roll: the list is the only thing that sets a child's band, and one loaded again
    with an old slip in it (G3 roll 5 as G4, 2026-09-30) would undo a correction unseen.

    The file is `{"children": [{"roll_no", "section", "band", "first_name", "last_name"?}]}`.
    Matching is on (section, roll_no), so re-running after a correction updates rather than
    duplicating — a child who changes section is a new row, which is the honest reading.
    """
    children = json.loads(Path(path).read_text())["children"]
    added = updated = 0
    changed = []
    with db.connect() as conn:
        tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
        for c in children:
            key = (tenant, c["section"], str(c["roll_no"]))
            was = conn.execute(
                "select band from child where tenant_id = %s and section = %s and roll_no = %s", key
            ).fetchone()
            row = conn.execute(
                "insert into child (tenant_id, roll_no, section, band) values (%s,%s,%s,%s)"
                " on conflict (tenant_id, section, roll_no) do update set band = excluded.band,"
                " updated_at = now() returning id, (xmax = 0) as inserted",
                (tenant, str(c["roll_no"]), c["section"], c["band"]),
            ).fetchone()
            added, updated = (added + 1, updated) if row["inserted"] else (added, updated + 1)
            if was and was["band"] != c["band"]:
                changed.append(f"{c['section']} roll {c['roll_no']}: {was['band']} → {c['band']}")
            conn.execute(
                "insert into pii.child (tenant_id, child_id, first_name, last_name, home_languages)"
                " values (%s,%s,%s,%s,%s)"
                " on conflict (tenant_id, child_id) do update set first_name = excluded.first_name,"
                " last_name = excluded.last_name, home_languages = excluded.home_languages,"
                " updated_at = now()",
                (tenant, row["id"], c["first_name"], c.get("last_name", ""), c.get("home_languages", [])),
            )
        conn.commit()
    return {"added": added, "already known": updated, "grade changed": changed}


def class_band(conn, section):
    """The grade a class works at: the one most of its active children are in, the lower on a tie, so the same every
    time. A child may work at another grade within a class, and is prescribed at their own (`test_week`); a class's
    week is its own grade's. `limit 1` over the class took whichever child came first, so one child entered in the
    wrong grade could move the whole class's week (G3 roll 5 as G4, 2026-09-30). None for a class with no child."""
    row = conn.execute(
        "select band from child where section = %s and active group by band order by count(*) desc, band limit 1",
        (section,),
    ).fetchone()
    return row and row["band"]


def names(conn, child_ids: list[str], actor: str) -> dict[str, str]:
    """Names for printing on a worksheet, through the logging accessor — every read is recorded
    in `access_log` with who asked. Nothing else in the engine may touch `pii.child` directly."""
    out = {}
    for cid in child_ids:
        row = conn.execute("select * from pii.read_child(%s, %s)", (cid, actor)).fetchone()
        if row:
            out[cid] = " ".join(x for x in (row["first_name"], row["last_name"]) if x)
    return out


def find(conn, section: str, first_name: str, actor: str) -> str:
    """The child id for a first name in a section, for the legacy importer's `--child`. The lookup
    is logged like a read, because it is one."""
    rows = conn.execute(
        "select c.id from child c join pii.child p on p.child_id = c.id"
        " where c.section = %s and lower(p.first_name) = lower(%s)",
        (section, first_name),
    ).fetchall()
    if len(rows) != 1:
        raise ValueError(f"{len(rows)} children called {first_name!r} in {section}")
    conn.execute(
        "insert into access_log (tenant_id, actor, child_id, action)"
        " select tenant_id, %s, id, 'find_child' from child where id = %s",
        (actor, rows[0]["id"]),
    )
    return rows[0]["id"]
