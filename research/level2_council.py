#!/usr/bin/env python3
"""Reconciles the council seats' verdicts on the Level 2 draft into a v2 draft, by rules a founder can read.

python3 research/level2_council.py --draft docs/school-os-level2-behaviours-draft.json \\
    --seats research/level2_council/educator.json research/level2_council/parent.json ... \\
    --chair research/level2_council/chair.json --out <v2.json> --log <changes.md>

Rules, in order, for each behaviour (a seat is one of educator, parent, development, rights):
  R1  the rights seat's skip is a safety veto: the row is retired.
  R2  two or more skips: retired.
  R3  one skip (not rights): the chair decides
  until then, accepted with the skip logged as a minority note.
  R4  edits from one seat only, no skip: applied (an uncontested edit within a seat's remit stands).
  R5  edits from several seats touching different fields: all applied
  the same field: the chair decides,
      and until then the first in the order rights, development, educator, parent is applied.
  R6  every seat accepts: accepted.
A chair decision (chair.json: decisions[], add[], regrow{}) overrides the rule for that row and is logged as such.
Missing behaviours the seats propose are listed for the chair, never added by the script. A retired row stays
in the file with status "retired" so the founders can restore it
a later row that grew from it must be
re-pointed by the chair (regrow), or the validator fails it. No model is called.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict

from level2_council_log import write_log

SEATS = ["rights", "development", "educator", "parent"]  # the order R5 falls back to
FIELDS = [
    "statement",
    "adult_sees",
    "counter_example",
    "capture_mode",
    "setting",
    "words",
]
INITIAL = {"educator": "E", "parent": "P", "development": "D", "rights": "R"}


def load(paths):
    seats = {}
    for p in paths:
        d = json.load(open(p))
        seats[d["seat"]] = d
    return seats


def verdicts_by_id(seats):
    by = defaultdict(dict)
    for name, d in seats.items():
        for v in d["verdicts"]:
            by[v["id"]][name] = v
    return by


def decide(vs):
    """vs: {seat: verdict}. Returns (outcome, rule, edits{field: (seat, value)}, needs_chair, notes[])."""
    skips = [s for s, v in vs.items() if v["verdict"] == "skip"]
    edits = [s for s, v in vs.items() if v["verdict"] == "edit"]
    notes = [
        f"{INITIAL[s]} {vs[s]['verdict']}: {vs[s].get('reason', '')}".strip()
        for s in SEATS
        if s in vs and vs[s]["verdict"] != "accept"
    ]
    if "rights" in skips:
        return "retired", "R1", {}, False, notes
    if len(skips) >= 2:
        return "retired", "R2", {}, False, notes
    merged, conflict = {}, False
    for s in SEATS:  # fallback order
        if s in edits:
            for f, val in vs[s].get("edit", {}).items():
                if f in merged and merged[f][1] != val:
                    conflict = True
                else:
                    merged.setdefault(f, (s, val))
    if len(skips) == 1:
        return ("edited" if merged else "accepted"), "R3", merged, True, notes
    if len(edits) == 1:
        return "edited", "R4", merged, False, notes
    if len(edits) >= 2:
        return "edited", "R5", merged, conflict, notes
    return "accepted", "R6", {}, False, notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--draft", required=True)
    ap.add_argument("--seats", nargs="+", required=True)
    ap.add_argument("--chair")
    ap.add_argument("--out", required=True)
    ap.add_argument("--log", required=True)
    ap.add_argument(
        "--ages",
        help="development seat's earliest fair age per Foundational row: {id: {from_age, why}}",
    )
    ap.add_argument(
        "--added-reviews",
        nargs="*",
        default=[],
        help="seats' verdicts on the added rows, logged for the founders",
    )
    a = ap.parse_args()
    doc = json.load(open(a.draft))
    seats = load(a.seats)
    by = verdicts_by_id(seats)
    chair = (
        json.load(open(a.chair))
        if a.chair
        else {"decisions": [], "add": [], "regrow": {}}
    )
    chair_by = {d["id"]: d for d in chair.get("decisions", [])}
    regrow = chair.get("regrow", {})
    adds = defaultdict(list)
    for b in chair.get("add", []):
        adds[(b["capability_id"], b["stage_id"])].append(b)

    outcomes = Counter()
    rules = Counter()
    needs = []
    log = []
    per_seat = {s: Counter() for s in seats}
    per_cell = defaultdict(lambda: {s: Counter() for s in seats})
    live_ids = set()
    for cap in doc["capabilities"]:
        for st in cap["stages"]:
            cell = (cap["capability_id"], st["stage_id"])
            for b in st["behaviours"]:
                vs = by.get(b["id"], {})
                for s, v in vs.items():
                    per_seat[s][v["verdict"]] += 1
                    per_cell[cell][s][v["verdict"]] += 1
                outcome, rule, edits, needs_chair, notes = decide(vs)
                if b["id"] in chair_by:
                    c = chair_by[b["id"]]
                    outcome = {
                        "accept": "accepted",
                        "edit": "edited",
                        "skip": "retired",
                    }[c["verdict"]]
                    edits = (
                        {
                            **edits,
                            **{
                                f: ("chair", val)
                                for f, val in c.get("edit", {}).items()
                            },
                        }
                        if c["verdict"] == "edit"
                        else {}
                    )
                    rule = "chair"
                    needs_chair = False
                    notes.append(f"chair {c['verdict']}: {c.get('reason', '')}")
                before = {}
                if outcome == "edited":
                    for f, (who, val) in edits.items():
                        if b.get(f) != val:
                            before[f] = b.get(f)
                            b[f] = val
                    if not before:
                        outcome = "accepted"  # an edit that changed nothing
                if outcome == "retired":
                    b["status"] = "retired"
                else:
                    b.pop("status", None)
                    live_ids.add(b["id"])
                b["council"] = {
                    "seats": {INITIAL[s]: vs[s]["verdict"] for s in SEATS if s in vs},
                    "outcome": outcome,
                    "rule": rule,
                    "notes": notes,
                    "before": before,
                }
                if needs_chair:
                    needs.append(
                        (cap["capability_id"], st["stage_id"], b["id"], rule, notes)
                    )
                outcomes[outcome] += 1
                rules[rule] += 1
                if outcome != "accepted" or notes:
                    log.append(
                        (
                            cap["capability_id"],
                            st["stage_id"],
                            b["id"],
                            outcome,
                            rule,
                            before,
                            b,
                            notes,
                        )
                    )
            for nb in adds.get(cell, []):
                row = {k: nb[k] for k in ["id", *FIELDS, "grows_from"]}
                row["council"] = {
                    "seats": {},
                    "outcome": "added",
                    "rule": "chair",
                    "notes": [f"chair add: {nb.get('reason', '')}"],
                    "before": {},
                }
                st["behaviours"].append(row)
                live_ids.add(row["id"])
                outcomes["added"] += 1
                log.append(
                    (
                        cap["capability_id"],
                        st["stage_id"],
                        row["id"],
                        "added",
                        "chair",
                        {},
                        row,
                        row["council"]["notes"],
                    )
                )
    ages = json.load(open(a.ages)) if a.ages else {}
    for cap in doc["capabilities"]:
        for st in cap["stages"]:
            for b in st["behaviours"]:
                if b["id"] in ages and b.get("status") != "retired":
                    b["from_age"] = int(ages[b["id"]]["from_age"])
                    if ages[b["id"]].get("why"):
                        b["from_age_why"] = ages[b["id"]]["why"]
    # re-point grows_from that named a retired row
    dangling = []
    for cap in doc["capabilities"]:
        for st in cap["stages"]:
            for b in st["behaviours"]:
                if b.get("status") == "retired" or not b.get("grows_from"):
                    continue
                if b["id"] in regrow:
                    b["council"]["before"].setdefault("grows_from", b["grows_from"])
                    b["grows_from"] = regrow[b["id"]]
                if b["grows_from"] not in live_ids:
                    dangling.append(
                        (cap["capability_id"], st["stage_id"], b["id"], b["grows_from"])
                    )
    # what the seats proposed as missing, and duplicates, for the chair
    missing = []
    duplicates = []
    could_not = []
    objections = {}
    notes_to_founders = {}
    for s, d in seats.items():
        for c in d.get("cells", []):
            for m in c.get("missing", []):
                missing.append((s, c["capability_id"], c["stage_id"], m))
            for pair in c.get("duplicates", []):
                duplicates.append((s, pair))
        for cn in d.get("could_not", []):
            could_not.append((s, cn))
        objections[s] = d.get("objections", [])
        notes_to_founders[s] = d.get("note_to_founders", "")
    doc["produced"] = (
        doc.get("produced", "")
        + "; v2 after the four-seat council review of 2026-09-26 (research/level2_council.py, seats in research/level2_council/)"
    )
    doc["council"] = {
        "seats": sorted(seats),
        "outcomes": dict(outcomes),
        "rules": dict(rules),
        "per_seat": {s: dict(c) for s, c in per_seat.items()},
        "per_cell": {
            f"{k[0]}/{k[1]}": {s: dict(c) for s, c in v.items()}
            for k, v in per_cell.items()
        },
        "needs_chair": len(needs),
        "dangling_grows_from": len(dangling),
    }
    json.dump(doc, open(a.out, "w"), indent=1, ensure_ascii=False)
    added_reviews = [json.load(open(p)) for p in a.added_reviews]
    doc["council"]["added_reviews"] = {
        r["seat"]: {v["id"]: v["verdict"] for v in r["verdicts"]} for r in added_reviews
    }
    doc["council"]["from_age_rows"] = sum(
        1
        for c in doc["capabilities"]
        for s in c["stages"]
        for b in s["behaviours"]
        if "from_age" in b
    )
    write_log(
        a.log,
        doc,
        seats,
        log,
        needs,
        dangling,
        missing,
        duplicates,
        could_not,
        objections,
        notes_to_founders,
        added_reviews,
    )
    print("outcomes", dict(outcomes), "rules", dict(rules))
    for s in SEATS:
        if s in per_seat:
            c = per_seat[s]
            n = sum(c.values())
            print(
                f"  {s:<12} accept {c['accept']:3d}  edit {c['edit']:3d}  skip {c['skip']:3d}  of {n}  ({100 * c['accept'] / n:.0f}% accepted as written)"
            )
    print(
        f"needs chair {len(needs)} · dangling grows_from {len(dangling)} · missing proposed {len(missing)} · duplicates named {len(duplicates)}"
    )
    return 1 if (needs or dangling) else 0


if __name__ == "__main__":
    sys.exit(main())
