"""The two commands that prove things: `engine audit` (every invariant) and `engine goal <name>`
(a goal and the commands that prove it). Their own module so `cli.py` stays under the ceiling."""

import sys

import typer

from engine import audit as audit_module
from engine import db
from engine import goal as goal_module
from engine import scenarios as scenarios_module


def _say(line: str, err: bool = False) -> None:
    """Echo and flush. A goal takes minutes and its output is usually piped into a log or a CI step;
    without the flush a person watching sees nothing until the whole run ends and assumes it hung."""
    typer.echo(line, err=err)
    (sys.stderr if err else sys.stdout).flush()


def register(app: typer.Typer) -> None:
    app.command()(audit)
    app.command()(goal)


def audit() -> None:
    """Every invariant the rows must satisfy, in one sweep. Exits 1 on any violation."""
    with db.connect() as conn:
        results = audit_module.run(conn)
    bad = 0
    for name, violations in results:
        _say(
            f"  {'FAIL' if violations else 'ok  '}  {name}" + (f"  → {len(violations)}" if violations else "")
        )
        for v in violations[:10]:
            _say(f"          {v}", err=True)
        if len(violations) > 10:
            _say(f"          … and {len(violations) - 10} more", err=True)
        bad += len(violations)
    _say(f"  {len(results)} invariants checked, {bad} violations")
    if bad:
        raise typer.Exit(1)


def goal(name: str = typer.Argument("", help="A goal in goals/; omit to list them")) -> None:
    """A goal and the commands that prove it. Exits 1 until every criterion passes."""
    if not name:
        for n in goal_module.names():
            _say(f"  {n}  —  {goal_module.load(n)['goal'].strip()}")
        return
    spec = goal_module.load(name)
    _say(f"  GOAL  {spec['goal'].strip()}")

    scenarios = goal_module.scenarios_of(spec)
    met = 0
    if scenarios:
        with db.connect() as conn:
            for sc in scenarios:
                m, failures = scenarios_module.run_one(conn, sc)
                met += not failures
                _say(f"  {'PASS' if not failures else 'FAIL'}  {sc['name']}")
                _say("          " + "  ".join(f"{k}={v}" for k, v in m.items()))
                for f in failures:
                    _say(f"          {f}", err=True)
        _say(f"  {met}/{len(scenarios)} scenarios met the bar completely")

    failed = []
    for crit in spec["criteria"]:
        _say(f"  ....  {crit['name']}")  # said before it runs: some of these take minutes
        ok, out = goal_module.run_criterion(crit)
        if not ok:
            failed.append(crit["name"])
        _say(f"  {'PASS' if ok else 'FAIL'}  {crit['name']}")
        _say(f"          $ {crit['run']}")
        tail = [ln for ln in out.strip().splitlines() if ln.strip()][-3:]
        for ln in tail if not ok else tail[-1:]:
            _say(f"          {ln[:110]}")

    short = len(scenarios) - met
    _say(
        f"  {len(spec['criteria']) - len(failed)}/{len(spec['criteria'])} criteria met"
        + (f" · not met: {', '.join(failed)}" if failed else "")
        + (f" · {short} scenarios short of the bar" if short else "")
        + ("" if failed or short else " · GOAL ACHIEVED")
    )
    if failed or short:
        raise typer.Exit(1)
