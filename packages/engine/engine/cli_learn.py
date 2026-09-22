"""ADR 0032 — the reader learns: the notebook, the second reader, the report and the replay. Its own
module, registered onto `engine read` from `cli_read.py`, so that file stays one screen."""

import typer

from engine import db, profiles, replay, roster, second_reader
from engine.adapters import ocr


def _ids(conn, section, child):
    return [roster.find(conn, section, c, "engine-cli") for c in child] if child else None


def _pct(a, b):
    return f"{a / b:.0%}" if b else "—"


def read_profile(
    section: str = typer.Option("", "--section", help="with --child: the class"),
    child: list[str] = typer.Option(
        [], "--child", help="one child's first name; default every checked child"
    ),
) -> None:
    """Rebuild each checked child's notebook from every check a person has made, and say what it
    holds: how often the reader was right, the child's own confidence floor, the kinds routed to a
    person, the digits the reader confuses in this hand, and the samples the second reader sees."""
    with db.connect() as conn:
        ids = _ids(conn, section, child)
        n = profiles.rebuild(conn, ids)
        for line in profiles.lines(conn, ids):
            typer.echo("  " + line)
        conn.commit()
    typer.echo(f"  {n} children profiled")


def read_guess(
    section: str = typer.Option("", "--section"),
    child: list[str] = typer.Option([], "--child"),
    eval_: bool = typer.Option(
        False, "--eval", help="score the second reader on what people have typed; write nothing"
    ),
) -> None:
    """The second reader, shown each child's own handwriting, guesses what the first gave up on:
    every waiting answer gets its one-click guess. --eval scores it instead (rule 7)."""
    with db.connect() as conn:
        cfg = ocr.settings(conn)
        ids = _ids(conn, section, child)
        if eval_:
            t = second_reader.evaluate(conn, cfg, ids)
            conn.commit()  # the model calls are spend, recorded whatever the score
            for paper, k, want, guess, right in t["details"]:
                typer.echo(
                    f"    {paper:<14} {k:>4}  person said {want or '(blank)':<10} guessed {guess or '(blank)':<10} {'right' if right else 'WRONG'}"
                )
            for fmt, v in sorted(t["by_kind"].items()):
                typer.echo(
                    f"  {profiles.KIND_WORDS.get(fmt, fmt):<16} {v['right']} of {v['n']} ({_pct(v['right'], v['n'])})"
                )
            typer.echo(
                f"  {t['right']} of {t['n']} guessed right ({_pct(t['right'], t['n'])}) on what the reader gave up on"
                f" · model spend Rs {t['spend_inr']:.2f}"
            )
            return
        guessed, asked = second_reader.backfill(conn, cfg, ids)
        conn.commit()
    typer.echo(f"  {guessed} waiting answers given a guess, over {asked} questions")


def read_report() -> None:
    """How the reader is doing, from every check people have made: by kind of question (and its
    standing against the 95% gate), by batch, and per child."""
    with db.connect() as conn:
        r = profiles.report(conn)
    t = r["total"]
    typer.echo(
        f"\n  checked by a person {t['checked']} · reader right {t['right']} of {t['stood_behind']} it stood behind"
        f" ({_pct(t['right'], t['stood_behind'])}) · silently wrong {t['silently_wrong']} · gave up {t['gave_up']}"
        f" (guess right {t['guess_right']})\n"
    )
    typer.echo(
        f"  {'by kind':<18} {'checked':>7} {'right':>6} {'silent':>7} {'gave up':>8} {'last 50':>9}   standing"
    )
    for fmt, k in sorted(r["kinds"].items()):
        standing = (
            "trusted"
            if k["trusted"]
            else f"not trusted ({k['window_right']} of {k['window_n']}; needs 95% of 50)"
        )
        typer.echo(
            f"  {profiles.KIND_WORDS.get(fmt, fmt):<18} {k['checked']:>7} {k['right']:>6} {k['silently_wrong']:>7}"
            f" {k['gave_up']:>8} {_pct(k['window_right'], k['window_n']):>9}   {standing}"
        )
    typer.echo(f"\n  {'by batch (day read)':<18} {'read':>7} {'flagged':>8} {'checked':>8} {'right':>6}")
    for b in r["batches"]:
        typer.echo(
            f"  {str(b['batch']):<18} {b['read']:>7} {_pct(b['flagged'], b['read']):>8} {b['checked']:>8} {_pct(b['right'], b['stood_behind']):>6}"
        )
    typer.echo("")
    for line in r["children"] or ["(no notebooks yet: run `engine read profile`)"]:
        typer.echo("  " + line)
    typer.echo("")


def read_replay(
    section: str = typer.Option(..., "--section"),
    child: list[str] = typer.Option(..., "--child"),
    no_second: bool = typer.Option(
        False, "--no-second", help="leave the second reader out of the 'with' run"
    ),
) -> None:
    """The proof: each signed-off paper of the child read again without a notebook and with the
    notebook built from the child's other papers, both scored against what people confirmed."""
    with db.connect() as conn:
        ids = _ids(conn, section, child)
        report = replay.run(conn, ids, second=not no_second)
        conn.commit()  # the second reader's calls are spend
    for r in report:
        if "skipped" in r:
            typer.echo(f"  {r['paper']} {r['file']}: {r['skipped']}")
            continue
        nb = r["notebook"]
        typer.echo(f"\n  {r['paper']} · {r['file']} · {r['n']} answers people settled")
        typer.echo(
            f"    notebook from the child's other papers: {nb['checks']} checks · floor {nb['floor']}"
            f" · routes {', '.join(nb['route']) or 'none'} · confuses {', '.join(f'{k} ×{v}' for k, v in nb['confusions'].items()) or 'nothing'}"
            f" · {nb['samples']} samples"
        )
        for label in ("without", "with"):
            s = r[label]
            typer.echo(
                f"    {label + ' the notebook:':<22} right {s['right']:>2} · silently wrong {s['silently_wrong']:>2}"
                f" · flagged {s['flagged']:>2} (one click {s['one_click']}, typing {s['typing']})"
                + (f" · missing {s['missing']}" if s["missing"] else "")
            )
    a, b = replay.totals(report, "without"), replay.totals(report, "with")
    typer.echo(
        f"\n  all papers, {a['n']} answers — without the notebook: right {a['right']}, silently wrong {a['silently_wrong']},"
        f" one click {a['one_click']}, typing {a['typing']}"
        f"\n  {' ' * 21}with the notebook:    right {b['right']}, silently wrong {b['silently_wrong']},"
        f" one click {b['one_click']}, typing {b['typing']}\n"
    )


def register(read_app: typer.Typer) -> None:
    for name, fn in (
        ("profile", read_profile),
        ("guess", read_guess),
        ("report", read_report),
        ("replay", read_replay),
    ):
        read_app.command(name)(fn)
