#!/usr/bin/env python3
"""Renders docs/spine/index.html: the clickable spine page with docs/spine/spine.json and the Plan view
(docs/spine/plan.json, research/spine_plan.js) inlined.
python3 research/spine_page.py"""

import json
from pathlib import Path

R = Path(__file__).resolve().parents[1]
tpl = (R / "research/spine_page.html").read_text()
data = json.dumps(
    json.load(open(R / "docs/spine/spine.json")),
    ensure_ascii=False,
    separators=(",", ":"),
).replace("</", "<\\/")
plan = (R / "docs/spine/plan.json").read_text().replace("</", "<\\/")
js = (R / "research/spine_plan.js").read_text()
out = R / "docs/spine/index.html"
out.write_text(
    tpl.replace("__SPINE__", data).replace("__PLAN__", plan).replace("__PLANJS__", js)
)
print("rendered", out, f"{out.stat().st_size // 1024} KB")
