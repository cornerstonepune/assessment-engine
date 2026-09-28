"""The crosswalk's answers, as ADR 0041's views (Ring B: derived, rebuilt at any time from the tables): which
framework levels sit at each age, what each subject's official statements are and how many are covered, and how
ready each step of each strand is. Only approved claims count; a proposal counts for nothing."""

from collections import Counter, defaultdict

LEARNING = ("competency", "learning_outcome", "learning_objective", "characteristic")


def approved(t):
    """The claims whose latest decision is an approval."""
    latest = {}
    for d in sorted(t["claim_decision"], key=lambda d: d["decided_at"]):
        latest[d["claim_id"]] = d["decision"]
    return {c for c, d in latest.items() if d == "approved"}


def age_levels(t, design):
    """For each year of age, the framework levels that cover it, and whether the framework printed those ages."""
    lo, hi = design["steps"]["from_age"], design["steps"]["to_age"]
    return [
        {
            "age": age,
            "levels": [
                {
                    "framework_code": lv["framework_code"],
                    "level": lv["code"],
                    "ages": [lv["age_from"], lv["age_to"]],
                    "printed": lv["age_basis"] == "printed",
                }
                for lv in t["framework_level"]
                if lv["age_from"] <= age < lv["age_to"]
            ],
        }
        for age in range(lo, hi + 1)
    ]


def subjects_of(statement, design):
    """The school's subjects an official statement speaks to: by the framework's own subject names."""
    fw, area = statement["framework_code"], statement["area"]
    if fw.startswith("CAM-"):
        return [s["code"] for s in design["subjects"] if s["cambridge"] == fw]
    subject, _, part = area.partition(" · ")
    if fw == "NCF-SE-2023":
        if subject == "foundational":
            return design["ncf_se_foundational"].get(part, [])
        return [s["code"] for s in design["subjects"] if subject in s["ncf_se"]]
    return [s["code"] for s in design["subjects"] if subject in s["ncert"]]


def framework_gap(t, design):
    """Per subject, framework and level: the official statements a child of those ages meets, and how many an
    approved alignment or exclusion covers. With nothing signed, every statement is a gap."""
    yes = approved(t)
    covered = {
        (a["framework_code"], a["statement_code"])
        for a in t.get("alignment", [])
        if a["claim_id"] in yes
    }
    covered |= {
        (e["framework_code"], e["statement_code"])
        for e in t.get("exclusion", [])
        if e["claim_id"] in yes
    }
    rows = defaultdict(lambda: {"statements": 0, "covered": 0})
    unserved = Counter()
    for s in t["framework_statement"]:
        if s["kind"] not in LEARNING:
            continue
        subjects = subjects_of(s, design)
        if not subjects:
            unserved[(s["framework_code"], s["area"].partition(" · ")[0])] += 1
        for subject in subjects:
            row = rows[(subject, s["framework_code"], s["level_code"] or "all stages")]
            row["statements"] += 1
            row["covered"] += (s["framework_code"], s["code"]) in covered
    return {
        "by_subject": [
            {
                "subject": k[0],
                "framework_code": k[1],
                "level": k[2],
                **v,
                "gap": v["statements"] - v["covered"],
            }
            for k, v in sorted(rows.items())
        ],
        "no_school_subject": [
            {"framework_code": k[0], "area": k[1], "statements": n}
            for k, n in sorted(unserved.items())
        ],
    }


def readiness(t):
    """Per step of a strand with the school's objectives on it: how much of the chain a person has signed."""
    yes = approved(t)
    statement = {
        s["lo_code"] for s in t.get("lo_statement", []) if s["claim_id"] in yes
    }
    aligned = defaultdict(set)
    for a in t.get("alignment", []):
        if a["claim_id"] in yes:
            aligned[a["lo_code"]].add(a["framework_code"].split("-")[0])
    outcome = {
        o["step_code"]: o for o in t.get("skill_outcome", []) if o["claim_id"] in yes
    }
    levels = {lv["code"] for lv in t["rubric_level"]}
    described = defaultdict(set)
    for d in t.get("rubric_descriptor", []):
        if d["claim_id"] in yes:
            described[d["outcome_code"]].add(d["level_code"])
    by_step = defaultdict(list)
    for p in t["objective_step"]:
        by_step[p["step_code"]].append(p["lo_code"])
    rows = []
    for step, los in sorted(by_step.items()):
        o = outcome.get(step)
        rows.append(
            {
                "step": step,
                "objectives": len(los),
                "placement_signed": sum(
                    p["claim_id"] in yes
                    for p in t["objective_step"]
                    if p["step_code"] == step
                ),
                "statement_approved": sum(lo in statement for lo in los),
                "ncf_se_signed": sum("NCF" in aligned[lo] for lo in los),
                "cambridge_signed": sum("CAM" in aligned[lo] for lo in los),
                "outcome_approved": bool(o),
                "rubric_complete": bool(o) and described[o["code"]] >= levels,
            }
        )
    return rows


def build(t, design):
    return {
        "age_levels": age_levels(t, design),
        "framework_gap": framework_gap(t, design),
        "readiness": readiness(t),
    }
