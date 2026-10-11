"""The school's own objectives read as the school wrote them (goals/c1-whole-curriculum.yaml).

Twelve Grade 4 objectives came through the Skill Map Review import with "art" replaced by "Visual arts" inside words
— "pVisual artsitioning", "chVisual artss", "PVisual artss of a whole" — the subject's rename run over substrings.
The Curriculum's grades cite these objectives (ADR 0047, A6), so a broken one is a broken source.
"""

import json
import pathlib
import re

REGISTRY = pathlib.Path(__file__).resolve().parents[3] / "supabase" / "seed" / "registry.json"
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
