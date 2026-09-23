"""W2's commands — `engine week …`: the class list, each child's prescription, the pack in handout order,
and its approval. `engine/cli.py` only mounts this."""

from pathlib import Path

import typer

from engine.core import db, roster
from engine.w2_print import assemble, focus_paper, pack, prescribe

week_app = typer.Typer(help="W2 — the week's papers", no_args_is_help=True)


@week_app.command("roster")
def week_roster(path: str) -> None:
    """Import or update the class list. Names go to the pii schema and nowhere else."""
    counts = roster.load(Path(path))
    for k, v in counts.items():
        typer.echo(f"  {k:<14}{v:>4}")


@week_app.command("prescribe")
def week_prescribe(
    section: str,
    week: str,
    skill_set: str = typer.Option(..., "--set", help="What was taught — the teacher's declaration"),
    kind: str = typer.Option("practice", "--kind", help="practice | assessment"),
) -> None:
    """Choose each child's difficulty for the week, and say which rule chose it."""
    with db.connect() as conn:
        rows = prescribe.for_class(conn, section, week, skill_set, kind)
        conn.commit()
    for r in rows:
        typer.echo(
            f"  {r['roll_no']:<4}{r['band']:<4}{r['difficulty']:<9}{prescribe.RULES.get(r['rule'], r['rule'])}"
        )
    by = {}
    for r in rows:
        by[r["difficulty"]] = by.get(r["difficulty"], 0) + 1
    typer.echo("  " + " · ".join(f"{n} at {d}" for d, n in sorted(by.items())))


@week_app.command("assemble")
def week_assemble(
    section: str,
    week: str,
    kind: str = typer.Option("practice", "--kind"),
    out: str = typer.Option("data/packs", "--out"),
    actor: str = typer.Option("engine-cli", "--actor", help="Who is printing — recorded on every name read"),
) -> None:
    """Build one paper per child plus spares, render them, and merge the pack in handout order."""
    outdir = db.REPO_ROOT / out / f"{section}-{week}-{kind}"
    with db.connect() as conn:
        built = assemble.for_week(conn, section, week, kind)
        for s in built["short"]:
            typer.echo(f"  SHORT  {s['roll_no']} at {s['difficulty']}: {s['why']}", err=True)
        if not built["sheets"]:
            conn.rollback()
            typer.echo("  nothing assembled — see why above", err=True)
            raise typer.Exit(1)
        summary = assemble.render(conn, built, outdir, week, actor, kind)
        conn.commit()
    typer.echo(f"  {summary['sheets']} named · {summary['spares']} spare · {summary['pages']} pages")
    typer.echo(f"  {summary['pack']}")


@week_app.command("approve")
def week_approve(
    section: str,
    week: str,
    kind: str = typer.Option("practice", "--kind"),
    by: str = typer.Option(..., "--by", help="Who is approving — written on every sheet in the week"),
) -> None:
    """N7's gate by hand, for an operator without the screen. The database refuses a printed sheet
    that cannot say who allowed it, so this is the only way it reaches a child."""
    with db.connect() as conn:
        out = pack.approve(conn, section, week, kind, by)
        conn.commit()
    typer.echo(
        f"  {out['sheets']} sheets approved by {out['approved_by']}"
        f" — {out['named']} named, {out['spares']} spare"
    )


@week_app.command("pack")
def week_pack(section: str, week: str, kind: str = typer.Option("practice", "--kind")) -> None:
    """The approved pack as one PDF, in handout order; refused while any paper in it waits for a teacher."""
    with db.connect() as conn:
        out = pack.pdf(conn, section, week, kind, db.REPO_ROOT / "data" / "packs")
    typer.echo(f"  {out}")


@week_app.command("focus")
def week_focus(
    section: str,
    first_name: str,
    week: str,
    make: bool = typer.Option(False, "--make", help="Print the paper; without it only the plan is shown"),
    by: str = typer.Option(
        "", "--by", help="Who approves it; required with --make (names are read through the logging accessor)"
    ),
) -> None:
    """One child's next paper, chosen from their own graph: the areas they lag in and why, the questions. With
    --make, the person named by --by approves it and it prints in their name."""
    if make and not by.strip():
        raise typer.BadParameter(
            "a paper prints only when a person approves it: name them with --by", param_hint="--by"
        )
    with db.connect() as conn:
        child = str(roster.find(conn, section, first_name, by or "cli"))
        if make:
            p = focus_paper.make(conn, child, week, by)
            conn.commit()
        else:
            p = focus_paper.plan(conn, child, week)
    if not p["areas"]:
        typer.echo("  nothing to work on: no area this child lags in yet")
        return
    for a in p["areas"]:
        typer.echo(f"  {a['name']} — {a['level']} · {len(a['questions'])} questions · {a['why']}")
    if make:
        typer.echo(f"  printed {p['questions']} questions · QR {p['qr']} · {p['pdf_path']}")
