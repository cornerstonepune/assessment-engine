"""The eval for the materials_read prompt (task M1-16; rules 2 and 7: a prompt is inactive until its score meets a bar a
person set before the first run). It runs the model on cases a person marked, passes what it answered through the same
check the engine uses (`materials_intake.check_reading`), and scores what code let through. Three measures:
`confirmed_wrong` (how many readings code confirmed that a person did not mark: a wrong item or quantity that would have
gone into a list; a count, the one that matters most), `found` (of what a person marked, the share confirmed) and `held_back_right`
(of the cases a person marked as needing a person, the share where nothing was confirmed)."""

import json
from collections.abc import Callable
from typing import Any

from engine.core import db
from engine.w2_print import materials_intake

PURPOSE = materials_intake.PURPOSE
GOLD = db.REPO_ROOT / "supabase" / "seed" / "materials_read_gold.json"


class NoGold(Exception):
    """There are no marked cases: nothing is scored and no model is called."""


def load_gold() -> list[dict[str, Any]]:
    return json.loads(GOLD.read_text())["cases"]


def score(
    cases: list[dict[str, Any]],
    catalogue: list[dict[str, Any]],
    ask: Callable[[str, list[dict[str, Any]]], dict[str, Any]],
) -> dict[str, float]:
    if not cases:
        raise NoGold("the gold set is empty: a person marks real requests first (D-028)")
    confirmed = wrong = marked = found = should_hold = held = 0
    for case in cases:
        want = {(e["item_code"], float(e["quantity"]), e["unit"]) for e in case["expect"]}
        answer = ask(case["note"], catalogue)
        got = {
            (r.item_code, float(r.quantity or 0), r.unit)
            for r in (
                materials_intake.check_reading(x, catalogue, case["note"])
                for x in answer.get("readings") or []
            )
            if r.status == "confirmed"
        }
        confirmed += len(got)
        wrong += len(got - want)
        marked += len(want)
        found += len(got & want)
        if not want:
            should_hold += 1
            held += 0 if got else 1
    return {
        "confirmed_wrong": float(wrong),
        "found": found / marked if marked else 1.0,
        "held_back_right": held / should_hold if should_hold else 1.0,
    }


def evaluate(conn: db.Conn, version: int | None = None) -> dict[str, float]:
    """Score prompt `version` (the active one by default) on the gold set, on the live catalogue."""
    tenant = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
    catalogue = materials_intake.catalogue(conn, tenant)
    return score(
        load_gold(),
        catalogue,
        lambda note, cat: materials_intake.ask_model(conn, note, cat, version=version),
    )
