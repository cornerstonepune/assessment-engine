"""`engine bank relabel`: a question's derived labels, recomputed (ADR 0030). Its own module so `cli.py`
does not grow past its ceiling."""

import typer

from engine import db, labels


def register(bank_app: typer.Typer) -> None:
    @bank_app.command("relabel")
    def bank_relabel(dry_run: bool = typer.Option(False, "--dry-run", help="Count, change nothing")) -> None:
        """Recompute the skills every generated question uses, from the question itself."""
        with db.connect() as conn:
            changed = labels.relabel(conn)
            if dry_run:
                conn.rollback()
            else:
                conn.commit()
        verb = "would change" if dry_run else "changed"
        typer.echo("  " + " · ".join(f"{name}: {n} {verb}" for name, n in changed.items()))
