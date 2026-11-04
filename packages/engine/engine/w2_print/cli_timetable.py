"""W2's timetable command — `engine timetable load …`: the school's tabs (as CSV) into the six timetable tables, or into
one SQL file for a person to run where this machine cannot reach. `engine/cli.py` only mounts this."""

import hashlib
from collections import Counter
from contextlib import ExitStack
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


def _vocabulary(conn: db.Conn | None) -> tt.Vocabulary:
    """The words the sheets are read with: the database's row, or the seed file's when there is no database, which is
    the same row (`engine load` puts the seed there)."""
    found = settings.config(conn, VOCABULARY) if conn else None
    return tt.Vocabulary.from_config(
        found or next(c["value"] for c in settings.seed("config.json", "config") if c["key"] == VOCABULARY)
    )


def _connect(stack: ExitStack) -> db.Conn | None:
    try:
        return stack.enter_context(db.connect())
    except (RuntimeError, psycopg.OperationalError):
        return None


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
    with ExitStack() as stack:
        conn = _connect(stack)
        if apply and conn is None:
            typer.echo(
                "There is no database to write to here: nothing was applied. Use --sql for a file to run elsewhere."
            )
            raise typer.Exit(1)
        files = {"frame": frame, "planner": planner, "calendar": calendar}
        texts = {k: p.read_text() for k, p in files.items()}
        digests = {p.name: hashlib.sha256(texts[k].encode()).hexdigest() for k, p in files.items()}
        vocab = _vocabulary(conn)
        plan = ld.build(
            ld.read_frame_csv(texts["frame"], vocab), ld.read_planner_csv(texts["planner"], vocab),
            ld.read_calendar_csv(texts["calendar"], vocab), vocab, first, last, _held(undecided),
        )  # fmt: skip
        source = f"{planner.name} sha256:{digests[planner.name][:12]}"
        target = ld.Target(grade, section, year, db.tenant_slug() if conn else "", source)
        added, linked = _run(conn, plan, target, apply) if conn else (None, None)
    _report(plan, added, linked, apply, f"fortnights {first} to {last}, {grade} {section} {year}")
    if sql:
        sql.write_text(sq.sql_file(plan, target, digests))
        typer.echo(
            f"  wrote {sql} ({len(plan.sessions)} sessions); run it in one transaction, it prints counts before and after"
        )


def _run(
    conn: db.Conn, plan: ld.Load, target: ld.Target, apply: bool
) -> tuple[dict[str, int] | None, int | None]:
    try:
        added = sq.apply(conn, plan, target)
        linked: int | None = sq.linked(conn)
    except sq.NoSuchClass as no:
        typer.echo(f"  no such class on this database: {no}; nothing was written")
        added, linked = None, None
    if apply and added is not None:
        conn.commit()
    else:
        conn.rollback()
    return added, linked


def _report(
    plan: ld.Load, added: dict[str, int] | None, linked: int | None, apply: bool, heading: str
) -> None:
    typer.echo(heading)
    verb = "added" if apply else "would add"
    for name, n in ld.summary(plan).items():
        typer.echo(f"  {name:<15}{n:>5}" + (f"   {verb} {added[name]:>5}" if added else ""))
    typer.echo(
        f"  planner lines linked to exactly one activity: {'unknown without a database' if linked is None else linked}"
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
