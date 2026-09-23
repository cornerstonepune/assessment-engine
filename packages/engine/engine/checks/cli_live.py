"""Is the live website answering? `engine live check` — the evidence a step closes on (BUILD-ORDER,
"Now: five steps"). Its own module so `cli.py` stays one screen per workflow."""

import typer

from engine.checks import live
from engine.checks import live_data as live_data_module

live_app = typer.Typer(help="The live website, read from its own logs", no_args_is_help=True)


@live_app.command("check")
def live_check(
    since: str = typer.Option("60m", "--since", help="how far back: 30m, 2h"),
    page: list[str] = typer.Option(
        [], "--page", help="a page that must have been served; default the six menu pages"
    ),
) -> None:
    """Every production request in the window: how many never finished, how many failed, which
    pages were served — and the live database's statement timeouts and slowest checkpoint."""
    ok, lines = live.check(since, page)
    for line in lines:
        typer.echo(line)
    if not ok:
        raise typer.Exit(1)


@live_app.command("data")
def live_data(
    url: str = typer.Option(
        "", "--url", help="a database address; default LIVE_READONLY_DATABASE_URL, else .env"
    ),
) -> None:
    """Do the live rows say what the website shows? Read only: every migration applied, every signed-off
    answer on a skill the site shows, each child's skills rebuilt from their answers, Marking counting
    each printed question once. Exits 1 on any failure."""
    ok, lines = live_data_module.check(url or None)
    for line in lines:
        typer.echo(line)
    if not ok:
        raise typer.Exit(1)


@live_app.command("homes")
def live_homes(
    url: str = typer.Option(
        "", "--url", help="a database address; default LIVE_READONLY_DATABASE_URL, else .env"
    ),
    week: str = typer.Option("", "--week", help="2026-W39; default this week"),
) -> None:
    """Every child's home paper this week as Make papers proposes it — section, roll, skill, level, questions.
    Read only; no name is printed."""
    week, rows = live_data_module.homes(url or None, week or None)
    typer.echo(f"  week {week}")
    for section, roll, what in rows:
        typer.echo(f"  {section:<6}{roll:>4}  {what}")
    typer.echo(f"  {len(rows)} children · {sum('×' in w for _, _, w in rows)} with a proposed paper")
