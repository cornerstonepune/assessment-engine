#!/usr/bin/env python3
"""Assembles the school's spine as one graph, docs/spine/spine.json: the imported and school layers
(research/spine_layers.py) plus the subject seats' crosswalks (research/spine_council/*.json), and checks it:
every edge names two nodes that exist; every NCF goal and competency feeds a capability; every competency has
grades; every NCERT outcome and school unit has a competency or a stated reason. No model is called.

python3 research/spine_build.py      # writes docs/spine/spine.json, prints the counts; exit 1 on a failed check
"""

import collections
import json
import sys

from spine_layers import R, SEATS, imported_layers

OUT = R / "docs/spine/spine.json"
SOURCES = [
    "NCF-SE 2023 (curricular goals and competencies, Part C)",
    "NCERT, Learning Outcomes at the Elementary Stage (2017)",
    "NCERT, Learning Outcomes at the Secondary Stage (2019)",
    "the school's skill map and learning-objective map (supabase/seed/registry.json)",
    "docs/school-os-level2-behaviours-draft.json (the 204 behaviours after the council)",
    "research/reports/Subject learning platforms survey.md",
]


def seat_files():
    return [
        d
        for p in sorted(SEATS.glob("*.json"))
        if isinstance(d := json.load(open(p)), dict) and "seat" in d
    ]


def add_crosswalks(g, seats):
    whys = {}
    for s in seats:
        by = "seat:" + s["seat"].replace("_followup", "")
        for x in s.get("competency_capabilities", []):
            for i, cap in enumerate(x["capabilities"]):
                g.edge(x["id"], f"cap.{cap}", "feeds", by, rank=i + 1)
        for x in s.get("competency_grades", []):
            for gr in x["grades"]:
                g.edge(f"grade.{gr}", x["id"], "expects", by)
            for lo_id in x.get("ncert", []):
                g.edge(lo_id, x["id"], "evidences", by)
        for section, kind in (
            ("ncert_competencies", "evidences"),
            ("unit_competencies", "builds_toward"),
        ):
            for x in s.get(section, []):
                for c in x["competencies"]:
                    g.edge(x["id"], c, kind, by)
                if not x["competencies"]:
                    whys[x["id"]] = x.get("why")
    mapped = {e["from"] for e in g.edges if e["kind"] in ("evidences", "builds_toward")}
    index = {n["id"]: n for n in g.nodes}
    for k, why in whys.items():
        if k not in mapped and k in index:
            index[k]["why"] = why


def check(g, seats):
    fails = [
        f"edge names a missing node: {e}"
        for e in g.edges
        if e["from"] not in g.ids or e["to"] not in g.ids
    ]
    outd, ind = collections.defaultdict(set), collections.defaultdict(set)
    for e in g.edges:
        outd[e["from"]].add(e["kind"])
        ind[e["to"]].add(e["kind"])
    if seats:
        for n in g.nodes:
            if n["layer"] in ("goal", "competency") and "feeds" not in outd[n["id"]]:
                fails.append(f"no capability: {n['id']}")
            if n["layer"] == "competency" and "expects" not in ind[n["id"]]:
                fails.append(f"no grade: {n['id']}")
            if (
                n["layer"] == "outcome"
                and "evidences" not in outd[n["id"]]
                and not n.get("why")
            ):
                fails.append(f"outcome without competency or reason: {n['id']}")
            if (
                n["layer"] == "unit"
                and "builds_toward" not in outd[n["id"]]
                and not n.get("why")
            ):
                fails.append(f"unit without competency or reason: {n['id']}")
    return fails


def main():
    g = imported_layers()
    seats = seat_files()
    add_crosswalks(g, seats)
    g.edges = list(
        {(e["from"], e["to"], e["kind"]): e for e in reversed(g.edges)}.values()
    )[::-1]
    fails = check(g, seats)
    notes = collections.defaultdict(list)
    for s in seats:
        notes[s["seat"].replace("_followup", "")] += s.get("notes", [])
    layers = collections.Counter(n["layer"] for n in g.nodes)
    bys = collections.Counter(e["by"].split(":")[0] for e in g.edges)
    names = sorted({s["seat"].replace("_followup", "") for s in seats})
    doc = {
        "built": "2026-09-26",
        "seats": names,
        "notes": notes,
        "layers": dict(layers),
        "edges_by": dict(bys),
        "sources": SOURCES,
        "nodes": g.nodes,
        "edges": g.edges,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    print(f"nodes {len(g.nodes)} · edges {len(g.edges)} · seats {names}")
    print("  layers:", dict(layers))
    print("  edges by:", dict(bys))
    if fails:
        print(f"FAILURES {len(fails)}")
        for f in fails[:40]:
            print("  ", f)
        return 1
    print(
        "every edge names two nodes that exist"
        + (
            "; every goal and competency feeds a capability; every competency has grades; every outcome and unit has a competency or a reason"
            if seats
            else " (no seats yet)"
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
