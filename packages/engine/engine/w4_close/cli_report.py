"""W4's report commands — `engine report …`: one child's report, and every report read back against Aseem's
findings. `engine/cli.py` only mounts this."""

import typer

from engine.core import db
from engine.w3_read import gold
from engine.w4_close import every_report, report

report_app = typer.Typer(help="W4 — a child's report, in the shape of Aseem's", no_args_is_help=True)


@report_app.command("child")
def report_child(
    child_id: str, since: str = typer.Option(None, "--since", help="Evidence from this date on")
) -> None:
    """One child's report: strong concepts, faulty ones each with the child's own example, and what comes next."""
    with db.connect() as conn:
        r = report.build(conn, child_id, since)
    for s in r["strong"]:
        typer.echo(f"  strong  {s['name']}  ({s['right']} of {s['answered']})")
    for f in r["faulty"]:
        ex = f["example"]
        shown = f"  e.g. {ex['question']} — wrote {ex['wrote']}, right {ex['right']}" if ex else ""
        typer.echo(f"  faulty  {f['name']} ×{f['times']} [{f['skill']}]{shown}")
    for u in r["unexplained"]:
        typer.echo(f"  wrong, no named mistake  {u['skill']} ×{u['times']}")
    n = r["next"]
    typer.echo(f"  next    {n['skill_set']} {n['level']}" if n else "  next    nothing to work on yet")


@report_app.command("gold")
def report_gold() -> None:
    """Every report against Aseem's findings. Exits 1 until every finding the papers hold is in the report."""
    with db.connect() as conn:
        findings = gold.check(conn)
        reports = {str(c): report.build(conn, c) for c in {f["child_id"] for f in findings}}
    rows = report.against(findings, reports)
    for r in rows:
        mark = {True: "IN", False: "MISSING", None: "APART"}[r["in_report"]]
        typer.echo(
            f"  {mark:<8}{r['first_name']:<10}{r['verdict']:<7}{r['skill_code']:<12}"
            f"{r['misconception_code'] or '':<22}{r['why']}"
        )
    held = [r for r in rows if r["in_report"] is not None]
    typer.echo(
        f"\n  {sum(r['in_report'] for r in held)} of {len(held)} findings the papers hold are in the report;"
        f" {len(rows) - len(held)} counted apart"
    )
    if not held or not all(r["in_report"] for r in held):
        raise typer.Exit(1)
    typer.echo("  every finding the papers hold is in the report")


@report_app.command("parents")
def report_parents(
    by: str = typer.Option(
        ..., "--by", help="who asked: each report's run carries it, as the page's button does"
    ),
    band: str = typer.Option(
        None, "--band", help="only this band's children (G2, G3, G4); every band if left out"
    ),
) -> None:
    """Every parent report that is due, written one after another: each child with signed-off answers whose report is
    missing or out of date. Each is held to its facts and kept as a draft for an educator to approve. Names each child
    by class and roll, never by name. Exits 1 while any report due was not kept."""
    with db.connect() as conn:
        kids = every_report.due(conn, band)
    if not kids:
        typer.echo("  nothing due: every child with signed-off answers has a report still true of them")
        return
    typer.echo(f"  {len(kids)} report(s) due")
    done = []
    for k in kids:
        (d,) = every_report.write_each(by, [k])
        done.append(d)
        who = f"{d['band']}{'' if d['section'] == d['band'] else ' ' + d['section']} roll {d['roll_no']}"
        typer.echo(f"  {who}  " + ("kept" if d["kept"] else f"not kept: {d['error']}") + f"  ({d['why']})")
    kept = sum(d["kept"] for d in done)
    typer.echo(f"  {kept} of {len(done)} kept, each a draft waiting for an educator to approve")
    if kept < len(done):
        raise typer.Exit(1)
