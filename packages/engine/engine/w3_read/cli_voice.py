"""`engine read voice expire` and `engine read voice retention` (task M1-01): the two jobs a K2 voice note needs on a clock.

`expire` leaves every note older than `voice.confirm_within_hours` (48) unconfirmed: it leaves her queue and never
becomes evidence. `retention` deletes recordings older than `voice.audio_retention_days`; that is O-14, open, and null
keeps every recording, so today it deletes nothing. Neither prints a transcript, a name or a recording.
"""

import typer

from engine.core import db, settings
from engine.w3_read import voice_intake, voice_store

voice_app = typer.Typer(help="K2 voice notes", no_args_is_help=True)


@voice_app.command("expire")
def expire() -> None:
    """Leave every note not confirmed in time unconfirmed (never evidence)."""
    with db.connect() as conn:
        typer.echo(f"left unconfirmed: {voice_intake.expire(conn)}")


@voice_app.command("retention")
def retention() -> None:
    """Delete recordings older than the school's retention; with none decided, keep them all."""
    with db.connect() as conn:
        days = settings.config(conn, "voice.audio_retention_days")
        if days is None:
            typer.echo("kept: how long a recording is kept is not decided (O-14); nothing deleted")
            return
        rows = conn.execute(
            "select audio_key from pii.educator_note where status in ('confirmed', 'left_unconfirmed')"
            " and received_at < now() - make_interval(days => %s)",
            (int(days),),
        ).fetchall()
    gone = 0
    for r in rows:
        p = voice_store.path(r["audio_key"])
        if p.exists():
            p.unlink()
            gone += 1
    typer.echo(f"recordings deleted: {gone} (older than {int(days)} days)")
