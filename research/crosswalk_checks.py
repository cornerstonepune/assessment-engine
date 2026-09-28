"""The checks on the crosswalk's rows (research/crosswalk_build.py): every link lands on a row that exists, every
statement keeps its page, every level and step its ages, every school objective is placed or waiting and none is
lost, and nothing is decided except by a person who signs. Each fault is named; none is explained away."""

import json
from collections import Counter
from pathlib import Path

R = Path(__file__).resolve().parents[1]
HPC = {
    "Beginner",
    "Proficient",
    "Advanced",
}  # the Holistic Progress Card's three levels (PARAKH, page 9)


def twice(rows, key):
    counts = Counter(key(r) for r in rows)
    return sorted(str(k) for k, n in counts.items() if n > 1)


def statements(t):
    faults = []
    frameworks = {f["code"] for f in t["framework"]}
    documents = Counter(d["framework_code"] for d in t["framework_document"])
    levels = {(lv["framework_code"], lv["code"]) for lv in t["framework_level"]}
    codes = {(s["framework_code"], s["code"]) for s in t["framework_statement"]}
    faults += [
        f"{f} has {documents[f]} documents, not one"
        for f in frameworks
        if documents[f] != 1
    ]
    faults += [
        f"statement twice: {k}"
        for k in twice(
            t["framework_statement"], lambda s: (s["framework_code"], s["code"])
        )
    ]
    faults += [
        f"level twice: {k}"
        for k in twice(
            t["framework_level"], lambda lv: (lv["framework_code"], lv["code"])
        )
    ]
    for s in t["framework_statement"]:
        key = f"{s['framework_code']} {s['code']}"
        if s["framework_code"] not in frameworks:
            faults.append(f"{key}: no such framework")
        if s["level_code"] and (s["framework_code"], s["level_code"]) not in levels:
            faults.append(f"{key}: no level {s['level_code']}")
        if s["parent_code"] and (s["framework_code"], s["parent_code"]) not in codes:
            faults.append(f"{key}: no parent {s['parent_code']}")
        words = (s["text"] or "").strip() or s.get(
            "text_sha256"
        )  # a closed framework keeps a fingerprint
        if not words or not isinstance(s["pdf_page"], int) or s["pdf_page"] < 1:
            faults.append(f"{key}: no text or no page")
    for lv in t["framework_level"]:
        if not lv["age_from"] < lv["age_to"] or not lv["age_basis"] or not lv["quote"]:
            faults.append(
                f"{lv['framework_code']} {lv['code']}: ages missing or not explained"
            )
    return faults


def counts(t):
    """As many statements as the importers verified, word for word, on their pages."""
    by = Counter(
        s["framework_code"]
        for s in t["framework_statement"]
        if s["kind"] not in ("strand", "substrand")
    )
    ncf = len(
        json.loads((R / "docs/spine/sources/ncf_se_2023_competencies.json").read_text())
    )
    ncert = len(
        json.loads((R / "docs/spine/sources/ncert_learning_outcomes.json").read_text())
    )
    want = {"NCF-SE-2023": ncf, "NCERT": ncert}
    got = {
        "NCF-SE-2023": by["NCF-SE-2023"],
        "NCERT": by["NCERT-LO-2017"] + by["NCERT-LO-2019"],
    }
    for path in sorted((R / "docs/crosswalk/statements").glob("cam-*.json")):
        book = json.loads(path.read_text())
        want[book["framework"]] = len(book["objectives"]) + len(book["notes"])
        got[book["framework"]] = by[book["framework"]]
    return [
        f"{k}: {got[k]} statements, the importer verified {n}"
        for k, n in want.items()
        if got[k] != n
    ]


def ladders(t, objectives, design):
    faults = []
    steps = {s["code"]: s for s in t["progression_step"]}
    progressions = {p["code"] for p in t["progression"]}
    claims = {c["id"] for c in t["claim"]}
    first = design["grade_age"]["grade_1_from"]
    graded = {o["code"]: o for o in objectives if o["band"].startswith("G")}
    faults += [
        f"step twice: {k}" for k in twice(t["progression_step"], lambda s: s["code"])
    ]
    faults += [f"claim twice: {k}" for k in twice(t["claim"], lambda c: c["id"])]
    for s in t["progression_step"]:
        if (
            s["progression_code"] not in progressions
            or s["claim_id"] not in claims
            or s["age_from"] >= s["age_to"]
        ):
            faults.append(f"step {s['code']}: no progression, no claim or no ages")
    for p in t["objective_step"]:
        o, step = graded.get(p["lo_code"]), steps.get(p["step_code"])
        if o is None or step is None or p["claim_id"] not in claims:
            faults.append(f"{p['lo_code']}: no such objective, step or claim")
        elif step["age_from"] != first + int(o["band"][1:]) - 1:
            faults.append(
                f"{p['lo_code']}: {o['band']} placed at age {step['age_from']}"
            )
    seen = Counter(
        [p["lo_code"] for p in t["objective_step"]]
        + [w["lo_code"] for w in t["objective_waiting"]]
    )
    faults += [
        f"{code}: neither placed nor waiting" for code in graded if seen[code] == 0
    ]
    faults += [f"{code}: placed or waiting twice" for code, n in seen.items() if n > 1]
    return faults


def claims(t):
    """A claim names one proposer (a person, a prompt or a rule), and only a signatory decides one."""
    faults = []
    for c in t["claim"]:
        proposers = [c["proposed_by"], c["prompt_purpose"], c["rule"]]
        if sum(x is not None for x in proposers) != 1 or not c["rationale"]:
            faults.append(f"claim {c['id']}: not one proposer, or no reason")
    signers = {s["educator"] for s in t["signatory"]}
    ids = {c["id"] for c in t["claim"]}
    for d in t["claim_decision"]:
        if d["decided_by"] not in signers or d["claim_id"] not in ids:
            faults.append(
                f"decision on {d['claim_id']}: by {d['decided_by']}, who does not sign, or no such claim"
            )
    return faults


def rubric(t):
    levels = sorted(t["rubric_level"], key=lambda lv: lv["ord"])
    faults = (
        []
        if [lv["ord"] for lv in levels] == list(range(1, len(levels) + 1))
        else ["rubric levels out of order"]
    )
    faults += [
        f"{lv['code']} reports as {lv['reports_as']}"
        for lv in levels
        if lv["reports_as"] not in HPC
    ]
    return faults


def check(t, objectives):
    design = json.loads((R / "docs/crosswalk/design.json").read_text())
    return (
        statements(t)
        + counts(t)
        + ladders(t, objectives, design)
        + claims(t)
        + rubric(t)
    )
