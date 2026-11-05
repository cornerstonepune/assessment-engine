"""`engine read voice expire`, `retention`, `check`, `replay` and `switch` (tasks M1-01, M1-04): the two jobs a K2 voice
note needs on a clock, the reader's score against what was said, a typed transcript read with no recording, and the
two switches turned by a signed command (`voice_switch.py`).

`expire` leaves every note older than `voice.confirm_within_hours` (48) unconfirmed: it leaves her queue and never
becomes evidence. `retention` deletes recordings older than `voice.audio_retention_days`; that is O-14, open, and null
keeps every recording, so today it deletes nothing. Neither prints a transcript, a name or a recording.
"""

import json
from pathlib import Path

import typer

from engine.core import db
from engine.w3_read import voice_check, voice_intake, voice_store, voice_switch

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
        days, gone = voice_store.retention(conn)
    if days is None:
        typer.echo("kept: how long a recording is kept is not decided (O-14); nothing deleted")
    else:
        typer.echo(f"recordings deleted: {gone} (older than {days} days)")


@voice_app.command("check")
def check(
    expected: Path = typer.Argument(..., help="JSON: per note, what was said (see voice_check.py)"),
) -> None:
    """Score drafted notes against what the educator says they said, field by field. Prints no transcript or name."""
    with db.connect() as conn:
        for line in voice_check.score(conn, json.loads(expected.read_text())).lines():
            typer.echo(line)


@voice_app.command("replay")
def replay(
    transcript: Path = typer.Argument(..., help="a text file of what a note said"),
    class_id: str = typer.Option(..., "--class", help="the class's id"),
) -> None:
    """Read a typed transcript against a class as a recording's would be; nothing is written, no service is called."""
    with db.connect() as conn:
        for line in voice_check.replay_lines(voice_check.replay(conn, class_id, transcript.read_text())):
            typer.echo(line)
        conn.rollback()


@voice_app.command("switch")
def switch(
    which: str = typer.Argument(
        ..., help="screens (What needs doing, the form, Confirm) or recording (record and play)"
    ),
    state: str = typer.Argument(..., help="on or off"),
    by: str = typer.Option(..., "--by", help="your email, the one you sign in with; your staff id is logged"),
    retention_ref: str = typer.Option(
        None,
        "--retention-ref",
        help="recording on only: the reference of Sarvam's written 'No retention' (D-065)",
    ),
) -> None:
    """Turn a K2 voice switch on or off, logged under your staff id. Recording needs --retention-ref to go on."""
    if state not in ("on", "off"):
        raise typer.BadParameter("say on or off")
    with db.connect() as conn:
        try:
            typer.echo(voice_switch.switch(conn, which, state == "on", by, retention_ref))
        except ValueError as e:
            conn.rollback()
            typer.echo(str(e), err=True)
            raise typer.Exit(1) from e
