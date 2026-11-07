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

from engine.adapters import llm_budget
from engine.adapters.llm import LLMError
from engine.core import db
from engine.w1_bank import map_ledger, map_why
from engine.w1_bank import map_probe as map_probe_mod
from engine.w1_bank import map_replay as map_replay_mod
from engine.w1_bank.k2_upload import config, curriculum_app
from engine.w1_bank.map_agents import (
    PROPOSE,
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


def _ask(
    conn: db.Conn,
    recorded: Path | None,
    propose_version: int | None = None,
    stage: str | None = None,
    validate_version: int | None = None,
) -> Ask:
    return recorded_ask(recorded) if recorded else model_ask(conn, propose_version, validate_version, stage)


def estimate(conn: db.Conn, gaps: int) -> tuple[int, float | None, int]:
    """(gaps, dollars a proposer call has cost on average, calls that average is taken from). Reads only."""
    camp = llm_budget.campaign_for(conn, PROPOSE)
    got = db.one(
        conn,
        "select count(*) as calls, avg(cost_inr) as inr from flow_run where flow = %s and cost_inr is not null",
        (PROPOSE,),
    )
    if not got["calls"] or camp is None:
        return gaps, None, 0
    return gaps, float(got["inr"]) / camp["inr_per_usd"], got["calls"]


def estimate_line(gaps: int, per_call: float | None, calls: int) -> str:
    if per_call is None:
        return f"{gaps} gaps to propose for; the cost of a call is not measured (none was paid for yet)"
    return (
        f"{gaps} gaps to propose for; about ${per_call:.4f} a proposer call over {calls} paid calls, "
        f"so about ${per_call * gaps:.2f} before any validator call"
    )


def _rules(conn: db.Conn, tenant: db.Id) -> Rules:
    r = map_ledger.rules(conn)
    return Rules(
        min_confidence=r["min_confidence"],
        audit_share=r["audit_share"],
        examples=int(r["examples"]),
        skill_confidence=r.get("skill_min_confidence"),
        from_examples=bool(r.get("require_examples", 0)),
        use_checker=bool(r.get("use_checker", 1)),
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
    stage: str = typer.Option("", "--stage", help="The campaign stage that pays for the calls"),
    version: int = typer.Option(0, "--version", help="The proposer's prompt version (0: the active one)"),
    validate_version: int = typer.Option(0, "--validate-version", help="The validator's (0: the active one)"),
    estimate_only: bool = typer.Option(False, "--estimate", help="Count the gaps and price them; no call"),
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
        if estimate_only:
            typer.echo(estimate_line(*estimate(conn, len(todo))))
            return
        ask = _ask(conn, recorded, version or None, stage or None, validate_version or None)
        pairs = frozenset((c, s) for k, c, s in done if k == "lo_skill")
        try:
            made = [
                *propose(b, todo, ask, rules, map_ledger.asked(conn, tenant)),
                *propose_lo_skills(b, ask, rules, pairs),
            ]
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


def _made(conn: db.Conn, ask: Ask, band: str, scored: set[str], pool: set[str]) -> list[Proposal]:
    tenant = _tenant(conn)
    blind = read_band(conn, tenant, band, frozenset(scored))
    blind.pool = frozenset(pool - scored)
    return [p for p in propose(blind, sorted(scored), ask, _rules(conn, tenant)) if p.kind == "skill"]


def _blind(conn: db.Conn, ask: Ask, band: str, scored: set[str], pool: set[str]) -> list[Scored]:
    return [
        Scored(p.subject_code, frozenset(skills(p)), p.status) for p in _made(conn, ask, band, scored, pool)
    ]


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


def replay_dev(conn: db.Conn, ask: Ask) -> tuple[list[Proposal], dict[str, frozenset[str]], Rules]:
    """The dev-set run of `evaluate`, with its proposals kept: (made, what people linked, the rules it decided by)."""
    band, tenant = config()["band"], _tenant(conn)
    whole = read_band(conn, tenant, band)
    tune, _ = gold_split(conn, whole)
    ranked = sorted(tune)
    a, b = set(ranked[::2]), set(ranked[1::2])
    made = [*_made(conn, ask, band, a, b), *_made(conn, ask, band, b, a)]
    return made, {c: whole.person_skills[c] for c in tune}, _rules(conn, tenant)


def replay_report(conn: db.Conn, gap_minutes: float, stage: str = "dev_eval") -> list[str]:
    """The latest stored run of a stage, read back. The dev run: its score as rebuilt, the counts by cause, each activity.
    The held-out run (which may have been cut short by its stage's cap): one line of counts for the activities it
    reached, with the precision of those that passed on their own and its interval."""
    calls = map_replay_mod.last_run(map_replay_mod.stored(conn, stage), gap_minutes)
    if not calls:
        raise ValueError(f"no stored run in {stage}: no reply was kept (it needs a run after M1-11c)")
    if stage == "held_out":
        return [json.dumps(_held_out_counts(conn, calls))]
    shown: dict[str, frozenset[str]] = {}
    ask, left = map_replay_mod.replaying(calls, shown)
    made, gold, rules = replay_dev(conn, ask)
    got = map_replay_mod.explain(made, gold, rules.min_confidence)
    scores = score([Scored(p.subject_code, frozenset(skills(p)), p.status) for p in made], gold)
    head = {"score": scores, "left_unread": {k: len(v) for k, v in left.items()}}
    summary = {
        **{k: v for k, v in got.items() if k != "rows"},
        **map_replay_mod.sweep(made, gold),
        **map_replay_mod.skill_split(made, gold, shown),
    }
    return [json.dumps(x, ensure_ascii=False, default=str) for x in (head, summary, *got["rows"])]


def _rebuilt(conn: db.Conn, calls: list) -> tuple[list[Proposal], Band, set[str], int, dict]:
    """The held-out run rebuilt for the activities that were answered (the run goes in code order and a cap may end
    it): (proposals, the band as people mapped it, the activities reached, how many were held out, replies unread)."""
    band, tenant = config()["band"], _tenant(conn)
    whole = read_band(conn, tenant, band)
    tune, held = gold_split(conn, whole)
    reached = held & {c[2] for c in calls if c[2]}
    ask, left = map_replay_mod.replaying(calls)
    return _made(conn, ask, band, reached, tune), whole, reached, len(held), left


def _held_out_counts(conn: db.Conn, calls: list) -> dict:
    made, whole, reached, held_total, left = _rebuilt(conn, calls)
    gold = {c: whole.person_skills[c] for c in reached}
    scores = score([Scored(p.subject_code, frozenset(skills(p)), p.status) for p in made], gold)
    return {
        **map_replay_mod.partial(made, gold, _rules(conn, _tenant(conn)).min_confidence, held_total),
        "score": scores,
        "left_unread": {k: len(v) for k, v in left.items()},
    }


def why_report(conn: db.Conn, gap_minutes: float) -> str:
    """The latest held-out run's passes in counts: by skills named, by confidence, where an added skill was linked."""
    calls = map_replay_mod.last_run(map_replay_mod.stored(conn, "held_out"), gap_minutes)
    if not calls:
        raise ValueError("no stored run in held_out: no reply was kept")
    made, whole, _, _, _ = _rebuilt(conn, calls)
    strand = {c: g.strand for c, g in whole.gaps.items()}
    return json.dumps(map_why.why(made, whole.person_skills, whole.names, strand))


@curriculum_app.command("map-replay")
def map_replay(
    gap_minutes: float = typer.Option(
        10.0, "--gap-minutes", help="A pause this long between calls ends a run"
    ),
    stage: str = typer.Option("dev_eval", "--stage", help="dev_eval (scored) or held_out (counts only)"),
) -> None:
    """Read back the latest dev-set run of the mapping agents from the replies flow_run kept: each activity's
    proposal against what people linked, why it did not pass on its own, the counts by cause. No model, no write."""
    with db.connect() as conn:
        conn.read_only = True
        try:
            lines = replay_report(conn, gap_minutes, stage)
        except ValueError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(1) from e
    for line in lines:
        typer.echo(line)


@curriculum_app.command("map-why")
def map_why_(
    gap_minutes: float = typer.Option(
        10.0, "--gap-minutes", help="A pause this long between calls ends a run"
    ),
) -> None:
    """What the proposals that passed on their own were like, from the held-out replies kept, in counts only.
    No model, no write."""
    with db.connect() as conn:
        conn.read_only = True
        try:
            typer.echo(why_report(conn, gap_minutes))
        except ValueError as e:
            typer.echo(str(e), err=True)
            raise typer.Exit(1) from e


@curriculum_app.command("map-probe")
def map_probe(
    version: int = typer.Option(0, "--version", help="The proposer's prompt version (0: the active one)"),
) -> None:
    """One call to the proposer, about one dev-set activity asked as the eval asks it, to see the vendor take the
    request. Prints the HTTP status and whether the reply passed the local check, and nothing else (the log is public).
    Spends one call from the campaign's `dev_eval` stage."""
    band_name, stage = config()["band"], "dev_eval"
    with db.connect() as conn:
        tenant = _tenant(conn)
        tune, _ = gold_split(conn, read_band(conn, tenant, band_name))
        code = sorted(tune)[0]
        blind = read_band(conn, tenant, band_name, frozenset({code}))
        blind.pool = frozenset(tune - {code})
        try:
            line = map_probe_mod.probe(
                blind, code, _rules(conn, tenant).examples, model_ask(conn, version or None, None, stage)
            )
        finally:
            conn.commit()  # the flow_run row: what the call spent and what it was told
    typer.echo(line)
