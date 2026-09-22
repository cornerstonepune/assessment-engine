"""W1's commands — `engine bank …`: fill a level, its coverage, the reviewers, recheck, flag, a sample
sheet, a skill set's mistakes. The taxonomy's commands (relabel, taxonomy, levels, refill) register here
from cli_taxonomy. `engine/cli.py` only mounts this."""

import typer

from engine.adapters.llm import LLMError
from engine.core import db
from engine.w1_bank import bank, inventory, review, spec
from engine.w1_bank.cli_taxonomy import register as register_taxonomy

bank_app = typer.Typer(help="W1 — the question bank", no_args_is_help=True)


def _echo_counts(counts: dict, reasons: dict) -> None:
    for k, v in counts.items():
        typer.echo(f"  {k:<16}{v:>5}")
    if reasons:
        typer.echo(
            "  rejected for: "
            + ", ".join(f"{k} ×{v}" for k, v in sorted(reasons.items(), key=lambda kv: -kv[1]))
        )


@bank_app.command("fill")
def bank_fill(
    skill_set: str,
    difficulty: str,
    n: int = typer.Option(50, "--n", help="Verified items wanted"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Generate and verify, write nothing"),
    offline: bool = typer.Option(
        False, "--offline", help="Use the samplers, not the model — no sentences, but no quota either"
    ),
    native: bool = typer.Option(
        False,
        "--native",
        help="Build from the skill set's own code generator (mental strategies, word problems, budget, estimation, efficient method) — no model, no sampler",
    ),
) -> None:
    """Generate, verify and store items for one skill set at one difficulty."""
    if native:
        with db.connect() as conn:
            counts, _ = bank.fill_native(
                conn, skill_set, difficulty, n, dry_run, after_batch=None if dry_run else conn.commit
            )
        _echo_counts(counts, {})
        return

    shown = []

    def show_reject(c: dict, probs: list) -> None:
        if len(shown) < 5:
            shown.append(c)
            typer.echo(
                f"  rejected  {c.get('a')} {c.get('op')} {c.get('b')} [{c.get('format')}]: {'; '.join(probs)}",
                err=True,
            )

    with db.connect() as conn:
        try:
            counts, reasons, _ = bank.fill(
                conn,
                skill_set,
                difficulty,
                n,
                dry_run,
                after_batch=None if dry_run else conn.commit,
                on_reject=show_reject,
                offline=offline,
            )
        except LLMError as e:
            conn.commit()  # keep the flow_run row that records the failure
            typer.echo(f"MODEL  {e}", err=True)
            raise typer.Exit(1)
    _echo_counts(counts, reasons)


@bank_app.command("coverage")
def bank_coverage() -> None:
    """Every skill set at every difficulty against what a class needs in a week (ADR 0016)."""
    with db.connect() as conn:
        rows = inventory.coverage(conn)
        need = inventory._class_need(conn)
    short = 0
    for r in rows:
        under = r["n"] < r["target"]
        short += under
        # A unit below the class need carries its own measured ceiling: its numbers ran out, and the
        # note says so rather than reading as a shortfall (ADR 0011, ADR 0016).
        floor = "" if r["target"] == need else f"  (ceiling {r['target']}: whole range enumerated)"
        typer.echo(f"  {r['code']:<20}{r['difficulty']:<9}{r['n']:>4}{' <' if under else '  '}{floor}")
    typer.echo(f"  {len(rows)} units, {short} under their target")


@bank_app.command("unclassified")
def bank_unclassified(limit: int = typer.Option(50, "--limit")) -> None:
    """Wrong answers no named mistake explains, commonest first — the candidates for a new
    misconception. Empty until real papers are read; the instrument exists first (ADR 0012)."""
    with db.connect() as conn:
        rows = inventory.unclassified(conn, limit)
    for r in rows:
        # A legacy item — read off a real paper before the bank existed — has no skill set.
        # Those are the most interesting rows here, so they print, they do not crash.
        unit = r["skill_set_code"] or "(from a real paper)"
        sp = r["spec"] or {}
        question = r["stem"] or f"{sp.get('a')} {sp.get('op')} {sp.get('b')}"
        typer.echo(
            f"  {r['children']:>3} children  {r['rung_code'] or '?':<4}{unit:<22}"
            f"wrote {r['wrote']!s:<8}{question[:44]}"
        )
    typer.echo(f"  {len(rows)} unexplained wrong answers")


@bank_app.command("review")
def bank_review(
    skill_set: str,
    difficulty: str,
    reviewer: str = typer.Option("pedagogy_review", "--reviewer", help="pedagogy_review | language_review"),
    seed: int = typer.Option(1, "--seed"),
) -> None:
    """Judge one unit's rule and a ≤5% sample of its items. Advisory: nothing is retired here."""
    with db.connect() as conn:
        try:
            verdicts, meta = review.review_unit(conn, skill_set, difficulty, reviewer, seed=seed)
        except LLMError as e:
            conn.commit()
            typer.echo(f"MODEL  {e}", err=True)
            raise typer.Exit(1)
        conn.commit()
    for v in verdicts:
        mark = "  " if v["verdict"] == "pass" else " <"
        typer.echo(
            f"  {v['verdict']:<7}{mark}{v['ref']:<26}{','.join(v.get('reasons', [])):<22}{v.get('note', '')[:40]}"
        )
    worst = sum(1 for v in verdicts if v["verdict"] != "pass")
    typer.echo(
        f"  {len(verdicts)} judged, {worst} not a pass · {meta.get('model')} · ₹{meta.get('cost_inr')}"
    )


@bank_app.command("recheck")
def bank_recheck() -> None:
    """Recompute every active generated item from its spec; the count of disagreements must be 0."""
    with db.connect() as conn:
        bad = inventory.recheck(conn)
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
        status = inventory.flag(conn, item_key, by, note)
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
        key = inventory.sheet(conn, skill_set, difficulty, n, db.REPO_ROOT / out, seed)
    typer.echo(
        f"  {key['sheet_id']}  {key['pages']} pages  {key['n_responses']} responses  -> {out}/{key['sheet_id']}.pdf"
    )


@bank_app.command("misconceptions")
def bank_misconceptions(
    skill_set: str,
    apply: bool = typer.Option(False, "--apply", help="Store the new ones and attach the list to the set"),
    computed_only: bool = typer.Option(
        False, "--computed-only", help="Attach what code computes and ask no model at all"
    ),
) -> None:
    """Every wrong method a child can use on this skill set: what code computes from the band's own
    numbers, then what only judgment finds. Without --apply nothing is stored. With it, the set's
    ratification is withdrawn — a changed list needs a signature."""
    if computed_only:
        with db.connect() as conn:
            added = spec.apply_computed(conn, skill_set)
            conn.commit()
        typer.echo(
            f"  {skill_set}: {len(added)} added from what code computes"
            + (f" — {', '.join(added)}" if added else ", nothing new")
        )
        return
    with db.connect() as conn:
        meta = {}
        try:
            r = spec.propose_misconceptions(conn, skill_set, apply=apply, meta=meta)
        except LLMError as e:
            conn.commit()  # keep the flow_run row that records the failure
            typer.echo(f"MODEL  {e}", err=True)
            raise typer.Exit(1)
        conn.commit()
    for band, codes in r["known"].items():
        typer.echo(f"  computed  {band:<9}{len(codes):>2}  {', '.join(codes) or '— no numbers to sample'}")
    for p in r["proposals"]:
        if p["dropped"]:
            tag = "dropped"
        elif p["matches"]:
            tag = ",".join(p["matches"])
        else:
            tag = "NEW (working only)" if p["downgraded"] else "NEW"
        ex = p.get("example")
        shows = f"{spec.expression(ex)} -> {ex['child_writes']}" if ex else "(no number to show)"
        typer.echo(f"  {tag[:30]:<31}{shows[:26]:<28}{p['name'][:44]}")
    added = sum(1 for p in r["proposals"] if not p["matches"] and not p["dropped"])
    thrown = sum(1 for p in r["proposals"] if p["dropped"])
    tail = "" if apply else "   (nothing stored — add --apply)"
    typer.echo(
        f"  {len(r['covered'])} computed by code, {added} added by the model, {thrown} thrown away"
        f" · {meta.get('model')} · ₹{meta.get('cost_inr')}{tail}"
    )


register_taxonomy(bank_app)
