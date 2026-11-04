"""W2's materials commands (task M1-10): `engine reminders --due`. `engine/cli.py` only mounts this."""

import typer

from engine.core import db
from engine.w2_print import materials_list, materials_remind


def register_materials(app: typer.Typer) -> None:
    @app.command("reminders")
    def reminders(
        due: bool = typer.Option(False, "--due", help="Count the materials reminders that have come due"),
    ) -> None:
        """Count the materials-list reminders due today. It sends nothing and changes nothing: the educator sees them
        in her inbox, and the box's timer runs this so the count is in its log."""
        if not due:
            raise typer.BadParameter("say what to do: --due")
        with db.connect() as conn:
            if not materials_list.enabled(conn):
                typer.echo("educator.timetable_enabled is off: nothing is due")
                return
            tenant = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
            n = materials_remind.due_counts(conn, materials_remind.school_today(conn), tenant)
        typer.echo(
            f"due: {n['reminders']} reminders for {n['lists']} lists (educator {n['educator']}, team {n['team']})"
        )
