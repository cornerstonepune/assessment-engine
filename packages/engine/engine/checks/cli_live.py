"""Is the live website answering? `engine live check` — the evidence a step closes on (BUILD-ORDER,
"Now: five steps"). Its own module so `cli.py` stays one screen per workflow."""

import shutil

import typer

from engine.checks import live, live_copy, rules, watch
from engine.checks import live_data as live_data_module
from engine.core import db

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


@live_app.command("copy")
def live_copy_cmd(
    live_url: str = typer.Option(
        ..., "--live", envvar="LIVE", help="live's address, only read; default $LIVE"
    ),
    copy_url: str = typer.Option(..., "--copy", envvar="COPY", help="the copy's address; default $COPY"),
) -> None:
    """Every live row onto the copy, from one snapshot of live, and every table's count on the copy checked against
    that same snapshot's. Exits 1 on any table that differs. Prints tables and counts, never an address."""
    live_counts, wrong = live_copy.copy(live_url, copy_url)
    for w in wrong:
        typer.echo(f"  differs: {w}")
    if wrong:
        raise typer.Exit(1)
    typer.echo(
        f"copied: {len(live_counts)} tables, {sum(live_counts.values())} rows, every count equal to live's snapshot"
    )


@live_app.command("watch")
def live_watch() -> None:
    """What is wrong on live now, one line each: runs stuck or failed, website errors, the disk nearly full. Run on the
    server every ten minutes by watch-live.yml; exits 1 when anything is wrong."""
    with db.connect() as conn:
        lines = watch.problems(conn, shutil.disk_usage(db.REPO_ROOT).free)
    for line in lines:
        typer.echo(line)
    if lines:
        raise typer.Exit(1)


@live_app.command("rules")
def live_rules(
    write: bool = typer.Option(
        False,
        "--write",
        help="write this database's rules as the migrations' (a database built from them alone)",
    ),
    url: str = typer.Option(
        "", "--url", help="a database address; default LIVE_READONLY_DATABASE_URL, else .env"
    ),
) -> None:
    """Does a database hold the rules the migrations make? One line a rule it holds otherwise; exits 1 on any.
    With --write, records this database's rules as the migrations' (engine/checks/rules.json)."""
    with db.connect(url or live_data_module.url()) as conn:
        if write:
            typer.echo(f"  {rules.write(conn)} rules written to {rules.FILE.name}")
            return
        conn.read_only = True
        drifted = rules.drift(conn)
    for d in drifted:
        typer.echo(f"  {d}")
    typer.echo(f"  {len(drifted)} rules held otherwise than the migrations make them")
    if drifted:
        raise typer.Exit(1)
