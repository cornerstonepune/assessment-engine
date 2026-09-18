"""engine — the operator's command line."""
import typer

from pathlib import Path

from engine import assemble, bank, db, legacy, loaders, prescribe, roster
from engine.adapters.llm import LLMError
from engine.assess import graph

app = typer.Typer(help="Cornerstone assessment engine", no_args_is_help=True)
bank_app = typer.Typer(help="W1 — the question bank", no_args_is_help=True)
week_app = typer.Typer(help="W2 — the week's papers", no_args_is_help=True)
legacy_app = typer.Typer(help="N3 — papers done before QR sheets, read into evidence", no_args_is_help=True)
app.add_typer(bank_app, name="bank")
app.add_typer(week_app, name="week")
app.add_typer(legacy_app, name="legacy")


@app.callback()
def main() -> None:
    """Keeps subcommand mode on: with one command Typer would otherwise collapse it to the root."""


def _echo_counts(counts: dict, reasons: dict) -> None:
    for k, v in counts.items():
        typer.echo(f"  {k:<16}{v:>5}")
    if reasons:
        typer.echo("  rejected for: " + ", ".join(f"{k} ×{v}" for k, v in sorted(reasons.items(), key=lambda kv: -kv[1])))


@bank_app.command("fill")
def bank_fill(
    skill_set: str,
    difficulty: str,
    n: int = typer.Option(50, "--n", help="Verified items wanted"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Generate and verify, write nothing"),
    offline: bool = typer.Option(False, "--offline", help="Use the samplers, not the model — no sentences, but no quota either"),
) -> None:
    """Generate, verify and store items for one skill set at one difficulty."""
    shown = []

    def show_reject(c: dict, probs: list) -> None:
        if len(shown) < 5:
            shown.append(c)
            typer.echo(f"  rejected  {c.get('a')} {c.get('op')} {c.get('b')} [{c.get('format')}]: {'; '.join(probs)}", err=True)

    with db.connect() as conn:
        try:
            counts, reasons, _ = bank.fill(conn, skill_set, difficulty, n, dry_run,
                                           after_batch=None if dry_run else conn.commit,
                                           on_reject=show_reject, offline=offline)
        except LLMError as e:
            conn.commit()  # keep the flow_run row that records the failure
            typer.echo(f"MODEL  {e}", err=True)
            raise typer.Exit(1)
    _echo_counts(counts, reasons)


@bank_app.command("recheck")
def bank_recheck() -> None:
    """Recompute every active generated item from its spec; the count of disagreements must be 0."""
    with db.connect() as conn:
        bad = bank.recheck(conn)
    for key in bad:
        typer.echo(f"MISMATCH  {key}", err=True)
    typer.echo(f"  {len(bad)} mismatches")
    if bad:
        raise typer.Exit(1)


@bank_app.command("flag")
def bank_flag(
    item_key: str,
    by: str = typer.Option(..., "--by", help="Who is flagging"),
    note: str = typer.Option("", "--note"),
) -> None:
    """Retire an item. Any staff member, any item, one line of reason."""
    with db.connect() as conn:
        status = bank.flag(conn, item_key, by, note)
        conn.commit()
    typer.echo(f"  {item_key}  {status}")


@bank_app.command("sheet")
def bank_sheet(
    skill_set: str,
    difficulty: str,
    n: int = typer.Option(12, "--n"),
    out: str = typer.Option("data/bank", "--out"),
    seed: int = typer.Option(1, "--seed"),
) -> None:
    """Render n active items as a sheet with QR and key, so the bank can be held in the hand."""
    with db.connect() as conn:
        key = bank.sheet(conn, skill_set, difficulty, n, db.REPO_ROOT / out, seed)
    typer.echo(f"  {key['sheet_id']}  {key['pages']} pages  {key['n_responses']} responses  -> {out}/{key['sheet_id']}.pdf")


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
    kind: str = typer.Option("practice", "--kind", help="practice | assessment | home"),
) -> None:
    """Choose each child's difficulty for the week, and say which rule chose it."""
    with db.connect() as conn:
        rows = prescribe.for_class(conn, section, week, skill_set, kind)
        conn.commit()
    for r in rows:
        typer.echo(f"  {r['roll_no']:<4}{r['band']:<4}{r['difficulty']:<9}{prescribe.RULES.get(r['rule'], r['rule'])}")
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
            typer.echo(f"  SHORT  {s['roll_no']} at {s['difficulty']}: {s['had']} questions left, needs {s['needed']}", err=True)
        if not built["sheets"]:
            conn.rollback()
            typer.echo("  nothing assembled — fill the bank first", err=True)
            raise typer.Exit(1)
        summary = assemble.render(conn, built, outdir, week, actor, kind)
        conn.commit()
    typer.echo(f"  {summary['sheets']} named · {summary['spares']} spare · {summary['pages']} pages")
    typer.echo(f"  {summary['pack']}")


@legacy_app.command("paper")
def legacy_paper(path: str) -> None:
    """Enter (or correct) a paper once: its printed questions become legacy items with a rung each."""
    with db.connect() as conn:
        template = legacy.load_paper(conn, path)
        conn.commit()
        _, items = legacy.paper_rows(conn, __import__("json").loads(Path(path).read_text())["code"])
    typer.echo(f"  {template}  {len(items)} questions")
    for key, it in sorted(items.items(), key=lambda kv: (int(''.join(ch for ch in kv[0] if ch.isdigit()) or 0), kv[0])):
        sp = it["spec"]
        typer.echo(f"  {key:<4}{sp.get('kind','bare'):<8}{sp.get('expr') or '':<14}= {str(sp.get('answer')):<6} "
                   f"{it['responses'][0]['misconceptions'] and len(it['responses'][0]['misconceptions']) or 0:>2} predictions")


@legacy_app.command("import")
def legacy_import(
    path: str,
    paper: str = typer.Option(..., "--paper", help="The paper's code, as entered with `legacy paper`"),
    child: str = typer.Option(..., "--child", help="The child's first name"),
    section: str = typer.Option(..., "--section", help="G2, G3 …"),
    pages: str = typer.Option("", "--pages", help="Only these pages of the file, e.g. 1,2"),
    mask: str = typer.Option("", "--mask", help="Name-band fraction per page, e.g. 1=0.16,2=0"),
    narrative: bool = typer.Option(False, "--narrative", help="Also ask for the whole-page reading (Channel B)"),
    actor: str = typer.Option("engine-cli", "--actor"),
) -> None:
    """Read one scan of one child's paper: candidate results a person then confirms."""
    page_list = [int(x) for x in pages.split(",") if x.strip()] or None
    masks = {int(k): float(v) for k, v in (kv.split("=") for kv in mask.split(",") if kv.strip())} or None
    with db.connect() as conn:
        cid = roster.find(conn, section, child, actor)
        try:
            summary = legacy.import_scan(conn, path, paper, cid, actor, page_list, masks, narrative)
        except LLMError as e:
            conn.commit()
            typer.echo(f"  could not read: {e}", err=True)
            raise typer.Exit(1)
        conn.commit()
    for r in summary["results"]:
        tail = " ".join(r["codes"]) if r["codes"] else ("working" if r["working"] != "none" else "")
        typer.echo(f"  {r['item']:<4}{r['question'][:34]:<36}read {r['read']!r:<12}{r['status']:<14}{tail}")
    if summary["unmatched"]:
        typer.echo(f"  not on the paper: {', '.join(summary['unmatched'])}")
    for n in summary["notes"]:
        typer.echo(f"  note: {n}")
    typer.echo(f"  {len(summary['results'])} answers over {summary['pages']} page(s) → candidate")


@legacy_app.command("remark")
def legacy_remark(child: str = typer.Option(..., "--child"), section: str = typer.Option(..., "--section"),
                  actor: str = typer.Option("engine-cli", "--actor")) -> None:
    """Mark a child's candidate results again from what was read — no model call."""
    with db.connect() as conn:
        cid = roster.find(conn, section, child, actor)
        n = legacy.remark(conn, cid)
        conn.commit()
    typer.echo(f"  {n} results changed")


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
def legacy_show(child: str = typer.Option(..., "--child"), section: str = typer.Option(..., "--section"),
                actor: str = typer.Option("engine-cli", "--actor")) -> None:
    """The child's map as the Growth screen shows it: rung, state, evidence, and the next step."""
    with db.connect() as conn:
        cid = roster.find(conn, section, child, actor)
        m = legacy.child_map(conn, cid)
        conn.commit()
    for s in m["states"]:
        rep = f"  repeats {s['repeating_misconception']}" if s["repeating_misconception"] else ""
        typer.echo(f"  {s['rung_code']:<4}{s['state']:<16}{s['n_correct']:>2}/{s['n_events']:<3} {s['descriptor'][:44]}{rep}")
    for n in m["next"]:
        typer.echo(f"  next {n['code']:<13}{n['difficulty'] or '—':<9}{n['rule']:<13}{' '.join(n['targets'] or [])}")
    if m["pending"]:
        typer.echo(f"  {m['pending']} candidate results awaiting confirmation")


@app.command("graph")
def graph_(child_id: str = typer.Option("", "--child", help="One child id; default every child with evidence")) -> None:
    """Rebuild Ring B — child_skill_state — from confirmed evidence."""
    with db.connect() as conn:
        n = graph.rebuild(conn, child_id or None)
        conn.commit()
    typer.echo(f"  {n} states")


@app.command("eval")
def eval_(
    purpose: str,
    n: int = typer.Option(10, "--n", help="Items asked per skill set × difficulty"),
    only: str = typer.Option("", "--only", help="One skill set code, else all"),
) -> None:
    """Score a prompt. For item_generate: accepted ÷ returned per skill set × difficulty, nothing stored."""
    if purpose != "item_generate":
        raise typer.BadParameter("only item_generate has an eval so far")
    total_ok = total = 0
    with db.connect() as conn:
        sets = conn.execute("select code, difficulty from skill_set order by code").fetchall()
        for s in sets:
            if only and s["code"] != only:
                continue
            for d in s["difficulty"]:
                counts, reasons, _ = bank.fill(conn, s["code"], d, n, dry_run=True)
                ok, ret = counts.get("accepted", 0), counts.get("returned", 0)
                total_ok += ok; total += ret
                worst = max(reasons, key=reasons.get) if reasons else "-"
                typer.echo(f"  {s['code']:<14}{d:<9}{ok:>3}/{ret:<3}  {worst}")
    typer.echo(f"  pass rate {total_ok}/{total} = {total_ok / total:.2f}" if total else "  nothing returned")


@app.command()
def load(
    check: bool = typer.Option(False, "--check", help="Load twice and fail if anything moved"),
) -> None:
    """Load the registry, ladder, levels, misconceptions, dimensions, prompts and thresholds."""
    counts = loaders.load_all()
    width = max(len(t) for t in counts)
    for table, n in counts.items():
        typer.echo(f"  {table:<{width}}  {n:>5}")

    bad = {k: v for k, v in loaders.orphans().items() if v}
    if bad:
        for label, codes in bad.items():
            typer.echo(f"ORPHAN  {label}: {', '.join(codes)}", err=True)
        raise typer.Exit(1)
    typer.echo("  every code referenced resolves")

    if check:
        again = loaders.load_all()
        moved = {t: (counts[t], again[t]) for t in counts if counts[t] != again[t]}
        if moved:
            for t, (was, now) in moved.items():
                typer.echo(f"CHANGED  {t}: {was} -> {now}", err=True)
            raise typer.Exit(1)
        typer.echo("  unchanged on a second run")


if __name__ == "__main__":
    app()
