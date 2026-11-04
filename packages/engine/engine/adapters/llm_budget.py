"""The hard stop on a campaign's spend (goals/m1-11-k2-complete-v1.yaml).

A campaign is a row of `llm.campaigns`: the purposes a piece of work spends on, a cap in US dollars, a safety margin and
the rupees to a dollar `llm.prices` was written at. Before any call whose purpose is in a campaign, `check` adds up what
those purposes have already cost (every call leaves a `flow_run` row with its cost) and refuses once the total reaches the
cap less the margin. The margin is what calls in flight at that moment can still add. A total that may be missing a
call is not a total, so a call that answered with no cost recorded, or one left running past ten minutes, stops the
campaign too, until a person has looked.
"""

STALE = "10 minutes"


class Refused(Exception):
    """The campaign's money is spent, or cannot be counted."""


def campaigns(conn) -> dict:
    row = conn.execute("select value from config where key = 'llm.campaigns'").fetchone()
    return (row or {}).get("value") or {}


def purposes(conn) -> list[str]:
    """Every purpose some campaign spends on: these answer to their campaign's cap, not to the daily budget."""
    return sorted({p for c in campaigns(conn).values() for p in c["purposes"]})


def check(conn, tenant_slug: str, purpose: str, stage: str | None = None) -> None:
    for name, c in campaigns(conn).items():
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
    spent = conn.execute(
        "select coalesce(sum(f.cost_inr), 0) as spent from flow_run f join tenant t on t.id = f.tenant_id"
        " where t.slug = %s and f.flow = any(%s) and f.trigger = %s",
        (tenant_slug, c["purposes"], f"engine:{stage}"),
    ).fetchone()["spent"]
    spent_usd, limit_usd = float(spent) / c["inr_per_usd"], stages[stage] - c.get("stage_margin_usd", 0)
    if spent_usd >= limit_usd:
        raise Refused(
            f"campaign {name} stage {stage} stopped: ${spent_usd:.2f} spent, at its limit of ${limit_usd:.2f}"
            f" (stage cap ${stages[stage]})"
        )


def _check_one(conn, tenant_slug: str, name: str, c: dict) -> None:
    got = conn.execute(
        "select coalesce(sum(f.cost_inr), 0) as spent,"
        " count(*) filter (where f.status = 'ok' and f.cost_inr is null) as no_cost,"
        f" count(*) filter (where f.status = 'running' and f.started_at < now() - interval '{STALE}') as stuck"  # noqa: S608
        " from flow_run f join tenant t on t.id = f.tenant_id where t.slug = %s and f.flow = any(%s)",
        (tenant_slug, c["purposes"]),
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
