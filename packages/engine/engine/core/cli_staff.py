"""`engine staff add` and `engine set-password`: who signs in to the website (goals/ui4a-staff-and-search.yaml).

A password is typed twice in the terminal and never echoed, logged or passed on a command line, so it cannot end up
in shell history or in anyone's chat. Run on Nimish's own machine: an educator's email goes from his terminal to the
database and nowhere else.
"""

import getpass
import secrets

import typer

from engine.core import db, settings
from engine.core.staff import NODE_DEFAULT_N, add, classes, save, set_classes, staff, staff_hash

staff_app = typer.Typer(help="Who signs in to the website", no_args_is_help=True)


def _password(n: int) -> str:
    """Hashed at the cost the `password.scrypt_n` row asks for, as the website hashes one a person sets themselves."""
    first = getpass.getpass("  New password (10+ characters, not shown): ")
    if len(first) < 10:
        raise typer.BadParameter("at least 10 characters")
    if getpass.getpass("  Once more: ") != first:
        raise typer.BadParameter("the two did not match — nothing changed")
    return staff_hash(first, secrets.token_hex(16), n)


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
    """Put a person on the staff list, with the classes they teach and a password they sign in with."""
    with db.connect() as conn:
        try:  # a class no child is in is refused before anyone types a password
            classes(conn, teaches)
        except ValueError as e:
            raise typer.BadParameter(str(e)) from e
        cost = int(settings.threshold(conn, "password.scrypt_n", NODE_DEFAULT_N))
    password = _password(cost)
    with db.connect() as conn:
        try:
            person = add(conn, email, name, role, password, teaches)
        except ValueError as e:
            raise typer.BadParameter(str(e)) from e
        conn.commit()
    typer.echo(
        f"  {person['name']} ({person['role']}) can sign in with {person['email']} and the password typed;"
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
    """Everyone who may sign in: name, role, email, the classes they teach, and whether they have a password yet."""
    with db.connect() as conn:
        people = staff(conn)
    for s in people:
        typer.echo(
            f"  {s['name']:<20}{s['role']:<13}{s['email']:<36}{'password set' if s.get('password') else 'no password':<14}"
            f"{_said(s.get('classes', []), s['role'])}"
        )
    typer.echo(f"  {len(people)} on the staff list")


def register(app: typer.Typer) -> None:
    """`engine staff …` and `engine set-password`, the name Nimish already uses."""
    app.add_typer(staff_app, name="staff")

    @app.command("set-password")
    def set_password(email: str) -> None:
        """Set a staff member's sign-in password for the web app. Typed here, hidden, never stored in clear.

        This only sets a password for someone already on the list; `engine staff add` puts a person on it.
        """
        with db.connect() as conn:
            people = staff(conn)
            me = next((s for s in people if s["email"].lower() == email.strip().lower()), None)
            if me is None:
                raise typer.BadParameter(
                    f"{email} is not on the staff list — nothing changed (engine staff add puts them on)"
                )
            me["password"] = _password(int(settings.threshold(conn, "password.scrypt_n", NODE_DEFAULT_N)))
            save(conn, people)
            conn.commit()
        typer.echo(f"  password set for {me['name']} ({me['role']}) — sign in with {me['email']}")
