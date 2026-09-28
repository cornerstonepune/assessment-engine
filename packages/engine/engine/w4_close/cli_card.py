"""W4's commands — `engine card …`: Friday's class card, built from the graph, and its confirmation.
`engine/cli.py` only mounts this."""

import typer

from engine.core import db
from engine.w4_close import card

card_app = typer.Typer(help="W4 — Friday's class card", no_args_is_help=True)


@card_app.command("build")
def card_build(section: str, week: str) -> None:
    """Build the section's card from its children's graphs and keep it as the week's rows."""
    with db.connect() as conn:
        got = card.build(conn, section)
        card.store(conn, section, week, got)
        conn.commit()
    for s in got["skills"]:
        g = s["groups"]
        line = " · ".join(f"{k.replace('_', ' ')} {len(g[k])}" for k in card.ORDER if k != "reteach" and g[k])
        typer.echo(f"  {s['name']:<40}{line}")
        for code, r in g["reteach"].items():
            typer.echo(f"    reteach {r['name']} ({code}): {len(r['children'])}")
    for ch in got["children"]:
        h = ch["home"]
        where = (
            f"{h['skill_set']} {h['level']}" + (f" — {h['mistake_name']}" if h["mistake_name"] else "")
            if h
            else ch["why"]
        )
        typer.echo(f"  roll {ch['roll_no']:>3}  home: {where}")


@card_app.command("confirm")
def card_confirm(
    section: str, week: str, by: str = typer.Option(..., "--by", help="The educator confirming")
) -> None:
    """Confirm the section's card for the week, by name, as it stands now."""
    with db.connect() as conn:
        row = card.confirm(conn, section, week, by, card.build(conn, section))
        conn.commit()
    typer.echo(f"  confirmed by {by} at {row['created_at']:%Y-%m-%d %H:%M}")
