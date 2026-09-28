#!/usr/bin/env python3
"""Builds docs/spine/plan.json: each grade's syllabus laid onto the school year, for the spine page.

For Grades 1-4 the syllabus is the school's own learning-objective map (supabase/seed/registry.json), in the map's
order and grouped by unit. For Grades 5-7, where the school has no map yet, it is NCERT's learning outcomes. Both are
joined to the school's proposed day and learning modes (docs/spine/plan_design.json, a proposal) and to NCF-SE's
hours, whose quotes research/timetable_data.py finds word for word on their page. Every number the page shows is
worked out here, where a test can check it (packages/engine/tests/test_spine_page.py): the calendar of each
scenario, the hours a year of each slot, the minutes a day by mode, and each syllabus paced across the fortnights.
The page only draws them. No model is called.

python3 research/plan_build.py      # exit 1 if an official number is not found on its page
"""

import collections
import itertools
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
    reg = json.loads((R / "supabase/seed/registry.json").read_text())
    units = json.loads((R / "docs/spine/sources/school_units.json").read_text())
    unit_id = {(u["subject"], u["unit"]): u["id"] for u in units}
    fixes = json.loads(
        (R / "research/spine_council/unit_subject_corrections.json").read_text()
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
    rows = json.loads(
        (R / "docs/spine/sources/ncert_learning_outcomes.json").read_text()
    )
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


def calendar(cal, scenario):
    """One scenario's year: weeks in school, working and teaching days, Saturdays, and the teaching days of each
    fortnight in turn (the last one takes what is left)."""
    weeks = 52 - cal["summer_weeks"] - cal["diwali_weeks"]
    work = weeks * 5 - cal["weekday_holidays"]
    teach = work - scenario["test_days"] - cal["event_days"]
    step = cal["fortnight_days"]
    return {
        "weeks": weeks,
        "work": work,
        "teach": teach,
        "saturdays": weeks // 2 if scenario["saturdays"] else 0,
        "days": [min(step, teach - start) for start in range(0, teach, step)],
    }


def flat(slot):
    """A slot's syllabus as one item per objective, in order: a unit of five objectives is five items."""
    if "units" in slot:
        return [uid for uid, _, n in slot["units"] for _ in range(n)]
    return list(slot["outcomes"])


def pace(items, days):
    """Cuts a syllabus, in its order, across the fortnights by teaching days: [[[id, n], ...] for each fortnight].

    Item i of k goes to the fortnight whose running total of days first passes (i + 0.5) / k of the year, so a
    fortnight of d days carries d / (all days) of the items, give or take one."""
    total, ends = sum(days), list(itertools.accumulate(days))
    out = [[] for _ in days]
    for i, x in enumerate(items):
        at = (i + 0.5) / len(items) * total
        cell = out[next(f for f, end in enumerate(ends) if at < end)]
        if cell and cell[-1][0] == x:
            cell[-1][1] += 1
        else:
            cell.append([x, 1])
    return out


def week(band):
    """{slot: {mode: minutes a week}} from the band's weekly rows."""
    out = collections.defaultdict(dict)
    for slot, mode, minutes in band["week"]:
        out[slot][mode] = out[slot].get(mode, 0) + minutes
    return dict(out)


def composition(design, band):
    """Minutes a weekday by mode. Academic time is split by the band's anatomy of an hour (concept, practice,
    check); Circle & close is the day's community time."""
    out = dict.fromkeys(design["modes"], 0.0)
    out["community"] = float(design["day"]["community"])
    for _, mode, minutes in band["week"]:
        # a row in one of the seven modes keeps its minutes; an academic row is split by the anatomy
        parts = {mode: 1} if mode in design["modes"] else band["anatomy"]
        for part, share in parts.items():
            out[part] += minutes / 5 * share
    return out


def hours(design, band, cal):
    """Hours a year for each slot of a band in one scenario, its share of Saturdays included, and Circle & close."""
    sat, out = band.get("saturday", {}), {}
    for slot, modes in week(band).items():
        weekdays = sum(modes.values()) / 60 * cal["teach"] / 5
        out[slot] = (
            weekdays
            + sat.get(slot, 0)
            * cal["saturdays"]
            * design["calendar"]["saturday_minutes"]
            / 60
        )
    out["Community"] = design["day"]["community"] / 60 * cal["teach"]
    return out


def load(entry, hrs, design):
    """NCERT's outcomes for a grade against the hours of the slots that teach them."""
    n, total, used = 0, 0.0, set()
    for subject, k in entry["ncert_counts"].items():
        slot = design["ncert_subject"][subject]
        if slot not in hrs:
            continue
        n += k
        if slot not in used:
            total, used = total + hrs[slot], used | {slot}
    return {
        "outcomes": n,
        "hours_each": total / n if n else None,
        "school_objectives": entry.get("school_objectives"),
    }


def build(design, official):
    """The plan: each grade's syllabus, the day by mode, each scenario's calendar and hours, and the year paced."""
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
    scenarios = []
    for s in design["scenarios"]:
        cal = calendar(design["calendar"], s)
        hrs = {name: hours(design, band, cal) for name, band in design["bands"].items()}
        per_grade = {g: load(e, hrs[e["band"]], design) for g, e in grades.items()}
        scenarios.append({**s, "calendar": cal, "hours": hrs, "load": per_grade})
    days = scenarios[0]["calendar"]["days"]
    return {
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
        "composition": {
            name: composition(design, band) for name, band in design["bands"].items()
        },
        "scenarios": scenarios,
        "year": {
            g: {slot: pace(flat(v), days) for slot, v in e["slots"].items()}
            for g, e in grades.items()
        },
    }


def main():
    official, missing = verified()
    if missing:
        print("not found on their page:", ", ".join(missing))
        return 1
    plan = build(json.loads(DESIGN.read_text()), official)
    OUT.write_text(json.dumps(plan, ensure_ascii=False, separators=(",", ":")))
    for grade, e in plan["grades"].items():
        items = {s: len(flat(v)) for s, v in e["slots"].items()}
        print(f"Grade {grade} ({e['syllabus']}): {sum(items.values())} items · {items}")
    if plan["skipped_subjects"]:
        print("school subjects with no slot:", plan["skipped_subjects"])
    cal = plan["scenarios"][0]["calendar"]
    print(f"{cal['teach']} teaching days in {len(cal['days'])} fortnights")
    print(
        f"wrote {OUT.relative_to(R)} · official numbers {len(official)}/{len(official) + len(missing)} checked on their page"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
