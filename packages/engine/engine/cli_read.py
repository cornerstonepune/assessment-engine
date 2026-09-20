"""W3 — reading papers and placing them on the skill graph. Its own module so `cli.py` stays one
screen per workflow, the same reason `cli_legacy.py` exists."""

import json
from pathlib import Path

import typer

from engine import db, external

read_app = typer.Typer(help="W3 — read papers and place them on the skill graph", no_args_is_help=True)


@read_app.command("map")
def read_map(
    path: str,
    pages: str = typer.Option("", "--pages", help="1,2,3 — default every page"),
    mask: float = typer.Option(-1.0, "--mask", help="fraction of page 1's top to paint out; default masks the name band (rule 6)"),
    out: str = typer.Option("", "--out", help="write the questions and matches to this json"),
) -> None:
    """Place one paper's printed questions against the skill registry, and say what fraction landed.

    Reads the questions only — no child's answer, no educator's mark — so one booklet stands for
    every child who sat that form.
    """
    want = [int(p) for p in pages.split(",") if p.strip()] if pages else None
    with db.connect() as conn:
        before = external.spend_today(conn)
        questions, matches, r, groups, by_n, conflicts = external.run(
            conn, path, want, None if mask < 0 else mask
        )
        conn.commit()
        spent = external.spend_today(conn) - before

    if not questions:
        typer.echo("  no printed questions found — nothing to place")
        raise typer.Exit(1)

    typer.echo(f"\n  {Path(path).name}  —  {len(questions)} printed questions on {len({q['page'] for q in questions})} pages\n")
    for m in sorted(matches, key=lambda m: (int("".join(c for c in m["n"] if c.isdigit()) or 0), m["n"])):
        q = by_n.get(m["n"], {})
        mark = {"clear": "  ok  ", "arguable": " ~ask ", "none": " MISS "}[m["confidence"]]
        typer.echo(f"{mark} {m['n']:>4}  {(m['skill_code'] or '—'):<14} {(q.get('what_it_tests') or '')[:62]}")
        if m["confidence"] == "none" and m.get("proposed_skill"):
            typer.echo(f"            proposes: {m['proposed_skill']}  ({m['reason']})")
        elif m.get("alternative_codes"):
            typer.echo(f"            or: {', '.join(m['alternative_codes'])}")

    typer.echo(
        f"\n  clear {r['clear']}   arguable {r['arguable']}   no match {r['none']}   of {r['total']}"
        f"\n  MAPPED {r['mapped']:.0%}  (clear alone {r['clear_only']:.0%})   model spend Rs {spent:.2f}"
    )
    if conflicts:
        typer.echo(
            f"\n  {len(conflicts)} question(s) read from two different pages — one of each pair is"
            "\n  invented. Kept the page that holds a run of questions, dropped the lone one:"
        )
        for c in conflicts:
            typer.echo(f"    n={c['n']}{c['part']}: kept page {c['kept']}, dropped page {c['dropped']}")

    if groups:
        typer.echo("\n  what the registry is missing, grouped:")
        for name, ns in groups:
            typer.echo(f"    {len(ns):>2} x  {name}   (questions {', '.join(str(n) for n in ns)})")

    if out:
        Path(out).write_text(json.dumps({"questions": questions, "matches": matches, "rate": r}, indent=1))
        typer.echo(f"\n  written to {out}")
