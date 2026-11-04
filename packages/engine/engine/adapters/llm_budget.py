"""The hard stop on a campaign's spend (goals/m1-11-k2-complete-v1.yaml).

A campaign is a row of `llm.campaigns`: the purposes a piece of work spends on, a cap in US dollars, a safety margin and
the rupees to a dollar `llm.prices` was written at. Before any call whose purpose is in a campaign, `check` adds up what
those purposes have already cost (every call leaves a `flow_run` row with its cost) and refuses once the total reaches the
cap less the margin. The margin is what calls in flight at that moment can still add. A total that may be missing a
call is not a total, so a call that answered with no cost recorded, or one left running past `llm.stale_minutes`
(a threshold row), stops the campaign too, until a person has looked.
"""


class Refused(Exception):
    """The campaign's money is spent, or cannot be counted."""


def campaigns(conn) -> dict:
    row = conn.execute("select value from config where key = 'llm.campaigns'").fetchone()
    return (row or {}).get("value") or {}


def purposes(camps: dict) -> list[str]:
    """Every purpose some campaign spends on: these answer to their campaign's cap, not to the daily budget."""
    return sorted({p for c in camps.values() for p in c["purposes"]})


def trigger_for(stage: str | None) -> str:
    """What a call leaves in flow_run.trigger: the writer (the adapter) and the readers here share this one form."""
    return f"engine:{stage}" if stage else "engine"


def check(conn, tenant_slug: str, purpose: str, stage: str | None = None, camps: dict | None = None) -> None:
    for name, c in (campaigns(conn) if camps is None else camps).items():
        if purpose in c["purposes"]:
            _check_one(conn, tenant_slug, name, c)
            if stage:
                _check_stage(conn, tenant_slug, name, c, stage)


def _check_stage(conn, tenant_slug: str, name: str, c: dict, stage: str) -> None:
    """A stage (dev eval, held-out score, the drafting) is one share of the campaign's money, tagged on each flow_run."""
    stages = c.get("stages") or {}
    if stage not in stages:
        raise Refused(
            f"campaign {name} has no stage called {stage} (its stages: {', '.join(stages) or 'none'})"
        )
    if stages[stage] is None:
        return  # no cap of its own: the campaign's holds
    spent = _spent(conn, tenant_slug, c["purposes"], trigger_for(stage))
    spent_usd, limit_usd = float(spent) / c["inr_per_usd"], stages[stage] - c.get("stage_margin_usd", 0)
    if spent_usd >= limit_usd:
        raise Refused(
            f"campaign {name} stage {stage} stopped: ${spent_usd:.2f} spent, at its limit of ${limit_usd:.2f}"
            f" (stage cap ${stages[stage]})"
        )


def _stale_minutes(conn) -> int:
    """How long a call may stay 'running' before its spend is counted as unknown (threshold llm.stale_minutes)."""
    row = conn.execute("select value from threshold where key = 'llm.stale_minutes'").fetchone()
    return int(row["value"]) if row else 10


def _check_one(conn, tenant_slug: str, name: str, c: dict) -> None:
    got = conn.execute(
        "select coalesce(sum(f.cost_inr), 0) as spent,"
        " count(*) filter (where f.status = 'ok' and f.cost_inr is null) as no_cost,"
        " count(*) filter (where f.status = 'running'"
        " and f.started_at < now() - make_interval(mins => %s)) as stuck"
        " from flow_run f join tenant t on t.id = f.tenant_id where t.slug = %s and f.flow = any(%s)",
        (_stale_minutes(conn), tenant_slug, c["purposes"]),
    ).fetchone()
    if got["no_cost"]:
        raise Refused(
            f"campaign {name} stopped: {got['no_cost']} calls answered with no cost recorded, so its spend is unknown"
        )
    if got["stuck"]:
        raise Refused(
            f"campaign {name} stopped: {got['stuck']} calls were left running, so its spend is unknown"
        )
    rate = c["inr_per_usd"]
    spent_usd, limit_usd = float(got["spent"]) / rate, c["cap_usd"] - c["margin_usd"]
    if spent_usd >= limit_usd:
        raise Refused(
            f"campaign {name} stopped: ${spent_usd:.2f} spent, at its limit of ${limit_usd:.2f}"
            f" (cap ${c['cap_usd']}, margin ${c['margin_usd']}); a person raises it in the config row llm.campaigns"
        )


def status(conn, tenant_slug: str, purpose: str, stage: str | None) -> dict | None:
    """Where a purpose's campaign stands, in dollars: the whole of it and, if a stage is named, the stage's share. None
    when no campaign spends on the purpose."""
    for name, c in campaigns(conn).items():
        if purpose not in c["purposes"]:
            continue
        rate, caps = c["inr_per_usd"], c.get("stages") or {}
        out = {
            "campaign": name,
            "spent_usd": _spent(conn, tenant_slug, c["purposes"]) / rate,
            "limit_usd": c["cap_usd"] - c["margin_usd"],
            "stage": stage,
            "stage_spent_usd": None,
            "stage_limit_usd": None,
        }
        if stage:
            out["stage_spent_usd"] = _spent(conn, tenant_slug, c["purposes"], trigger_for(stage)) / rate
            if caps.get(stage) is not None:
                out["stage_limit_usd"] = caps[stage] - c.get("stage_margin_usd", 0)
        return out
    return None


def line(got: dict | None) -> str:
    """The status as one line for a person watching the run."""
    if not got:
        return "no campaign spends on this"
    text = f"spent ${got['spent_usd']:.2f} of ${got['limit_usd']:.2f}"
    if got["stage"]:
        text += f"; stage {got['stage']} ${got['stage_spent_usd']:.2f}"
        text += (
            f" of ${got['stage_limit_usd']:.2f}"
            if got["stage_limit_usd"] is not None
            else " (the campaign's cap)"
        )
    return text


def _spent(conn, tenant_slug: str, purposes: list[str], trigger: str | None = None) -> float:
    row = conn.execute(
        "select coalesce(sum(f.cost_inr), 0) as spent from flow_run f join tenant t on t.id = f.tenant_id"
        " where t.slug = %s and f.flow = any(%s) and (%s::text is null or f.trigger = %s)",
        (tenant_slug, purposes, trigger, trigger),
    ).fetchone()
    return float(row["spent"])
