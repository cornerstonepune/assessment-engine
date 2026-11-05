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


def forecast(conn: db.Conn, stage: str, pages: int, texts: int = 0) -> str:
    t = drafting_settings(conn)
    size = int(t["batch_pages"])
    prices = (conn.execute("select value from config where key = 'llm.prices'").fetchone() or {"value": {}})[
        "value"
    ]
    models = _models(conn)

    def inr(purpose: str, n: int, tin: str, tout: str) -> float:
        rate = prices.get(models.get(purpose, ""), {})
        return n * (t[tin] * rate.get("in", 0) + t[tout] * rate.get("out", 0)) / 1_000_000

    page = inr(DRAFT, pages, "est_draft_in", "est_draft_out") + inr(
        CHECK, pages, "est_check_in", "est_check_out"
    )
    share = t["est_revise_share"]  # the pages the checker finds a fault in: written and read once more
    cost = page * (1 + share) + inr(SPLIT, texts, "est_split_in", "est_split_out")
    cost += sum(
        inr(p, pages, "est_check_in", "est_check_out") for p in _shadows(conn)
    )  # read once, never revised
    status = llm_budget.status(conn, db.tenant_slug(), DRAFT, stage)
    rate = next(iter((llm_budget.campaigns(conn) or {"-": {"inr_per_usd": 88}}).values()))["inr_per_usd"]
    revised = math.ceil(pages * share / size)
    calls = 2 * math.ceil(pages / size) + 2 * revised + math.ceil(texts / int(t["batch_materials"]))
    worst = page * (int(t["batch_rounds"]) + 2) + inr(SPLIT, texts, "est_split_in", "est_split_out")
    # every page asked for again in every round, and every page revised
    return (
        f"forecast (token counts assumed, not measured): {pages} pages and {texts} materials texts"
        f" → about {calls} calls, about ${cost / rate:.2f}, up to ${worst / rate:.2f} if every page went round every time;"
        f" now {llm_budget.line(status)}; nothing was called"
    )
