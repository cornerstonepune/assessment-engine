"""The gold-set eval of the curriculum mapping agents, and the links code can make on its own
(goals/m1-05-mapping-agents.yaml).

The activities people mapped are the gold set: 100 are the dev set, for tuning prompts, and the rest are held out for
the final score only (blueprint chapter P-08). The split is the same every run and draws on every subject; a
held-out activity is never an example the proposer sees, and its links are hidden when the agents map it blind; code
scores what they did against what people did. A "none" on an activity people mapped counts as wrong. The bars are threshold rows (`eval.curriculum_map.*`), set
before anything is applied. Pure: no database, no model.
"""

import hashlib
from collections import defaultdict
from dataclasses import dataclass


@dataclass(frozen=True)
class Scored:
    """One held-out activity after the agents and the checks: the skills proposed and where the proposal went."""

    activity: str
    skills: frozenset[str]
    status: str


def split(strands: dict[str, str], dev: int) -> tuple[set[str], set[str]]:
    """(dev, held out) of the activities people mapped: `dev` of them for tuning the prompts, taken in turn from
    every subject, and the rest held out for the final score only. Chosen by a hash of each code, so every run and
    every machine splits them the same way."""
    by: dict[str, list[str]] = defaultdict(list)
    for code, strand in strands.items():
        by[strand].append(code)
    queues = [sorted(v, key=lambda c: hashlib.sha256(c.encode()).hexdigest()) for _, v in sorted(by.items())]
    chosen: set[str] = set()
    while len(chosen) < min(dev, len(strands)):
        for q in queues:
            if q and len(chosen) < dev:
                chosen.add(q.pop(0))
    return chosen, set(strands) - chosen


def score(run: list[Scored], gold: dict[str, frozenset[str]]) -> dict[str, float]:
    """The run against what people linked. Of the proposals that passed on their own: the share whose every skill a
    person also linked (skill_all_right), and the share of the people's links they found (skill_found); and the share
    of all proposals that passed on their own (auto_passed). Nothing passed scores 0, never a free pass."""
    passed = [r for r in run if r.status == "auto_passed"]
    right = sum(1 for r in passed if r.skills and r.skills <= gold.get(r.activity, frozenset()))
    links = sum(len(gold.get(r.activity, frozenset())) for r in passed)
    found = sum(len(r.skills & gold.get(r.activity, frozenset())) for r in passed)
    return {
        "n": float(len(run)),
        "skill_all_right": right / len(passed) if passed else 0.0,
        "skill_found": found / links if links else 0.0,
        "auto_passed": len(passed) / len(run) if run else 0.0,
    }


def lo_skill_pairs(
    objectives: dict[str, set[str]], skills: dict[str, set[str]]
) -> dict[tuple[str, str], str]:
    """{(objective, skill): the activity that shows it} where an activity leaves no doubt: one objective tests each of
    its skills, or one skill is what each of its objectives tests. Two and two is a guess, so none is made."""
    out: dict[tuple[str, str], str] = {}
    for activity in sorted(objectives.keys() & skills.keys()):
        los, sks = objectives[activity], skills[activity]
        if len(los) == 1 or len(sks) == 1:
            for lo in sorted(los):
                for sk in sorted(sks):
                    out.setdefault((lo, sk), activity)
    return out
