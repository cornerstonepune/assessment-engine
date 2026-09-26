#!/usr/bin/env python3
"""Renders docs/spine/index.html: the clickable spine page with docs/spine/spine.json inlined.
python3 research/spine_page.py"""

import json, sys
from pathlib import Path

R = Path(__file__).resolve().parents[1]
tpl = (R / "research/spine_page.html").read_text()
data = json.dumps(
    json.load(open(R / "docs/spine/spine.json")),
    ensure_ascii=False,
    separators=(",", ":"),
).replace("</", "<\\/")
out = R / "docs/spine/index.html"
out.write_text(tpl.replace("__SPINE__", data))
print("rendered", out, f"{out.stat().st_size // 1024} KB")
