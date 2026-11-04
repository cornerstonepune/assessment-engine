"""A sheet for people to mark drafted K2 pages keep or reject (goals/m1-11f-draft-rules.yaml).

The machine's verdicts on the drafts (the checker's, the drafter's own confidence) have no score until they are set against
a person's. This lists a spread of drafted pages, the school's text beside the draft, with two empty columns for the
person: `verdict` (keep, change or reject) and `what_is_wrong`. What the machine said of a draft is left off on purpose:
a person who has read it marks differently. The pages are taken from every section in turn, the same ones every time.
"""

import csv
import io

import typer

from engine.core import db
from engine.w1_bank.k2_gaps import PAGE_PARTS
from engine.w1_bank.k2_upload import config, curriculum_app
from engine.w1_bank.map_eval import split


def sheet(conn: db.Conn, tenant: db.Id, band: str, n: int) -> list[dict]:
    """→ up to `n` drafted pages, each one row: where it is, the school's materials, each text part with who wrote it."""
    pages = {
        r["code"]: r
        for r in conn.execute(
            "select a.code, a.name, a.strand, a.materials, a.objective, a.steps, a.thinking, a.level_0, a.level_1,"
            " a.level_2, a.level_3 from activity a where a.tenant_id = %s and a.band = %s and exists ("
            "select 1 from activity_part_source s where s.tenant_id = a.tenant_id and s.activity_code = a.code"
            " and s.source = 'drafted') order by a.code",
            (tenant, band),
        ).fetchall()
    }
    by = {
        (r["activity_code"], r["part"]): r["source"]
        for r in conn.execute(
            "select activity_code, part, source from activity_part_source where tenant_id = %s", (tenant,)
        ).fetchall()
    }
    chosen, _ = split({c: r["strand"] for c, r in pages.items()}, n)
    out = []
    for code in sorted(chosen):
        r = pages[code]
        row = {
            "code": code,
            "section": r["strand"],
            "activity": r["name"],
            "materials": r["materials"].strip(),
        }
        for part in PAGE_PARTS:
            row[part] = (r[part] or "").strip()
            row[f"{part}_by"] = by.get((code, part), "school" if row[part] else "")
        out.append({**row, "verdict": "", "what_is_wrong": ""})
    return out


def to_csv(rows: list[dict]) -> str:
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return buf.getvalue()


@curriculum_app.command("gold-sheet")
def gold_sheet(n: int = typer.Option(30, "--pages", help="How many pages")) -> None:
    """Print a CSV of drafted pages, the school's text beside the draft, for people to mark keep, change or reject."""
    with db.connect() as conn:
        conn.read_only = True
        tenant = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
        typer.echo(to_csv(sheet(conn, tenant, config()["band"], n)), nl=False)
