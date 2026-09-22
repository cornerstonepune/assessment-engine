"""Does the graph reach what a good teacher reached by hand? `engine gold` — Aseem's five Grade 3
reports as W3's gold (ADR 0028). Its own module so `cli.py` stays one screen per workflow."""

import typer

from engine.core import db
from engine.w3_read import gold

gold_app = typer.Typer(
    help="W3's gold — Aseem's own diagnoses, read back against the graph", no_args_is_help=True
)


@gold_app.command("load")
def gold_load(
    path: str = typer.Argument(
        ..., help="the transcription, kept beside the reports and never in the repository"
    ),
) -> None:
    """Load the transcribed findings. Loading twice changes nothing; a changed finding needs confirming again."""
    with db.connect() as conn:
        n = gold.load(conn, path)
    typer.echo(f"  {n} findings loaded")


@gold_app.command("confirm")
def gold_confirm(
    by: str = typer.Option(..., "--by", help="the person who read the transcription against the reports"),
) -> None:
    """A person says the transcription is what the reports say."""
    with db.connect() as conn:
        n = gold.confirm(conn, by)
    typer.echo(f"  {n} findings confirmed by {by}")


@gold_app.command("check")
def gold_check() -> None:
    """Every finding: where it stands between the child's page and the child's graph. Exits 1 until
    every finding the papers hold is in the graph."""
    with db.connect() as conn:
        results = gold.check(conn)
    for r in results:
        seen = f"{r['answer']!r}" if r["result_id"] else ""
        also = " · a pattern in the graph" if r["misconception_code"] in r["patterns"] else ""
        typer.echo(
            f"  {r['outcome']:<31} {r['first_name']:<10} {r['verdict']:<6} {r['skill_code']:<11}"
            f" {r['item_key'] or '':<22} Aseem {r['child_answer'] or '—'!s:<6} page {seen:<9}"
            f" {r['misconception_code'] or ''}{also}"
        )
    line, ok = gold.summary(results)
    typer.echo(f"\n  {line}")
    if not ok:
        raise typer.Exit(1)
    typer.echo("  every finding the papers hold is in the graph")
