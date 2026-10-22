"""`engine staff`: who signs in to the website (goals/ui4a-staff-and-search.yaml).

Everyone signs in with their school Google account (goals/a1-sign-in-with-google.yaml), and a school email new to the
list joins it as an educator on its own. `engine staff add` is for a person who must hold another role from their
first sign-in, the coordinator. Run on Nimish's own machine: an email goes from his terminal to the database and
nowhere else.
"""

import typer

from engine.core import db
from engine.core.staff import add, set_classes, staff

staff_app = typer.Typer(help="Who signs in to the website", no_args_is_help=True)


def _said(teaches: list[str], role: str) -> str:
    if role == "coordinator":
        return "every class"
    return ", ".join(teaches) if teaches else "no class yet"


@staff_app.command("add")
def add_(
    email: str,
    name: str = typer.Option(..., "--name", help="As the website says it beside every decision they take"),
    role: str = typer.Option("educator", "--role", help="One the school's decisions name (people.decides)"),
    teaches: list[str] = typer.Option(
        [], "--class", help="A class they teach (as on the site: G2); once per class"
    ),
) -> None:
    """Put a person on the staff list, with their role and the classes they teach, before they first sign in."""
    with db.connect() as conn:
        try:
            person = add(conn, email, name, role, teaches)
        except ValueError as e:
            raise typer.BadParameter(str(e)) from e
        conn.commit()
    typer.echo(
        f"  {person['name']} ({person['role']}) can sign in with Google as {person['email']};"
        f" their classes: {_said(person['classes'], person['role'])}"
    )


@staff_app.command("classes")
def classes_(
    email: str,
    teaches: list[str] = typer.Argument(None, help="Every class they teach now (as on the site: G2 G3)"),
    none: bool = typer.Option(False, "--none", help="They teach no class (they see the whole school)"),
) -> None:
    """Say which classes a person teaches: what the site opens on for them. Replaces the classes they had."""
    teaches = teaches or []
    if not teaches and not none:
        raise typer.BadParameter("name the classes they teach, or --none for no class")
    with db.connect() as conn:
        try:
            me = set_classes(conn, email, teaches)
        except ValueError as e:
            raise typer.BadParameter(str(e)) from e
        conn.commit()
    typer.echo(f"  {me['name']} ({me['role']}) teaches {_said(me['classes'], me['role'])}")


@staff_app.command("list")
def list_() -> None:
    """Everyone who may sign in: name, role, email and the classes they teach."""
    with db.connect() as conn:
        people = staff(conn)
    for s in people:
        typer.echo(
            f"  {s['name']:<20}{s['role']:<13}{s['email']:<36}{_said(s.get('classes', []), s['role'])}"
        )
    typer.echo(f"  {len(people)} on the staff list")


def register(app: typer.Typer) -> None:
    """`engine staff …`."""
    app.add_typer(staff_app, name="staff")
