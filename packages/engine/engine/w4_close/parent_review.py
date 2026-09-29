"""The parent report's second reader (goals/w4c-parent-report.yaml): a model reads each draft against its facts and
quotes every sentence the facts do not support. Code holds the words to the facts where a pattern can
(`parent_check`); what a sentence *means* only a reader can hold — v7 to v12 on live, each passing the check, still
said "has mastered" of a skill only improving, "on more than one paper" of skills seen on one, and made thirty-five a
three-digit number. What the reviewer quotes goes back to the writer, as the check's findings do.

Scored against a hand-judged gold set (supabase/seed/parent_review_gold.json): every wrong sentence flagged, and
nothing in a draft a person read and found right (rule 7; the bar is all of them, rule 12).
"""

import json
import re

from engine.adapters import llm
from engine.core import db

PURPOSE = "parent_review"
GOLD = "supabase/seed/parent_review_gold.json"


def told(facts):
    """What the writer was given: every fact but what comes next, which the page says itself."""
    return {k: v for k, v in facts.items() if k != "next"}


def review(conn, facts, draft, ask=None, version=None, meta=None):
    """→ the reviewer's findings, one line each: the quoted words and the fact they go beyond. [] when all hold."""
    ask = ask or llm.generate
    out = ask(conn, PURPOSE, {"facts": told(facts), "draft": draft}, meta=meta, version=version)
    return [f"{u['quote']!r} is not supported: {u['why']}" for u in out["unsupported"]]


def _words(text):
    return set(re.findall(r"[a-z]+", text.lower()))


def _same(flagged, bad):
    """A flag lands on a bad quote when one holds the other, or they share most of their words."""
    a, b = flagged.lower().strip(" .'\""), bad.lower().strip(" .'\"")
    if a in b or b in a:
        return True
    wa, wb = _words(a), _words(b)
    return bool(wb) and len(wa & wb) / len(wb) >= 0.6


def evaluate(conn, version=None, ask=None, gold=None):
    """Every case of the gold set reviewed once → {"n", "bad", "caught", "false_flags", "misses", "wrong"}."""
    ask = ask or llm.generate
    gold = gold or json.loads((db.REPO_ROOT / GOLD).read_text())
    out = {"version": version, "n": 0, "bad": 0, "caught": 0, "false_flags": 0, "misses": [], "wrong": []}
    for c in gold["cases"]:
        got = ask(conn, PURPOSE, {"facts": told(c["facts"]), "draft": c["draft"]}, meta={}, version=version)
        quotes = [u["quote"] for u in got["unsupported"]]
        out["n"] += 1
        out["bad"] += len(c["bad"])
        for b in c["bad"]:
            if any(_same(q, b) for q in quotes):
                out["caught"] += 1
            else:
                out["misses"].append({"ref": c["ref"], "bad": b, "flagged": quotes})
        for u in got["unsupported"]:
            if not any(_same(u["quote"], b) for b in c["bad"]):
                out["false_flags"] += 1
                out["wrong"].append({"ref": c["ref"], "quote": u["quote"], "why": u["why"]})
    return out
