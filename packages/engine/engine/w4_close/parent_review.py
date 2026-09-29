"""The parent report's second reader (goals/w4c-parent-report.yaml, goals/j5-parent-review-jev.yaml): every sentence of
a draft read against its facts, each by the cheapest reader that can answer it. Code holds the words to the facts where
a pattern can (`parent_check`, first, as a report is written); what a sentence *means* only a reader can hold — v7 to
v12 on live, each passing the check, still said "has mastered" of a skill only improving, "on more than one paper" of
skills seen on one, and made thirty-five a three-digit number.

Jev (ADR 0036) is asked of each sentence with only the facts it is about: the summary and a skill's line against the
child's standing (`parent_review.claims`), a mistake's line against what happens in that mistake (`.mistakes`), a home
activity against the facts (`.home`). What it is sure is wrong goes back to the writer, what it is sure is right passes,
and only what it is unsure of is read by the model, which quotes what the facts do not support. Jev unreachable, the
model reads the whole draft as before. What either finds goes back to the writer, as the check's findings do.

Scored against a hand-judged gold set (supabase/seed/parent_review_gold.json): every wrong sentence flagged, and
nothing in a draft a person read and found right (rule 7; the bar is all of them, rule 12).
"""

import json
import re

from engine.adapters import jev, llm
from engine.core import db
from engine.w4_close.parent_check import _texts as texts
from engine.w4_close.parent_check import check

PURPOSE = "parent_review"
PARTS = ("claims", "skills", "mistakes", "home")
GOLD = "supabase/seed/parent_review_gold.json"
# below the first Jev is sure a sentence is wrong; from the second, sure it is right; between, the model reads it
BARS = (("review.jev_wrong_below", 0.1), ("review.jev_sure_above", 0.5))


def told(facts):
    """What the writer was given: every fact but what comes next, which the page says itself."""
    return {k: v for k, v in facts.items() if k != "next"}


def split(text):
    """A text's sentences: each ends at a full stop, question or exclamation mark before a capital or [child]."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z\[])", text or "") if s.strip()]


def _bars(conn):
    rows = {r["key"]: float(r["value"]) for r in conn.execute(
        "select key, value from threshold where key = any(%s)", ([k for k, _ in BARS],))}  # fmt: skip
    return tuple(rows.get(k, default) for k, default in BARS)


def _on(conn, purpose):
    return (
        conn.execute("select 1 from prompt where purpose = %s and active", (purpose,)).fetchone() is not None
    )


def _skill(facts, sid):
    for state in ("can_do", "nearly", "improving"):
        for x in facts.get(state) or []:
            if x.get("id") == sid:
                return {"state": state, **x}
    return {"state": "not in the facts", "id": sid}


def questions(facts, draft):
    """→ [(part, state, sentences)], one Jev call each: every sentence of the draft, with only the facts it is about."""
    whole = told(facts)
    mistakes = {m["id"]: m for m in facts.get("working_on") or []}
    out = [("claims", whole, split(draft["summary"]))]
    # a skill set's line is asked as a line about that skill set: the page prints how secure it is beside the line
    out += [
        ("skills", {"grade": facts.get("grade"), "skill": _skill(facts, c["id"])}, split(c["sentence"]))
        for c in draft["can_do"]
    ]
    out += [
        (
            "mistakes",
            mistakes.get(w["id"], {"id": w["id"], "what_happens": "not in the facts"}),
            split(w["explanation"]),
        )
        for w in draft["working_on"]
    ]
    out.append(("home", whole, [s for h in draft["at_home"] for s in split(h)]))
    return [q for q in out if q[2]]


def _jev(conn, facts, draft, ask, version):
    """→ {sentence: Jev's chance the facts support it}, one call per part of the draft."""
    p = {}
    for part, state, sentences in questions(facts, draft):
        asks = {f"s{i}": s for i, s in enumerate(sentences)}
        yes = ask(conn, f"{PURPOSE}.{part}", state, asks, version=version)["yes"]
        p.update({s: yes[k] for k, s in asks.items()})
    return p


def _only(draft, keep):
    """The draft with only the sentences in `keep`, every part still there: what the model is given to read."""

    def kept(t):
        return " ".join(s for s in split(t) if s in keep)

    return {
        "summary": kept(draft["summary"]),
        "can_do": [{**c, "sentence": kept(c["sentence"])} for c in draft["can_do"] if kept(c["sentence"])],
        "working_on": [
            {**w, "explanation": kept(w["explanation"])}
            for w in draft["working_on"]
            if kept(w["explanation"])
        ],
        "at_home": [kept(h) for h in draft["at_home"] if kept(h)],
    }


def for_reader(draft):
    """The draft as the model reads it: its skill lines as `skill_lines`. Under the draft's own `can_do`, a line for a
    nearly secure skill set read as a claim it was secure — in the facts `can_do` means secure — and Haiku flagged 65
    right lines so (run 36520653494), though its instructions said a line for any of the three lists is right."""
    return {("skill_lines" if k == "can_do" else k): v for k, v in draft.items()}


def as_drafted(shown):
    return {("can_do" if k == "skill_lines" else k): v for k, v in shown.items()}


def findings(conn, facts, draft, ask=None, version=None, meta=None, jev_ask=None, jev_version=None, seen=None,
             model_on=None, jev_on=None):  # fmt: skip
    """→ [(quote, why)]: every sentence the facts do not support, and which reader said so. A reader reads a school's
    reports only once switched on (rule 7); an eval names the versions it scores, or says which readers are on."""
    seen = {} if seen is None else seen
    for k in ("sentences", "unsure", "read_by_model"):
        seen.setdefault(k, 0)
    seen["sentences"] += sum(len(split(t)) for t in texts(draft))
    if model_on is None:
        model_on = version is not None or _on(conn, PURPOSE)
    if jev_on is None:
        jev_on = jev_version is not None or all(_on(conn, f"{PURPOSE}.{part}") for part in PARTS)
    found, unsure = [], draft
    if jev_on:
        try:
            p = _jev(conn, facts, draft, jev_ask or jev.decide_yes_no, jev_version)
        except jev.JevError:
            p = None  # Jev unreachable: the model reads the whole draft, as before Jev
        if p is not None:
            wrong, sure = _bars(conn)
            found = [
                (s, f"the facts do not show it (Jev: {q:.2f} that they do)")
                for s, q in p.items()
                if q < wrong
            ]
            keep = {s for s, q in p.items() if wrong <= q < sure}
            seen["unsure"] += len(keep)
            unsure = _only(draft, keep) if keep else None
    if model_on and unsure:
        seen["read_by_model"] += sum(len(split(t)) for t in texts(unsure))
        out = (ask or llm.generate)(
            conn, PURPOSE, {"facts": told(facts), "draft": for_reader(unsure)}, meta=meta, version=version
        )
        found += [(u["quote"], u["why"]) for u in out["unsupported"]]
    return found


def review(conn, facts, draft, ask=None, version=None, meta=None, jev_ask=None, jev_version=None):
    """→ the readers' findings, one line each: the quoted words and why. [] when all hold, or no reader is on."""
    got = findings(conn, facts, draft, ask, version, meta, jev_ask, jev_version)
    return [f"{q!r} is not supported: {why}" for q, why in got]


def _words(text):
    return set(re.findall(r"[a-z]+", text.lower()))


def _same(flagged, bad):
    """A flag lands on a bad quote when one holds the other, or they share most of their words."""
    a, b = flagged.lower().strip(" .'\""), bad.lower().strip(" .'\"")
    if a in b or b in a:
        return True
    wa, wb = _words(a), _words(b)
    return bool(wb) and len(wa & wb) / len(wb) >= 0.6


def evaluate(conn, version=None, ask=None, gold=None, jev_ask=None, jev_version=None):
    """Every case of the gold set read as a report is written: code's check first (a draft it sends back is caught
    whole — or, if a person found it right, flagged wrongly), then the readers the eval names: the model when `version`
    or `ask` is given, Jev when `jev_version` or `jev_ask` is. → {"n", "bad", "caught", "by_code", "false_flags",
    "misses", "wrong", "sentences", "unsure", "read_by_model", "unanswered", "error"}."""
    model_on, jev_on = version is not None or ask is not None, jev_version is not None or jev_ask is not None
    failed = []  # an eval that names Jev and could not ask it fails, never scores as Jev saying nothing
    jev_ask = jev.counting(jev_ask or jev.decide_yes_no, failed) if jev_on else None
    gold = gold or json.loads((db.REPO_ROOT / GOLD).read_text())
    seen = {"sentences": 0, "unsure": 0, "read_by_model": 0}
    out = {"version": version, "jev_version": jev_version, "n": 0, "bad": 0, "caught": 0, "by_code": 0,
           "false_flags": 0, "misses": [], "wrong": []}  # fmt: skip
    for c in gold["cases"]:
        out["n"] += 1
        out["bad"] += len(c["bad"])
        sent_back = check(c["facts"], c["draft"])
        if sent_back:
            out["by_code"] += len(c["bad"])
            out["caught"] += len(c["bad"])
            if not c["bad"]:
                out["false_flags"] += 1
                out["wrong"].append({"ref": c["ref"], "quote": "(the check)", "why": sent_back[0]})
            continue
        got = findings(conn, c["facts"], c["draft"], ask=ask, version=version, meta={}, jev_ask=jev_ask,
                       jev_version=jev_version, seen=seen, model_on=model_on, jev_on=jev_on)  # fmt: skip
        quotes = [q for q, _ in got]
        for b in c["bad"]:
            if any(_same(q, b) for q in quotes):
                out["caught"] += 1
            else:
                out["misses"].append({"ref": c["ref"], "bad": b, "flagged": quotes})
        for q, why in got:
            if not any(_same(q, b) for b in c["bad"]):
                out["false_flags"] += 1
                out["wrong"].append({"ref": c["ref"], "quote": q, "why": why})
    return {**out, **seen, "unanswered": len(failed), "error": failed[0] if failed else ""}
