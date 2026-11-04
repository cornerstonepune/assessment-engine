"""W2's timetable command — `engine timetable load …`: the school's tabs (as CSV) into the six timetable tables, or into
one SQL file for a person to run where this machine cannot reach. `engine/cli.py` only mounts this."""

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path

import psycopg
import typer

from engine.core import db, settings
from engine.w2_print import k2_timetable as tt
from engine.w2_print import k2_timetable_load as ld
from engine.w2_print import k2_timetable_sql as sq

timetable_app = typer.Typer(help="W2 — the K2 timetable from the school's tabs", no_args_is_help=True)
VOCABULARY = "timetable.vocabulary"


def _held(items: list[str]) -> dict[date, str]:
    out: dict[date, str] = {}
    for item in items:
        day, _, why = item.partition("=")
        if not why.strip():
            raise typer.BadParameter(f"--undecided wants DATE=REASON, got {item!r}")
        out[date.fromisoformat(day.strip())] = why.strip()
    return out


def _vocabulary(online: bool) -> tt.Vocabulary:
    """The words the sheets are read with: the database's row, or the seed file's when there is no database, which is
    the same row (`engine load` puts the seed there)."""
    if online:
        with db.connect() as conn:
            found = settings.config(conn, VOCABULARY)
        if found:
            return tt.Vocabulary.from_config(found)
    seed = json.loads((db.REPO_ROOT / "supabase/seed/config.json").read_text())["config"]
    return tt.Vocabulary.from_config(next(c["value"] for c in seed if c["key"] == VOCABULARY))


def _online() -> bool:
    try:
        with db.connect():
            return True
    except (RuntimeError, psycopg.OperationalError):
        return False


@timetable_app.command("load")
def load(
    frame: Path = typer.Option(..., help="the Time table tab as CSV"),
    planner: Path = typer.Option(..., help="the Monthly Planner tab as CSV"),
    calendar: Path = typer.Option(..., help="the Pre-Primary calendar tab as CSV"),
    section: str = typer.Option(..., help="the section of the class on this database"),
    grade: str = typer.Option(..., help="the grade code of the class, as in the grade table"),
    first: int = typer.Option(10, "--from", help="first fortnight"),
    last: int = typer.Option(17, "--to", help="last fortnight"),
    year: str = typer.Option("2026-27"),
    undecided: list[str] = typer.Option(
        [], "--undecided", help="DATE=REASON: a day two sources disagree about"
    ),
    sql: Path | None = typer.Option(None, "--sql", help="write the rows as one SQL file here"),
    apply: bool = typer.Option(False, "--apply", help="write to this database (otherwise a dry run)"),
) -> None:
    """Dry run unless --apply: prints counts, never the school's text. Safe to run twice."""
    online = _online()
    if apply and not online:
        typer.echo(
            "There is no database to write to here: nothing was applied. Use --sql for a file to run elsewhere."
        )
        raise typer.Exit(1)
    texts = {k: p.read_text() for k, p in {"frame": frame, "planner": planner, "calendar": calendar}.items()}
    digests = {
        p.name: hashlib.sha256(texts[k].encode()).hexdigest()
        for k, p in (("frame", frame), ("planner", planner), ("calendar", calendar))
    }
    vocab = _vocabulary(online)
    plan = ld.build(
        ld.read_frame_csv(texts["frame"], vocab), ld.read_planner_csv(texts["planner"], vocab),
        ld.read_calendar_csv(texts["calendar"], vocab), vocab, first, last, _held(undecided),
    )  # fmt: skip
    target = ld.Target(
        grade,
        section,
        year,
        db.tenant_slug() if online else "",
        f"{planner.name} sha256:{digests[planner.name][:12]}",
    )
    added, linked = _run(plan, target, apply) if online else (None, None)
    typer.echo(f"fortnights {first} to {last}, {grade} {section} {year}")
    for name, n in ld.summary(plan).items():
        typer.echo(
            f"  {name:<15}{n:>5}"
            + (f"   {'added' if apply else 'would add'} {added[name]:>5}" if added else "")
        )
    typer.echo(
        f"  planner lines linked to exactly one activity: {linked if linked is not None else 'unknown without a database'}"
    )
    typer.echo(
        f"  planner lines with no period, by heading: {dict(Counter(k for _, k, _ in plan.no_slot)) or 'none'}"
    )
    for label, items in (
        ("undecided day", plan.undecided),
        ("fortnight with no planner row", plan.missing_plan),
        ("conflict", plan.conflicts),
    ):
        for what, why in items:
            typer.echo(f"  {label}: {what} — {why}")
    if sql:
        sql.write_text(sq.sql_file(plan, target, digests))
        typer.echo(
            f"  wrote {sql} ({len(plan.sessions)} sessions); run it in one transaction, it prints counts before and after"
        )


def _run(plan: ld.Load, target: ld.Target, apply: bool) -> tuple[dict[str, int] | None, int | None]:
    with db.connect() as conn:
        try:
            added = sq.apply(conn, plan, target)
        except sq.NoSuchClass as no:
            typer.echo(f"  no such class on this database: {no}; nothing was written")
            return None, None
        linked = sq.linked(conn)
        conn.commit() if apply else conn.rollback()
    return added, linked
