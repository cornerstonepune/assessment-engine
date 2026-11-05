"""`engine staff import` and `engine enrol k2` (goals/m0-05-people-enrolment.yaml). A dry run unless `--apply --by <email>`.

A dry run changes no row but the access log, which records that the children's names were read to compare them. Both
commands print counts, line numbers and roll numbers, never a name, an email or a birthday. `--by` is the signer's
email (the one they sign in with); the rows keep their staff id, not the email (goals/fix-staff-by-id.yaml).
"""

from datetime import date
from pathlib import Path

import typer

from engine.core import db, people

enrol_app = typer.Typer(help="Put a class's children in it", no_args_is_help=True)


def finish(conn: db.Conn, out: people.Report, apply: bool) -> None:
    """Say what happened; commit only a run that is applied and has no refused row (the dry run's one write is the log)."""
    for line in out.lines:
        typer.echo(line)
    for why in out.refused:
        typer.echo(f"  REFUSED  {why}")
    for what, n in sorted(out.counts.items()):
        typer.echo(f"  {what}: {n}")
    if out.refused:
        conn.rollback()
        typer.echo(
            "  nothing was written" + (" — fix the refused rows above, then run again" if apply else "")
        )
        raise typer.Exit(1)
    conn.commit()
    typer.echo(
        "  written." if apply else "  dry run — nothing written. Add --apply --by <your email> to write it."
    )


def need_by(apply: bool, by: str | None) -> str:
    if apply and not (by or "").strip():
        raise typer.BadParameter(
            "--apply needs --by <your email>: your staff id is kept with every row written"
        )
    return (by or "").strip()


def staff_import(
    apply: bool = typer.Option(False, "--apply", help="Write it; without this nothing is written"),
    by: str = typer.Option(
        None, "--by", help="Your email, the one you sign in with; your staff id is kept with each grant"
    ),
) -> None:
    """Copy the website's staff list into the staff tables (the list itself is left as it is)."""
    who = need_by(apply, by)
    with db.connect() as conn:
        finish(conn, people.import_staff(conn, who, apply), apply)


@enrol_app.command("k2")
def k2(
    csv_path: Path = typer.Argument(
        ..., help="The Children List as CSV: number, name, birthday. Keep it outside git."
    ),
    apply: bool = typer.Option(False, "--apply", help="Write it; without this nothing is written"),
    by: str = typer.Option(
        None,
        "--by",
        help="Your email, the one you sign in with; your staff id is kept with every row written",
    ),
    match_existing: bool = typer.Option(
        False,
        "--match-existing",
        help="A child already at that roll number in K2, with the same name, is the same child",
    ),
    since: str = typer.Option(None, "--from", help="The day they join the class, 2026-11-05; default today"),
    teacher: str = typer.Option(
        None, "--teacher", help="The K2 class educator's email (must be on the staff tables)"
    ),
    override_reason: str = typer.Option(
        None, "--override-reason", help="Why a second class educator is right; kept"
    ),
    section: str = typer.Option("A", "--section", help="The class's own section in the grade (K2-A)"),
) -> None:
    """Load the K2 class and its children from the Children List, with their roll numbers."""
    who = need_by(apply, by)
    try:
        day = date.fromisoformat(since) if since else None
    except ValueError as e:
        raise typer.BadParameter("--from is a day like 2026-11-05") from e
    with db.connect() as conn:
        try:
            out = people.enrol_k2(
                conn,
                "k2",
                csv_path,
                who,
                apply,
                match_existing,
                day,
                teacher,
                override_reason,
                section.strip(),
            )
        except ValueError as e:
            raise typer.BadParameter(str(e)) from e
        finish(conn, out, apply)
