"""N3 — papers done before QR sheets, read into evidence. Its own module so the operator's
command line stays one screen per workflow (CLAUDE.md rule 11: split along a responsibility)."""

from pathlib import Path

import typer

from engine import db, legacy, roster
from engine.adapters.llm import LLMError

legacy_app = typer.Typer(help="N3 — papers done before QR sheets, read into evidence", no_args_is_help=True)


@legacy_app.command("paper")
def legacy_paper(path: str) -> None:
    """Enter (or correct) a paper once: its printed questions become legacy items with a rung each."""
    with db.connect() as conn:
        template = legacy.load_paper(conn, path)
        conn.commit()
        _, items = legacy.paper_rows(conn, __import__("json").loads(Path(path).read_text())["code"])
    typer.echo(f"  {template}  {len(items)} questions")
    for key, it in sorted(
        items.items(), key=lambda kv: (int("".join(ch for ch in kv[0] if ch.isdigit()) or 0), kv[0])
    ):
        sp = it["spec"]
        typer.echo(
            f"  {key:<4}{sp.get('kind', 'bare'):<8}{sp.get('expr') or '':<14}= {sp.get('answer')!s:<6} "
            f"{it['responses'][0]['misconceptions'] and len(it['responses'][0]['misconceptions']) or 0:>2} predictions"
        )


@legacy_app.command("import")
def legacy_import(
    path: str,
    paper: str = typer.Option(..., "--paper", help="The paper's code, as entered with `legacy paper`"),
    child: str = typer.Option(..., "--child", help="The child's first name"),
    section: str = typer.Option(..., "--section", help="G2, G3 …"),
    pages: str = typer.Option("", "--pages", help="Only these pages of the file, e.g. 1,2"),
    mask: str = typer.Option("", "--mask", help="Name-band fraction per page, e.g. 1=0.16,2=0"),
    narrative: bool = typer.Option(
        False, "--narrative", help="Also ask for the whole-page reading (Channel B)"
    ),
    again: bool = typer.Option(
        False, "--again", help="Re-read even though the file is unchanged: the PAPER changed (engine.stale)"
    ),
    actor: str = typer.Option("engine-cli", "--actor"),
) -> None:
    """Read one scan of one child's paper: candidate results a person then confirms."""
    page_list = [int(x) for x in pages.split(",") if x.strip()] or None
    masks = {int(k): float(v) for k, v in (kv.split("=") for kv in mask.split(",") if kv.strip())} or None
    with db.connect() as conn:
        cid = roster.find(conn, section, child, actor)
        try:
            summary = legacy.import_scan(conn, path, paper, cid, actor, page_list, masks, narrative, again)
        except LLMError as e:
            conn.commit()
            typer.echo(f"  could not read: {e}", err=True)
            raise typer.Exit(1)
        conn.commit()
    if summary.get("already"):
        typer.echo(
            f"  already read as capture {summary['capture_id']} ({summary['already_results']} answers) — nothing to do"
        )
        return
    for r in summary["results"]:
        tail = " ".join(r["codes"]) if r["codes"] else ("working" if r["working"] != "none" else "")
        typer.echo(f"  {r['item']:<4}{r['question'][:34]:<36}read {r['read']!r:<12}{r['status']:<14}{tail}")
    if summary["unmatched"]:
        typer.echo(f"  not on the paper: {', '.join(summary['unmatched'])}")
    for n in summary["notes"]:
        typer.echo(f"  note: {n}")
    typer.echo(f"  {len(summary['results'])} answers over {summary['pages']} page(s) → candidate")


@legacy_app.command("dedupe")
def legacy_dedupe() -> None:
    """Void every live capture but the best one per (sheet, file) pair — the fix for a paper read
    more than once. Nothing is deleted; run `engine graph` after to rebuild from what remains."""
    with db.connect() as conn:
        backfilled, voided = legacy.dedupe(conn)
        conn.commit()
    typer.echo(f"  {backfilled} captures given a content hash, {voided} superseded")


@legacy_app.command("remark")
def legacy_remark(
    child: str = typer.Option("", "--child"),
    section: str = typer.Option("", "--section"),
    every_child: bool = typer.Option(
        False, "--every-child", help="every child with an answer not signed off"
    ),
    actor: str = typer.Option("engine-cli", "--actor"),
) -> None:
    """Mark a child's candidate results again from what was read — no model call. `--every-child` is how
    a change to the marking rule reaches every answer already read, in one transaction (ADR 0029)."""
    with db.connect() as conn:
        if every_child:
            ids = [
                r["child_id"]
                for r in conn.execute(
                    "select distinct si.child_id from item_result r join capture c on c.id = r.capture_id"
                    " join sheet_instance si on si.id = c.sheet_instance_id where r.state = 'candidate'"
                ).fetchall()
            ]
        elif child and section:
            ids = [roster.find(conn, section, child, actor)]
        else:
            raise typer.BadParameter("name one child with --child and --section, or say --every-child")
        n = sum(legacy.remark(conn, cid) for cid in ids)
        conn.commit()
    typer.echo(f"  {n} results changed" + (f" across {len(ids)} children" if every_child else ""))


@legacy_app.command("confirm")
def legacy_confirm(
    child: str = typer.Option(..., "--child"),
    section: str = typer.Option(..., "--section"),
    by: str = typer.Option(..., "--by", help="Who is confirming — recorded on every evidence row"),
) -> None:
    """A person confirms a child's candidate results; they become evidence and the map is rebuilt."""
    with db.connect() as conn:
        cid = roster.find(conn, section, child, by)
        n = legacy.confirm(conn, cid, by)
        conn.commit()
    typer.echo(f"  {n} results confirmed")


@legacy_app.command("show")
def legacy_show(
    child: str = typer.Option(..., "--child"),
    section: str = typer.Option(..., "--section"),
    actor: str = typer.Option("engine-cli", "--actor"),
) -> None:
    """The child's map as the Growth screen shows it: rung, state, evidence, and the next step."""
    with db.connect() as conn:
        cid = roster.find(conn, section, child, actor)
        m = legacy.child_map(conn, cid)
        conn.commit()
    for s in m["states"]:
        rep = f"  repeats {s['repeating_misconception']}" if s["repeating_misconception"] else ""
        typer.echo(
            f"  {s['rung_code']:<4}{s['state']:<16}{s['n_correct']:>2}/{s['n_events']:<3} {s['descriptor'][:44]}{rep}"
        )
    for n in m["next"]:
        typer.echo(
            f"  next {n['code']:<13}{n['difficulty'] or '—':<9}{n['rule']:<13}{' '.join(n['targets'] or [])}"
        )
    if m["pending"]:
        typer.echo(f"  {m['pending']} candidate results awaiting confirmation")
