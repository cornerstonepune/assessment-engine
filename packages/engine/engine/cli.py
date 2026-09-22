"""engine — the operator's command line."""

import getpass
import hashlib
import json
import secrets
from pathlib import Path

import typer

from engine import assemble, bank, db, loaders, prescribe, review, roster, spec
from engine.adapters.llm import LLMError
from engine.assess import graph
from engine.cli_check import register as register_checks
from engine.cli_gold import gold_app
from engine.cli_legacy import legacy_app
from engine.cli_library import library_app
from engine.cli_live import live_app
from engine.cli_read import read_app

app = typer.Typer(help="Cornerstone assessment engine", no_args_is_help=True)
bank_app = typer.Typer(help="W1 — the question bank", no_args_is_help=True)
week_app = typer.Typer(help="W2 — the week's papers", no_args_is_help=True)
app.add_typer(bank_app, name="bank")
app.add_typer(week_app, name="week")
app.add_typer(legacy_app, name="legacy")
app.add_typer(read_app, name="read")
app.add_typer(live_app, name="live")
app.add_typer(library_app, name="library")
app.add_typer(gold_app, name="gold")
register_checks(app)


@app.callback()
def main() -> None:
    """Keeps subcommand mode on: with one command Typer would otherwise collapse it to the root."""


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
        rows = bank.coverage(conn)
        need = bank._class_need(conn)
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
        rows = bank.unclassified(conn, limit)
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
    typer.echo(
        f"  {key['sheet_id']}  {key['pages']} pages  {key['n_responses']} responses  -> {out}/{key['sheet_id']}.pdf"
    )


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
        typer.echo(
            f"  {r['roll_no']:<4}{r['band']:<4}{r['difficulty']:<9}{prescribe.RULES.get(r['rule'], r['rule'])}"
        )
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
            typer.echo(f"  SHORT  {s['roll_no']} at {s['difficulty']}: {s['why']}", err=True)
        if not built["sheets"]:
            conn.rollback()
            typer.echo("  nothing assembled — see why above", err=True)
            raise typer.Exit(1)
        summary = assemble.render(conn, built, outdir, week, actor, kind)
        conn.commit()
    typer.echo(f"  {summary['sheets']} named · {summary['spares']} spare · {summary['pages']} pages")
    typer.echo(f"  {summary['pack']}")


@week_app.command("approve")
def week_approve(
    section: str,
    week: str,
    kind: str = typer.Option("practice", "--kind"),
    by: str = typer.Option(..., "--by", help="Who is approving — written on every sheet in the week"),
) -> None:
    """N7's gate by hand, for an operator without the screen. The database refuses a printed sheet
    that cannot say who allowed it, so this is the only way it reaches a child."""
    with db.connect() as conn:
        out = assemble.approve(conn, section, week, kind, by)
        conn.commit()
    typer.echo(
        f"  {out['sheets']} sheets approved by {out['approved_by']}"
        f" — {out['named']} named, {out['spares']} spare"
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


@app.command()
def ratify(
    by: str = typer.Option(..., "--by", help="Who is ratifying — recorded on every row"),
    code: str = typer.Option("", "--code", help="One skill set; default every draft"),
) -> None:
    """Ratify skill-set specs (N1, W1 gate 1). Editing a spec later withdraws it again."""
    with db.connect() as conn:
        rows = spec.ratify(conn, by, code or None)
        conn.commit()
        left = conn.execute("select count(*) as n from skill_set where status = 'draft'").fetchone()["n"]
    for r in rows:
        typer.echo(f"  ratified  {r['code']:<22}v{r['version']:<3}{by}")
    typer.echo(f"  {len(rows)} ratified, {left} still draft")


def staff_hash(password: str, salt: str) -> str:
    """`scrypt$salt$hash` exactly as `apps/web/lib/auth.ts` checks it: node's `scryptSync` defaults
    (N=16384, r=8, p=1), 64 bytes, and the hex salt used as TEXT, not decoded — node takes a string
    salt as its UTF-8 bytes, and decoding it here would make every password look wrong."""
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1, dklen=64)
    return f"scrypt${salt}${digest.hex()}"


@app.command("set-password")
def set_password(email: str) -> None:
    """Set a staff member's sign-in password for the web app. Typed here, hidden, never stored in clear.

    The approval screen is behind a staff sign-in, and the only staff row had no password, so no
    one could get in to approve a paper. The password is asked for twice in the terminal and never
    echoed, logged or passed on a command line — it cannot end up in shell history or in anyone's
    chat. This only sets a password for someone already on the list; who is on the list is not a
    thing a command decides.
    """
    first = getpass.getpass("  New password (10+ characters, not shown): ")
    if len(first) < 10:
        raise typer.BadParameter("at least 10 characters")
    if getpass.getpass("  Once more: ") != first:
        raise typer.BadParameter("the two did not match — nothing changed")
    with db.connect() as conn:
        row = conn.execute("select value from config where key = 'app.staff'").fetchone()
        staff = row["value"] if row else []
        me = next((s for s in staff if s["email"].lower() == email.strip().lower()), None)
        if me is None:
            raise typer.BadParameter(f"{email} is not on the staff list — nothing changed")
        me["password"] = staff_hash(first, secrets.token_hex(16))
        conn.execute("update config set value = %s where key = 'app.staff'", (json.dumps(staff),))
        conn.commit()
    typer.echo(f"  password set for {me['name']} ({me['role']}) — sign in with {me['email']}")


@app.command("graph")
def graph_(
    child_id: str = typer.Option("", "--child", help="One child id; default every child with evidence"),
) -> None:
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
    """Score a prompt. item_generate: accepted ÷ returned. The reviewers: agreement with the
    hand-judged gold set in supabase/seed/validator_gold.json."""
    if purpose == spec.MISCONCEPTION_PROMPT:
        with db.connect() as conn:
            # One skill set per kind the engine knows, chosen by a row and not by a list in code: a
            # pure-arithmetic set (where code should cover everything and the model add nothing) and
            # an open-response set (where only the model can help). --only names one instead.
            codes = (
                [only]
                if only
                else [
                    r["code"]
                    for r in conn.execute(
                        "select distinct on (eval_type, has_words) code from ("
                        "  select code, eval_type, (formats && array['word_1step','word_2step']) as has_words"
                        "  from skill_set) x order by eval_type, has_words, code"
                    ).fetchall()
                ]
            )
            try:
                r = spec.evaluate_misconception_list(conn, codes)
            except LLMError as e:
                conn.commit()
                typer.echo(f"MODEL  {e}", err=True)
                raise typer.Exit(1)
            conn.commit()
        for row in r["rows"]:
            typer.echo(
                f"  {row['code']:<20}code covered {row['covered']:>2}"
                f"  ·  model: {row['proposed']} proposed, {row['new']} added,"
                f" {row['already']} already covered, {row['dropped']} thrown away,"
                f" {row['downgraded']} downgraded"
            )
        typer.echo(
            f"  {purpose}: {r['useful']} of the model's proposals survived as additions"
            f" over {len(r['rows'])} skill sets · {r['model']} · ₹{r['cost_inr']}"
        )
        return

    if purpose in review.REVIEWERS:
        gold = __import__("json").loads((db.REPO_ROOT / "supabase/seed/validator_gold.json").read_text())
        with db.connect() as conn:
            try:
                r = review.evaluate(conn, purpose, gold)
            except LLMError as e:
                conn.commit()
                typer.echo(f"MODEL  {e}", err=True)
                raise typer.Exit(1)
            conn.commit()
        for d in r["disagreements"]:
            typer.echo(
                f"  DISAGREED  {d['ref']:<5}person said {d['expected']:<7}"
                f"reviewer said {d['got']:<7}{d['text']}",
                err=True,
            )
        typer.echo(
            f"  {purpose}: agreed {r['agreed']}/{r['cases']} = {r['rate']}"
            f" · right reason {r['reason_agreed']}/{r['cases']}"
            f" · {r['model']} · {r['calls']} calls · ₹{r['cost_inr']}"
        )
        return
    if purpose != "item_generate":
        raise typer.BadParameter(
            f"no eval for {purpose!r}; try item_generate, {' or '.join(review.REVIEWERS)}"
        )
    total_ok = total = 0
    with db.connect() as conn:
        sets = conn.execute("select code, difficulty from skill_set order by code").fetchall()
        for s in sets:
            if only and s["code"] != only:
                continue
            for d in s["difficulty"]:
                counts, reasons, _ = bank.fill(conn, s["code"], d, n, dry_run=True)
                ok, ret = counts.get("accepted", 0), counts.get("returned", 0)
                total_ok += ok
                total += ret
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
