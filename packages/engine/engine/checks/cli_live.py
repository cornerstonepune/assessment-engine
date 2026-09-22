"""Is the live website answering? `engine live check` — the evidence a step closes on (BUILD-ORDER,
"Now: five steps"). Its own module so `cli.py` stays one screen per workflow."""

import typer

from engine.checks import live

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
