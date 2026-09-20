"""Does a version of `legacy_extract` read a page the way a person did? `engine read eval`.

Written after v3 shipped without one and regressed the reader from 24/24 to 17/24 — by quietly
supplying the *correct* answer in seven places instead of the wrong one the child actually wrote.
Every mark came back "correct", the paper looked perfect, and nothing in the system could tell.
Rule 7 says every model output ships with an eval; this is the one that was owed.

The gold is `supabase/seed/read_gold.json`: what a person saw, by eye, on a real page. It contains
answers that are WRONG on purpose, because a reader that computes rather than transcribes scores
perfectly against a gold set of right answers and catastrophically against this one.

The number is per response, which is W3's unit (goals/w3-read-and-graph.yaml), and it is the worst
of `runs` repeats rather than one run's luck — the same guard the skill matcher needed when it
swung 84-97% across passes.
"""

import json
from pathlib import Path

from engine import db, legacy
from engine.adapters import llm

GOLD = db.REPO_ROOT / "supabase" / "seed" / "read_gold.json"
ASSESSMENTS = "~/cornerstone/assessments"


def gold_sheets():
    return json.loads(GOLD.read_text())["sheets"]


def _key(a):
    return f"{a['n']}{a.get('part', '')}"


def read_once(conn, sheet, root=ASSESSMENTS):
    """One pass of the active `legacy_extract` over a gold sheet → {key: read}.

    Reads exactly as `legacy.import_scan` does — same masks from the paper row, same expected count
    per page — so the eval measures the reader in service, not a convenient version of it.
    """
    template, by_key = legacy.paper_rows(conn, sheet["paper"])
    paper = template["key"] if isinstance(template["key"], dict) else json.loads(template["key"])
    masks = {p["n"]: p.get("mask", 0) for p in paper["pages"]}
    out = {}
    for page_no, jpeg in enumerate(legacy.render_pages(Path(root).expanduser() / sheet["file"]), 1):
        expected = sum(1 for it in by_key.values() if it["spec"].get("page", 1) == page_no)
        jpeg = legacy.mask_name_band(jpeg, masks[page_no])
        got = llm.generate(conn, "legacy_extract", {"expected": str(expected)}, images=[jpeg])
        for r in got["items"]:
            out[_key(r)] = r
    return out


def score(gold_answers, read):
    """→ per-response counts. `missing` is the one that hides: a response with no row at all cannot
    be corrected by anyone, because nobody is shown it."""
    exact = wrong_value = missing = state_wrong = 0
    details = []
    for a in gold_answers:
        k = _key(a)
        got = read.get(k)
        if got is None:
            missing += 1
            details.append((k, a["child_answer"], "— no row —"))
            continue
        said = legacy.normalise_answer(got.get("child_answer", "") or "")
        want = legacy.normalise_answer(a["child_answer"] or "")
        if said == want:
            exact += 1
        else:
            wrong_value += 1
            details.append((k, want or "(blank)", said or "(blank)"))
        if "answer_state" in got and got["answer_state"] != a["answer_state"]:
            state_wrong += 1
    total = len(gold_answers)
    return {
        "total": total,
        "exact": exact,
        "wrong_value": wrong_value,
        "missing": missing,
        "state_wrong": state_wrong,
        "read_exactly_right": round(exact / total, 4) if total else 0.0,
        "responses_given_a_row": round((total - missing) / total, 4) if total else 0.0,
        "details": details,
    }


def run(conn, runs=1, root=ASSESSMENTS):
    """Every gold sheet, `runs` times. The reported rate is the WORST run, never the mean."""
    per_run = []
    for _ in range(runs):
        agg = {"total": 0, "exact": 0, "wrong_value": 0, "missing": 0, "state_wrong": 0, "details": []}
        for sheet in gold_sheets():
            s = score(sheet["answers"], read_once(conn, sheet, root))
            for k in ("total", "exact", "wrong_value", "missing", "state_wrong"):
                agg[k] += s[k]
            agg["details"] += [(sheet["file"], *d) for d in s["details"]]
        agg["read_exactly_right"] = round(agg["exact"] / agg["total"], 4) if agg["total"] else 0.0
        agg["responses_given_a_row"] = (
            round((agg["total"] - agg["missing"]) / agg["total"], 4) if agg["total"] else 0.0
        )
        per_run.append(agg)
    worst = min(per_run, key=lambda r: r["read_exactly_right"])
    return worst, per_run
