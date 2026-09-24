"""`engine read file` — one scanned file of many papers: what is in it, and with `--names`, each library
worksheet copy read and marked for the child named on it (`copies`). Its own module so `cli_read.py` stays
under the ceiling."""

import typer

from engine.core import db
from engine.w3_read import copies, sorting


def read_file(
    path: str,
    names: str = typer.Option(
        "",
        "--names",
        help="One per library worksheet copy, in file order: a first name, a roll number, or ? to skip",
    ),
    section: str = typer.Option("", "--section", help="G2, G3 … — whose class list the names are in"),
    actor: str = typer.Option("engine-cli", "--actor"),
) -> None:
    """One scanned file of many papers, sorted by the QR on each page: which pages are whose paper, and which
    pages carry no code this system printed. Without --names it reads only — no answer is read and nothing is
    written. With --names each library worksheet copy is read and marked for its child, every answer waiting on
    Marking for a person to sign off."""
    if names:
        if not section:
            raise typer.BadParameter("say whose class list the names are in with --section")
        return _read_copies(path, [n for n in names.split(",")], section, actor)
    with db.connect() as conn:
        papers = sorting.sort_file(conn, path)
        conn.rollback()
    for p in papers:
        pages = f"p{p['pages'][0]}" + (f"–{p['pages'][-1]}" if len(p["pages"]) > 1 else "")
        s, w = p["sheet"], p["worksheet"]
        if w:
            short = (
                f", {len(p['pages'])} of its {p['length']} pages" if len(p["pages"]) != p["length"] else ""
            )
            what = f"{p['qr']}  worksheet · {w['skill']} · {w['level']} · {w['questions']} questions{short}"
        elif s:
            who = f"{s['section']} roll {s['roll_no']}" if s["roll_no"] else "no child"
            seen = f", already read {s['captures']}×" if s["captures"] else ""
            what = f"{p['qr']}  {who} · {s['kind']} · {s['paper'] or s['source']} · {s['questions']} questions{seen}"
        elif p["qr"]:
            what = f"{p['qr']}  " + (
                "not in sheet_instance" if p["ours"] else "not a code this system prints"
            )
        else:
            what = "no QR read"
        flag = f"  (no QR on p{', p'.join(map(str, p['unread']))})" if p["qr"] and p["unread"] else ""
        typer.echo(f"  {pages:<9}{what}{flag}")
    found = sum(1 for p in papers if p["sheet"])
    typer.echo(
        f"  {sum(len(p['pages']) for p in papers)} pages · {len(papers)} papers · {found} found in sheet_instance"
    )


def _read_copies(path, names, section, actor):
    """Each copy's line names the child by roll number, never by name (rule 6)."""
    with db.connect() as conn:
        done = copies.read(conn, path, section, names, actor)
        rolls = {
            str(r["id"]): r["roll_no"]
            for r in conn.execute(
                "select id, roll_no from child where id = any(%s)",
                ([c["child_id"] for c in done if c["child_id"]],),
            )
        }
        waiting = 0
        for c in done:
            pages = f"p{c['pages'][0]}–{c['pages'][-1]}"
            if c.get("skipped"):
                typer.echo(f"  copy {c['copy']:>2}  {pages:<8}{c['code']:<8}  not read: no child named")
                continue
            t = copies.tally(conn, c["capture_id"])
            waiting += t["waiting"]
            again = "  (read before: nothing new)" if c["already"] else ""
            unread = (
                f", questions {', '.join(map(str, c['unread']))} for a person to mark" if c["unread"] else ""
            )
            typer.echo(
                f"  copy {c['copy']:>2}  {pages:<8}{c['code']:<8}  {section} roll {rolls[str(c['child_id'])]:<3}"
                f" {c['answers']} answers: {t['right'] + t['right_waiting']} read right, {t['wrong']} wrong,"
                f" {t['blank']} blank{unread}{again}"
            )
        conn.commit()
    typer.echo(
        f"  {waiting} answers wait on Marking for a person; none counts on a child's skills until signed off"
    )


def register(read_app: typer.Typer) -> None:
    read_app.command("file")(read_file)
