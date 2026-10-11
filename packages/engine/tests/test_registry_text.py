"""The school's own objectives read as the school wrote them (goals/c1-whole-curriculum.yaml).

Twelve Grade 4 objectives came through the Skill Map Review import with "art" replaced by "Visual arts" inside words
— "pVisual artsitioning", "chVisual artss", "PVisual artss of a whole" — the subject's rename run over substrings.
The Curriculum's grades cite these objectives (ADR 0047, A6), so a broken one is a broken source.
"""

import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[3]
REGISTRY = ROOT / "supabase" / "seed" / "registry.json"
# a subject's name glued to letters on either side: the replacement ran inside a word
BROKEN = re.compile(r"[A-Za-z]Visual arts|Visual arts[a-z]")


def _strings(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _strings(v, f"{path}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _strings(v, f"{path}[{i}]")
    elif isinstance(node, str):
        yield path, node


def test_the_schools_objectives_read_as_the_school_wrote_them():
    said = list(_strings(json.loads(REGISTRY.read_text())))
    assert [f"{p}: {s[:80]}" for p, s in said if BROKEN.search(s)] == []
    # and the repaired words are the school's own, not dropped
    text = "\n".join(s for _, s in said)
    for words in (
        "partitioning, rounding",
        "Parts of a whole",
        "bar charts",
        "quarter-turns",
        "start/end times",
    ):
        assert words in text, words


def test_the_spines_units_read_as_the_registry_does():
    """The spine's unit table is the registry's units as imported on 2026-09-15, its ids cited by the seats' records:
    repaired in place, ids kept, so the plan finds every objective's unit by its words. A unit the broken text had split
    in two ("Part 2" beside "PVisual arts 2") is one unit again, its objectives under the first id."""
    units = json.loads((ROOT / "docs" / "spine" / "sources" / "school_units.json").read_text())
    assert [f"{u['id']}: {s[:80]}" for u in units for _, s in _strings(u) if BROKEN.search(s)] == []
    reg = json.loads(REGISTRY.read_text())
    keys = {(u["subject"], u["unit"]) for u in units}
    assert [o["code"] for o in reg["learning_objectives"] if (o["subject"], o["unit"]) not in keys] == []
    plan = json.loads((ROOT / "docs" / "spine" / "plan.json").read_text())
    rows = [r for e in plan["grades"].values() for v in e["slots"].values() for r in v if isinstance(r, list)]
    assert [r for r in rows if r and r[0] is None] == []
    assert not BROKEN.search(json.dumps(plan, ensure_ascii=False))
