"""`engine curriculum propose | review | apply | revert`: the curriculum mapping agents
(goals/m1-05-mapping-agents.yaml).

Every command is a dry run unless `--apply --by <email>` is given, as `engine curriculum k2` is; the email is looked up
by the engine (`staff_of_email`) and only the member of staff's id is kept, never a name. The activities people mapped
are split once: a dev set (`map.dev_count`) for tuning prompts, and the rest held out for the final score; the
proposer's examples come from the dev set only. `evaluate` has the agents map the held-out set blind; `engine eval
curriculum_map` (on the box) and `engine curriculum eval --recorded` score it against the bars
(`eval.curriculum_map.*`, engine/checks/evals.py). Nothing is applied until a run has met them. Without a model key
(this build container) every command takes `--recorded <file>`: replies a file holds, {purpose: {code: reply}}.
"""

import json
from pathlib import Path
from typing import cast

import typer

from engine.adapters.llm import LLMError
from engine.core import db
from engine.w1_bank import map_ledger
from engine.w1_bank.k2_upload import config, curriculum_app
from engine.w1_bank.map_agents import (
    Ask,
    Band,
    Proposal,
    Rules,
    model_ask,
    propose,
    propose_lo_skills,
    read_band,
    recorded_ask,
)
from engine.w1_bank.map_eval import Scored, score, split

PURPOSE = "curriculum_map"  # its bars: eval.curriculum_map.*
RECORDED = typer.Option(None, "--recorded", help="Replies a file holds, in place of the model (no key here)")
APPLY = typer.Option(False, "--apply", help="Write it. Without this, nothing is written")
BY = typer.Option("", "--by", help="The email of the member of staff running it; only their id is kept")


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


def staff_of(conn: db.Conn, by: str) -> db.Id:
    """The member of staff an email names, by id; refused when no one, or more than one, has it."""
    row = conn.execute("select public.staff_of_email(%s) as id", (by,)).fetchone()
    if not row or row["id"] is None:
        raise typer.BadParameter("no one member of staff has the email given to --by")
    return row["id"]


def _needs_by(write: bool, by: str) -> None:
    if write and not by.strip():  # before anything is read: every row keeps who made it
        raise typer.BadParameter("--by is required with --apply: every row keeps who made it")


def gold_split(conn: db.Conn, whole: Band) -> tuple[set[str], set[str]]:
    """(dev, held out) of the activities people mapped (a skill and an objective each)."""
    gold = {c for c in whole.person_skills if whole.objectives.get(c)}
    return split({c: whole.gaps[c].strand for c in gold}, int(map_ledger.rules(conn)["dev_count"]))


def _show(made: list[Proposal]) -> None:
    for p in made:
        typer.echo(
            f"  {p.status:<12} {p.kind:<9} {p.subject_code}  {json.dumps(p.proposal, ensure_ascii=False)}"
            + (f"  ({p.reason})" if p.reason else "")
        )
    counts = {s: sum(1 for p in made if p.status == s) for s in ("auto_passed", "needs_person", "rejected")}
    typer.echo(f"{len(made)} proposals: " + ", ".join(f"{n} {s}" for s, n in counts.items()))


@curriculum_app.command("propose")
def propose_(
    band: str = typer.Option(
        "", "--band", help="Default: the band of the K2 sheet (supabase/seed/k2_sheet.json)"
    ),
    recorded: Path | None = RECORDED,
    write: bool = APPLY,
    by: str = BY,
) -> None:
    """Propose for every gap of the band not already proposed, and record where each went."""
    _needs_by(write, by)
    with db.connect() as conn:
        tenant = _tenant(conn)
        staff = staff_of(conn, by) if write else None
        b, rules = read_band(conn, tenant, band or config()["band"]), _rules(conn, tenant)
        b.pool = frozenset(gold_split(conn, b)[0])
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
        ) as e:  # no active prompt (none is, until its eval meets the bars), no key, no recorded reply
            conn.commit()  # the flow_run rows: what was spent
            typer.echo(f"MODEL  {e}", err=True)
            raise typer.Exit(1) from e
        _show(made)
        if staff is not None:
            run = map_ledger.record(conn, tenant, made, staff)
            conn.commit()
            typer.echo(f"recorded as run {run}")
        else:
            typer.echo("dry run: nothing was written (add --apply --by <email> to record it)")


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
                map_ledger.settle(conn, tenant, decide, yes, staff_of(conn, by), why)
            except ValueError as e:
                raise typer.BadParameter(str(e)) from e
            conn.commit()
            typer.echo(f"{decide}: {'approved' if yes else 'rejected'}")
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
        tenant = _tenant(conn)
        done = map_ledger.apply(conn, tenant, staff_of(conn, by) if write else "", write)
        for d in done:
            typer.echo(f"  {d}")
        if write:
            conn.commit()
            typer.echo(f"applied {len(done)}")
        else:
            typer.echo(f"dry run: {len(done)} would be applied (add --apply --by <email>)")


@curriculum_app.command("revert")
def revert_(proposal: str, why: str = typer.Option(..., "--why"), write: bool = APPLY, by: str = BY) -> None:
    """Undo one applied proposal: its links removed, its level words emptied where still its own."""
    _needs_by(write, by)
    with db.connect() as conn:
        tenant = _tenant(conn)
        try:
            typer.echo(map_ledger.revert(conn, tenant, proposal, staff_of(conn, by) if write else None, why))
        except ValueError as e:
            raise typer.BadParameter(str(e)) from e
        if write:
            conn.commit()
        else:
            conn.rollback()
            typer.echo("dry run: nothing was written (add --apply --by <email>)")


def skills(p: Proposal) -> list[str]:
    """The skill codes a proposal names (none for a "none")."""
    raw = p.proposal.get("skills")
    return [str(s) for s in cast(list[object], raw)] if isinstance(raw, list) else []


def _blind(conn: db.Conn, ask: Ask, band: str, scored: set[str], pool: set[str]) -> list[Scored]:
    tenant = _tenant(conn)
    blind = read_band(conn, tenant, band, frozenset(scored))
    blind.pool = frozenset(pool - scored)
    made = [p for p in propose(blind, sorted(scored), ask, _rules(conn, tenant)) if p.kind == "skill"]
    return [Scored(p.subject_code, frozenset(skills(p)), p.status) for p in made]


def evaluate(conn: db.Conn, ask: Ask, band: str = "", dev: bool = False) -> dict[str, float]:
    """The held-out set mapped blind, its examples from the dev set, scored against what people linked. With `dev`
    (tuning a prompt) the dev set instead, in two halves, each half's examples the other's: an activity scored is
    never an example. Writes nothing."""
    band = band or config()["band"]  # the band is the sheet's row, never a code here (rule 1)
    whole: Band = read_band(conn, _tenant(conn), band)
    tune, held = gold_split(conn, whole)
    if dev:
        ranked = sorted(tune)
        a, b = set(ranked[::2]), set(ranked[1::2])
        runs, scored = [*_blind(conn, ask, band, a, b), *_blind(conn, ask, band, b, a)], tune
    else:
        runs, scored = _blind(conn, ask, band, held, tune), held
    return score(runs, {c: whole.person_skills[c] for c in scored})
