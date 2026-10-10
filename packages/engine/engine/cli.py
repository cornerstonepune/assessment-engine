"""engine — the operator's command line."""

import getpass
import hashlib
import json
import secrets

import typer

from engine.adapters.llm import LLMError
from engine.assess import graph
from engine.checks.cli_check import register as register_checks
from engine.checks.cli_live import live_app
from engine.core import asks, db, loaders, references
from engine.w1_bank import bank, mistake_guess, review, spec, story_shape
from engine.w1_bank.cli_bank import bank_app
from engine.w2_print.cli_library import library_app
from engine.w2_print.cli_week import week_app
from engine.w3_read.cli_gold import gold_app
from engine.w3_read.cli_legacy import legacy_app
from engine.w3_read.cli_read import read_app
from engine.w4_close import parent_report, parent_review
from engine.w4_close.cli_card import card_app
from engine.w4_close.cli_report import report_app

# every purpose `engine eval` scores, each against its bars (`checks.bars`)
EVALS = (
    parent_report.PURPOSE,
    parent_review.PURPOSE,
    spec.MISCONCEPTION_PROMPT,
    story_shape.PURPOSE,
    mistake_guess.PURPOSE,
    "week_skills",
    *review.REVIEWERS,
    "item_generate",
)

app = typer.Typer(help="Cornerstone assessment engine", no_args_is_help=True)
app.add_typer(bank_app, name="bank")
app.add_typer(week_app, name="week")
app.add_typer(legacy_app, name="legacy")
app.add_typer(read_app, name="read")
app.add_typer(live_app, name="live")
app.add_typer(library_app, name="library")
app.add_typer(gold_app, name="gold")
app.add_typer(card_app, name="card")
app.add_typer(report_app, name="report")
register_checks(app)


@app.callback()
def main() -> None:
    """Keeps subcommand mode on: with one command Typer would otherwise collapse it to the root."""


@app.command()
def ratify(
    by: str = typer.Option(..., "--by", help="Who is ratifying — recorded on every row"),
    code: str = typer.Option("", "--code", help="One skill set; default every draft"),
) -> None:
    """Ratify skill-set specs (N1, W1 gate 1). Editing a spec later withdraws it again."""
    with db.connect() as conn:
        rows = spec.ratify(conn, by, code or None)
        conn.commit()
        left = db.one(conn, "select count(*) as n from skill_set where status = 'draft'")["n"]
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


@app.command("asks")
def asks_(
    waiting: bool = typer.Option(False, "--open", help="Only the questions no one has answered yet"),
) -> None:
    """Every question the engine drafted for a person, and what they answered on the site: agreed, or corrected in
    their own words (goals/ny1-needs-you.yaml). `bin/update-live` prints it, so the next change starts from it."""
    with db.connect() as conn:
        lines = asks.report(conn, waiting)
    typer.echo("\n".join(lines) if lines else "  no questions")


@app.command("graph")
def graph_(
    child_id: str = typer.Option("", "--child", help="One child id; default every child with evidence"),
) -> None:
    """Rebuild Ring B — child_skill_state, and each question's item_stat — from confirmed evidence."""
    from engine.w1_bank import learn

    with db.connect() as conn:
        n = graph.rebuild(conn, child_id or None)
        questions = learn.item_stats(conn)
        conn.commit()
    typer.echo(f"  {n} states · {questions} questions with confirmed answers")


def _unanswered(r, n):
    """A Jev eval Jev did not answer fails and says why: with no key it used to score as nothing chosen, and pass."""
    if r["unanswered"]:
        typer.echo(f"JEV  not answered on {r['unanswered']} of {n}: {r['error']}", err=True)
        raise typer.Exit(1)


def _of(part: float, whole: float) -> float:
    return part / whole if whole else 0.0


def _held(purpose: str, scores: dict[str, float]) -> None:
    """An eval's scores against its bars, rows in `threshold` (`checks.bars`): it exits 1 below any bar, or with none
    on record (goals/p1-done-means-every-check.yaml)."""
    from engine.checks import bars

    with db.connect() as conn:
        missed = bars.short(scores, bars.bars(conn, purpose))
    for m in missed:
        typer.echo(f"  BELOW  {purpose}: {m}", err=True)
    if missed:
        raise typer.Exit(1)
    typer.echo(f"  {purpose}: every bar met")


def _eval_reviewer(purpose: str) -> None:
    """A reviewer's agreement with the hand-judged cases in supabase/seed/validator_gold.json, and each case it
    disagreed on."""
    gold = __import__("json").loads((db.REPO_ROOT / "supabase/seed/validator_gold.json").read_text())
    with db.connect() as conn:
        try:
            r = review.evaluate(conn, purpose, gold)
        except ValueError as e:  # no hand-judged case to score it against
            typer.echo(f"  {e}", err=True)
            raise typer.Exit(1)
        except LLMError as e:
            conn.commit()
            typer.echo(f"MODEL  {e}", err=True)
            raise typer.Exit(1)
        conn.commit()
    for d in r["disagreements"]:
        typer.echo(
            f"  DISAGREED  {d['ref']:<5}person said {d['expected']:<7}reviewer said {d['got']:<7}{d['text']}",
            err=True,
        )
    typer.echo(
        f"  {purpose}: agreed {r['agreed']}/{r['cases']} = {r['rate']}"
        f" · right reason {r['reason_agreed']}/{r['cases']}"
        f" · {r['model']} · {r['calls']} calls · ₹{r['cost_inr']}"
    )
    _held(purpose, {"agreed": r["rate"], "right_reason": _of(r["reason_agreed"], r["cases"])})


def _eval_item_generate(n: int, only: str) -> None:
    """item_generate: questions the validator accepted of those the model returned, per skill set and level."""
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
                worst = max(reasons, key=lambda k: reasons[k]) if reasons else "-"
                typer.echo(f"  {s['code']:<14}{d:<9}{ok:>3}/{ret:<3}  {worst}")
    typer.echo(f"  pass rate {total_ok}/{total} = {total_ok / total:.2f}" if total else "  nothing returned")
    _held("item_generate", {"pass_rate": _of(total_ok, total)})


@app.command("eval")
def eval_(
    purpose: str,
    n: int = typer.Option(10, "--n", help="Items asked per skill set × difficulty"),
    only: str = typer.Option("", "--only", help="One skill set code, else all"),
    version: int = typer.Option(
        0, "--version", help="parent_report: the prompt version to score, active or not"
    ),
    review_version: int = typer.Option(
        0, "--review-version", help="parent_report: the parent_review version that reads each draft"
    ),
    jev_version: int = typer.Option(
        0,
        "--jev-version",
        help="parent_review: the version of Jev's three questions that reads first (0: none)",
    ),
) -> None:
    """Score a prompt. item_generate: accepted ÷ returned. The reviewers: agreement with the
    hand-judged gold set in supabase/seed/validator_gold.json. parent_report: every child with signed-off answers,
    each draft held to its facts by code — the bar is all of them."""
    if purpose == parent_report.PURPOSE:
        with db.connect() as conn:
            try:
                r = parent_report.evaluate(conn, version or None, review_version=review_version or None)
            except LLMError as e:
                conn.commit()
                typer.echo(f"MODEL  {e}", err=True)
                raise typer.Exit(1)
            conn.commit()  # the flow_run rows: what the eval spent
        typer.echo(json.dumps(r, indent=2, ensure_ascii=False))
        typer.echo(
            f"parent_report v{version or 'active'}: {r['passed']}/{r['n']} held to their facts, {r['first_try']} first time"
        )
        return _held(purpose, {"held": _of(r["passed"], r["n"])})
    if purpose == parent_review.PURPOSE:
        with db.connect() as conn:
            try:
                r = parent_review.evaluate(conn, version or None, jev_version=jev_version or None)
            except LLMError as e:
                conn.commit()
                typer.echo(f"MODEL  {e}", err=True)
                raise typer.Exit(1)
            conn.commit()
        typer.echo(json.dumps(r, indent=2, ensure_ascii=False))
        typer.echo(
            f"parent_review v{version or '-'}, Jev v{jev_version or '-'}: {r['caught']}/{r['bad']} wrong sentences"
            f" caught, {r['false_flags']} flagged that were right, over {r['n']} drafts ({r['by_code']} by code first)"
            f" · the model read {r['read_by_model']} of {r['sentences']} sentences"
        )
        _unanswered(r, r["n"])
        return _held(purpose, {"caught": _of(r["caught"], r["bad"]), "flagged_right": r["false_flags"]})
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
        return _held(purpose, {"useful": r["useful"]})

    if purpose == story_shape.PURPOSE:
        with db.connect() as conn:
            r = story_shape.evaluate(conn)
            conn.commit()
        for m in r["misses"]:
            typer.echo(
                f"  {'LEFT' if m['got'] is None else 'MISS':<5} {m['text'][:60]}  wanted {m['want']}, {m['got'] or m['why']}"
            )
        typer.echo(
            f"  {purpose}: named {r['named']}/{r['n']}, the shape right on {r['right']} · one-step answers computed"
            f" {r['keyed']}, wrong {r['wrong_answer']} · left for a person {r['left']}"
        )
        _unanswered(r, r["n"])
        return _held(purpose, {"shape_right": _of(r["right"], r["n"]), "wrong_answers": r["wrong_answer"]})

    if purpose == mistake_guess.PURPOSE:
        with db.connect() as conn:
            r = mistake_guess.evaluate(conn, mistake_guess.gold())
            conn.commit()
        typer.echo(
            f"  {purpose}: the right mistake first {r['first']}/{r['cases']}, among the three {r['listed']}/{r['cases']}"
            f" · slips called NONE {r['slips_none']}/{r['slips']} · slips given a mistake {r['false_named']}"
        )
        _unanswered(r, r["cases"])
        return _held(
            purpose,
            {
                "first": _of(r["first"], r["cases"]),
                "listed": _of(r["listed"], r["cases"]),
                "slips_none": _of(r["slips_none"], r["slips"]),
                "false_named": r["false_named"],
            },
        )

    if purpose == "week_skills":
        from engine.w2_print import week_note

        with db.connect() as conn:
            r = week_note.evaluate(conn)
            conn.commit()
        for m in r["misses"]:
            typer.echo(f"  MISS  {m['note'][:70]}  wanted {m['want']}  ticked {m['got']}")
        typer.echo(
            f"  {purpose}: the exact skill sets on {r['exact']}/{r['n']} notes · precision {r['precision']}"
            f" · recall {r['recall']}"
        )
        _unanswered(r, r["n"])
        return _held(
            purpose, {"exact": _of(r["exact"], r["n"]), "precision": r["precision"], "recall": r["recall"]}
        )

    if purpose in review.REVIEWERS:
        return _eval_reviewer(purpose)
    if purpose != "item_generate":
        raise typer.BadParameter(f"no eval for {purpose!r}; there is one for {', '.join(EVALS)}")
    return _eval_item_generate(n, only)


@app.command()
def load(
    check: bool = typer.Option(False, "--check", help="Load twice and fail if anything moved"),
    settings: bool = typer.Option(False, "--settings", help="Only prompts, thresholds and config (a deploy)"),
) -> None:
    """Load the registry, ladder, levels, misconceptions, dimensions, prompts and thresholds."""
    if settings:
        for table, n in loaders.load_settings().items():
            typer.echo(f"  {table:<9}  {n:>5}")
        return
    counts = loaders.load_all()
    width = max(len(t) for t in counts)
    for table, n in counts.items():
        typer.echo(f"  {table:<{width}}  {n:>5}")

    bad = {k: v for k, v in references.orphans().items() if v}
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


@app.command()
def contract() -> None:
    """Write the website's list of the engine's routes (apps/web/lib/engine-routes.ts) from the engine itself:
    after a route or a request body changes, so the website's type check reads what the engine now serves."""
    from engine.api import contract as routes

    routes.OUT.write_text(routes.written(routes.spec()))
    typer.echo(f"  wrote {routes.OUT.relative_to(db.REPO_ROOT)}: {len(routes.routes(routes.spec()))} routes")


if __name__ == "__main__":
    app()
