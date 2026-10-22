"""The English foundation's derived rows (research/english_check.py): what each topic holds in teaching order, which
objective each skill covers, what comes before each skill, which question types each level uses, and where every
Stage 3 and 4 objective landed. They are worked out from the drafted rows, never edited by hand; `--write` rewrites
them and the check fails while one is out of date. Also the counts the check reports.
"""

import json
from collections import Counter

import english_check as ec


def derived(t, objs):
    skills = sorted(t["skill"], key=lambda s: (s["grade"], s["order"]))
    topics = [
        dict(x, skill_sets=[s["code"] for s in skills if s["topic"] == x["code"]]) for x in t["topic"]
    ]
    observed = {n["objective"]: n for n in t["not_on_paper"]}
    coverage = []
    for code, o in objs.items():
        if o["stage"] not in ec.STAGES:
            continue
        on = [s["code"] for s in skills if code in s["objectives"]]
        coverage.append({
            "objective": code, "stage": o["stage"], "grade": ec.STAGES[o["stage"]], "strand": o["strand"],
            "substrand": o["substrand"], "on_paper": bool(on), "skills": on,
            "observed": None if on else observed.get(code, {}).get("reason"),
        })
    qt = sorted({(s["skill_code"], s["difficulty"], s["question_type"]) for s in t["skill_level_sample"]})
    return {
        "topic": {"topics": topics},
        "objective_coverage": {"objective_coverage": coverage},
        "skill_objective": {"skill_objectives": [
            {"skill_code": s["code"], "framework": ec.FRAMEWORK, "objective": c} for s in skills for c in s["objectives"]
        ]},
        "skill_prerequisite": {"skill_prerequisites": [
            {"skill_code": s["code"], "before_code": b} for s in skills for b in s["before"]
        ]},
        "skill_level_question_type": {"skill_level_question_types": [
            {"skill_code": k, "difficulty": d, "question_type": q} for k, d, q in qt
        ]},
    }


def stale(t, objs, write=False):
    faults = []
    for name, rows in derived(t, objs).items():
        path = ec.DRAFT / f"{name}.json"
        text = json.dumps(rows, ensure_ascii=False, indent=1) + "\n"
        if write:
            path.write_text(text)
        elif not path.exists() or path.read_text() != text:
            faults.append(f"{path.relative_to(ec.R)} is out of date: python3 research/english_check.py --write")
    return faults


def counts(t, objs, ran):
    qtypes = {q["code"]: q for q in t["question_type"]}
    stage = {g: [c for c, o in objs.items() if ec.STAGES.get(o["stage"]) == g] for g in ec.STAGES.values()}
    paper = {c for s in t["skill"] for c in s["objectives"]}
    out = {}
    for g, codes in stage.items():
        skills = [s for s in t["skill"] if s["grade"] == g]
        mine = {s["code"] for s in skills}
        samples = [s for s in t["skill_level_sample"] if s["skill_code"] in mine]
        out[g] = {
            "objectives": len(codes),
            "on_paper": sum(c in paper for c in codes),
            "observed_by_educator": sum(c in {n["objective"] for n in t["not_on_paper"]} for c in codes),
            "skills": len(skills),
            "levels": sum(lv["skill_code"] in mine for lv in t["skill_level"]),
            "examples": len(samples),
            "examples_marked_by": dict(Counter(qtypes.get(s["question_type"], {}).get("marked_by") for s in samples)),
            "passages": sum(p["grade"] == g for p in t["passage"]),
        }
    out["mistakes"] = len(t["misconception"])
    out["skill_mistake_links"] = len(t["skill_mistake"])
    out["rubrics"] = len(t["rubric"])
    out["question_types"] = len(t["question_type"])
    out["checks_run_by_code"] = dict(sorted(ran.items()))
    return out
