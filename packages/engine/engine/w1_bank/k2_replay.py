"""Read back a draft run from the replies flow_run kept (goals/m1-12d-draft-replay.yaml).

The first dev run saved 1 page of 60: the rest failed the code checks, twice, and nothing said which rule. Every paid
reply is kept on its flow_run row; judging them again with the run's own judge, in the order they were paid for, says
how many pages broke which rule on which ask. No model is called and nothing is written. The report is counts and rule
names and nothing of the school's: the job log is public.
"""

import json
from collections import Counter

import typer

from engine.adapters import llm_budget
from engine.core import db
from engine.w1_bank import k2_batch as batch
from engine.w1_bank import map_replay
from engine.w1_bank.k2_draft import DRAFT, _judge, wanted
from engine.w1_bank.k2_upload import config, curriculum_app

Kept = tuple[str, object]  # (outcome, reply)


def stored(conn: db.Conn, stage: str, gap_minutes: float) -> list[Kept]:
    """The latest run's kept replies of the page maker in this stage, oldest first: a pause longer than `gap_minutes`
    between two calls ends a run."""
    rows = conn.execute(
        "select started_at, result->>'outcome' as outcome, result->'reply' as reply from flow_run"
        " where flow = %s and trigger = %s and result ? 'outcome' order by started_at",
        (DRAFT, llm_budget.trigger_for(stage)),
    ).fetchall()
    calls: list[map_replay.Call] = [
        (r["started_at"], DRAFT, "", r["outcome"], r["reply"] or {}, "") for r in rows
    ]
    return [(c[3], c[4]) for c in map_replay.last_run(calls, gap_minutes)]


def tally(kept: list[Kept], want: dict[str, list[str]], judge) -> dict:
    """Each kept reply judged again: for the nth time a page was answered, how many pages, how many good, and the rules
    the others broke. A refused reply is one the run took as nothing."""
    seen: Counter[str] = Counter()
    ever_good: set[str] = set()
    asks: dict[int, dict] = {}
    refused = 0
    for outcome, reply in kept:
        keys = [
            k
            for k in dict.fromkeys(
                it["key"] for it in batch.items(reply, "pages") if isinstance(it, dict) and "key" in it
            )
            if k in want
        ]
        if outcome == "refused" or not keys:
            refused += 1
            continue
        good, bad = judge(reply, {k: want[k] for k in keys})
        for k in keys:
            seen[k] += 1
            row = asks.setdefault(seen[k], {"attempt": seen[k], "asked": 0, "good": 0, "faults": Counter()})
            row["asked"] += 1
            if k in good:
                row["good"] += 1
                ever_good.add(k)
            else:
                row["faults"][batch.rule_of(bad.get(k, ""))] += 1
    return {
        "replies": len(kept),
        "refused": refused,
        "pages_good": len(ever_good),
        "pages_never_good": len(set(seen) - ever_good),
        "attempts": [{**a, "faults": dict(a["faults"].most_common())} for _, a in sorted(asks.items())],
    }


def lines(got: dict) -> list[str]:
    head = {k: got[k] for k in ("replies", "refused", "pages_good", "pages_never_good")}
    return [json.dumps(x) for x in (head, *got["attempts"])]


@curriculum_app.command("draft-replay")
def draft_replay(
    stage: str = typer.Option("dev_eval", "--stage", help="The stage whose latest draft run is read back"),
    gap_minutes: float = typer.Option(
        10.0, "--gap-minutes", help="A pause this long between calls ends a run"
    ),
) -> None:
    """Judge the kept replies of the latest draft run again: which rule each page broke on each ask. Counts and rule
    names only. No model, no write."""
    with db.connect() as conn:
        conn.read_only = True
        tenant = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
        kept = stored(conn, stage, gap_minutes)
        if not kept:
            typer.echo("no kept draft reply in this stage", err=True)
            raise typer.Exit(1)
        want, rows = wanted(conn, tenant, config()["band"], None)
        out = tally(kept, want, _judge(conn, rows))
    for line in lines(out):
        typer.echo(line)
