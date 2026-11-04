"""`engine skill-links` — a person's list of prerequisite pairs loaded as proposed links, and one link confirmed by id
(goals/m1-15-skill-links.yaml). Its own module so `cli.py` stays one screen per workflow."""

from collections.abc import Iterator
from contextlib import contextmanager

import typer

from engine.core import db
from engine.w3_read import skill_links

skill_links_app = typer.Typer(
    help="Skills that come before others: load a list as proposals, confirm one link", no_args_is_help=True
)


@contextmanager
def refusals() -> Iterator[None]:
    """A refused list or confirmation is said in words and exits 1; nothing it did is kept (the connection rolls back)."""
    try:
        yield
    except skill_links.Refused as e:
        typer.echo(f"  {e}", err=True)
        raise typer.Exit(1) from None


@skill_links_app.command("load")
def load(
    path: str = typer.Argument(
        ...,
        help="a CSV with the columns before_code, after_code, reason, source (and strength, if the list has it)",
    ),
) -> None:
    """Load the list as PROPOSED links between registry skills. Loading twice changes nothing; a link that is
    already there is never reworded or unconfirmed. A wrong pair refuses the whole list and names its line."""
    with refusals(), db.connect() as conn:
        done = skill_links.load(conn, path)
    typer.echo(
        f"  {done.added} links proposed, {done.there} were there already. Nothing reads a link until it is confirmed."
    )


@skill_links_app.command("confirm")
def confirm(
    link_id: str = typer.Argument(..., help="the link's id"),
    by: str = typer.Option(..., "--by", help="the email of the member of staff who confirms it"),
) -> None:
    """One member of staff says one link is right. The link is then read by everything that reads confirmed links."""
    with refusals(), db.connect() as conn:
        word = skill_links.confirm(conn, link_id, by)
    typer.echo(
        "  confirmed." if word == "confirmed" else "  already confirmed; the first person's word stands."
    )
