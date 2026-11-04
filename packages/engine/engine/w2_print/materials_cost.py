"""What the note-reading step has cost this month against its cap (task M1-16). Read from the calls already recorded in
`flow_run` (every model call leaves one with its tokens and cost); it never calls a model. The cap and the month are the
campaign's (`llm.campaigns`, the one that spends on `materials_read`). After the first real notes the averages replace the design note's assumed token
counts."""

from typing import Any

from engine.adapters import llm_budget
from engine.core import db
from engine.w2_print import materials_intake


def report(conn: db.Conn) -> dict[str, Any]:
    camp = llm_budget.campaign_for(conn, materials_intake.PURPOSE)
    if camp is None:
        raise LookupError(f"no campaign in llm.campaigns spends on {materials_intake.PURPOSE}")
    start = llm_budget.window_start(conn, camp)
    got = db.one(
        conn,
        "select count(*) as calls, count(*) filter (where f.status = 'error') as errors,"
        " count(*) filter (where f.status = 'running') as running,"
        " count(*) filter (where f.status = 'ok' and f.cost_inr is null) as cost_unknown,"
        " coalesce(sum(f.tokens_in), 0) as tokens_in, coalesce(sum(f.tokens_out), 0) as tokens_out,"
        " coalesce(sum(f.cost_inr), 0) as cost_inr, avg(f.tokens_in) as avg_in, avg(f.tokens_out) as avg_out"
        " from flow_run f join tenant t on t.id = f.tenant_id"
        " where t.slug = %s and f.flow = any(%s) and f.started_at >= %s::timestamptz",
        (db.tenant_slug(), camp["purposes"], start),
    )
    usd = float(got["cost_inr"]) / camp["inr_per_usd"]
    limit = camp["cap_usd"] - camp["margin_usd"]
    return {
        "calls": got["calls"],
        "errors": got["errors"],
        "running": got["running"],
        "cost_unknown": got["cost_unknown"],
        # the gate refuses once a call may be missing from the total (a call still running, or answered with no cost)
        "spend_known": not (got["running"] or got["cost_unknown"]),
        "tokens_in": int(got["tokens_in"]),
        "tokens_out": int(got["tokens_out"]),
        "cost_inr": float(got["cost_inr"]),
        "cost_usd": usd,
        "cap_usd": camp["cap_usd"],
        "limit_usd": limit,
        "share_of_limit": usd / limit if limit else 0,
        "avg_tokens_in": None if got["avg_in"] is None else round(float(got["avg_in"])),
        "avg_tokens_out": None if got["avg_out"] is None else round(float(got["avg_out"])),
    }
