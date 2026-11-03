"""`engine curriculum k2`: the K2 team's activity sheet, uploaded (goals/m0-02-k2-curriculum-upload.yaml).

Nimish, D-050: curriculum is an upload, people edit it afterwards, there is no signing step. The sheet's tab is read as
a CSV (exported by whoever has the sheet; this tab only, the workbook's other tabs hold children's names) and compared
with the `activity` rows. A dry run prints the comparison and writes nothing; `--apply` writes what the comparison
says. The sheet's words are stored as written; nothing a person edited on the site is overwritten (it is listed);
nothing is deleted; an empty cell never empties a filled field. Running twice changes nothing the second time.
"""

import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import typer

from engine.core import db

SEED = db.REPO_ROOT / "supabase" / "seed" / "k2_sheet.json"
BULLET = re.compile(r"^\s*(?:[•·●▪◦*–—-]|\d+[.)])\s*")
FIELDS = ("strand", "objective", "materials", "level_0", "level_1", "level_2", "level_3", "sheet_no")


def config() -> dict:
    return json.loads(SEED.read_text())


def _col(letters: str) -> int:
    n = 0
    for ch in letters:
        n = n * 26 + ord(ch) - 64
    return n - 1


def words(text: str) -> str:
    """What two spellings of the same words share: letters and digits only, any case."""
    return re.sub(r"[\W_]+", "", text).lower()


@dataclass
class Row:
    line: int  # the sheet's own row number
    values: dict[str, str]
    pillar: str
    extra: dict[str, str] = field(default_factory=dict)  # report-only columns, never stored


def read_csv(path: Path, cfg: dict | None = None) -> tuple[list[Row], list[tuple[int, str]]]:
    """→ the K2 activity rows, and the rows skipped with the reason (every row that is not an activity says why)."""
    cfg = cfg or config()
    cols = {k: _col(v) for k, v in cfg["columns"].items()}
    bad = set(cfg["error_cells"])
    rows: list[Row] = []
    skipped: list[tuple[int, str]] = []
    with path.open(newline="", encoding="utf-8") as f:
        for line, raw in enumerate(csv.reader(f), start=1):
            if line == 1:
                continue
            get = lambda k, raw=raw: raw[cols[k]].strip() if cols[k] < len(raw) else ""  # noqa: E731
            year, name, number = get("year"), get("name"), get("sheet_no")
            if not any(c.strip() for c in raw):
                continue
            if year.upper() != cfg["year"]:
                skipped.append(
                    (line, f"not {cfg['year']} (year '{year}')" if year else "a heading or spacer row")
                )
                continue
            if not name or name in bad:
                skipped.append((line, "no activity name" if not name else f"activity name is {name}"))
                continue
            values = {
                k: ("" if get(k) in bad else get(k)) for k in cols if k not in ("year", "name", "pillar")
            }
            values["name"] = name
            values["sheet_no"] = number if re.fullmatch(r"\d+", number) else ""
            extra = {k: (raw[_col(c)].strip() if _col(c) < len(raw) else "") for k, c in _extra(cfg).items()}
            rows.append(Row(line, values, get("pillar"), extra))
    return rows, skipped


def _extra(cfg: dict) -> dict[str, str]:
    return {f"{g}:{c}": c for g, cs in cfg["report_only"].items() for c in cs}


def bullets(text: str) -> tuple[list[str], int]:
    """A learning-outcomes cell as its separate outcomes (wrapped lines joined, a repeated outcome kept once), and
    how many repeats it dropped."""
    items: list[str] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        if BULLET.match(line) or not items:
            items.append(BULLET.sub("", line).strip())
        else:
            items[-1] += " " + line.strip()
    seen: set[str] = set()
    kept = [i for i in items if not (words(i) in seen or seen.add(words(i)))]
    return kept, len(items) - len(kept)


@dataclass
class Plan:
    inserts: list[Row] = field(default_factory=list)
    changes: list[tuple[str, Row, dict[str, tuple[str, str]]]] = field(
        default_factory=list
    )  # code, row, field → (was, now)
    kept: list[tuple[str, str, str]] = field(default_factory=list)  # code, field, why
    same: int = 0
    unmatched_db: list[str] = field(default_factory=list)
    by_name_only: list[tuple[str, int]] = field(default_factory=list)
    objectives: list[tuple[str | None, int, str, Row]] = field(
        default_factory=list
    )  # activity code (None: added), ord, title, row
    repeated_bullets: int = 0
    levels_filled: list[str] = field(default_factory=list)
    levels_missing: list[str] = field(default_factory=list)


def match(rows: list[Row], dbrows: list[dict]) -> dict[int, dict | None]:
    """Sheet row → its database row: the same strand and name, taken in the order both list them; a row whose strand
    was spelt otherwise is matched by name when exactly one such activity is left."""
    pool: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for d in sorted(dbrows, key=lambda d: d["code"]):
        pool[(words(d["strand"]), words(d["name"]))].append(d)
    out: dict[int, dict | None] = {}
    for r in rows:
        left = pool.get((words(r.values["strand"]), words(r.values["name"])))
        out[r.line] = left.pop(0) if left else None
    for r in rows:
        if out[r.line] is None:
            same_name = [d for k, ds in pool.items() for d in ds if k[1] == words(r.values["name"])]
            if len(same_name) == 1:
                out[r.line] = same_name[0]
                pool[(words(same_name[0]["strand"]), words(same_name[0]["name"]))].remove(same_name[0])
    return out


def plan(rows: list[Row], dbrows: list[dict], person_edited: set[tuple[str, str]]) -> Plan:
    p = Plan()
    matched = match(rows, dbrows)
    taken = {d["code"] for d in matched.values() if d}
    p.unmatched_db = sorted(d["code"] for d in dbrows if d["code"] not in taken)
    for r in rows:
        d = matched[r.line]
        found, dropped = bullets(r.values.get("objective", ""))
        p.repeated_bullets += dropped
        p.objectives += [(d["code"] if d else None, i, t, r) for i, t in enumerate(found, start=1)]
        if d is None:
            p.inserts.append(r)
            continue
        if words(d["strand"]) != words(r.values["strand"]):
            p.by_name_only.append((d["code"], r.line))
        diff: dict[str, tuple[str, str]] = {}
        for f in FIELDS:
            was, now = d[f] or "", r.values.get(f, "")
            if not now or was == now:
                continue
            if was and (d["code"], f) in person_edited:
                p.kept.append((d["code"], f, "edited on the site; the sheet's words are not written over it"))
            else:
                diff[f] = (was, now)
        if diff:
            p.changes.append((d["code"], r, diff))
        else:
            p.same += 1
        if not any(d[f"level_{i}"] for i in (1, 2, 3)):
            (
                p.levels_filled if any(r.values.get(f"level_{i}") for i in (1, 2, 3)) else p.levels_missing
            ).append(d["code"])
    return p


def report(p: Plan, skipped: list[tuple[int, str]], n_rows: int, n_db: int) -> str:
    by_reason: dict[str, list[int]] = defaultdict(list)
    for line, why in skipped:
        by_reason[why].append(line)
    out = [
        f"sheet rows that are K2 activities: {n_rows}    activities in the database (K2): {n_db}",
        f"  same as the database already:        {p.same}",
        f"  would change an existing activity:   {len(p.changes)}",
        f"  would be added (not in database):    {len(p.inserts)}",
        f"  in the database, not in the sheet:   {len(p.unmatched_db)} (never deleted)",
        f"  kept because edited on the site:     {len(p.kept)}",
        f"  levels filled where there were none: {len(p.levels_filled)}; still none (the sheet has none): {len(p.levels_missing)}",
        f"  learning outcomes to link:           {len(p.objectives)} (on {len({r.line for *_, r in p.objectives})} activities;"
        f" {p.repeated_bullets} repeated outcomes kept once)",
        "skipped sheet rows, with the reason:",
    ]
    out += [
        f"  {len(v):>4} × {why}: rows {', '.join(map(str, v[:12]))}{' …' if len(v) > 12 else ''}"
        for why, v in sorted(by_reason.items())
    ]
    counts: dict[str, int] = defaultdict(int)
    for _, _, diff in p.changes:
        for f in diff:
            counts[f] += 1
    out.append("levels filled from the sheet: " + (", ".join(sorted(p.levels_filled)) or "none"))
    out.append(
        "levels still missing (the sheet has none either): " + (", ".join(sorted(p.levels_missing)) or "none")
    )
    out.append(
        "fields that would change: " + (", ".join(f"{f} {n}" for f, n in sorted(counts.items())) or "none")
    )
    return "\n".join(out)


def snapshot(conn, tenant) -> tuple[list[dict], set[tuple[str, str]]]:
    cfg = config()
    dbrows = conn.execute(
        "select code, strand, name, objective, materials, level_0, level_1, level_2, level_3, sheet_no from activity"
        " where tenant_id = %s and band = %s",
        (tenant, cfg["band"]),
    ).fetchall()
    edited = {
        (r["code"], r["field"])
        for r in conn.execute(
            "select code, field from curriculum_edit where tenant_id = %s and record = 'activity'"
            " and changed_by not like %s",
            (tenant, cfg["upload_label"] + "%"),
        ).fetchall()
    }
    return dbrows, edited


def apply(conn, tenant, p: Plan, by: str) -> dict[str, int]:
    """Writes the plan in the caller's transaction: edits are kept by the database's own trigger under `by`."""
    conn.execute("select set_config('app.changed_by', %s, true)", (by,))
    cfg = config()
    top = db.one(
        conn,
        "select coalesce(max(substring(code from '[0-9]+$')::int), 0) as n from activity"
        " where tenant_id = %s and band = %s",
        (tenant, cfg["band"]),
    )["n"]
    for code, _, diff in p.changes:
        sets = ", ".join(f"{f} = %s" for f in diff)
        conn.execute(
            f"update activity set {sets} where tenant_id = %s and code = %s",  # noqa: S608 — field names come from FIELDS
            [now for _, now in diff.values()] + [tenant, code],
        )
    codes: dict[int, str] = {}
    for r in p.inserts:
        top += 1
        code = f"ACT-{cfg['band']}-{top:04d}"
        codes[r.line] = code
        v = r.values
        conn.execute(
            "insert into activity (tenant_id, code, band, strand, name, objective, materials, level_0, level_1, level_2,"
            " level_3, sheet_no, source_file, source_tab, source_row, source_url)"
            " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                tenant,
                code,
                cfg["band"],
                v["strand"],
                v["name"],
                v["objective"],
                v["materials"],
                v["level_0"],
                v["level_1"],
                v["level_2"],
                v["level_3"],
                v["sheet_no"],
                "(K2) Sr KG Planning Sheet_26-27",
                cfg["tab"],
                str(r.line),
                f"https://docs.google.com/spreadsheets/d/{cfg['sheet_id']}/edit",
            ),
        )
    made = 0
    for code, i, title, r in p.objectives:
        code = code or codes[r.line]
        lo = f"LO-{cfg['band']}-{code.rsplit('-', 1)[1]}-{i}"
        if conn.execute(
            "select 1 from learning_objective where tenant_id = %s and code = %s", (tenant, lo)
        ).fetchone():
            conn.execute(
                "update learning_objective set title = %s, subject = %s, unit = %s where tenant_id = %s and code = %s"
                " and title is distinct from %s and not exists (select 1 from curriculum_edit e where e.tenant_id = %s"
                " and e.record = 'learning_objective' and e.code = %s and e.changed_by not like %s)",
                (
                    title,
                    r.pillar or r.values["strand"],
                    r.values["strand"],
                    tenant,
                    lo,
                    title,
                    tenant,
                    lo,
                    cfg["upload_label"] + "%",
                ),
            )
        else:
            conn.execute(
                "insert into learning_objective (tenant_id, code, band, subject, unit, title, signal) values (%s,%s,%s,%s,%s,%s,'')",
                (tenant, lo, cfg["band"], r.pillar or r.values["strand"], r.values["strand"], title),
            )
            made += 1
        conn.execute(
            "insert into activity_objective (tenant_id, activity_code, lo_code, ord) values (%s,%s,%s,%s)"
            " on conflict do nothing",
            (tenant, code, lo, i),
        )
    return {"changed": len(p.changes), "added": len(p.inserts), "objectives_made": made}


curriculum_app = typer.Typer(help="The curriculum as the school's teams wrote it", no_args_is_help=True)


@curriculum_app.command("k2")
def k2(
    csv_path: Path = typer.Argument(
        ..., exists=True, help="The sheet's tab, exported as CSV and kept outside git"
    ),
    do_apply: bool = typer.Option(False, "--apply", help="Write it. Without this, nothing is written"),
    by: str = typer.Option("", "--by", help="Who is uploading, kept on every change"),
) -> None:
    if do_apply and not by.strip():  # before anything is read or opened: every change keeps who made it
        raise typer.BadParameter("--by is required with --apply: every change keeps who made it")
    cfg = config()
    rows, skipped = read_csv(csv_path, cfg)
    with db.connect() as conn:
        conn.read_only = not do_apply
        tenant = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
        dbrows, edited = snapshot(conn, tenant)
        p = plan(rows, dbrows, edited)
        typer.echo(report(p, skipped, len(rows), len(dbrows)))
        if do_apply:
            typer.echo(f"applied: {apply(conn, tenant, p, f'{cfg["upload_label"]} — {by.strip()}')}")
        else:
            typer.echo("dry run: nothing was written (add --apply to write it)")
