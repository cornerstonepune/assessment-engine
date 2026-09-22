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
from engine.core import db, loaders
from engine.w1_bank import bank, review, spec
from engine.w1_bank.cli_bank import bank_app
from engine.w2_print.cli_library import library_app
from engine.w2_print.cli_week import week_app
from engine.w3_read import place
from engine.w3_read.cli_gold import gold_app
from engine.w3_read.cli_legacy import legacy_app
from engine.w3_read.cli_read import read_app

app = typer.Typer(help="Cornerstone assessment engine", no_args_is_help=True)
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
    """Rebuild Ring B — child_skill_state — from confirmed evidence, and each old question's skill sets."""
    with db.connect() as conn:
        place.place(conn)
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
