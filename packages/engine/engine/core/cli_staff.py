"""`engine staff add` and `engine set-password`: who signs in to the website (goals/ui4a-staff-and-search.yaml).

A password is typed twice in the terminal and never echoed, logged or passed on a command line, so it cannot end up
in shell history or in anyone's chat. Run on Nimish's own machine: an educator's email goes from his terminal to the
database and nowhere else.
"""

import getpass
import secrets

import typer

from engine.core import db
from engine.core.staff import add, save, staff, staff_hash

staff_app = typer.Typer(help="Who signs in to the website", no_args_is_help=True)


def _password() -> str:
    first = getpass.getpass("  New password (10+ characters, not shown): ")
    if len(first) < 10:
        raise typer.BadParameter("at least 10 characters")
    if getpass.getpass("  Once more: ") != first:
        raise typer.BadParameter("the two did not match — nothing changed")
    return staff_hash(first, secrets.token_hex(16))


@staff_app.command("add")
def add_(
    email: str,
    name: str = typer.Option(..., "--name", help="As the website says it beside every decision they take"),
    role: str = typer.Option("educator", "--role", help="One the school's decisions name (people.decides)"),
) -> None:
    """Put a person on the staff list, with a password they sign in with."""
    password = _password()
    with db.connect() as conn:
        try:
            person = add(conn, email, name, role, password)
        except ValueError as e:
            raise typer.BadParameter(str(e)) from e
        conn.commit()
    typer.echo(
        f"  {person['name']} ({person['role']}) can sign in with {person['email']} and the password typed"
    )


@staff_app.command("list")
def list_() -> None:
    """Everyone who may sign in: name, role, email, and whether they have a password yet."""
    with db.connect() as conn:
        people = staff(conn)
    for s in people:
        typer.echo(
            f"  {s['name']:<20}{s['role']:<13}{s['email']:<36}{'password set' if s.get('password') else 'no password'}"
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
            me["password"] = _password()
            save(conn, people)
            conn.commit()
        typer.echo(f"  password set for {me['name']} ({me['role']}) — sign in with {me['email']}")
