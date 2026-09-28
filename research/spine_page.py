#!/usr/bin/env python3
"""Renders docs/spine/index.html, the spine page: every item on the same five steps (why, what NCF-SE asks, in the
grade, when, how we check), a grade's year fortnight by fortnight, and the school day across the grades.

Built from docs/spine/spine.json (the spine), docs/spine/plan.json (the plan, from research/plan_build.py) and the
threads research/spine_thread.py works out. research/spine_page.html is the frame; research/spine_view.js and
research/spine_plan.js only draw. Everything is inlined, so the one file is the page. No model is called.

python3 research/spine_page.py
"""

import collections
import json
import re
from pathlib import Path

import spine_thread

R = Path(__file__).resolve().parents[1]
TEMPLATE = R / "research/spine_page.html"
SCRIPTS = [R / "research/spine_view.js", R / "research/spine_plan.js"]
OUT = R / "docs/spine/index.html"
# The thread the page opens on: Grade 3's addition and subtraction, which reaches all five steps.
START = "unit.315~3"
KEEP = (
    "text", "code", "stage", "grade", "subject", "area", "src", "why", "counter", "capture", "setting",
    "from_age", "objectives", "samples", "relabelled", "bands", "domain",
)  # fmt: skip
# 122 of the school's arts and social-science units are named "• Title: … / • Focus: … / • Key Concepts: …"; the page
# names them by their title and shows the focus and key concepts on their card, word for word.
TITLED = re.compile(
    r"^\W*Title:\s*(?P<label>.+?)\s*/\s*\W*Focus:\s*(?P<focus>.+?)(?:\s*/\s*\W*Key Concepts:\s*(?P<concepts>.+))?$",
    re.DOTALL,
)


def mostly_shows(spine):
    """{capability: the word(s) most of its behaviours are evidence for}, from the council's behaviours."""
    shown, word_of = collections.defaultdict(list), collections.defaultdict(list)
    for e in spine["edges"]:
        if e["kind"] == "shown_by":
            shown[e["from"]].append(e["to"])
        if e["kind"] == "evidence_for":
            word_of[e["from"]].append(e["to"])
    label = {n["id"]: n["label"] for n in spine["nodes"]}
    out = {}
    for cap, behaviours in shown.items():
        counts = collections.Counter(w for b in behaviours for w in word_of[b])
        top = max(counts.values(), default=0)
        out[cap] = [label[w] for w, k in counts.most_common() if k == top]
    return out


def page_data():
    """Everything the page draws, with items named by their ids."""
    spine = json.loads((R / "docs/spine/spine.json").read_text())
    plan = json.loads((R / "docs/spine/plan.json").read_text())
    threads, opened = spine_thread.build(spine, plan)
    words = mostly_shows(spine)
    items = {}
    for n in spine["nodes"]:
        item = {"layer": n["layer"], "label": n["label"]}
        item.update({k: n[k] for k in KEEP if n.get(k) not in (None, "", [])})
        titled = TITLED.match(n["label"]) if n["layer"] == "unit" else None
        if titled:
            item.update({k: v.strip() for k, v in titled.groupdict().items() if v})
        if n["id"] in words:
            item["words"] = words[n["id"]]
        items[n["id"]] = item
    subjects = {
        n["id"].split(".", 1)[1]: n["label"]
        for n in spine["nodes"]
        if n["layer"] == "subject"
    }
    return {
        "built": spine["built"],
        "sources": spine["sources"],
        "notes": spine["notes"],
        "subjects": subjects,
        "steps": spine_thread.STEPS,
        "home": spine_thread.HOME,
        "items": items,
        "threads": threads,
        "open": opened,
        "start": START,
        "plan": plan,
    }


def compact(data):
    """The page's copy: items as a list and each one named by its place in it, which halves the file. The syllabus
    lists behind the year are left out; the year itself is kept."""
    ids = list(data["items"])
    at = {i: n for n, i in enumerate(ids)}

    def grp(g):
        g = dict(g)
        for field in ("ids", "on"):
            if field in g:
                g[field] = [at[i] for i in g[field]]
        if "head" in g:
            g["head"] = at[g["head"]]
        return g

    threads = {
        k: {
            **t,
            "id": at[t["id"]],
            "steps": {s: [grp(g) for g in gs] for s, gs in t["steps"].items()},
        }
        for k, t in data["threads"].items()
    }
    plan = dict(data["plan"])
    plan["year"] = {
        g: {
            slot: [[[at[x], n] for x, n in cell] for cell in cells]
            for slot, cells in slots.items()
        }
        for g, slots in plan["year"].items()
    }
    plan["grades"] = {
        g: {k: v for k, v in e.items() if k != "slots"}
        for g, e in plan["grades"].items()
    }
    return {
        **data,
        "items": [{"id": i, **data["items"][i]} for i in ids],
        "threads": threads,
        "open": [data["open"].get(i) for i in ids],
        "plan": plan,
    }


def render():
    data = json.dumps(compact(page_data()), ensure_ascii=False, separators=(",", ":"))
    script = "\n".join(f.read_text() for f in SCRIPTS)
    page = TEMPLATE.read_text().replace("__PAGE__", data.replace("</", "<\\/"))
    return page.replace("__JS__", script)


if __name__ == "__main__":
    OUT.write_text(render())
    print("rendered", OUT, f"{OUT.stat().st_size // 1024} KB")
