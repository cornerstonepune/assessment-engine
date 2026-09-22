"""Every question on a numbered worksheet (ADR 0026): `engine library build` and `engine library
check`. Its own module so `cli.py` stays one screen per workflow."""

import typer

from engine.core import db
from engine.w2_print import library

library_app = typer.Typer(
    help="The worksheet library: every question on a numbered worksheet", no_args_is_help=True
)


@library_app.command("build")
def library_build(
    dry_run: bool = typer.Option(False, "--dry-run", help="say what would change; change nothing"),
) -> None:
    """Deal worksheets until every active question is on one and every level has its worksheets;
    retire any worksheet that holds a question no longer in the bank."""
    with db.connect() as conn:
        done = library.build(conn, dry_run=dry_run)
        if dry_run:
            conn.rollback()
            typer.echo(f"  would make {done['made']} · would retire {done['retired']}")
        else:
            conn.commit()
            typer.echo(f"  made {done['made']} · retired {done['retired']}")


@library_app.command("check")
def library_check() -> None:
    """Every rule a worksheet and a level must hold, read back from the rows. Exits 1 on any problem."""
    with db.connect() as conn:
        levels, found = library.check(conn)
        sheets = conn.execute(
            "select count(*) as n from sheet_template where source = 'library' and retired_at is null"
        ).fetchone()["n"]
    for level, problems in list(found.items())[:20]:
        typer.echo(
            f"  {level}: {'; '.join(problems[:3])}"
            + (f" … and {len(problems) - 3} more" if len(problems) > 3 else ""),
            err=True,
        )
    total = sum(len(p) for p in found.values())
    typer.echo(
        f"  {sheets} worksheets · {levels - len(found)} of {levels} skill-levels ready · {total} problems"
    )
    if found:
        raise typer.Exit(1)
