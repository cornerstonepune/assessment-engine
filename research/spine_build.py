#!/usr/bin/env python3
"""Assembles the school's spine as one graph, docs/spine/spine.json, from the imported sources and the seats' crosswalks,
and checks it: every edge names two nodes that exist; every NCF competency has a capability and grades; every NCERT
outcome and every school unit has a competency or a stated reason. No model is called.

python3 research/spine_build.py            # writes docs/spine/spine.json and prints the counts; exit 1 on a failed check
"""

import collections
import json
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
SRC = R / "docs/spine/sources"
SEATS = R / "research/spine_council"
OUT = R / "docs/spine/spine.json"

WORDS = [
    (
        "capable",
        "knows things deeply and can do something with them; can find out what they do not know",
    ),
    (
        "kind",
        "notices other people and acts for them, including when it costs something",
    ),
    (
        "unafraid",
        "tries, asks, disagrees and shows their work in front of others, and treats a wrong answer as information",
    ),
]
STAGES = [
    (
        "foundational",
        "Foundational",
        "Nursery to Grade 2 · ages 3–8",
        ["N", "K1", "K2", "G1", "G2"],
    ),
    ("preparatory", "Preparatory", "Grades 3–5", ["G3", "G4", "G5"]),
    ("middle", "Middle", "Grades 6–8", ["G6", "G7", "G8"]),
    ("secondary", "Secondary", "Grades 9–10", ["G9", "G10"]),
]
GRADE_LABEL = {
    "N": "Nursery",
    "K1": "Junior KG",
    "K2": "Senior KG",
    **{f"G{i}": f"Grade {i}" for i in range(1, 11)},
}
SUBJECTS = {  # ncf subject / area -> subject node
    "foundational": ("foundational", "Foundational stage domains"),
    "mathematics": ("mathematics", "Mathematics"),
    "science": ("science", "Science"),
    "world-around-us": ("world-around-us", "The World Around Us"),
    "environmental-education": (
        "environmental-education",
        "Environmental Education (Grade 10)",
    ),
    "social-science": ("social-science", "Social Science"),
    "individuals-in-society": (
        "individuals-in-society",
        "Individuals in Society (Grade 9)",
    ),
    "art": ("art", "Art Education"),
    "physical-education": ("physical-education", "Physical Education and Well-being"),
    "vocational": ("vocational", "Vocational Education"),
    "language": ("language", "Language"),
}
NCERT_SUBJECT = {
    "math": "mathematics",
    "evs": "world-around-us",
    "sci": "science",
    "sst": "social-science",
    "eng": "language",
    "hpe": "physical-education",
    "art": "art",
}
UNIT_SUBJECT = {
    "Numeracy": "mathematics",
    "Science": "science",
    "Home Science": "science",
    "Global perspectives": "social-science",
    "Literacy": "language",
    "Literacy - English": "language",
    "Phonics": "language",
    "Literacy - Hindi": "language",
    "Literacy - Marathi": "language",
    "Visual Arts": "art",
    "Primary Computing": "computing",
    "Routines": "routines",
}
PLATFORMS = [  # from research/reports/Subject learning platforms survey.md: the products whose per-child export was opened
    (
        "ixl",
        "IXL",
        "mathematics",
        "per-skill CSV export; first choice for maths practice",
    ),
    (
        "khan",
        "Khan Academy",
        "mathematics",
        "free; per-skill export only on the Districts tier (250 licences)",
    ),
    ("mindspark", "Mindspark", "mathematics", "only against a signed per-child export"),
    ("codeorg", "Code.org", "computing", "exports levels for free"),
    ("lexia", "Lexia", "language", "reading, the tablet years; per-skill export"),
    ("quill", "Quill", "language", "sentence skills; per-skill export"),
    (
        "nmm",
        "No More Marking",
        "language",
        "the whole piece of writing, comparative judgement",
    ),
]


def main():
    nodes, edges = [], []
    seen = set()

    def node(id, layer, label, **kw):
        if id in seen:
            return
        seen.add(id)
        nodes.append({"id": id, "layer": layer, "label": label, **kw})

    def edge(a, b, kind, by, **kw):
        edges.append({"from": a, "to": b, "kind": kind, "by": by, **kw})

    # L0 words, stages, grades, subjects
    for w, meaning in WORDS:
        node(f"word.{w}", "word", w, text=meaning)
    for sid, name, sub, grades in STAGES:
        node(f"stage.{sid}", "stage", name, text=sub)
        for g in grades:
            node(f"grade.{g}", "grade", GRADE_LABEL[g], stage=sid)
            edge(f"stage.{sid}", f"grade.{g}", "has_grade", "school")
    for key, (sid, name) in SUBJECTS.items():
        node(f"subject.{sid}", "subject", name)
    node("subject.computing", "subject", "Computing (the school's own strand)")
    node("subject.routines", "subject", "Routines (not a subject)")
    # L1 capabilities, L2 behaviours
    draft = json.load(open(R / "docs/school-os-level2-behaviours-draft.json"))
    for c in draft["capabilities"]:
        node(
            f"cap.{c['capability_id']}",
            "capability",
            c["name"],
            text=c["observable_at_16"],
        )
        for s in c["stages"]:
            for b in s["behaviours"]:
                if b.get("status") == "retired":
                    continue
                bid = f"beh.{b['id']}"
                node(
                    bid,
                    "behaviour",
                    b["statement"],
                    text=b["adult_sees"],
                    counter=b["counter_example"],
                    stage=s["stage_id"],
                    capture=b["capture_mode"],
                    setting=b["setting"],
                    words=b["words"],
                    from_age=b.get("from_age"),
                    council=b.get("council", {}).get("outcome"),
                )
                edge(f"cap.{c['capability_id']}", bid, "shown_by", "council")
                edge(f"stage.{s['stage_id']}", bid, "at_stage", "council")
                for w in b["words"]:
                    edge(bid, f"word.{w}", "evidence_for", "council")
    # L3 NCF competencies (imported)
    ncf = json.load(open(SRC / "ncf_se_2023_competencies.json"))
    for e in ncf:
        nid = e["id"]
        node(
            nid,
            "goal" if e["kind"] == "CG" else "competency",
            e["text"],
            code=e["code"],
            subject=e["subject"],
            area=e.get("area"),
            stage=e["stage"],
            src="NCF-SE 2023",
        )
        edge(
            f"subject.{SUBJECTS[e['subject']][0]}",
            nid,
            "sets",
            "imported",
            src="NCF-SE 2023",
        )
        edge(f"stage.{e['stage']}", nid, "at_stage", "imported", src="NCF-SE 2023")
        if e["kind"] == "C":
            edge(e["cg"], nid, "has_competency", "imported", src="NCF-SE 2023")
    # L4 NCERT outcomes and the school's units (imported / school)
    lo = json.load(open(SRC / "ncert_learning_outcomes.json"))
    for e in lo:
        node(
            e["id"],
            "outcome",
            e["text"],
            subject=NCERT_SUBJECT[e["subject"]],
            grade=f"G{e['class']}",
            area=e.get("area"),
            src=e["src"],
        )
        edge(f"grade.G{e['class']}", e["id"], "expects", "imported", src=e["src"])
        edge(
            f"subject.{NCERT_SUBJECT[e['subject']]}",
            e["id"],
            "sets",
            "imported",
            src=e["src"],
        )
    units = json.load(open(SRC / "school_units.json"))
    for u in units:
        node(
            u["id"],
            "unit",
            u["unit"],
            subject=UNIT_SUBJECT[u["subject"]],
            school_subject=u["subject"],
            bands=u["bands"],
            objectives=u["n"],
            samples=u["samples"],
            src="the school's learning-objective map (registry.json, built 2026-09-15)",
        )
        for b in u["bands"]:
            edge(f"grade.{b}", u["id"], "taught_in", "school")
        edge(f"subject.{UNIT_SUBJECT[u['subject']]}", u["id"], "has_unit", "school")
    # L5 skills, rungs (the engine's ladder), and the school's own skill→NCF links
    reg = json.load(open(R / "supabase/seed/registry.json"))
    domains = {d["code"]: d["name"] for d in reg["domains"]}
    for k, v in reg["skills"].items():
        bands = sorted(
            {m["b"] for m in v.get("ms", [])},
            key=lambda b: ["PG", "N", "K1", "K2", "G1", "G2", "G3", "G4"].index(b),
        )
        node(
            f"skill.{k}",
            "skill",
            v["name"],
            text=v.get("desc", ""),
            domain=domains.get(k.split(".")[0]),
            type=v.get("type"),
            bands=bands,
            src="the school's skill map",
        )
        for c in re.findall(r"\b(C(?:G)?-\d+(?:\.\d+)?)", v.get("cg", "")):
            edge(
                f"skill.{k}",
                f"ncf.fnd.F.{c}",
                "evidences",
                "school",
                src="the school's skill map",
            )
        for b in bands:
            if b != "PG":
                edge(f"grade.{b}", f"skill.{k}", "tracked_in", "school")
    lo_skill = collections.defaultdict(set)
    for x in reg["learning_objective_skills"]:
        lo_skill[x["lo"]].add(x["skill"])
    unit_of = {}
    for x in reg["learning_objectives"]:
        unit_of[x["code"]] = next(
            (
                u["id"]
                for u in units
                if u["subject"] == x["subject"] and u["unit"] == x["unit"]
            ),
            None,
        )
    unit_skills = collections.defaultdict(set)
    for code, skills in lo_skill.items():
        if unit_of.get(code):
            unit_skills[unit_of[code]] |= skills
    for uid, skills in unit_skills.items():
        for sk in skills:
            if f"skill.{sk}" in seen:
                edge(
                    uid,
                    f"skill.{sk}",
                    "builds",
                    "school",
                    src="the school's learning-objective map",
                )
    for r in json.load(open(R / "supabase/seed/rungs.json"))["rungs"]:
        node(
            f"rung.{r['code']}",
            "rung",
            f"{r['code']} · {r['descriptor']}",
            band=r["band"],
            src="the engine's ladder (rungs.json)",
        )
        for sk in r.get("skill_codes", []):
            if f"skill.{sk}" in seen:
                edge(
                    f"rung.{r['code']}",
                    f"skill.{sk}",
                    "tests",
                    "school",
                    src="the engine's ladder",
                )
        edge(
            f"grade.{r['band']}", f"rung.{r['code']}", "at_grade", "school"
        ) if f"grade.{r['band']}" in seen else None
    for pid, name, subj, note in PLATFORMS:
        node(
            f"platform.{pid}",
            "platform",
            name,
            text=note,
            src="the platform survey, 2026-09-26",
        )
        edge(f"platform.{pid}", f"subject.{subj}", "practises", "survey")
    # the seats' crosswalks (generated)
    seat_files = sorted(SEATS.glob("*.json"))
    seats = [json.load(open(p)) for p in seat_files]
    for s in seats:
        by = f"seat:{s['seat']}"
        for x in s.get("competency_capabilities", []):
            for i, cap in enumerate(x["capabilities"]):
                edge(x["id"], f"cap.{cap}", "feeds", by, rank=i + 1)
        for x in s.get("competency_grades", []):
            for g in x["grades"]:
                edge(f"grade.{g}", x["id"], "expects", by)
            for lo_id in x.get("ncert", []):
                edge(lo_id, x["id"], "evidences", by)
        for x in s.get("ncert_competencies", []):
            for c in x["competencies"]:
                edge(x["id"], c, "evidences", by)
            if not x["competencies"]:
                nodes[[n["id"] for n in nodes].index(x["id"])]["why"] = x.get("why")
        for x in s.get("unit_competencies", []):
            for c in x["competencies"]:
                edge(x["id"], c, "builds_toward", by)
            if not x["competencies"]:
                nodes[[n["id"] for n in nodes].index(x["id"])]["why"] = x.get("why")
    notes = {s["seat"]: s.get("notes", []) for s in seats}
    # dedupe edges
    uniq = {}
    for e in edges:
        uniq.setdefault((e["from"], e["to"], e["kind"]), e)
    edges[:] = list(uniq.values())
    # checks
    ids = {n["id"] for n in nodes}
    fails = []
    for e in edges:
        if e["from"] not in ids or e["to"] not in ids:
            fails.append(f"edge names a missing node: {e}")
    outd = collections.defaultdict(set)
    ind = collections.defaultdict(set)
    for e in edges:
        outd[e["from"]].add(e["kind"])
        ind[e["to"]].add(e["kind"])
    comp = [n for n in nodes if n["layer"] == "competency"]
    goals = [n for n in nodes if n["layer"] == "goal"]
    if seats:
        for n in comp + goals:
            if "feeds" not in outd[n["id"]]:
                fails.append(f"no capability: {n['id']}")
        for n in comp:
            if "expects" not in ind[n["id"]]:
                fails.append(f"no grade: {n['id']}")
        for n in nodes:
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
    layers = collections.Counter(n["layer"] for n in nodes)
    bys = collections.Counter(e["by"].split(":")[0] for e in edges)
    doc = {
        "built": "2026-09-26",
        "seats": [s["seat"] for s in seats],
        "notes": notes,
        "layers": dict(layers),
        "edges_by": dict(bys),
        "sources": [
            "NCF-SE 2023 (curricular goals and competencies, Part C)",
            "NCERT, Learning Outcomes at the Elementary Stage (2017)",
            "NCERT, Learning Outcomes at the Secondary Stage (2019)",
            "the school's skill map and learning-objective map (supabase/seed/registry.json)",
            "docs/school-os-level2-behaviours-draft.json (the 204 behaviours after the council)",
            "research/reports/Subject learning platforms survey.md",
        ],
        "nodes": nodes,
        "edges": edges,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    print(
        f"nodes {len(nodes)} · edges {len(edges)} · seats {[s['seat'] for s in seats]}"
    )
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
            "; every competency has a capability and grades; every outcome and unit has a competency or a reason"
            if seats
            else " (no seats yet)"
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
