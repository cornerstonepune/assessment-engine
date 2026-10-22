"""Do a skill's level rows say what its blob says? `engine levels check` (goals/b1-levels-are-rows.yaml).

B1 moves each level out of the JSON on `skill_set` into a row of `skill_level`. Until the blob goes, both are read, so
both must agree: level by level the same words and rule, the same grade (named in `level_band`, else the skill's own)
and the same approval; the counts of levels per grade and of approved levels equal; and, for every level, the
generator's questions drawn on one seed from the row's rule the same as from the blob's. Read only; safe on a copy of
live, where the rehearsal runs it before and after update-live.
"""

import json
import random
from collections import Counter
from typing import Any

import typer

from engine.assess import bands
from engine.assess import draw as drawing
from engine.core import db, levels
from engine.w1_bank import bank, cases, kinds

SEED = 1


def draw(conn: db.Conn, s: dict[str, Any], check: dict[str, Any], seed: int = SEED, n: int = 4) -> list[str]:
    """`n` questions as the generator draws them from one level's rule on `seed`, each said as JSON: a level of cases
    through its cases, a card level from its kinds' list, a native format through its own generator, any other through
    the samplers the bank fills offline with."""
    check = kinds.resolve(conn, check)
    rng = random.Random(seed)
    rung = s["rung_code"]
    if check.get("cases"):
        return [it.item_id for _, it in drawing.level(rng, check, cases.for_level(conn, check), rung, n)]
    if check.get("format") == "card":
        return [it.item_id for it in kinds.listed(check, rng, rung)[:n]]
    fmt = check.get("format") or (s["formats"] or [None])[0]
    if fmt in bands.NATIVE_GENERATORS:
        out = []
        for _ in range(n):
            try:
                out.append(bands.native_item(fmt, check, rng, rung, "Conceptual").item_id)
            except RuntimeError:
                out.append("(no question on these numbers)")
        return out
    usable = [check["format"]] if check.get("format") in bank.SAMPLER_FORMATS else list(s["formats"])
    return [json.dumps(c, sort_keys=True, default=str) for c in bank._sampled(check, usable, n, seed=seed)]


def _blob(conn: db.Conn) -> list[dict[str, Any]]:
    return conn.execute(
        "select s.code, s.rung_code, s.formats, e.key as level, e.value as entry,"
        " coalesce(s.level_band ->> e.key, s.grade) as grade, s.level_approved ? e.key as approved"
        " from skill_set s"
        " cross join jsonb_each(s.difficulty) e order by s.code, e.key"
    ).fetchall()


def compare(conn: db.Conn, draws: int = 4) -> dict[str, Any]:
    """The blob against the rows, level by level. `disagree` lists every level where they part, and why; with `draws`,
    each level's questions are drawn from both on one seed and compared."""
    blob = _blob(conn)
    rows = {(r["skill_code"], r["difficulty"]): r for r in conn.execute("select * from skill_level")}
    built = levels.every(conn)
    disagree, drawn = [], 0
    for b in blob:
        key = (b["code"], b["level"])
        row = rows.get(key)
        if row is None:
            disagree.append(f"{b['code']} {b['level']}: no row")
            continue
        for what, there, here in (
            ("words", b["entry"].get("words"), row["looks_like"]),
            ("rule", {k: v for k, v in b["entry"].items() if k != "words"}, row["rule"]),
            ("grade", b["grade"], row["grade"]),
            ("approval", b["approved"], row["confirmed_at"] is not None),
            ("levels object", b["entry"], built.get(b["code"], {}).get(b["level"])),
        ):
            if there != here:
                disagree.append(
                    f"{b['code']} {b['level']}: {what} {there!r} in the blob, {here!r} in the row"
                )
        if draws and "check" in b["entry"]:
            from_blob = draw(conn, b, b["entry"]["check"], n=draws)
            from_rows = draw(conn, b, row["rule"]["check"], n=draws)
            drawn += bool(from_blob)
            if from_blob != from_rows:
                disagree.append(
                    f"{b['code']} {b['level']}: drew {from_rows} from the row, {from_blob} from the blob"
                )
    disagree += [
        f"{c} {d}: a row the blob does not have"
        for c, d in rows.keys() - {(b["code"], b["level"]) for b in blob}
    ]
    return {
        "levels": len(blob),
        "drawable": sum(
            "check" in b["entry"] for b in blob
        ),  # a level with no check is drawn from nothing (English, E0)
        "rows": len(rows),
        "drawn": drawn,
        "grades": {
            "blob": dict(Counter(b["grade"] for b in blob)),
            "rows": dict(Counter(r["grade"] for r in rows.values())),
        },
        "approved": {
            "blob": sum(b["approved"] for b in blob),
            "rows": sum(r["confirmed_at"] is not None for r in rows.values()),
        },
        "disagree": disagree,
    }


levels_app = typer.Typer(help="A skill's levels, as rows (skill_level)", no_args_is_help=True)


@levels_app.command("check")
def check_(
    draws: int = typer.Option(
        4, "--draws", help="questions drawn from each level, rows and blob, on one seed"
    ),
) -> None:
    """Do the level rows say what the blob says, and draw the same questions? Exits 1 if any level parts."""
    with db.connect() as conn:
        r = compare(conn, draws)
    grades = " · ".join(f"{g} {n}" for g, n in sorted(r["grades"]["rows"].items()))
    typer.echo(f"  {r['levels']} levels in the blob, {r['rows']} rows · grades {grades}")
    typer.echo(f"  approved: {r['approved']['blob']} in the blob, {r['approved']['rows']} in the rows")
    typer.echo(f"  drawn on seed {SEED}: {r['drawn']} levels, {draws} questions each, from rows and blob")
    for line in r["disagree"][:20]:
        typer.echo(f"  FAIL  {line}", err=True)
    same = r["grades"]["blob"] == r["grades"]["rows"] and r["approved"]["blob"] == r["approved"]["rows"]
    if r["disagree"] or not same or r["levels"] != r["rows"]:
        typer.echo(f"  the rows and the blob disagree on {len(r['disagree'])} levels")
        raise typer.Exit(1)
    typer.echo("  the rows and the blob agree on every level")
