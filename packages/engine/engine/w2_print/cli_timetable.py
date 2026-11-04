"""W2's timetable command — `engine timetable load …`: the school's tabs (as CSV) into the six timetable tables, or into
one SQL file for a person to run where this machine cannot reach. `engine/cli.py` only mounts this."""

import hashlib
import json
from collections import Counter
from contextlib import ExitStack
from dataclasses import replace
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
    try:
        return tt.Vocabulary.from_config(
            found
            or next(c["value"] for c in settings.seed("config.json", "config") if c["key"] == VOCABULARY)
        )
    except KeyError as missing:
        raise typer.BadParameter(
            f"this database's {VOCABULARY} row is older than the code (no {missing}): run `engine load`"
        ) from missing


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
    spans: Path | None = typer.Option(
        None, "--spans", help="frame_spans.json: activities merged over several periods"
    ),
    use_row: list[str] = typer.Option(
        [],
        "--use-row",
        help="N=K: Fortnight N is listed twice; use row K (1 = first). Without it neither row is loaded",
    ),
    sql: Path | None = typer.Option(
        None,
        "--sql",
        help="write the rows as one SQL file here (and one per row of a fortnight listed twice that nobody has chosen)",
    ),
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
        held, use = _held(undecided), {int(n): int(k) for n, _, k in (u.partition("=") for u in use_row)}
        frame_in = ld.read_frame_csv(texts["frame"], vocab, json.loads(spans.read_text()) if spans else None)
        cal_in = ld.read_calendar_csv(texts["calendar"], vocab)
        plan_in = ld.read_planner_csv(texts["planner"], vocab, use)
        plan = ld.build(frame_in, plan_in, cal_in, vocab, first, last, held)
        source = f"{planner.name} sha256:{digests[planner.name][:12]}"
        target = ld.Target(grade, section, year, db.tenant_slug() if conn else "", source)
        added, linked = _run(conn, plan, target, apply) if conn else (None, None)
    _report(plan, added, linked, apply, f"fortnights {first} to {last}, {grade} {section} {year}")
    if sql:
        sql.write_text(sq.sql_file(plan, target, digests))
        for n, rows in plan_in.candidates.items():
            for k in () if n in use else range(1, len(rows) + 1):
                alone = ld.build(
                    frame_in, ld.read_planner_csv(texts["planner"], vocab, {n: k}), cal_in, vocab, n, n, held
                )
                where = replace(target, source=f"{target.source} row {k} of {len(rows)} of Fortnight {n}")
                out = sql.with_name(f"{sql.stem}_fn{n}_row{k}{sql.suffix}")
                out.write_text(sq.sql_file(alone, where, digests))
                typer.echo(
                    f"  wrote {out}: Fortnight {n} as its row {k} of {len(rows)} says; apply at most one, once the school has said which"
                )
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
        ("row used as told", plan.chosen),
        ("undecided day", plan.undecided),
        ("fortnight with no planner row", plan.missing_plan),
        ("conflict", plan.conflicts),
    ):
        for what, why in items:
            typer.echo(f"  {label}: {what} — {why}")
