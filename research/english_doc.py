#!/usr/bin/env python3
"""The English educator's review document, written from the seed rows (supabase/seed/english/) as one Markdown file
per tab into data/english_doc/ (gitignored): a tab for each grade and topic, one section per skill, and a tab of
the skills an educator observes. Each skill's section quotes its Cambridge objectives word for word, read at build
time from the recorded copy of the framework (research/english_check.py), so Cambridge's words are never committed;
then its kinds of question (one right answer that code checks, or an open answer a person reads), what each level
means, the passages, and every sample with its right answer and its likely wrong answers, each with the mistake it
shows. Written for a teacher: no codes but Cambridge's own.

python3 research/english_doc.py      # prints the files it wrote
"""

import json
import re
import sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R / "research"))
import english_check as ec  # noqa: E402

OUT = R / "data/english_doc"
LEVELS = ["Easy", "Medium", "Hard", "Advance"]
GRADE = {"G3": "Grade 3", "G4": "Grade 4"}


def cell(text):
    """Text safe inside a table cell: one line, pipes escaped."""
    return re.sub(r"\s*\n\s*", " / ", str(text)).replace("|", "\\|").strip()


def shown(v):
    """An answer as a teacher reads it."""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        return "; ".join(f"{k}: {', '.join(x) if isinstance(x, list) else x}" for k, x in v.items())
    if v and isinstance(v[0], list):
        return "; ".join(f"{a} → {b}" for a, b in v)
    return ", ".join(map(str, v))


def question(s, passages):
    parts = [s["ask"]]
    if s.get("passage"):
        parts.append(f"(Passage {passages[s['passage']]})")
    if s.get("text"):
        parts.append(f"The educator reads aloud: *{s['text']}*" if s["question_type"] == "ENG.DICTATION" else f"*{s['text']}*")
    opts = s.get("options")
    if isinstance(opts, list):
        parts.append("Options: " + " · ".join(opts))
    elif isinstance(opts, dict):
        parts.append("Match: " + " · ".join(opts.get("left", [])) + " — with — " + " · ".join(opts.get("right", [])))
    return " ".join(parts)


def right(s, kinds):
    out = shown(s["answer"])
    if s.get("accept"):
        out += f" (also right: {', '.join(s['accept'])})"
    if kinds[s["question_type"]]["answer"] == "open" and s.get("key_points"):
        out = f"A good answer: {out} Looks for: {'; '.join(s['key_points'])}."
    return out


def wrongs(s, mistakes):
    return "; ".join(f"*{w}* — {mistakes[c]['name'].rstrip('.')}" for w, c in (s.get("wrong") or {}).items())


def skill_section(sk, t, objs, kinds, mistakes):
    levels = {lv["difficulty"]: lv for lv in t["skill_level"] if lv["skill_code"] == sk["code"]}
    samples = sorted(
        (s for s in t["skill_level_sample"] if s["skill_code"] == sk["code"]),
        key=lambda s: (LEVELS.index(s["difficulty"]), sk["question_types"].index(s["question_type"]), s["n"]),
    )
    used = []
    for s in samples:
        if s.get("passage") and s["passage"] not in used:
            used.append(s["passage"])
    numbers = {code: i for i, code in enumerate(used, 1)}
    by_code = {p["code"]: p for p in t["passage"]}
    out = [f"## {GRADE[sk['grade']]} · skill {sk['order']}: {sk['name']}", ""]
    out += ["**Cambridge objectives**", ""]
    for c in sk["objectives"]:
        out += [f"> **{c}** {objs[c]['words']}", ""]
    out += [f"**What the child does.** {sk['learning_objective']}", ""]
    out += ["**Kinds of question**", "", "| Kind | Answer | Who checks it | Levels |", "| --- | --- | --- | --- |"]
    for q in sk["question_types"]:
        k = kinds[q]
        at = [d for d in LEVELS if any(s["difficulty"] == d and s["question_type"] == q for s in samples)]
        answer, who = (
            ("One right answer", "Code checks it")
            if k["answer"] == "one"
            else ("Open answer", "A person reads every answer")
        )
        out.append(f"| {k['name']} | {answer} | {who} | {', '.join(at)} |")
    out += ["", "**What each level means**", "", "| Level | What changes |", "| --- | --- |"]
    out += [f"| {d} | {cell(levels[d]['looks_like'])} |" for d in LEVELS]
    out.append("")
    if used:
        out += ["**Passages**", ""]
        for code in used:
            p = by_code[code]
            out += [f"*Passage {numbers[code]}: {p.get('title') or 'untitled'}*", ""]
            out += ["> " + line if line.strip() else ">" for line in p["text"].split("\n")]
            out.append("")
    for d in LEVELS:
        mine = [s for s in samples if s["difficulty"] == d]
        out += [f"### {d}", ""]
        for q in sk["question_types"]:
            rows = [s for s in mine if s["question_type"] == q]
            if not rows:
                continue
            out += [f"**{kinds[q]['name']}**", "", "| # | Question | Right answer | Likely wrong answers and the mistake each shows |",
                    "| --- | --- | --- | --- |"]  # fmt: skip
            for s in rows:
                out.append(
                    f"| {s['n']} | {cell(question(s, numbers))} | {cell(right(s, kinds))} | {cell(wrongs(s, mistakes))} |"
                )
            out.append("")
    return "\n".join(out)


def observed_tab(t, objs):
    out = ["# Skills an educator observes", "",
           "Not on a paper: speaking, listening, reading aloud and work seen over time. Each is one milestone an "
           "educator marks yes, sometimes or not yet, for the observation tool that comes later.", ""]  # fmt: skip
    off = {n["objective"]: n for n in t["not_on_paper"]}
    for g in ("G3", "G4"):
        out += [f"## {GRADE[g]}", "", "| Cambridge objective | Milestone (yes / sometimes / not yet) | How to observe it |",
                "| --- | --- | --- |"]  # fmt: skip
        for o in (x for x in t["observed_skill"] if x["grade"] == g):
            quote = " ".join(f"**{c}** {objs[c]['words']}" for c in o["objectives"])
            how = " ".join(off[c]["observe"] for c in o["objectives"])
            out.append(f"| {cell(quote)} | **{cell(o['name'])}.** {cell(o['milestone'])} | {cell(how)} |")
        out.append("")
    return "\n".join(out)


def main():
    t = ec.load()
    objs, _ = ec.framework()
    kinds = {q["code"]: q for q in t["question_type"]}
    mistakes = {m["code"]: m for m in t["misconception"]}
    topics = sorted(t["topic"], key=lambda x: x["order"])
    OUT.mkdir(parents=True, exist_ok=True)
    written = []
    for g in ("G3", "G4"):
        for tp in topics:
            mine = sorted((s for s in t["skill"] if s["grade"] == g and s["topic"] == tp["code"]), key=lambda s: s["order"])
            if not mine:
                continue
            body = [f"# {GRADE[g]}: {tp['name']}", ""]
            body += [skill_section(s, t, objs, kinds, mistakes) + "\n" for s in mine]
            path = OUT / f"{g}-{tp['order']:02d}-{tp['code'].split('.')[1].lower()}.md"
            path.write_text("\n".join(body))
            written.append((path, tp["name"], len(mine)))
    (OUT / "observed.md").write_text(observed_tab(t, objs))
    written.append((OUT / "observed.md", "Skills an educator observes", len(t["observed_skill"])))
    for path, name, n in written:
        print(f"{path.relative_to(R)}\t{name}\t{n}\t{path.stat().st_size} bytes")
    json.dump([[str(p.relative_to(R)), n] for p, n, _ in written], (OUT / "index.json").open("w"))


if __name__ == "__main__":
    main()
