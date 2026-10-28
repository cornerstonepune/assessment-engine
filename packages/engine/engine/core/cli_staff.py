"""`engine staff add` and `engine set-password`: who signs in to the website (goals/ui4a-staff-and-search.yaml).

A password is typed twice in the terminal and never echoed, logged or passed on a command line, so it cannot end up
in shell history or in anyone's chat. Run on Nimish's own machine: an educator's email goes from his terminal to the
database and nowhere else.
"""

import getpass
import secrets
from pathlib import Path

import typer

from engine.core import db, settings, staff_load, staff_remove
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


@staff_app.command("remove")
def remove_(
    emails: list[str] = typer.Argument(..., help="Each email to take off the list (case does not matter)"),
    apply_: bool = typer.Option(
        False, "--apply", help="Do it. Without this nothing changes and what would happen is only shown"
    ),
) -> None:
    """Take people off the staff list, so they can no longer sign in.

    Without --apply this changes nothing and says, for each email, "would
    remove NAME (ROLE)" or why it is refused. With --apply the named people
    are removed together and no one else is touched. Example:

    engine staff remove teacher@example.test

    It refuses an email that is not on the list, the same email named twice,
    and a removal that would leave no coordinator who can sign in. If any is
    refused, nothing is removed. An email need not look like an address.

    Removing a person signs them out at their next request. It never deletes
    evidence or decisions: their past sign-offs stay as they were, and the
    site then shows their email where it showed their name. It does not reset
    a password or change anyone's classes.
    """
    with db.connect() as conn:
        # --apply holds the list while it is read and written, so the website cannot be overwritten between
        if apply_:
            conn.execute("select 1 from config where key = 'app.staff' for update")
        lines = staff_remove.plan(conn, emails)
        refused = sum(ln.action == "refused" for ln in lines)
        if refused or not apply_:  # an applied removal says what it did, not what it would do
            for ln in lines:
                typer.echo(f"  {ln.email:<36}{ln.said}")
        if not apply_:
            typer.echo(
                f"  {len(lines) - refused} to remove, {refused} refused. This was a dry run: nothing changed."
                " Add --apply to do it."
            )
            return
        if refused:
            typer.echo(
                f"  {refused} refused, so nothing was applied. Fix the list of emails and run it again."
            )
            raise typer.Exit(1)
        gone = staff_remove.apply(conn, lines)
        conn.commit()
    typer.echo(f"  Removed {len(gone)}: " + ", ".join(f"{s['name']} ({s['role']})" for s in gone) + ".")
    typer.echo(
        "  They are signed out at their next request. Their past sign-offs are kept as they were,"
        " and the site shows their email where it showed their name."
    )


@staff_app.command("load")
def load_(
    path: Path = typer.Argument(
        ..., help="The table: a CSV, or a table copied from a spreadsheet; keep it outside the repository"
    ),
    apply_: bool = typer.Option(
        False, "--apply", help="Write it. Without this nothing changes and the table is only shown"
    ),
    skip_refused: bool = typer.Option(
        False, "--skip-refused", help="With --apply: do the rows that are fine, leave the refused ones"
    ),
    change_roles: bool = typer.Option(
        False,
        "--change-roles",
        help="Also change the role of a person already on the list to the one in the table (a coordinator sees every class)",
    ),
    passwords_to: Path | None = typer.Option(
        None,
        "--passwords-to",
        help="With --apply: also write the new passwords to this new file (mode 600, outside the repository)",
    ),
) -> None:
    """Put a table of staff on the list: each person's classes and subjects, and a one-time password for the new ones.

    The file has a header row and the columns name, email, role, subjects, classes. Subjects and classes hold several
    values in one cell, separated by commas, semicolons or spaces; a subject is its code or its name (Maths), a class is
    written as the site writes it (G3). Example row: Example Teacher, teacher@example.test, educator, Maths, G3

    Without --apply this changes nothing and says what each row would do. People not in the file are never changed.
    """
    keep, rows = _read_the_table(path, passwords_to, apply_)
    given: dict[str, str] = {}
    with db.connect() as conn:
        if (
            apply_
        ):  # the list is held while it is read and written, so the website cannot be overwritten between
            conn.execute("select 1 from config where key = 'app.staff' for update")
        lines = staff_load.plan(conn, rows, change_roles)
        refused = _show(lines, sum(s["email"].lower() not in {ln.email for ln in lines} for s in staff(conn)))
        if not apply_:
            typer.echo(
                "  This was a dry run: nothing changed, and no password was made. Add --apply to do it."
            )
            return
        if refused and not skip_refused:
            typer.echo(
                "  Some rows are refused, so nothing was applied. Fix the file, or add --skip-refused to do the rest."
            )
            raise typer.Exit(1)
        given = staff_load.apply(
            conn, lines, int(settings.threshold(conn, "password.scrypt_n", NODE_DEFAULT_N))
        )
        if keep and given:
            try:
                staff_load.write_private(keep, "".join(f"{e}  {p}\n" for e, p in given.items()))
            except ValueError as e:
                raise typer.BadParameter(str(e)) from e
        conn.commit()
    typer.echo("  Applied.")
    _hand_over(given, keep)


def _read_the_table(
    path: Path, passwords_to: Path | None, apply_: bool
) -> tuple[Path | None, list[dict[str, str]]]:
    """The table and the passwords file checked before anything else happens: both outside the repository, the second
    new and wanted only with --apply. Notes about ignored columns are said as they are found."""
    try:
        table = staff_load.outside_repository(path, "the table")
        keep = staff_load.outside_repository(passwords_to, "the passwords file") if passwords_to else None
        if keep and not apply_:
            raise ValueError("--passwords-to goes with --apply")
        if keep and keep.exists():
            raise ValueError(f"{keep} already exists — it is never overwritten; name a new file")
        rows, notes = staff_load.read_table(table)
    except (ValueError, OSError) as e:
        raise typer.BadParameter(str(e)) from e
    for note in notes:
        typer.echo(f"  {note}")
    return keep, rows


def _show(lines: list[staff_load.Line], outside: int) -> int:
    """Say what each row does and the totals → how many rows are refused."""
    for ln in lines:
        typer.echo(f"  row {ln.row:<3}{ln.email:<36}{ln.said}" + "".join(f"  [{r}]" for r in ln.reads))
    count = {a: sum(ln.action == a for ln in lines) for a in ("add", "update", "same", "refused")}
    typer.echo(
        f"  {count['add']} to add, {count['update']} to update, {count['same']} no change, {count['refused']} refused."
        f" {outside} others on the list are not in the file and are left as they are (this tool removes no one)."
    )
    return count["refused"]


def _hand_over(given: dict[str, str], keep: Path | None) -> None:
    """The one-time passwords, in the terminal and nowhere else but the private file asked for."""
    if not given:
        return
    typer.echo(
        "\n  Give each person theirs in person or by phone, not in a group chat."
        " They should change it from Change password after the first sign-in.\n"
    )
    typer.echo(f"  {'email':<36}password")
    for email, password in given.items():
        typer.echo(f"  {email:<36}{password}")
    typer.echo("\n  These are shown once and kept nowhere" + (f" except {keep}." if keep else "."))


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
