"""`engine bank relabel` (a question's derived labels, recomputed — ADR 0030) and `engine bank taxonomy`
(every case of the team's taxonomy, counted in the bank). Their own module so `cli.py` does not grow past
its ceiling."""

from collections import Counter

import typer

from engine import cases, db, labels


def register(bank_app: typer.Typer) -> None:
    @bank_app.command("relabel")
    def bank_relabel(dry_run: bool = typer.Option(False, "--dry-run", help="Count, change nothing")) -> None:
        """Recompute the skills every generated question uses, from the question itself."""
        with db.connect() as conn:
            changed = labels.relabel(conn)
            if dry_run:
                conn.rollback()
            else:
                conn.commit()
        verb = "would change" if dry_run else "changed"
        typer.echo("  " + " · ".join(f"{name}: {n} {verb}" for name, n in changed.items()))

    @bank_app.command("taxonomy")
    def bank_taxonomy(
        show: str = typer.Option("gaps", "--show", help="gaps (missing and thin), all, or none"),
    ) -> None:
        """Every case of the team's addition & subtraction taxonomy, and how many questions hold it."""
        with db.connect() as conn:
            rows = cases.count(conn)
        for r in rows:
            if show == "all" or (show == "gaps" and r["state"] != "covered"):
                where = ", ".join(f"{code} {level} {n}" for (code, level), n in r["where"]) or "—"
                typer.echo(
                    f"  {r['code']:<4} {r['state']:<8} {r['n']:>5}  columns {r['vertical']:>4} · line {r['horizontal']:>4}"
                    f"  {r['label'][:62]:<62}  {where}"
                )
        by = Counter(r["state"] for r in rows)
        typer.echo(f"  {len(rows)} cases · {by['covered']} covered · {by['missing']} missing · {by['thin']} thin")

