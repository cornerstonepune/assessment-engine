#!/usr/bin/env python3
"""Checks one crosswalk seat's file: ids exist, grades sit inside the row's stage, every row of the seat's remit is covered."""
import json, sys, collections
S="/tmp/claude-0/-home-user-assessment-engine/d7e26dee-8cf8-540f-b08a-b0d73dec61fc/scratchpad"
NCF={e["id"]:e for e in json.load(open(f"{S}/ncf_competencies.json"))}
LO={e["id"]:e for e in json.load(open(f"{S}/ncert/ncert_lo.json"))}
UNITS={e["id"]:e for e in json.load(open(f"{S}/school_units.json"))}
CAPS={c["id"] for c in json.load(open(f"{S}/capabilities.json"))}
STAGE_GRADES={"foundational":{"N","K1","K2","G1","G2"},"preparatory":{"G3","G4","G5"},"middle":{"G6","G7","G8"},"secondary":{"G9","G10"}}
REMIT={  # seat -> (ncf subjects, ncert subjects, unit subjects)
 "math":({"mathematics"},{"math"},{"Numeracy"}),
 "science":({"science","world-around-us","environmental-education"},{"evs","sci"},{"Science","Home Science"}),
 "social":({"social-science","individuals-in-society"},{"sst"},{"Global perspectives"}),
 "language":({"language"},{"eng"},{"Literacy","Literacy - English","Phonics","Literacy - Hindi","Literacy - Marathi"}),
 "arts":({"art","physical-education","vocational"},{"art","hpe"},{"Visual Arts","Primary Computing","Routines"}),
 "foundational":({"foundational"},set(),set()),
}
def main(path):
    d=json.load(open(path)); seat=d.get("seat"); errs=[]
    if seat not in REMIT: print("PROBLEMS 1\n   seat must be one of", sorted(REMIT)); return 1
    ncf_s, lo_s, unit_s = REMIT[seat]
    mine_ncf={i for i,e in NCF.items() if e["subject"] in ncf_s}
    mine_c={i for i in mine_ncf if NCF[i]["kind"]=="C"}
    mine_lo={i for i,e in LO.items() if e["subject"] in lo_s}
    mine_units={i for i,e in UNITS.items() if e["subject"] in unit_s}
    cc={x["id"]:x for x in d.get("competency_capabilities",[])}
    for i in mine_ncf-set(cc): errs.append(f"competency_capabilities: missing {i}")
    for i,x in cc.items():
        if i not in NCF: errs.append(f"competency_capabilities: unknown id {i}")
        caps=x.get("capabilities",[])
        if not 1<=len(caps)<=3 or not set(caps)<=CAPS: errs.append(f"competency_capabilities {i}: capabilities {caps}")
    cg={x["id"]:x for x in d.get("competency_grades",[])}
    for i in mine_c-set(cg): errs.append(f"competency_grades: missing {i}")
    for i,x in cg.items():
        if i not in NCF: errs.append(f"competency_grades: unknown id {i}"); continue
        allowed=STAGE_GRADES[NCF[i]["stage"]]
        if not x.get("grades") or not set(x["grades"])<=allowed: errs.append(f"competency_grades {i}: grades {x.get('grades')} not within {sorted(allowed)}")
        for l in x.get("ncert",[]):
            if l not in LO: errs.append(f"competency_grades {i}: unknown ncert {l}")
    nc={x["id"]:x for x in d.get("ncert_competencies",[])}
    for i in mine_lo-set(nc): errs.append(f"ncert_competencies: missing {i}")
    for i,x in nc.items():
        if i not in LO: errs.append(f"ncert_competencies: unknown id {i}"); continue
        comps=x.get("competencies",[])
        if not comps and not x.get("why"): errs.append(f"ncert_competencies {i}: empty without why")
        for c in comps:
            if c not in NCF: errs.append(f"ncert_competencies {i}: unknown competency {c}")
    uc={x["id"]:x for x in d.get("unit_competencies",[])}
    for i in mine_units-set(uc): errs.append(f"unit_competencies: missing {i}")
    for i,x in uc.items():
        if i not in UNITS: errs.append(f"unit_competencies: unknown id {i}"); continue
        comps=x.get("competencies",[])
        if not comps and not x.get("why"): errs.append(f"unit_competencies {i}: empty without why")
        for c in comps:
            if c not in NCF: errs.append(f"unit_competencies {i}: unknown competency {c}")
    if len(d.get("notes",[]))>5: errs.append("notes: at most five")
    print(f"seat {seat}: competencies {len(cc)}/{len(mine_ncf)} · graded {len(cg)}/{len(mine_c)} · ncert {len(nc)}/{len(mine_lo)} · units {len(uc)}/{len(mine_units)}")
    if errs:
        print(f"PROBLEMS {len(errs)}"); [print("  ",e) for e in errs[:60]]; return 1
    print("OK"); return 0
if __name__=="__main__": sys.exit(main(sys.argv[1]))
