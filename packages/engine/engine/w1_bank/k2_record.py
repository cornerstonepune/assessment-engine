"""`engine curriculum draft-record`: record the pages a style rule held back, from the drafts already paid for
(goals/m1-12p-advisory-rules.yaml).

Before the style rules became advisory (`k2.format.advisory_rules`) a page that broke one was left for a person and its
draft was only kept as a reply. Those kept drafts are read again with the rule as it is now; a page whose draft passes
is recorded in the ledger as the checker not having read it, with the notes of what it broke, and `apply` writes it as
a check-me draft. No model is called. The report is counts and rule names: the log is public.
"""

from collections import Counter

import typer

from engine.core import db
from engine.w1_bank import k2_batch as batch
from engine.w1_bank import k2_check, k2_replay, k2_shown, map_ledger
from engine.w1_bank.cli_map import BY, staff_of
from engine.w1_bank.k2_draft import wanted
from engine.w1_bank.k2_upload import config, curriculum_app

ALL_RUNS = (
    10_000_000.0  # minutes: no pause is long enough to end a run, so every kept reply of the stage is read
)


def record_kept(conn, tenant, staff, band, stage, kept, write, say) -> dict:
    """Each page still wanted whose kept draft the judge accepts now, recorded unread by the checker. `write`: false counts."""
    want, rows = wanted(conn, tenant, band, None)
    judge = k2_shown.judge_for(conn, rows)
    drafts = k2_replay.kept_drafts(kept, want, judge)
    good, _ = judge(list(drafts.values()), {k: want[k] for k in drafts}) if drafts else ({}, {})
    least = map_ledger.rules(conn)["min_confidence"]
    notes = getattr(judge, "notes", {})
    made = [
        k2_check.proposal(
            k, good[k], drafts[k], None, [{"round": 1, "recorded_from": "a kept draft"}], least, False,
            stage=stage, notes=notes.get(k), unread=True,
        )
        for k in sorted(good)
    ]  # fmt: skip
    if write and made:
        map_ledger.record(conn, tenant, made, staff)
    counts = Counter(batch.rule_of(n) for k in good for n in notes.get(k, []))
    out = {"recorded": len(made), "no_accepted_draft": len(want) - len(made), "notes": dict(counts)}
    say(
        f"{out['recorded']} pages recorded from kept drafts (no model call); {out['no_accepted_draft']} have none"
    )
    say(f"notes on them: {batch.line_of(counts)}")
    return out


@curriculum_app.command("draft-record")
def draft_record(
    stage: str = typer.Option(..., "--stage", help="The stage whose kept drafts are read"),
    by: str = BY,
    dry_run: bool = typer.Option(False, "--dry-run", help="Count and write nothing"),
) -> None:
    """Record the pages a style rule held back from the drafts already paid for. No model, no cost."""
    if not dry_run and not by.strip():
        raise typer.BadParameter("--by is required for a real run: every row keeps who ran it")
    with db.connect() as conn:
        tenant = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
        staff = None if dry_run else staff_of(conn, by)
        kept = k2_replay.stored(conn, stage, ALL_RUNS)
        record_kept(conn, tenant, staff, config()["band"], stage, kept, not dry_run, typer.echo)
        conn.commit()
