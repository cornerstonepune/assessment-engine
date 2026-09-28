"""Drafts made by the drafting method (docs/crosswalk/drafting-method.md), checked and turned into claims.

A draft is refused when code can see it breaks the method: a statement that does not exist or sits too far from the
step's age, a relation outside the four, an objective with neither a statement nor a reason for NCF-SE or Cambridge,
a sentence that does not begin with what a child does or uses a word the method never uses, a rubric without a line
for every level, a Cambridge statement at the step's age that the draft neither aligns nor lists. The words the
method allows are read from the method itself, so the check and the prompt cannot drift apart. No model is called.
"""

import json
import re
from pathlib import Path

R = Path(__file__).resolve().parents[1]
CW = R / "docs/crosswalk"
METHOD = CW / "drafting-method.md"
RELATIONS = {"meets", "extends", "partly_meets", "prepares_for"}
COVERS = {"meets", "extends", "partly_meets"}
PROPOSALS = {"add_to", "new", "leave_out"}
FAMILY = {"NCF-SE": "NCF-SE-2023", "Cambridge": "CAM-"}
CAP = 35  # words in one sentence of "what we say"


def words():
    """(allowed first words, words never used), read from the method's own paragraph "## Words"."""
    text = " ".join(METHOD.read_text().split())
    allowed = re.search(r"the words a draft may begin with: (.*?)\.", text).group(1)
    never = re.search(r"Never, anywhere in a draft: (.*?)\.", text).group(1)
    return {w.strip() for w in allowed.split(",")}, {
        w.strip() for w in never.split(",")
    }


def sentence_faults(label, text, allowed, never, cap=CAP, first=True):
    faults = []
    lowered = " " + re.sub(r"[^\w' -]+", " ", text.lower()) + " "
    faults += [f"{label}: uses '{w}'" for w in never if f" {w} " in lowered]
    for s in re.split(r"(?<=[.!?])\s+", text.strip()):
        head = re.sub(r"[^\w-]", "", s.split()[0].lower()) if s.split() else ""
        if first and head not in allowed:
            faults.append(f"{label}: begins with '{head}', not what a child does")
    if len(text.split()) > cap:
        faults.append(f"{label}: {len(text.split())} words, over {cap}")
    return faults


def family(framework_code):
    return next(
        (f for f, prefix in FAMILY.items() if framework_code.startswith(prefix)), None
    )


def window(step, levels, statement):
    """True when the statement's level covers the step's ages or a year either side; a statement for all stages
    (a way of working) always does."""
    level = levels.get((statement["framework_code"], statement["level_code"]))
    if level is None:
        return statement["level_code"] is None
    return (
        level["age_from"] < step["age_to"] + 1
        and level["age_to"] > step["age_from"] - 1
    )


def check(draft, t):
    """Every way the draft breaks the method, named."""
    allowed, never = words()
    faults = []
    steps = {s["code"]: s for s in t["progression_step"]}
    step = steps.get(draft["step"])
    if step is None:
        return [f"{draft['step']}: no such step"]
    statements = {(s["framework_code"], s["code"]): s for s in t["framework_statement"]}
    levels = {(lv["framework_code"], lv["code"]): lv for lv in t["framework_level"]}
    on_step = {
        p["lo_code"] for p in t["objective_step"] if p["step_code"] == draft["step"]
    }
    capabilities = {c["code"] for c in t["capability"]}
    skill_sets = {
        s["code"]
        for s in json.loads((R / "supabase/seed/skill_sets.json").read_text())[
            "skill_sets"
        ]
    }
    drafted = [o["lo_code"] for o in draft["objectives"]]
    faults += [
        f"{lo}: on the step but not drafted" for lo in sorted(on_step - set(drafted))
    ]
    faults += [
        f"{lo}: drafted but not on the step" for lo in drafted if lo not in on_step
    ]
    faults += [
        f"{lo}: drafted twice" for lo in {x for x in drafted if drafted.count(x) > 1}
    ]
    seen = set()
    for o in draft["objectives"]:
        lo = o["lo_code"]
        families = set()
        for a in o["alignments"]:
            key = (a["framework_code"], a["statement_code"])
            s = statements.get(key)
            if s is None:
                faults.append(f"{lo}: cites {key}, which does not exist")
                continue
            if not window(step, levels, s):
                faults.append(
                    f"{lo}: cites {a['statement_code']} at {s['level_code']}, too far from the step's age"
                )
            if a["relation"] not in RELATIONS or not a["reason"].strip():
                faults.append(
                    f"{lo}: {a['statement_code']} has relation '{a['relation']}' or no reason"
                )
            if (lo, *key) in seen:
                faults.append(f"{lo}: cites {a['statement_code']} twice")
            seen.add((lo, *key))
            families.add(family(a["framework_code"]))
        for fam, reason in (
            ("NCF-SE", o["no_ncf_reason"]),
            ("Cambridge", o["no_cambridge_reason"]),
        ):
            if (fam in families) == bool(reason):
                faults.append(
                    f"{lo}: {fam} needs a statement or a reason, not both and not neither"
                )
        faults += sentence_faults(f"{lo} what we say", o["what_we_say"], allowed, never)
        cap = o["capability"]
        faults += [
            f"{lo}: no capability {c}"
            for c in (cap["primary"], cap["secondary"])
            if c and c not in capabilities
        ]
        faults += [
            f"{lo}: no skill set {s}" for s in o["skill_sets"] if s not in skill_sets
        ]
        faults += [
            f"{lo}: overlaps {x}, which is not on the step"
            for x in o["overlaps"]
            if x not in on_step
        ]
    faults += sentence_faults(
        "the outcome", draft["outcome"]["text"], allowed, never, cap=120
    )
    scale = {lv["code"] for lv in t["rubric_level"]}
    given = [d["level_code"] for d in draft["descriptors"]]
    if sorted(given) != sorted(scale):
        faults.append(
            f"the rubric has lines for {sorted(given)}, the scale has {sorted(scale)}"
        )
    for d in draft["descriptors"]:
        faults += sentence_faults(
            f"the {d['level_code']} line",
            d["text"],
            allowed,
            never,
            cap=60,
            first=False,
        )
    faults += gaps(draft, t, step, statements, on_step, allowed, never)
    return faults


def gaps(draft, t, step, statements, on_step, allowed, never):
    """Every Cambridge statement of the strand at the step's age or a year younger is aligned or listed."""
    faults = []
    aligned = {
        (a["framework_code"], a["statement_code"])
        for o in draft["objectives"]
        for a in o["alignments"]
        if a["relation"] in COVERS
    }
    listed = {
        (g["framework_code"], g["statement_code"]): g for g in draft["not_covered"]
    }
    new = {
        f"new:{g['statement_code']}"
        for g in draft["not_covered"]
        if g["proposal"] == "new"
    }
    for key, g in listed.items():
        if key not in statements:
            faults.append(f"not covered: {key} does not exist")
        if key in aligned:
            faults.append(f"not covered: {key[1]} is aligned in the draft already")
        if g["proposal"] not in PROPOSALS or not g["reason"].strip():
            faults.append(
                f"not covered: {key[1]} has proposal '{g['proposal']}' or no reason"
            )
        if g["proposal"] == "add_to" and g["lo_code"] not in on_step | new:
            faults.append(
                f"not covered: {key[1]} is added to {g['lo_code']}, which is not on the step"
            )
        if g["proposal"] == "new":
            faults += sentence_faults(
                f"new objective for {key[1]}", g["what_we_say"], allowed, never
            )
    progression = next(
        p for p in t["progression"] if p["code"] == step["progression_code"]
    )
    levels = {(lv["framework_code"], lv["code"]): lv for lv in t["framework_level"]}
    for key, s in statements.items():
        level = levels.get((s["framework_code"], s["level_code"]))
        near = (
            level
            and level["age_from"] < step["age_to"]
            and level["age_to"] > step["age_from"] - 1
        )
        strand = s["area"].split(" · ")[0]
        if (
            s["framework_code"].startswith("CAM-")
            and s["kind"] == "learning_objective"
            and near
            and strand in progression["cambridge_strands"]
            and key not in aligned
            and key not in listed
        ):
            faults.append(
                f"{s['code']} ({s['level_code']}) is neither aligned nor listed as not covered"
            )
    return faults


def claims(draft, t, claim):
    """The draft as rows of ADR 0041's tables, each row a claim proposed by the method's prompt."""
    step = next(s for s in t["progression_step"] if s["code"] == draft["step"])
    prompt = draft["method"]["purpose"]
    rows = {
        name: []
        for name in (
            "lo_statement",
            "alignment",
            "no_alignment",
            "lo_capability",
            "skill_set_objective",
            "skill_outcome",
            "outcome_objective",
            "rubric_descriptor",
            "exclusion",
            "gap_proposal",
        )
    }
    code = draft["step"]
    for o in draft["objectives"]:
        lo = o["lo_code"]
        rows["lo_statement"].append(
            {
                "lo_code": lo,
                "text": o["what_we_say"],
                "supersedes": None,
                "claim_id": claim(
                    "lo_statement",
                    lo,
                    "What we say, drafted from: " + "; ".join(o["actions"]),
                    prompt=prompt,
                ),
            }
        )
        for a in o["alignments"]:
            key = f"{lo}:{a['framework_code']}:{a['statement_code']}"
            rows["alignment"].append(
                {
                    "lo_code": lo,
                    "framework_code": a["framework_code"],
                    "statement_code": a["statement_code"],
                    "relation": a["relation"],
                    "claim_id": claim("alignment", key, a["reason"], prompt=prompt),
                }
            )
        for fam, reason in (
            ("NCF-SE", o["no_ncf_reason"]),
            ("Cambridge", o["no_cambridge_reason"]),
        ):
            if reason:
                rows["no_alignment"].append(
                    {
                        "lo_code": lo,
                        "framework_family": fam,
                        "claim_id": claim(
                            "no_alignment", f"{lo}:{fam}", reason, prompt=prompt
                        ),
                    }
                )
        for weight in ("primary", "secondary"):
            if cap := o["capability"][weight]:
                rows["lo_capability"].append(
                    {
                        "lo_code": lo,
                        "capability_code": cap,
                        "weight": weight,
                        "claim_id": claim(
                            "lo_capability",
                            f"{lo}:{cap}",
                            f"The {weight} capability {lo} builds.",
                            prompt=prompt,
                        ),
                    }
                )
        for s in o["skill_sets"]:
            rows["skill_set_objective"].append(
                {
                    "skill_set_code": s,
                    "lo_code": lo,
                    "claim_id": claim(
                        "skill_set_objective",
                        f"{s}:{lo}",
                        f"{s}'s questions test what {lo} asks.",
                        prompt=prompt,
                    ),
                }
            )
        rows["outcome_objective"].append(
            {
                "outcome_code": code,
                "lo_code": lo,
                "claim_id": claim(
                    "outcome_objective",
                    f"{code}:{lo}",
                    f"{lo} is on the step {code}.",
                    prompt=prompt,
                ),
            }
        )
    rows["skill_outcome"].append(
        {
            "code": code,
            "progression_code": step["progression_code"],
            "step_code": code,
            "text": draft["outcome"]["text"],
            "scale_code": t["rubric_scale"][0]["code"],
            "claim_id": claim(
                "skill_outcome",
                code,
                "The step's outcome, gathering its objectives.",
                prompt=prompt,
            ),
        }
    )
    for d in draft["descriptors"]:
        rows["rubric_descriptor"].append(
            {
                "outcome_code": code,
                "level_code": d["level_code"],
                "text": d["text"],
                "exemplar": "",
                "claim_id": claim(
                    "rubric_descriptor",
                    f"{code}:{d['level_code']}",
                    f"The {d['level_code']} line of {code}.",
                    prompt=prompt,
                ),
            }
        )
    for g in draft["not_covered"]:
        key = f"{code}:{g['framework_code']}:{g['statement_code']}"
        if g["proposal"] == "leave_out":
            rows["exclusion"].append(
                {
                    "framework_code": g["framework_code"],
                    "statement_code": g["statement_code"],
                    "progression_code": step["progression_code"],
                    "claim_id": claim("exclusion", key, g["reason"], prompt=prompt),
                }
            )
        else:
            rows["gap_proposal"].append(
                {
                    "framework_code": g["framework_code"],
                    "statement_code": g["statement_code"],
                    "step_code": code,
                    "proposal": g["proposal"],
                    "lo_code": g.get("lo_code"),
                    "what_we_say": g.get("what_we_say"),
                    "claim_id": claim("gap_proposal", key, g["reason"], prompt=prompt),
                }
            )
    return rows


def drafts():
    return [json.loads(p.read_text()) for p in sorted((CW / "drafts").glob("*.json"))]
