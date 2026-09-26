"""The spine's imported and school layers, as nodes and edges: the three words, stages and grades, subjects, the
eight capabilities and their behaviours, NCF-SE competencies, NCERT outcomes, the school's units, skills and rungs,
and the surveyed platforms. research/spine_build.py adds the seats' crosswalks and checks the whole graph."""

import collections
import json
import re
from pathlib import Path

R = Path(__file__).resolve().parents[1]
SRC = R / "docs/spine/sources"
SEATS = R / "research/spine_council"

WORDS = {
    "capable": "knows things deeply and can do something with them; can find out what they do not know",
    "kind": "notices other people and acts for them, including when it costs something",
    "unafraid": "tries, asks, disagrees and shows their work in front of others, and treats a wrong answer as information",
}
STAGES = {
    "foundational": (
        "Foundational",
        "Nursery to Grade 2 · ages 3–8",
        ["N", "K1", "K2", "G1", "G2"],
    ),
    "preparatory": ("Preparatory", "Grades 3–5", ["G3", "G4", "G5"]),
    "middle": ("Middle", "Grades 6–8", ["G6", "G7", "G8"]),
    "secondary": ("Secondary", "Grades 9–10", ["G9", "G10"]),
}
GRADE_LABEL = {
    "N": "Nursery",
    "K1": "Junior KG",
    "K2": "Senior KG",
    **{f"G{i}": f"Grade {i}" for i in range(1, 11)},
}
SUBJECTS = {
    "foundational": "Foundational stage domains",
    "mathematics": "Mathematics",
    "science": "Science",
    "world-around-us": "The World Around Us",
    "environmental-education": "Environmental Education (Grade 10)",
    "social-science": "Social Science",
    "individuals-in-society": "Individuals in Society (Grade 9)",
    "art": "Art Education",
    "physical-education": "Physical Education and Well-being",
    "vocational": "Vocational Education",
    "language": "Language",
    "computing": "Computing (the school's own strand)",
    "routines": "Routines (not a subject)",
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
PLATFORMS = [  # research/reports/Subject learning platforms survey.md: the products whose per-child export was opened
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
BANDS = ["PG", "N", "K1", "K2", "G1", "G2", "G3", "G4"]


class Graph:
    def __init__(self):
        self.nodes, self.edges, self.ids = [], [], set()

    def node(self, id, layer, label, **kw):
        if id not in self.ids:
            self.ids.add(id)
            self.nodes.append({"id": id, "layer": layer, "label": label, **kw})

    def edge(self, a, b, kind, by, **kw):
        self.edges.append({"from": a, "to": b, "kind": kind, "by": by, **kw})


def load(name):
    return json.load(open(SRC / name))


def imported_layers():
    g = Graph()
    for w, meaning in WORDS.items():
        g.node(f"word.{w}", "word", w, text=meaning)
    for sid, (name, sub, grades) in STAGES.items():
        g.node(f"stage.{sid}", "stage", name, text=sub)
        for gr in grades:
            g.node(f"grade.{gr}", "grade", GRADE_LABEL[gr], stage=sid)
            g.edge(f"stage.{sid}", f"grade.{gr}", "has_grade", "school")
    for sid, name in SUBJECTS.items():
        g.node(f"subject.{sid}", "subject", name)
    draft = json.load(open(R / "docs/school-os-level2-behaviours-draft.json"))
    for c in draft["capabilities"]:
        cap = f"cap.{c['capability_id']}"
        g.node(cap, "capability", c["name"], text=c["observable_at_16"])
        for s in c["stages"]:
            for b in (b for b in s["behaviours"] if b.get("status") != "retired"):
                bid = f"beh.{b['id']}"
                g.node(
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
                g.edge(cap, bid, "shown_by", "council")
                g.edge(f"stage.{s['stage_id']}", bid, "at_stage", "council")
                for w in b["words"]:
                    g.edge(bid, f"word.{w}", "evidence_for", "council")
    for e in load("ncf_se_2023_competencies.json"):
        g.node(
            e["id"],
            "goal" if e["kind"] == "CG" else "competency",
            e["text"],
            code=e["code"],
            subject=e["subject"],
            area=e.get("area"),
            stage=e["stage"],
            src="NCF-SE 2023",
        )
        g.edge(
            f"subject.{e['subject']}", e["id"], "sets", "imported", src="NCF-SE 2023"
        )
        g.edge(
            f"stage.{e['stage']}", e["id"], "at_stage", "imported", src="NCF-SE 2023"
        )
        if e["kind"] == "C":
            g.edge(e["cg"], e["id"], "has_competency", "imported", src="NCF-SE 2023")
    for e in load("ncert_learning_outcomes.json"):
        subj = NCERT_SUBJECT[e["subject"]]
        g.node(
            e["id"],
            "outcome",
            e["text"],
            subject=subj,
            grade=f"G{e['class']}",
            area=e.get("area"),
            src=e["src"],
        )
        g.edge(f"grade.G{e['class']}", e["id"], "expects", "imported", src=e["src"])
        g.edge(f"subject.{subj}", e["id"], "sets", "imported", src=e["src"])
    fixes_path = SEATS / "unit_subject_corrections.json"
    fixes = json.load(open(fixes_path)) if fixes_path.exists() else {}
    units = load("school_units.json")
    for u in units:
        subj = fixes.get(u["id"], {}).get("subject") or UNIT_SUBJECT[u["subject"]]
        extra = {"relabelled": fixes[u["id"]]["why"]} if u["id"] in fixes else {}
        g.node(
            u["id"],
            "unit",
            u["unit"],
            subject=subj,
            school_subject=u["subject"],
            bands=u["bands"],
            objectives=u["n"],
            samples=u["samples"],
            src="the school's learning-objective map (registry.json, built 2026-09-15)",
            **extra,
        )
        for b in u["bands"]:
            g.edge(f"grade.{b}", u["id"], "taught_in", "school")
        g.edge(f"subject.{subj}", u["id"], "has_unit", "school")
    reg = json.load(open(R / "supabase/seed/registry.json"))
    domains = {d["code"]: d["name"] for d in reg["domains"]}
    for k, v in reg["skills"].items():
        bands = sorted({m["b"] for m in v.get("ms", [])}, key=BANDS.index)
        g.node(
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
            g.edge(
                f"skill.{k}",
                f"ncf.fnd.F.{c}",
                "evidences",
                "school",
                src="the school's skill map",
            )
        for b in (b for b in bands if b != "PG"):
            g.edge(f"grade.{b}", f"skill.{k}", "tracked_in", "school")
    unit_by_name = {(u["subject"], u["unit"]): u["id"] for u in units}
    unit_skills = collections.defaultdict(set)
    lo_unit = {
        x["code"]: unit_by_name.get((x["subject"], x["unit"]))
        for x in reg["learning_objectives"]
    }
    for x in reg["learning_objective_skills"]:
        if lo_unit.get(x["lo"]) and f"skill.{x['skill']}" in g.ids:
            unit_skills[lo_unit[x["lo"]]].add(x["skill"])
    for uid, skills in unit_skills.items():
        for sk in skills:
            g.edge(
                uid,
                f"skill.{sk}",
                "builds",
                "school",
                src="the school's learning-objective map",
            )
    for r in json.load(open(R / "supabase/seed/rungs.json"))["rungs"]:
        g.node(
            f"rung.{r['code']}",
            "rung",
            f"{r['code']} · {r['descriptor']}",
            band=r["band"],
            src="the engine's ladder (rungs.json)",
        )
        for sk in (s for s in r.get("skill_codes", []) if f"skill.{s}" in g.ids):
            g.edge(
                f"rung.{r['code']}",
                f"skill.{sk}",
                "tests",
                "school",
                src="the engine's ladder",
            )
        if f"grade.{r['band']}" in g.ids:
            g.edge(f"grade.{r['band']}", f"rung.{r['code']}", "at_grade", "school")
    for pid, name, subj, note in PLATFORMS:
        g.node(
            f"platform.{pid}",
            "platform",
            name,
            text=note,
            src="the platform survey, 2026-09-26",
        )
        g.edge(f"platform.{pid}", f"subject.{subj}", "practises", "survey")
    return g
