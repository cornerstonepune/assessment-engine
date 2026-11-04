"""A sheet for people to mark drafted K2 pages keep or reject (goals/m1-11f-draft-rules.yaml, m1-11h-gold-sheet-delivery).

The machine's verdicts on the drafts (the checker's, the drafter's own confidence) have no score until they are set against
a person's. This lists a spread of drafted pages, the school's text beside the draft, with two empty columns for the
person: `verdict` (keep, change or reject) and `what_is_wrong`. What the machine said of a draft is left off on purpose:
a person who has read it marks differently. The pages are taken from every section in turn, the same ones every time.
The drafts are read from the ledger, so a draft nobody has applied yet is on it too.

The sheet holds the school's lesson text, and this repository and its logs are public: it is never printed in a run or
committed. It reaches a person as a download from the site, behind the staff sign-in (`api/routes/gold.py`).
"""

import csv
import io

import typer

from engine.core import db
from engine.w1_bank import map_ledger
from engine.w1_bank.k2_gaps import PAGE_PARTS
from engine.w1_bank.k2_upload import config, curriculum_app
from engine.w1_bank.map_eval import split

GONE = frozenset({"rejected", "reverted"})  # a draft turned down or taken back is not one to mark


def sheet(conn: db.Conn, tenant: db.Id, band: str, n: int) -> list[dict]:
    """→ up to `n` drafted pages, each one row: where it is, the school's materials, each text part with who wrote it."""
    drafts = {
        p["subject_code"]: p["proposal"]["parts"]
        for p in map_ledger.standing(conn, tenant)
        if p["kind"] == "page_part" and p["now"] not in GONE
    }
    pages = {
        r["code"]: r
        for r in conn.execute(
            "select code, name, strand, materials, objective, steps, thinking, level_0, level_1, level_2, level_3"
            " from activity where tenant_id = %s and band = %s order by code",
            (tenant, band),
        ).fetchall()
        if r["code"] in drafts
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
            if part in drafts[code]:
                row[part], row[f"{part}_by"] = str(drafts[code][part]).strip(), "drafted"
            else:
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
def gold_sheet(
    n: int = typer.Option(30, "--pages", help="How many pages"),
    out: str = typer.Option(..., "--out", help="The file to write; never a log, the text is the school's"),
) -> None:
    """Write a CSV of drafted pages, the school's text beside the draft, for people to mark keep, change or reject."""
    with db.connect() as conn:
        conn.read_only = True
        tenant = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
        rows = sheet(conn, tenant, config()["band"], n)
    with open(out, "w", newline="") as f:
        f.write(to_csv(rows))
    typer.echo(f"wrote {len(rows)} pages")
