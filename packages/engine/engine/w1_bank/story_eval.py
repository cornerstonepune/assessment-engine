"""How well the story reader names a story, scored against the gold: stories in words none of the engine's own
templates use, each with its case and, for one step, its answer (`supabase/seed/story_shape_gold.json`). Split from
`story_shape.py` on 2026-10-12, when settling a pair by its print (`story_cases.py`) brought the reader to its ceiling:
reading a story and scoring the reader are two jobs. `engine eval story_shape` runs it (rule 7).
"""

import json

from engine.adapters import jev, llm
from engine.core import db
from engine.w1_bank.story_shape import PURPOSE, name, taxonomies

GOLD = db.REPO_ROOT / "supabase" / "seed" / "story_shape_gold.json"


def gold():
    return json.loads(GOLD.read_text(encoding="utf-8"))["stories"]


def evaluate(conn, stories=None, ask=None, version=None):
    """Jev against the gold, read by the active prompt row or `version`: of the stories it names, how many cases are
    right and how many one-step answers are right of those it computes (the number that matters — a wrong case of the
    same operation still gives the right key); how many it leaves for a person. With no stories given, the gold's
    stories of the taxonomies the version reads: v1 is held to the + and − stories it was scored on."""
    if stories is None:
        reads = taxonomies(llm.active_prompt(conn, PURPOSE, version=version))
        of = {r["code"]: r["taxonomy"] for r in conn.execute("select code, taxonomy from taxonomy_case")}
        stories = [g for g in gold() if of.get(g["case"]) in reads]
    named = right = keyed = wrong_answer = left = 0
    misses, failed = [], []
    asking = jev.counting(ask or jev.decide, failed)
    for g in stories:
        before = len(failed)
        got = name(conn, g["text"], asking, version)
        if len(failed) > before:  # Jev not answering is not Jev unsure: nobody was asked
            continue
        by = "case" if "case" in g else "shape"  # a story given with its shape alone is held to its shape
        if got[by] is None:
            left += 1
            if (
                got["answer"] is not None
            ):  # the case waits on a person, the answer does not: it is held to the gold too
                keyed += 1
                wrong_answer += (got["answer"], got["remainder"]) != (g.get("answer"), g.get("remainder"))
            misses.append(
                {"text": g["text"], "want": g[by], "got": None, "why": got["why"], "ranked": got["ranked"]}
            )
            continue
        named += 1
        right += got[by] == g[by]
        if got["answer"] is not None:  # a key computed for a story that is not one step is a wrong key too
            keyed += 1
            wrong_answer += (got["answer"], got["remainder"]) != (g.get("answer"), g.get("remainder"))
        if got[by] != g[by]:
            misses.append(
                {"text": g["text"], "want": g[by], "got": got[by], "why": "", "ranked": got["ranked"]}
            )
    return {
        "n": len(stories),
        "named": named,
        "right": right,
        "left": left,
        "keyed": keyed,
        "wrong_answer": wrong_answer,
        "misses": misses,
        "unanswered": len(failed),
        "error": failed[0] if failed else "",
    }
