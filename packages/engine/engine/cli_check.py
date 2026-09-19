"""The two commands that prove things: `engine audit` (every invariant) and `engine goal <name>`
(a goal and the commands that prove it). Their own module so `cli.py` stays under the ceiling."""

import typer

from engine import audit as audit_module
from engine import db
from engine import goal as goal_module
from engine import scenarios as scenarios_module


def register(app: typer.Typer) -> None:
    app.command()(audit)
    app.command()(goal)


def audit() -> None:
    """Every invariant the rows must satisfy, in one sweep. Exits 1 on any violation."""
    with db.connect() as conn:
        results = audit_module.run(conn)
    bad = 0
    for name, violations in results:
        typer.echo(
            f"  {'FAIL' if violations else 'ok  '}  {name}" + (f"  → {len(violations)}" if violations else "")
        )
        for v in violations[:10]:
            typer.echo(f"          {v}", err=True)
        if len(violations) > 10:
            typer.echo(f"          … and {len(violations) - 10} more", err=True)
        bad += len(violations)
    typer.echo(f"  {len(results)} invariants checked, {bad} violations")
    if bad:
        raise typer.Exit(1)


def goal(name: str = typer.Argument("", help="A goal in goals/; omit to list them")) -> None:
    """A goal and the commands that prove it. Exits 1 until every criterion passes."""
    if not name:
        for n in goal_module.names():
            typer.echo(f"  {n}  —  {goal_module.load(n)['goal']}")
        return
    spec, results = goal_module.check(name)
    typer.echo(f"  GOAL  {spec['goal'].strip()}")
    scenarios = goal_module.scenarios_of(spec)
    met = 0
    if scenarios:
        with db.connect() as conn:
            for sc, m, failures in scenarios_module.run(scenarios, conn):
                met += not failures
                typer.echo(f"  {'PASS' if not failures else 'FAIL'}  {sc['name']}")
                typer.echo("          " + "  ".join(f"{k}={v}" for k, v in m.items()))
                for f in failures:
                    typer.echo(f"          {f}", err=True)
        typer.echo(f"  {met}/{len(scenarios)} scenarios met the bar completely")
    for c, ok, out in results:
        typer.echo(f"  {'PASS' if ok else 'FAIL'}  {c['name']}")
        typer.echo(f"          $ {c['run']}")
        tail = [ln for ln in out.strip().splitlines() if ln.strip()][-3:]
        for ln in tail if not ok else tail[-1:]:
            typer.echo(f"          {ln[:110]}")
    failed = [c["name"] for c, ok, _ in results if not ok]
    short = len(scenarios) - met
    typer.echo(
        f"  {len(results) - len(failed)}/{len(results)} criteria met"
        + (f" · not met: {', '.join(failed)}" if failed else "")
        + (f" · {short} scenarios short of the bar" if short else "")
        + ("" if failed or short else " · GOAL ACHIEVED")
    )
    if failed or short:
        raise typer.Exit(1)
