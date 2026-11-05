"""Two checkers on the same drafts, side by side (goals/m1-12a-page-format.yaml, Nimish 2026-11-05).

A run can ask other checkers beside the one that drives the revision (config row k2.checkers). Each verdict is kept in the
ledger labelled by its model. This reads them back: how often they agree, whether the second finds every fault the first
does, and what each costs a page, so a person can choose which checks the rest. `summary` holds counts and costs and none
of the school's words (the log is public); `rows` and `to_csv` hold the words, for a person's browser only.
"""

import json
from typing import cast

import typer

from engine.adapters import llm_budget
from engine.core import db
from engine.w1_bank import k2_gold, map_ledger
from engine.w1_bank.k2_format import render
from engine.w1_bank.k2_upload import curriculum_app


def _pages(conn: db.Conn, tenant: db.Id, stage: str) -> list[dict]:
    """The newest drafted proposal of each page in this stage."""
    newest: dict[str, dict] = {}
    for p in map_ledger.standing(conn, tenant):  # oldest first
        if p["kind"] == "page_part" and p["proposal"].get("stage") == stage:
            newest[p["subject_code"]] = p
    return list(newest.values())


def _faults(check: dict) -> str:
    return " | ".join(f"{f['part']}: {f['reason']}" for f in check["faults"])


def _parts(check: dict) -> set[str]:
    return {f["part"] for f in check["faults"]}


def rows(conn: db.Conn, tenant: db.Id, stage: str) -> list[dict]:
    """One row a page that two checkers read: both verdicts and faults, the school's own words, the draft."""
    school = {
        r["code"]: r
        for r in conn.execute(
            "select a.code, a.name, a.objective, a.materials, coalesce((select array_agg(s.part) from activity_part_source s"
            " where s.tenant_id = a.tenant_id and s.activity_code = a.code and s.source = 'drafted'), '{}') as drafted"
            " from activity a where a.tenant_id = %s",
            (tenant,),
        ).fetchall()
    }
    out = []
    for p in _pages(conn, tenant, stage):
        checks = p["proposal"].get("checks") or []
        if len(checks) < 2:
            continue
        first, second = checks[0], checks[1]
        s = school.get(p["subject_code"])
        out.append(
            {
                "code": p["subject_code"], "activity": s["name"] if s else "",
                "first_model": first["model"], "first_verdict": first["verdict"], "first_faults": _faults(first),
                "second_model": second["model"], "second_verdict": second["verdict"], "second_faults": _faults(second),
                "verdicts_agree": "yes" if first["verdict"] == second["verdict"] else "no",
                "second_found_every_first_fault": "yes" if _parts(first) <= _parts(second) else "no",
                "school_objective": s["objective"].strip() if s and "objective" not in s["drafted"] else "",
                "school_materials": s["materials"].strip() if s else "",
                "draft_steps": render("steps", p["proposal"]["parts"]["steps"]) if "steps" in p["proposal"]["parts"] else "",
            }
        )  # fmt: skip
    return out


def summary(conn: db.Conn, tenant: db.Id, stage: str) -> dict:
    """Counts and costs only. The cost a page is the checker's own spend in this stage over the pages it read."""
    pages = [p for p in _pages(conn, tenant, stage) if len(p["proposal"].get("checks") or []) >= 2]
    n = len(pages)
    rate = next(iter((llm_budget.campaigns(conn) or {"-": {"inr_per_usd": 88}}).values()))["inr_per_usd"]
    limit = float(
        db.one(conn, "select value from config where key = 'k2.drafting'")["value"].get(
            "report_usd_per_page_limit", 0.02
        )
    )

    def spent(flow: str) -> float:
        got = conn.execute(
            "select coalesce(sum(cost_inr), 0) as n from flow_run where tenant_id = %s and flow = %s and trigger = %s",
            (tenant, flow, llm_budget.trigger_for(stage)),
        ).fetchone()
        return float(cast(dict, got)["n"])

    checkers: dict[str, dict] = {}
    for p in pages:
        for c in p["proposal"]["checks"]:
            purpose = c["checker"].rsplit(" v", 1)[0]
            checkers.setdefault(purpose, {"model": c["model"], "pages": 0, "disagree": 0})
            checkers[purpose]["pages"] += 1
            checkers[purpose]["disagree"] += c["verdict"] == "disagree"
    for purpose, c in checkers.items():
        c["usd_per_page"] = round(spent(purpose) / rate / n, 5) if n else 0.0
    maker = spent("k2_page_draft") / rate / n if n else 0.0
    total = maker + sum(c["usd_per_page"] for c in checkers.values())
    pairs = [(p["proposal"]["checks"][0], p["proposal"]["checks"][1]) for p in pages]
    return {
        "stage": stage, "pages": n, "inr_per_usd": rate, "checkers": checkers,
        "maker_usd_per_page": round(maker, 5), "usd_per_page": round(total, 5), "limit_usd_per_page": limit,
        "within_stop_rule": total <= limit,
        "pairs": {
            "verdicts_agree": sum(a["verdict"] == b["verdict"] for a, b in pairs),
            "verdicts_differ": sum(a["verdict"] != b["verdict"] for a, b in pairs),
            "found_every_fault": sum(_parts(a) <= _parts(b) for a, b in pairs),
            "missed_a_fault": sum(not _parts(a) <= _parts(b) for a, b in pairs),
            "found_more": sum(bool(_parts(b) - _parts(a)) for a, b in pairs),
        },
    }  # fmt: skip


to_csv = k2_gold.to_csv


@curriculum_app.command("checkers")
def checkers_cmd(stage: str = typer.Option("dev_eval", "--stage")) -> None:
    """The two checkers on the same drafts: agreement, whether the second finds every fault the first does, and the cost
    a page of each. Counts and money only; the words are in the staff download."""
    with db.connect() as conn:
        conn.read_only = True
        tenant = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
        typer.echo(json.dumps(summary(conn, tenant, stage)))
