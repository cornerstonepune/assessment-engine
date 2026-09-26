#!/usr/bin/env python3
"""Checks one crosswalk seat's file: ids exist, grades sit inside the row's stage, every row of the seat's remit is
covered or given a reason. python3 research/spine_council/check_seat.py <seat file>"""

import json
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[2]
SRC = R / "docs/spine/sources"
NCF = {e["id"]: e for e in json.load(open(SRC / "ncf_se_2023_competencies.json"))}
LO = {e["id"]: e for e in json.load(open(SRC / "ncert_learning_outcomes.json"))}
UNITS = {e["id"]: e for e in json.load(open(SRC / "school_units.json"))}
CAPS = {
    c["capability_id"]
    for c in json.load(open(R / "docs/school-os-level2-behaviours-draft.json"))[
        "capabilities"
    ]
}
FOLLOW = json.load(open(Path(__file__).with_name("followup_remit.json")))
STAGE_GRADES = {
    "foundational": {"N", "K1", "K2", "G1", "G2"},
    "preparatory": {"G3", "G4", "G5"},
    "middle": {"G6", "G7", "G8"},
    "secondary": {"G9", "G10"},
}
REMIT = {  # seat -> (NCF subjects, NCERT subjects, school unit subjects)
    "math": ({"mathematics"}, {"math"}, {"Numeracy"}),
    "science": (
        {"science", "world-around-us", "environmental-education"},
        {"evs", "sci"},
        {"Science", "Home Science"},
    ),
    "social": (
        {"social-science", "individuals-in-society"},
        {"sst"},
        {"Global perspectives"},
    ),
    "language": (
        {"language"},
        {"eng"},
        {
            "Literacy",
            "Literacy - English",
            "Phonics",
            "Literacy - Hindi",
            "Literacy - Marathi",
        },
    ),
    "arts": (
        {"art", "physical-education", "vocational"},
        {"art", "hpe"},
        {"Visual Arts", "Primary Computing", "Routines"},
    ),
    "foundational": ({"foundational"}, set(), set()),
    "arts_followup": (set(), set(), set()),
}


def remit(seat):
    ncf_s, lo_s, unit_s = REMIT[seat]
    ncf = {i for i, e in NCF.items() if e["subject"] in ncf_s}
    units = {i for i, e in UNITS.items() if e["subject"] in unit_s}
    if seat == "arts_followup":
        ncf, units = set(FOLLOW["ncf"]), set(FOLLOW["units"])
    elif seat == "arts":
        ncf -= set(
            FOLLOW["ncf"]
        )  # the recovered minimum-standard rows belong to the follow-up file
    lo = {i for i, e in LO.items() if e["subject"] in lo_s}
    return ncf, {i for i in ncf if NCF[i]["kind"] == "C"}, lo, units


def main(path):
    d = json.load(open(path))
    seat, errs = d.get("seat"), []
    if seat not in REMIT:
        print("PROBLEMS 1\n   seat must be one of", sorted(REMIT))
        return 1
    mine_ncf, mine_c, mine_lo, mine_units = remit(seat)
    cc = {x["id"]: x for x in d.get("competency_capabilities", [])}
    errs += [
        f"competency_capabilities: missing {i}" for i in sorted(mine_ncf - set(cc))
    ]
    for i, x in cc.items():
        caps = x.get("capabilities", [])
        if i not in NCF or not 1 <= len(caps) <= 3 or not set(caps) <= CAPS:
            errs.append(
                f"competency_capabilities {i}: unknown id or capabilities {caps}"
            )
    cg = {x["id"]: x for x in d.get("competency_grades", [])}
    errs += [f"competency_grades: missing {i}" for i in sorted(mine_c - set(cg))]
    for i, x in cg.items():
        if i not in NCF:
            errs.append(f"competency_grades: unknown id {i}")
            continue
        allowed = STAGE_GRADES[NCF[i]["stage"]]
        if not x.get("grades") or not set(x["grades"]) <= allowed:
            errs.append(
                f"competency_grades {i}: grades {x.get('grades')} not within {sorted(allowed)}"
            )
        errs += [
            f"competency_grades {i}: unknown ncert {lo}"
            for lo in x.get("ncert", [])
            if lo not in LO
        ]
    for section, universe, mine in (
        ("ncert_competencies", LO, mine_lo),
        ("unit_competencies", UNITS, mine_units),
    ):
        rows = {x["id"]: x for x in d.get(section, [])}
        errs += [f"{section}: missing {i}" for i in sorted(mine - set(rows))]
        for i, x in rows.items():
            comps = x.get("competencies", [])
            if i not in universe:
                errs.append(f"{section}: unknown id {i}")
            elif not comps and not x.get("why"):
                errs.append(f"{section} {i}: empty without why")
            errs += [
                f"{section} {i}: unknown competency {c}" for c in comps if c not in NCF
            ]
    if len(d.get("notes", [])) > 5:
        errs.append("notes: at most five")
    print(
        f"seat {seat}: competencies {len(cc)}/{len(mine_ncf)} · graded {len(cg)}/{len(mine_c)} · units {len(d.get('unit_competencies', []))}/{len(mine_units)}"
    )
    if errs:
        print(f"PROBLEMS {len(errs)}")
        for e in errs[:60]:
            print("  ", e)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
