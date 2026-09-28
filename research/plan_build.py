#!/usr/bin/env python3
"""Builds docs/spine/plan.json: each grade's syllabus laid onto the school year, for the spine page's Plan view.

For Grades 1-4 the syllabus is the school's own learning-objective map (supabase/seed/registry.json), in the map's
order and grouped by unit. For Grades 5-7, where the school has no map yet, it is NCERT's learning outcomes. Both are
joined to the school's proposed day and learning modes (docs/spine/plan_design.json, a proposal) and to NCF-SE's
hours, whose quotes research/timetable_data.py finds word for word on their page. No model is called.

python3 research/plan_build.py      # exit 1 if an official number is not found on its page
"""

import collections
import json
import sys
from pathlib import Path

from timetable_data import verified

R = Path(__file__).resolve().parents[1]
DESIGN = R / "docs/spine/plan_design.json"
OUT = R / "docs/spine/plan.json"
USED = [
    "illustrative",
    "hours_are_schools_call",
    "foundational_minutes",
    "working_days",
    "assessment_days",
    "event_days",
    "instruction_days",
    "saturdays",
    "prep_hours",
    "middle_hours",
    "art_pe_ve_need_time",
    "periods_projects",
    "mastery_time",
]


def band_of(grade):
    return "G1-2" if grade <= 2 else "G3-5" if grade <= 5 else "G6-7"


def school_syllabus(design):
    """Grades 1-4: {grade: {slot: [[unit id, unit, objectives], ...]}} in the map's order, and the unmapped subjects."""
    reg = json.load(open(R / "supabase/seed/registry.json"))
    units = json.load(open(R / "docs/spine/sources/school_units.json"))
    unit_id = {(u["subject"], u["unit"]): u["id"] for u in units}
    fixes = json.load(
        open(R / "research/spine_council/unit_subject_corrections.json")
    )  # the seats' relabels
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    skipped = collections.Counter()
    for lo in sorted(reg["learning_objectives"], key=lambda x: x["code"]):
        if lo["band"] not in ("G1", "G2", "G3", "G4"):
            continue
        grade = int(lo["band"][1:])
        uid = unit_id.get((lo["subject"], lo["unit"]))
        slot = design["school_subject"].get(lo["subject"])
        if uid in fixes:
            slot = design["corrected_subject"].get(fixes[uid]["subject"], slot)
        if slot is None:
            skipped[lo["subject"]] += 1
            continue
        if slot == "studio":
            slot = design["studio_slot"][band_of(grade)]
        rows = out[grade][slot]
        if rows and rows[-1][0] == uid and rows[-1][1] == lo["unit"]:
            rows[-1][2] += 1
        else:
            rows.append([uid, lo["unit"], 1])
    return out, dict(skipped)


def ncert_syllabus(design):
    """{grade: {slot: [outcome ids]}} in the document's order, and {grade: {subject: count}}."""
    rows = json.load(open(R / "docs/spine/sources/ncert_learning_outcomes.json"))
    out = collections.defaultdict(lambda: collections.defaultdict(list))
    counts = collections.defaultdict(collections.Counter)
    for r in rows:
        if r["class"] <= 7:
            counts[r["class"]][r["subject"]] += 1
            out[r["class"]][design["ncert_subject"][r["subject"]]].append(r["id"])
    return out, counts


def ncf_hours(design, official):
    """NCF-SE's hours a year for each slot of each band, from the checked tables."""
    prep, mid = official["prep_hours"]["value"], official["middle_hours"]["value"]
    fnd, days = (
        official["foundational_minutes"]["value"],
        official["instruction_days"]["value"]["days"],
    )
    out = {}
    for name, band in design["bands"].items():
        ncf = band["ncf"]
        if name == "G1-2":
            out[name] = {slot: fnd[slot] * days / 60 for slot in ("R1", "R2", "Maths")}
        else:
            table = prep if name == "G3-5" else mid
            out[name] = {slot: table[key] for slot, key in ncf.items() if key in table}
    return out


def main():
    official, missing = verified()
    if missing:
        print("not found on their page:", ", ".join(missing))
        return 1
    design = json.load(open(DESIGN))
    school, skipped = school_syllabus(design)
    ncert, ncert_counts = ncert_syllabus(design)
    grades = {}
    for grade in range(1, 8):
        entry = {"band": band_of(grade), "ncert_counts": dict(ncert_counts[grade])}
        if grade <= 4:
            entry["syllabus"] = "school"
            entry["slots"] = {
                slot: {"units": rows} for slot, rows in school[grade].items()
            }
            entry["school_objectives"] = sum(
                n for rows in school[grade].values() for _, _, n in rows
            )
        else:
            entry["syllabus"] = "ncert"
            entry["slots"] = {
                slot: {"outcomes": ids} for slot, ids in ncert[grade].items()
            }
        grades[str(grade)] = entry
    plan = {
        "built": "2026-09-28",
        "design": design,
        "ncf_hours": ncf_hours(design, official),
        "official": {
            k: {
                f: official[k][f]
                for f in ("quote", "doc", "pdf_page", "printed_page", "value")
            }
            for k in USED
        },
        "grades": grades,
        "skipped_subjects": skipped,
    }
    OUT.write_text(json.dumps(plan, ensure_ascii=False, separators=(",", ":")))
    for grade, e in grades.items():
        items = {
            s: sum(u[2] for u in v["units"]) if "units" in v else len(v["outcomes"])
            for s, v in e["slots"].items()
        }
        print(f"Grade {grade} ({e['syllabus']}): {sum(items.values())} items · {items}")
    if skipped:
        print("school subjects with no slot:", skipped)
    print(
        f"wrote {OUT.relative_to(R)} · official numbers {len(official)}/{len(official) + len(missing)} checked on their page"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
