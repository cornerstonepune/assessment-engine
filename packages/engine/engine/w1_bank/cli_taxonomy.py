"""`engine bank relabel` (a question's derived labels, recomputed — ADR 0030) and `engine bank taxonomy`
(every case of the team's taxonomy, counted in the bank). Their own module so `cli.py` does not grow past
its ceiling."""

from collections import Counter

import typer

from engine.core import db
from engine.w1_bank import cases, labels, refill, rehome


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
        typer.echo(
            f"  {len(rows)} cases · {by['covered']} covered · {by['missing']} missing · {by['thin']} thin"
        )
        with db.connect() as conn:
            where = cases.placed(conn)
        for code, section, _, state in where:
            if state == "unplaced":
                typer.echo(f"  {code:<4} §{section:<5} unplaced: no level in use names it")
        on = Counter(state for *_, state in where)
        typer.echo(
            f"  {len(where)} cases · {on['placed']} placed in a level · {on['pattern']} patterns the levels climb"
            f" · {on['unplaced']} unplaced"
        )

    @bank_app.command("rehome")
    def bank_rehome(dry_run: bool = typer.Option(False, "--dry-run", help="Count, change nothing")) -> None:
        """Retire the skill sets the seed says are replaced and move their questions to the taxonomy-shaped
        skill and level each one is. Nothing is regenerated; a question with no place is retired, saying why."""
        with db.connect() as conn:
            out = rehome.rehome(conn)
            if dry_run:
                conn.rollback()
            else:
                conn.commit()
        for (code, level), n in sorted(out["moved"].items()):
            typer.echo(f"  {code:<12} {level:<8} {n:>5}")
        typer.echo(
            f"  {'would retire' if dry_run else 'retired'} {len(out['retired_sets'])} skill sets"
            f" · moved {sum(out['moved'].values())} questions · no place {sum(out['no_place'].values())}"
            f" · {out['old_papers']} old papers' sums onto their skill"
        )

    @bank_app.command("levels")
    def bank_levels(
        apply: bool = typer.Option(False, "--apply", help="Write them; default only lists"),
    ) -> None:
        """The rewritten levels from the seed onto the skill sets in the database; each waits for approval."""
        with db.connect() as conn:
            changed = cases.propose_levels(conn)
            if apply:
                conn.commit()
            else:
                conn.rollback()
        verb = "now wait for approval" if apply else "would change (run with --apply)"
        typer.echo(f"  {len(changed)} skill sets {verb}: {', '.join(changed) or '—'}")

    @bank_app.command("refill")
    def bank_refill() -> None:
        """Retire every question its level's rule no longer holds, then fill every level to its target.
        Commits level by level, so a long run keeps what it has made."""
        with db.connect() as conn:

            def said(code, difficulty, n):
                conn.commit()
                if n:
                    typer.echo(f"  {code:<20} {difficulty:<8} +{n}")

            retired, added = refill.refill(conn, after_level=said)
            conn.commit()
        typer.echo(
            f"  retired {sum(retired.values())} questions outside their level · added {sum(added.values())}"
        )
