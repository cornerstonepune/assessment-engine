"""What a K2 drafting run will cost, before it runs (goals/m1-11-k2-complete-v1.yaml; M1-12a). The tokens per page are
ASSUMED numbers of a config row (k2.drafting) until a run has measured them; `forecast` says so. No call is made."""

import math

from engine.adapters import llm_budget
from engine.core import db, settings
from engine.w1_bank.k2_check import CHECK, DRAFT, SPLIT, VERSIONS


def drafting_settings(conn: db.Conn) -> dict[str, float]:
    """The drafting run's operational numbers (config row k2.drafting)."""
    row = db.one(
        conn, "select value from config where key = 'k2.drafting'"
    )  # a missing row is a failed deploy
    return {k: float(v) for k, v in row["value"].items()}


def _models(conn: db.Conn) -> dict[str, str]:
    """Each prompt purpose a run asks, with the model of the row it asks for."""
    out = {}
    for purpose, version in VERSIONS.items():
        row = conn.execute(
            "select model from prompt where purpose = %s and version = %s", (purpose, version)
        ).fetchone()
        out[purpose] = row["model"] if row else ""
    return out


def _shadows(conn: db.Conn) -> list[str]:
    """The other checkers a run asks beside the one that drives (config row k2.checkers); empty when it is off."""
    named = settings.config(conn, "k2.checkers").get("shadow", [])
    return [p for p in named if p in VERSIONS and p != CHECK]


def _per_call(conn: db.Conn, purpose: str, floor: int) -> tuple[float, int]:
    """The mean cost in rupees of one answered call of the prompt row a run asks for, and how many calls it is over; none
    (zero calls) while fewer than `floor` have been paid for."""
    got = conn.execute(
        "select avg(cost_inr) as mean, count(*) as n from (select cost_inr from flow_run where flow = %s"
        " and request ->> 'version' = %s and status = 'ok' and cost_inr is not null order by started_at desc limit 200) x",
        (purpose, str(VERSIONS[purpose])),
    ).fetchone()
    n = int(got["n"]) if got else 0
    return (float(got["mean"]), n) if got and n >= floor else (0.0, 0)


def _sent_back(conn: db.Conn, floor: int) -> tuple[float, int]:
    """The share of pages this maker drafted that a checker sent back (a second round on the ledger), and how many pages."""
    got = conn.execute(
        "select count(*) as n, count(*) filter (where jsonb_array_length(coalesce(proposal -> 'history', '[]')) > 1) as back"
        " from curriculum_proposal where kind = 'page_part' and about is null and proposer = %s",
        (f"{DRAFT} v{VERSIONS[DRAFT]}",),
    ).fetchone()
    n = int(got["n"]) if got else 0
    return (int(got["back"]) / n, n) if got and n >= floor else (0.0, 0)


def forecast(conn: db.Conn, stage: str, pages: int, texts: int = 0, reused: int = 0) -> str:
    t = drafting_settings(conn)
    size, floor = int(t["batch_pages"]), int(t.get("measured_min_calls", 5))
    prices = (conn.execute("select value from config where key = 'llm.prices'").fetchone() or {"value": {}})[
        "value"
    ]
    models, how = _models(conn), []

    def inr(purpose: str, n: int, tin: str, tout: str) -> float:
        """What `n` pages (or texts) cost at this purpose: from the calls made if there are enough, else assumed tokens."""
        mean, calls = _per_call(conn, purpose, floor)
        how.append(f"{purpose} measured over {calls} calls" if calls else f"{purpose} assumed")
        if calls:
            return mean * math.ceil(n / size)
        rate = prices.get(models.get(purpose, ""), {})
        return n * (t[tin] * rate.get("in", 0) + t[tout] * rate.get("out", 0)) / 1_000_000

    page = inr(DRAFT, pages - reused, "est_draft_in", "est_draft_out") + inr(
        CHECK, pages, "est_check_in", "est_check_out"
    )
    share, seen = _sent_back(conn, int(t.get("measured_min_pages", 20)))
    how.append(f"pages sent back measured over {seen} pages" if seen else "pages sent back assumed")
    share = (
        share if seen else t["est_revise_share"]
    )  # the pages the checker finds a fault in: written and read once more
    cost = page * (1 + share) + inr(SPLIT, texts, "est_split_in", "est_split_out")
    cost += sum(
        inr(p, pages, "est_check_in", "est_check_out") for p in _shadows(conn)
    )  # read once, never revised
    status = llm_budget.status(conn, db.tenant_slug(), DRAFT, stage)
    rate = next(iter((llm_budget.campaigns(conn) or {"-": {"inr_per_usd": 88}}).values()))["inr_per_usd"]
    revised = math.ceil(pages * share / size)
    calls = (
        math.ceil((pages - reused) / size)
        + math.ceil(pages / size)
        + 2 * revised
        + math.ceil(texts / int(t["batch_materials"]))
    )
    worst = page * (int(t["batch_rounds"]) + 2) + inr(SPLIT, texts, "est_split_in", "est_split_out")
    # every page asked for again in every round, and every page revised
    basis = (
        "token counts assumed, not measured"
        if all("assumed" in h for h in how)
        else "; ".join(dict.fromkeys(how))
    )
    return (
        f"forecast ({basis}): {pages} pages"
        + (f" ({reused} first drafts kept: no maker call for them)" if reused else "")
        + f" and {texts} materials texts"
        f" → about {calls} calls, about ${cost / rate:.2f}, up to ${worst / rate:.2f} if every page went round every time;"
        f" now {llm_budget.line(status)}; nothing was called"
    )
