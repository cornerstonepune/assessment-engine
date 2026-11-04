"""W2's timetable command — `engine timetable load …`: the school's tabs (as CSV) into the six timetable tables, or into
one SQL file for a person to run where this machine cannot reach. `engine/cli.py` only mounts this."""

import hashlib
from collections import Counter
from datetime import date
from pathlib import Path

import typer

from engine.core import db, settings
from engine.w2_print import k2_timetable as tt
from engine.w2_print import k2_timetable_load as ld
from engine.w2_print import k2_timetable_sql as sq

timetable_app = typer.Typer(help="W2 — the K2 timetable from the school's tabs", no_args_is_help=True)


def _held(items: list[str]) -> dict[date, str]:
    out: dict[date, str] = {}
    for item in items:
        day, _, why = item.partition("=")
        if not why.strip():
            raise typer.BadParameter(f"--undecided wants DATE=REASON, got {item!r}")
        out[date.fromisoformat(day.strip())] = why.strip()
    return out


@timetable_app.command("load")
def load(
    frame: Path = typer.Option(..., help="the Time table tab as CSV"),
    planner: Path = typer.Option(..., help="the Monthly Planner tab as CSV"),
    calendar: Path = typer.Option(..., help="the Pre-Primary calendar tab as CSV"),
    section: str = typer.Option(..., help="the K2 section on this database"),
    first: int = typer.Option(10, "--from", help="first fortnight"),
    last: int = typer.Option(17, "--to", help="last fortnight"),
    grade: str = typer.Option("K2"),
    year: str = typer.Option("2026-27"),
    undecided: list[str] = typer.Option(
        [], "--undecided", help="DATE=REASON: a day two sources disagree about"
    ),
    sql: Path | None = typer.Option(None, "--sql", help="write the rows as one SQL file here"),
    apply: bool = typer.Option(False, "--apply", help="write to this database (otherwise a dry run)"),
) -> None:
    """Dry run unless --apply: prints counts, never the school's text. Safe to run twice."""
    texts = {p.name: p.read_text() for p in (frame, planner, calendar)}
    vocab = tt.Vocabulary.from_config(_vocab())
    plan = ld.build(
        ld.read_frame_csv(texts[frame.name], vocab), ld.read_planner_csv(texts[planner.name], vocab),
        ld.read_calendar_csv(texts[calendar.name], vocab), vocab, first, last, _held(undecided),
    )  # fmt: skip
    target = ld.Target(grade, section, year, db.tenant_slug())
    try:
        with db.connect() as conn:
            plan = ld.link_activities(plan, ld.activity_names(conn, grade))
            added = _try(conn, plan, target, apply)
    except RuntimeError:  # no database on this machine: the SQL file is the way
        added = None
    typer.echo(f"fortnights {first} to {last}, {grade} {section} {year}")
    for name, n in ld.summary(plan).items():
        typer.echo(
            f"  {name:<15}{n:>5}"
            + (f"   {'added' if apply else 'would add'} {added[name]:>5}" if added else "")
        )
    typer.echo(
        f"  planner lines linked to exactly one activity: {sum(1 for e in plan.plan_entries if e.activity_code)}"
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
        digests = {
            p.name: hashlib.sha256(texts[p.name].encode()).hexdigest() for p in (frame, planner, calendar)
        }
        sql.write_text(sq.sql_file(plan, target, digests))
        typer.echo(
            f"  wrote {sql} ({len(plan.sessions)} sessions); run it in one transaction, it prints counts before and after"
        )


def _vocab() -> dict:
    with db.connect() as conn:
        found = settings.config(conn, "timetable.vocabulary")
    if not found:
        raise typer.BadParameter("this database has no timetable.vocabulary row: run `engine load`")
    return found


def _try(conn: db.Conn, plan: ld.Load, target: ld.Target, apply: bool) -> dict[str, int] | None:
    try:
        added = sq.apply(conn, plan, target)
    except sq.NoSuchClass as no:
        typer.echo(f"  no such class on this database: {no}; nothing was written")
        return None
    if apply:
        conn.commit()
    else:
        conn.rollback()
    return added
