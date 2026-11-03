"""`engine curriculum propose | review | apply | revert`: the curriculum mapping agents
(goals/m1-05-mapping-agents.yaml).

Every command is a dry run unless `--apply --by <name>` is given, as `engine curriculum k2` is. `evaluate` holds out
a share of what people mapped and has the agents map it blind; `engine eval curriculum_map` (on the box) and `engine
curriculum eval --recorded` score it against the bars (`eval.curriculum_map.*`, engine/checks/evals.py). Nothing is
applied until a run has met them. Without a model key (this build container) every command takes
`--recorded <file>`: replies a file holds, {purpose: {code: reply}}, in place of the model.
"""

import json
from pathlib import Path

import typer

from engine.adapters.llm import LLMError
from engine.core import db
from engine.w1_bank import map_ledger
from engine.w1_bank.k2_upload import curriculum_app
from engine.w1_bank.map_agents import (
    Ask,
    Band,
    Rules,
    model_ask,
    propose,
    propose_lo_skills,
    read_band,
    recorded_ask,
)
from engine.w1_bank.map_eval import Scored, held_out, score

PURPOSE = "curriculum_map"  # its bars: eval.curriculum_map.*
RECORDED = typer.Option(None, "--recorded", help="Replies a file holds, in place of the model (no key here)")
APPLY = typer.Option(False, "--apply", help="Write it. Without this, nothing is written")
BY = typer.Option("", "--by", help="Who is running it, kept on every row")


def _tenant(conn: db.Conn) -> db.Id:
    return db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]


def _ask(conn: db.Conn, recorded: Path | None) -> Ask:
    return recorded_ask(recorded) if recorded else model_ask(conn)


def _rules(conn: db.Conn, tenant: db.Id) -> Rules:
    r = map_ledger.rules(conn)
    return Rules(
        min_confidence=r["min_confidence"],
        audit_share=r["audit_share"],
        examples=int(r["examples"]),
        stopped=map_ledger.stopped(conn, tenant, r["audit_rejected_at_most"], r["audit_min_decided"]),
    )


def _needs_by(write: bool, by: str) -> None:
    if write and not by.strip():  # before anything is read: every row keeps who made it
        raise typer.BadParameter("--by is required with --apply: every row keeps who made it")


@curriculum_app.command("propose")
def propose_(
    band: str = typer.Option("K2", "--band"),
    recorded: Path | None = RECORDED,
    write: bool = APPLY,
    by: str = BY,
) -> None:
    """Propose for every gap of the band not already proposed, and record where each went."""
    _needs_by(write, by)
    with db.connect() as conn:
        tenant = _tenant(conn)
        b, rules = read_band(conn, tenant, band), _rules(conn, tenant)
        done = map_ledger.proposed(conn, tenant)
        todo = [
            c for c in sorted(b.gaps) if not any((k, c, "") in done for k in ("skill", "objective", "levels"))
        ]
        ask = _ask(conn, recorded)
        pairs = frozenset((c, s) for k, c, s in done if k == "lo_skill")
        try:
            made = [*propose(b, todo, ask, rules), *propose_lo_skills(b, ask, rules, pairs)]
        except (
            LLMError
        ) as e:  # no active prompt (none is until its eval meets the bars), no key, no recorded reply
            conn.commit()  # the flow_run rows: what was spent
            typer.echo(f"MODEL  {e}", err=True)
            raise typer.Exit(1) from e
        for p in made:
            typer.echo(
                f"  {p.status:<12} {p.kind:<9} {p.subject_code}  {json.dumps(p.proposal, ensure_ascii=False)}"
                + (f"  ({p.reason})" if p.reason else "")
            )
        counts = {
            s: sum(1 for p in made if p.status == s) for s in ("auto_passed", "needs_person", "rejected")
        }
        typer.echo(f"{len(made)} proposals: " + ", ".join(f"{n} {s}" for s, n in counts.items()))
        if write:
            run = map_ledger.record(conn, tenant, made, f"machine for {by.strip()}")
            conn.commit()
            typer.echo(f"recorded as run {run}")
        else:
            typer.echo("dry run: nothing was written (add --apply --by <name> to record it)")


@curriculum_app.command("review")
def review_(
    decide: str = typer.Option("", "--decide", help="The proposal a person is answering"),
    yes: bool = typer.Option(False, "--yes"),
    no: bool = typer.Option(False, "--no"),
    why: str = typer.Option("", "--why"),
    by: str = BY,
) -> None:
    """The person's list: everything waiting for a person, oldest first. With --decide, their yes or no."""
    with db.connect() as conn:
        tenant = _tenant(conn)
        if decide:
            if yes == no or not by.strip():
                raise typer.BadParameter("--decide takes one of --yes or --no, and --by")
            try:
                map_ledger.settle(conn, tenant, decide, yes, by.strip(), why)
            except ValueError as e:
                raise typer.BadParameter(str(e)) from e
            conn.commit()
            typer.echo(f"{decide}: {'approved' if yes else 'rejected'} by {by.strip()}")
            return
        rows = map_ledger.standing(conn, tenant, "needs_person")
        for r in rows:
            typer.echo(
                f"  {r['id']}  {r['kind']:<9} {r['subject_code']}  "
                f"{json.dumps(r['proposal'], ensure_ascii=False)}  ({r['reason']})"
            )
        typer.echo(f"{len(rows)} waiting for a person")


@curriculum_app.command("apply")
def apply_(write: bool = APPLY, by: str = BY) -> None:
    """Make every proposal that passed on its own or that a person approved."""
    _needs_by(write, by)
    with db.connect() as conn:
        done = map_ledger.apply(conn, _tenant(conn), by.strip(), write)
        for d in done:
            typer.echo(f"  {d}")
        if write:
            conn.commit()
            typer.echo(f"applied {len(done)}")
        else:
            typer.echo(f"dry run: {len(done)} would be applied (add --apply --by <name>)")


@curriculum_app.command("revert")
def revert_(proposal: str, why: str = typer.Option(..., "--why"), write: bool = APPLY, by: str = BY) -> None:
    """Undo one applied proposal: its links removed, its level words emptied where still its own."""
    _needs_by(write, by)
    with db.connect() as conn:
        try:
            typer.echo(map_ledger.revert(conn, _tenant(conn), proposal, by.strip() or "dry run", why))
        except ValueError as e:
            raise typer.BadParameter(str(e)) from e
        if write:
            conn.commit()
        else:
            conn.rollback()
            typer.echo("dry run: nothing was written (add --apply --by <name>)")


def evaluate(conn: db.Conn, ask: Ask, band: str = "K2") -> dict[str, float]:
    """The held-out share of what people mapped, mapped blind, scored against what they linked. Writes nothing."""
    tenant = _tenant(conn)
    whole: Band = read_band(conn, tenant, band)
    gold = {c: s for c, s in whole.person_skills.items() if whole.objectives.get(c)}
    hide = held_out({c: whole.gaps[c].strand for c in gold}, map_ledger.rules(conn)["holdout_share"])
    blind = read_band(conn, tenant, band, frozenset(hide))
    made = [p for p in propose(blind, sorted(hide), ask, _rules(conn, tenant)) if p.kind == "skill"]
    skills = {p.subject_code: frozenset(str(s) for s in p.proposal.get("skills") or []) for p in made}  # type: ignore[union-attr]
    return score([Scored(p.subject_code, skills[p.subject_code], p.status) for p in made], gold)
