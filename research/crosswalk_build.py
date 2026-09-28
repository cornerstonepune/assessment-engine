#!/usr/bin/env python3
"""Builds the curriculum crosswalk as rows shaped like ADR 0041's tables, from the documents in hand: NCF-SE 2023,
NCERT's learning outcomes (2017, 2019) and the Cambridge Primary frameworks (copies, until the school's own arrive).

Zone 1, what others say, is read from the importers' verified rows and never typed: every statement keeps its PDF
page. Zone 2 puts age at the centre (Nimish, 28 Sep: "What should the child be able to do at what age should be our
baseline"): each framework level carries the ages it prints, or says how they were worked out; each strand is a ladder
of one step per year of age; each of the school's objectives sits at its grade's age. Everything that is a judgement
lands as a claim that is proposed, not signed. The structure is read from docs/crosswalk/design.json. No model is
called.

python3 research/crosswalk_build.py      # writes docs/crosswalk/tables/*.json; exit 1 if a check fails
"""

import json
import sys
from pathlib import Path

import crosswalk_drafts
import crosswalk_views
from crosswalk_cambridge import fingerprint
from crosswalk_official import (
    cambridge,
    official_frameworks,
    official_levels,
    official_statements,
)
from spine_sources import fetch as fetch_official

R = Path(__file__).resolve().parents[1]
CW = R / "docs/crosswalk"
TABLES = CW / "tables"
SPINE = R / "docs/spine/sources"
REGISTRY = R / "supabase/seed/registry.json"
MADE = json.loads((CW / "design.json").read_text())[
    "made"
]  # the day the design's rules were proposed


def claim(claims, kind, key, rationale, rule=None, prompt=None, made=None):
    """A proposed claim: who or what proposed it, when, and why. Nobody has decided it. `made` is the date the
    proposal was made (the design's or the draft's), so a rebuild writes the same rows."""
    cid = f"{kind}:{key}"
    claims.append(
        {
            "id": cid,
            "kind": kind,
            "proposed_by": None,
            "prompt_purpose": prompt,
            "prompt_version": 1 if prompt else None,
            "rule": rule,
            "rationale": rationale,
            "created_at": made or MADE,
        }
    )
    return cid


def ladders(design, objectives, claims):
    """The progressions, one step per year of age, and each school objective at its grade's age on its strand."""
    progressions = [
        {
            "code": p["code"],
            "subject": p["subject"],
            "strand": p["strand"],
            "cambridge_strands": p["cambridge_strands"],
        }
        for p in design["progressions"]
    ]
    steps = []
    lo, hi = design["steps"]["from_age"], design["steps"]["to_age"]
    for p in progressions:
        for age in range(lo, hi + 1):
            code = f"{p['code']}.{age}"
            steps.append(
                {
                    "progression_code": p["code"],
                    "ord": age - lo + 1,
                    "code": code,
                    "age_from": age,
                    "age_to": age + 1,
                    "claim_id": claim(
                        claims,
                        "progression_step",
                        code,
                        f"{p['strand']}, the step for ages {age} to {age + 1}. "
                        + design["steps"]["rule"],
                        rule="research/crosswalk_build.py: one step per year of age",
                    ),
                }
            )
    subject_of = {name: s["code"] for s in design["subjects"] for name in s["school"]}
    single = {}
    for p in progressions:
        single.setdefault(p["subject"], []).append(p["code"])
    placed, waiting = [], []
    first = design["grade_age"]["grade_1_from"]
    for o in objectives:
        if not o["band"].startswith("G"):
            continue
        subject = subject_of[o["subject"]]
        units = design["unit_strand"].get(o["subject"], {})
        strand = (
            single[subject][0] if len(single[subject]) == 1 else units.get(o["unit"])
        )
        if strand is None:
            waiting.append(
                {
                    "lo_code": o["code"],
                    "subject": subject,
                    "unit": o["unit"],
                    "title": o["title"],
                }
            )
            continue
        age = first + int(o["band"][1:]) - 1
        how = (
            "its subject has one strand"
            if len(single[subject]) == 1
            else f"its unit, {o['unit']}, is {strand}"
        )
        placed.append(
            {
                "lo_code": o["code"],
                "progression_code": strand,
                "step_code": f"{strand}.{age}",
                "claim_id": claim(
                    claims,
                    "objective_step",
                    o["code"],
                    f"Grade {o['band'][1:]} is ages {age} to {age + 1} ({design['grade_age']['rule']}); {how}. "
                    "The drafting method checks each objective's strand.",
                    rule="research/crosswalk_build.py: at its grade's age, on its unit's strand",
                ),
            }
        )
    return progressions, steps, placed, waiting


def school(design):
    """The signatory, the graduate profile's capabilities and the rubric scale."""
    s = design["signatory"]
    signatory = [
        {
            "subject": s["subject"],
            "educator": s["educator"],
            "valid_from": s["valid_from"],
            "valid_to": None,
        }
    ]
    spine = json.loads((R / "docs/spine/spine.json").read_text())
    capability = [
        {"code": n["id"].removeprefix("cap."), "label": n["label"], "text": n["text"]}
        for n in spine["nodes"]
        if n["layer"] == "capability"
    ]
    scale = design["rubric"]["scale"]
    rubric_scale = [
        {
            "code": scale["code"],
            "name": scale["name"],
            "status": design["rubric"]["status"],
        }
    ]
    rubric_level = [
        {"scale_code": scale["code"], **level} for level in design["rubric"]["levels"]
    ]
    return signatory, capability, rubric_scale, rubric_level


def public(tables):
    """The tables as this public repository keeps them: a framework whose words may not be republished keeps each
    statement's place and the fingerprint of its words, not the words (headings of strands stay)."""
    closed = {f["code"] for f in tables["framework"] if f.get("text_in_repo") is False}
    rows = []
    for s in tables["framework_statement"]:
        if s["framework_code"] in closed and s["kind"] not in ("strand", "substrand"):
            s = {
                **s,
                "text": None,
                "items": len(s["items"]),
                "text_sha256": fingerprint(s),
            }
        rows.append(s)
    return {**tables, "framework_statement": rows}


def write(name, rows):
    """One row per line, so a change to one row is one line of the diff."""
    TABLES.mkdir(parents=True, exist_ok=True)
    body = ",\n".join(json.dumps(r, ensure_ascii=False) for r in rows)
    (TABLES / f"{name}.json").write_text(f"[\n{body}\n]\n")


def main():
    from crosswalk_checks import check

    design = json.loads((CW / "design.json").read_text())
    sources = json.loads((CW / "sources.json").read_text())
    objectives = json.loads(REGISTRY.read_text())["learning_objectives"]
    frameworks, documents = official_frameworks(
        json.loads((SPINE / "official_documents.json").read_text())
    )
    fetch_official()  # the official copies, each checked against its recorded fingerprint
    levels, statements = official_levels(design), official_statements()
    cf, cd, cl, cs = cambridge(sources)
    frameworks, documents, levels, statements = (
        frameworks + cf,
        documents + cd,
        levels + cl,
        statements + cs,
    )
    claims = []
    progressions, steps, placed, waiting = ladders(design, objectives, claims)
    signatory, capability, rubric_scale, rubric_level = school(design)
    tables = {
        "framework": frameworks,
        "framework_document": documents,
        "framework_level": levels,
        "framework_statement": statements,
        "progression": progressions,
        "progression_step": steps,
        "objective_step": placed,
        "objective_waiting": waiting,
        "signatory": signatory,
        "capability": capability,
        "rubric_scale": rubric_scale,
        "rubric_level": rubric_level,
        "claim": claims,
        "claim_decision": [],
    }
    faults = check(tables, objectives)
    for draft in crosswalk_drafts.drafts():
        faults += [
            f"{draft['step']}: {f}" for f in crosswalk_drafts.check(draft, tables)
        ]
        rows = crosswalk_drafts.claims(
            draft, tables, lambda *a, **k: claim(claims, *a, **k, made=draft["drafted"])
        )
        for name, more in rows.items():
            tables.setdefault(name, []).extend(more)
    decisions = sorted((CW / "decisions").glob("*.json"))
    tables["claim_decision"] = [
        d for path in decisions for d in json.loads(path.read_text())
    ]
    faults += check(tables, objectives) if decisions else []
    for name, rows in public(tables).items():
        write(name, rows)
    views = CW / "views"
    views.mkdir(parents=True, exist_ok=True)
    for name, rows in crosswalk_views.build(tables, design).items():
        (views / f"{name}.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=1) + "\n"
        )
    for name, rows in tables.items():
        print(f"{name}: {len(rows)}")
    for f in faults:
        print("FAULT:", f)
    return 1 if faults else 0


if __name__ == "__main__":
    sys.exit(main())
