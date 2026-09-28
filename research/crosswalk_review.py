#!/usr/bin/env python3
"""The approval rows for one drafted step (ADR 0041, zone 4): each objective with what NCF-SE, Cambridge and NCERT say
and what we say, the outcome with its rubric lines, and the statements no objective covers, each row with the claims
a decision on it decides. research/crosswalk_sheet.py lays them out for Akanksha; research/crosswalk_decisions.py reads
her decisions back.
"""

import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
CW = R / "docs/crosswalk"
TABLES = CW / "tables"
OUT = R / "data/crosswalk_review"
WORDS = R / "data/crosswalk_statements"
RELATION = {
    "meets": "meets",
    "extends": "goes further than",
    "partly_meets": "partly meets",
    "prepares_for": "prepares for",
}


def load():
    """The tables, with Cambridge's words put back from data/ where this machine has them (they are not in git)."""
    t = {p.stem: json.loads(p.read_text()) for p in TABLES.glob("*.json")}
    local = {}
    for path in sorted(WORDS.glob("*.json")):
        book = json.loads(path.read_text())
        local |= {(book["framework"], o["code"]): o for o in book["objectives"]}
        # a note's code is its place among the notes, as research/crosswalk_official.py numbers them
        local |= {
            (book["framework"], f"note.{n['stage']}.{k}"): n
            for k, n in enumerate(book["notes"], 1)
        }
    for s in t["framework_statement"]:
        if s["text"] is None and (s["framework_code"], s["code"]) in local:
            o = local[(s["framework_code"], s["code"])]
            s["text"], s["items"] = o["text"], o.get("items", [])
    return t


def slug(step):
    return step.lower().replace(".", "-")


def said(t, framework, lo, brief=False):
    """What one framework says for an objective: each aligned statement with its relation and reason, or why none.
    Brief: a plain "meets" carries no reason, and a statement's words are left to the list at the end."""
    statements = {(s["framework_code"], s["code"]): s for s in t["framework_statement"]}
    reasons = {c["id"]: c["rationale"] for c in t["claim"]}
    lines = []
    for a in t["alignment"]:
        if a["lo_code"] == lo and a["framework_code"].startswith(framework):
            s = statements[(a["framework_code"], a["statement_code"])]
            where = (
                f"{s['printed_code'] or s['code']}, {s['level_code']}, p{s['pdf_page']}"
            )
            why = (
                ""
                if brief and a["relation"] == "meets"
                else f" Why: {reasons[a['claim_id']]}"
            )
            words = "" if brief == "codes" else f": “{whole(s)}”"
            lines.append(
                f"{RELATION[a['relation']].capitalize()} — {where}{words}{why}"
            )
    for n in t["no_alignment"]:
        if n["lo_code"] == lo and framework.startswith(
            {"NCF-SE": "NCF", "Cambridge": "CAM"}[n["framework_family"]]
        ):
            lines.append(f"Nothing at this age. {reasons[n['claim_id']]}")
    return "\n\n".join(lines) or "—"


def whole(s):
    if s["text"] is None:
        return "(the words are in the school's copy only; run research/crosswalk_cambridge.py)"
    return " ".join([s["text"], *s["items"]])


def rows(t, step, brief=False):
    """The sheet's rows, each with the claims a decision on it decides."""
    los = {
        o["code"]: o
        for o in json.loads((R / "supabase/seed/registry.json").read_text())[
            "learning_objectives"
        ]
    }
    caps = {c["code"]: c["label"] for c in t["capability"]}
    sets = {
        s["code"]: s["name"]
        for s in json.loads((R / "supabase/seed/skill_sets.json").read_text())[
            "skill_sets"
        ]
    }
    draft = json.loads((CW / "drafts" / f"{slug(step)}.json").read_text())
    by_lo = {}
    for name in (
        "lo_statement",
        "alignment",
        "no_alignment",
        "lo_capability",
        "skill_set_objective",
        "outcome_objective",
    ):
        for r in t[name]:
            if r["lo_code"] in {o["lo_code"] for o in draft["objectives"]}:
                by_lo.setdefault(r["lo_code"], []).append(r["claim_id"])
    placed = {p["lo_code"]: p["claim_id"] for p in t["objective_step"]}
    objectives = []
    for i, o in enumerate(draft["objectives"], 1):
        lo, school = o["lo_code"], los[o["lo_code"]]
        objectives.append(
            {
                "row": f"O{i:02}",
                "claims": [placed[lo], *by_lo[lo]],
                "cells": [
                    lo,
                    school["unit"],
                    school["title"],
                    o["what_we_say"],
                    said(t, "NCF", lo, brief),
                    said(t, "CAM", lo, brief),
                    said(t, "NCERT", lo, "codes" if brief else False),
                    ", ".join(
                        caps[c]
                        for c in (
                            o["capability"]["primary"],
                            o["capability"]["secondary"],
                        )
                        if c
                    ),
                    "\n".join(f"{s}: {sets[s]}" for s in o["skill_sets"]) or "none yet",
                    ", ".join(o["overlaps"]) or "—",
                    o.get("optional", ""),
                ],
            }
        )
    outcome = next(o for o in t["skill_outcome"] if o["code"] == step)
    stepped = next(s for s in t["progression_step"] if s["code"] == step)
    levels = {lv["code"]: lv for lv in t["rubric_level"]}
    rubric = [
        {
            "row": "R1",
            "claims": [stepped["claim_id"], outcome["claim_id"]],
            "cells": [
                "The outcome",
                outcome["text"],
                f"Ages {stepped['age_from']} to {stepped['age_to']}",
            ],
        }
    ]
    for i, d in enumerate(
        sorted(
            (d for d in t["rubric_descriptor"] if d["outcome_code"] == step),
            key=lambda d: levels[d["level_code"]]["ord"],
        ),
        2,
    ):
        lv = levels[d["level_code"]]
        rubric.append(
            {
                "row": f"R{i}",
                "claims": [d["claim_id"]],
                "cells": [
                    lv["label"],
                    d["text"],
                    f"Suggested when {lv['suggested_by']}; reported as {lv['reports_as']}",
                ],
            }
        )
    statements = {(s["framework_code"], s["code"]): s for s in t["framework_statement"]}
    reasons = {c["id"]: c["rationale"] for c in t["claim"]}
    gaps = [g for g in t["gap_proposal"] if g["step_code"] == step]
    gaps += [
        dict(e, proposal="leave_out")
        for e in t["exclusion"]
        if e["claim_id"].startswith(f"exclusion:{step}:")
    ]
    uncovered = []
    for i, g in enumerate(gaps, 1):
        s = statements[(g["framework_code"], g["statement_code"])]
        target = g.get("lo_code") or ""
        if target.startswith("new:"):
            target = f"the new objective proposed for {target.removeprefix('new:')}"
        detail = {
            "add_to": f"Add it to {target}",
            "new": f"A new objective: {g.get('what_we_say')}",
            "leave_out": "Leave it out at this step",
        }[g["proposal"]]
        uncovered.append(
            {
                "row": f"G{i:02}",
                "claims": [g["claim_id"]],
                "cells": [
                    f"{s['printed_code'] or s['code']} ({s['framework_code']}, {s['level_code']}, p{s['pdf_page']})",
                    whole(s),
                    detail,
                    reasons[g["claim_id"]],
                ],
            }
        )
    return objectives, rubric, uncovered
