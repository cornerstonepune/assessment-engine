#!/usr/bin/env python3
"""Checks the English foundation for Grades 3 and 4 (supabase/seed/english/), drafted from Cambridge Primary English
0058, Stages 3 and 4 (Nimish, 2026-10-21: "make the entire set of learning objectives, the difficulty levels, and
everything as per Grade 3 and Grade 4 of the Cambridge board … The teacher will only go and approve or edit").

The rows are drafts shaped like the maths seed tables, so they load later with no rework; nothing here touches the
database. The framework is read from the copy recorded in docs/crosswalk/sources.json, refused if its fingerprint
differs (research/crosswalk_cambridge.py). Every check is code: an objective that is neither on a paper nor listed as
observed by an educator, a level without its rule or three examples, an answer the rule does not give, an example
that shares a run of words with Cambridge's text.

python3 research/english_check.py            # exit 1 on any fault; prints the counts
python3 research/english_check.py --write    # also rewrites the derived files (english_derive.py)
python3 research/english_check.py --chunk DIR --only EN3.SPELL.   # a draft in DIR, faults for those skills only
"""

import argparse
import difflib
import functools
import json
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "research"))
import english_rules as er  # noqa: E402
DRAFT = R / "supabase/seed/english"
FRAMEWORK = "CAM-PRI-ENG-0058"
STAGES = {3: "G3", 4: "G4"}
TABLES = ("subject", "topic", "skill", "skill_level", "skill_level_sample", "passage", "misconception",
          "skill_mistake", "question_type", "not_on_paper", "rubric", "observed_skill")
# a rule's keys: the ones code checks on every example of the level, and the ones that only describe it
CHECKED = {"passage_words", "text_words", "answer_letters", "answer_words", "options", "items", "alpha_depth",
           "pattern", "errors", "answer_in_passage", "parts", "marks", "answer_from"}
DESCRIBED = {"context", "clues", "support", "text_kind", "focus", "note"}
REASONS = {"spoken", "listening", "read aloud", "a habit over time", "range of reading over a term",
           "extended writing", "handwriting", "on screen", "enjoyment and choice"}
# the American spellings a British-spelt paper must not carry (Cambridge writes British English)
AMERICAN = {"color", "colors", "colored", "colorful", "favorite", "favorites", "favor", "honor", "neighbor",
            "neighbors", "neighborhood", "behavior", "center", "centers", "theater", "gray", "mom", "moms",
            "organize", "organized", "realize", "realized", "recognize", "apologize", "traveled", "traveling",
            "jewelry", "catalog", "defense", "practicing", "flavor", "humor", "labor", "harbor", "rumor", "odor",
            "vapor", "armor", "meters", "liter", "liters", "airplane", "candies", "cookie", "cookies", "math"}
SHINGLE, LONG_SHINGLE = 6, 8


def load(root=DRAFT, chunk=None):
    """Every table as a list of rows. A chunk (a draft not yet merged) replaces the tracked samples of the skills it
    holds samples for and the passages it holds by code, and adds its other rows to the tracked ones."""
    t = {}
    for name in TABLES:
        path = root / f"{name}.json"
        t[name] = next(iter(json.loads(path.read_text()).values())) if path.exists() else []
        if chunk and (extra := Path(chunk) / f"{name}.json").exists():
            rows = next(iter(json.loads(extra.read_text()).values()))
            if name == "skill_level_sample":
                mine = {r["skill_code"] for r in rows}
                t[name] = [r for r in t[name] if r["skill_code"] not in mine]
            elif name == "passage":
                mine = {r["code"] for r in rows}
                t[name] = [r for r in t[name] if r["code"] not in mine]
            t[name] = t[name] + rows
    return t


@functools.cache
def framework():
    """The framework's objectives with their words, and its whole text, from the recorded copy (fingerprint checked)."""
    import crosswalk_cambridge as cc
    import pymupdf

    source = next(s for s in json.loads(cc.SOURCES.read_text()) if s["framework"] == FRAMEWORK)
    rows, _, missing, _ = cc.read(source)
    if missing:
        raise SystemExit(f"{FRAMEWORK}: {len(missing)} objectives not found on their page: {missing[:5]}")
    text = " ".join(page.get_text() for page in pymupdf.open(cc.fetch(source)))
    return {r["code"]: dict(r, words=cc.whole(r)) for r in rows}, cc.norm(text)


def vocabulary():
    v = json.loads((R / "supabase/seed/vocabulary.json").read_text())
    return [d["code"] for d in v["difficulties"]], [g["code"] for g in v["grades"]]


def units():
    return {u["id"]: u for u in json.loads((R / "docs/spine/sources/school_units.json").read_text())}


def rubric_scale():
    """The four rubric levels, read from the drafting method's own table (docs/crosswalk/drafting-method.md)."""
    text = (R / "docs/crosswalk/drafting-method.md").read_text()
    return [w.strip() for w in re.search(r"The rubric scale: (.*?)\.", text).group(1).split(",")]


def shingles(text, n):
    w = [x.lower().replace("’", "'") for x in er.words(text)]
    return {" ".join(w[i : i + n]) for i in range(len(w) - n + 1)}


def example_texts(s, passages):
    """Every piece of text an example puts on a paper or in its key."""
    out = [s.get("ask") or "", s.get("text") or "", passages.get(s.get("passage"), {}).get("text", "")]
    for v in (s.get("options"), s.get("answer"), s.get("accept"), s.get("key_points")):
        out += flat(v)
    return out


def flat(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    if isinstance(v, dict):
        return [x for k, val in v.items() for x in [k, *flat(val)]]
    return [x for i in v for x in flat(i)]


def check_coverage(t, objs):
    """Every Stage 3 and 4 objective is on a paper (a skill of its grade) or listed as observed by an educator."""
    faults, paper = [], {}
    for s in t["skill"]:
        for c in s["objectives"]:
            paper.setdefault(c, []).append(s["code"])
            if c not in objs:
                faults.append(f"{s['code']}: {c} is not an objective of {FRAMEWORK}")
            elif STAGES.get(objs[c]["stage"]) != s["grade"]:
                faults.append(f"{s['code']}: {c} is Stage {objs[c]['stage']}, the skill is {s['grade']}")
    seen = {}
    for n in t["not_on_paper"]:
        c = n["objective"]
        seen[c] = seen.get(c, 0) + 1
        if c not in objs:
            faults.append(f"not on paper: {c} is not an objective of {FRAMEWORK}")
        if c in paper:
            faults.append(f"{c} is both on a paper ({paper[c]}) and listed as not on paper")
        if n.get("reason") not in REASONS or not n.get("why", "").strip() or not n.get("observe", "").strip():
            faults.append(f"not on paper: {c} needs a reason from the list, why and how an educator observes it")
    faults += [f"not on paper: {c} listed {k} times" for c, k in seen.items() if k > 1]
    for c, o in objs.items():
        if o["stage"] in STAGES and c not in paper and c not in seen:
            faults.append(f"{c}: Stage {o['stage']} objective neither on a paper nor observed (silently dropped)")
    return faults


def check_skills(t):
    import crosswalk_drafts as cd

    allowed, never = cd.words()
    faults, codes = [], {s["code"]: s for s in t["skill"]}
    _, grades = vocabulary()
    topics, qtypes, known = {x["code"] for x in t["topic"]}, {q["code"]: q for q in t["question_type"]}, units()
    names = [s["code"] for s in t["skill"]]
    faults += [f"{c}: defined twice" for c in sorted({c for c in names if names.count(c) > 1})]
    for s in t["skill"]:
        c = s["code"]
        if s["grade"] not in grades or s["topic"] not in topics:
            faults.append(f"{c}: grade {s['grade']} or topic {s['topic']} is not a row")
        faults += cd.sentence_faults(c, s["learning_objective"], allowed, never)
        for q in s["question_types"]:
            if q not in qtypes or qtypes[q]["reaches"] == "observed":
                faults.append(f"{c}: {q} is not a question type a paper carries")
        for u in s["school_units"]:
            if u not in known or s["grade"] not in known[u]["bands"]:
                faults.append(f"{c}: {u} is not a school unit of {s['grade']}")
        for b in s["before"]:
            if b not in codes or b == c:
                faults.append(f"{c}: before {b} is not another skill")
            elif (grades.index(codes[b]["grade"]), codes[b]["order"]) >= (grades.index(s["grade"]), s["order"]):
                faults.append(f"{c}: {b} comes before it but is taught after it")
    for g in {s["grade"] for s in t["skill"]}:
        mine = sorted((s for s in t["skill"] if s["grade"] == g), key=lambda s: s["order"])
        if [s["order"] for s in mine] != list(range(1, len(mine) + 1)):
            faults.append(f"{g}: teaching order is not 1 to {len(mine)}")
        numbered = [unit_number(known.get(s["school_units"][0])) for s in mine]
        numbered = [n for n in numbered if n is not None]
        if numbered != sorted(numbered):
            faults.append(f"{g}: the teaching order does not follow the school's units: {numbered}")
        for a, b in [(a, b) for i, a in enumerate(mine) for b in mine[i + 1 :]]:
            for field in ("name", "learning_objective"):
                ratio = difflib.SequenceMatcher(None, a[field].lower(), b[field].lower()).ratio()
                if ratio > 0.85:
                    faults.append(f"{a['code']} and {b['code']}: {field}s are the same skill ({ratio:.2f})")
    return faults


def unit_number(unit):
    m = re.match(r"Unit (\d+)", (unit or {}).get("unit", ""))
    return int(m.group(1)) if m else None


def check_levels(t):
    faults, levels = [], {}
    order, _ = vocabulary()
    skills = {s["code"]: s for s in t["skill"]}
    for lv in t["skill_level"]:
        key = (lv["skill_code"], lv["difficulty"])
        if key in levels:
            faults.append(f"{key}: twice")
        levels[key] = lv
        s = skills.get(lv["skill_code"])
        if not s or lv["grade"] != s["grade"]:
            faults.append(f"{key}: no such skill, or the grade differs from the skill's")
        if not lv.get("looks_like", "").strip() or "\n" in lv["looks_like"] or len(lv["looks_like"].split()) > 30:
            faults.append(f"{key}: the rule needs one line of 30 words or fewer saying what changes")
        if not lv.get("rule") or (bad := set(lv["rule"]) - CHECKED - DESCRIBED):
            faults.append(f"{key}: rule {lv.get('rule')} is empty or has keys code does not know: {bad if lv.get('rule') else ''}")
        elif not set(lv["rule"]) & CHECKED:
            faults.append(f"{key}: the rule has nothing code can check on its examples")
    for s in skills.values():
        mine = [levels.get((s["code"], d)) for d in order]
        if None in mine:
            faults.append(f"{s['code']}: levels {[d for d, m in zip(order, mine, strict=True) if not m]} missing")
            continue
        for a, b in [(a, b) for i, a in enumerate(mine) for b in mine[i + 1 :]]:
            if a["looks_like"] == b["looks_like"] or a["rule"] == b["rule"]:
                faults.append(f"{s['code']}: {a['difficulty']} and {b['difficulty']} are the same level")
    return faults, levels


def check_mistakes(t):
    faults = []
    codes = {m["code"]: m for m in t["misconception"]}
    skills = {s["code"] for s in t["skill"]}
    names = [m["code"] for m in t["misconception"]]
    faults += [f"{c}: defined twice" for c in sorted({c for c in names if names.count(c) > 1})]
    for m in t["misconception"]:
        if not re.fullmatch(r"M_ENG_[A-Z0-9_]+", m["code"]) or not m.get("name") or not m.get("description"):
            faults.append(f"{m['code']}: needs an M_ENG_ code, a name and what the wrong answer looks like")
        if m.get("detectable_by") not in ("answer_lookup", "model", "educator"):
            faults.append(f"{m['code']}: detectable_by must say who can spot it")
    used = {}
    for link in t["skill_mistake"]:
        if link["skill_code"] not in skills or link["misconception_code"] not in codes:
            faults.append(f"skill_mistake {link}: no such skill or mistake")
        used.setdefault(link["skill_code"], []).append(link["misconception_code"])
    faults += [f"{c}: no skill shows this mistake" for c in codes if c not in {m for v in used.values() for m in v}]
    faults += [f"{s}: fewer than two named mistakes" for s in skills if len(used.get(s, [])) < 2]
    faults += [f"{s}: a mistake linked twice" for s, v in used.items() if len(v) != len(set(v))]
    return faults, used


SCALE = ["yes", "sometimes", "not yet"]


def check_observed(t, pdf_text):
    """Every objective that is not on a paper is in exactly one observed skill: a milestone an educator marks yes,
    sometimes or not yet, for the observation engine to come. None is on a paper, none copies Cambridge's words."""
    faults, seen = [], {}
    long = shingles(pdf_text, LONG_SHINGLE)
    off = {n["objective"]: n for n in t["not_on_paper"]}
    codes = [o["code"] for o in t["observed_skill"]]
    faults += [f"{c}: defined twice" for c in sorted({c for c in codes if codes.count(c) > 1})]
    for o in t["observed_skill"]:
        c = o["code"]
        if not re.fullmatch(r"EN[34]\.OBS\.\d{2}", c) or o.get("grade") != f"G{c[2]}":
            faults.append(f"{c}: needs a code EN3.OBS.nn or EN4.OBS.nn and the grade it names")
        if o.get("kind") not in REASONS or not o.get("name", "").strip():
            faults.append(f"{c}: needs a name and a kind from {sorted(REASONS)}")
        m = o.get("milestone", "")
        if not m.strip() or "\n" in m or len(m.split()) > 30:
            faults.append(f"{c}: the milestone is one sentence of 30 words or fewer")
        if o.get("scale") != SCALE:
            faults.append(f"{c}: the scale is {SCALE}")
        for obj in o.get("objectives") or []:
            seen[obj] = seen.get(obj, 0) + 1
            if obj not in off:
                faults.append(f"{c}: {obj} is not an objective listed as not on paper")
            elif off[obj]["objective"][0] != c[2]:
                faults.append(f"{c}: {obj} is of another grade")
        if not o.get("objectives"):
            faults.append(f"{c}: names no objective")
        if hit := shingles(o.get("name", "") + " " + m, LONG_SHINGLE) & long:
            faults.append(f"{c}: copies Cambridge's words: {sorted(hit)[:2]}")
    faults += [f"{obj}: in {k} observed skills" for obj, k in seen.items() if k > 1]
    faults += [f"{obj}: not on paper and in no observed skill" for obj in off if obj not in seen]
    return faults


def check_rubrics(t):
    faults, scale = [], rubric_scale()
    import crosswalk_drafts as cd

    _, never = cd.words()
    for r in t["rubric"]:
        if r.get("scale") != scale:
            faults.append(f"{r['code']}: scale is not the drafting method's {scale}")
        for k in r["skill_codes"]:
            if k not in {s["code"] for s in t["skill"]}:
                faults.append(f"{r['code']}: {k} is not a skill")
        for crit in r["criteria"]:
            if list(crit.get("levels", {})) != scale:
                faults.append(f"{r['code']}.{crit['code']}: needs one line for each of {scale}")
            for lvl, line in crit.get("levels", {}).items():
                faults += cd.sentence_faults(f"{r['code']}.{crit['code']}.{lvl}", line, set(), never, cap=40, first=False)
    return faults


def main(argv=None):
    import english_derive
    import english_samples

    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--chunk")
    ap.add_argument("--only", default="")
    a = ap.parse_args(argv)
    t = load(chunk=a.chunk)
    objs, pdf_text = framework()
    faults = check_skills(t)
    lv_faults, levels = check_levels(t)
    mk_faults, used = check_mistakes(t)
    sm_faults, ran = english_samples.check(t, levels, used, objs, pdf_text)
    faults += lv_faults + mk_faults + sm_faults + check_rubrics(t)
    if not a.chunk or t["observed_skill"]:
        faults += check_observed(t, pdf_text)
    if not a.chunk:
        faults += check_coverage(t, objs)
        faults += english_derive.stale(t, objs, write=a.write)
    only = tuple(p for p in a.only.split(",") if p)
    if only:
        faults = [f for f in faults if any(p in f for p in only)]
    counts = english_derive.counts(t, objs, ran)
    print(json.dumps(counts, indent=1))
    for f in faults:
        print("FAULT", f)
    print(f"{len(faults)} faults")
    return 1 if faults else 0


if __name__ == "__main__":
    sys.exit(main())
