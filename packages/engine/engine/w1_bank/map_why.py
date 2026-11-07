"""What the proposals that passed on their own were like, in counts only (goals/m1-12n-map-why.yaml).

The held-out score says how many passes were wrong; this says where the wrong ones are, so a rule that would catch
them can be chosen without spending: by how many skills a proposal named, by confidence, and, for those that added a
skill people did not link, whether people linked that skill to a like activity. Pure: no database, no model. It names
no activity, no skill and no phrase of the school's (the log is public); it is only counts.
"""

import math
from collections.abc import Mapping, Sequence

from engine.w1_bank.map_check import Proposal
from engine.w1_bank.map_replay import family, wilson


def _share(passed: int, right: int) -> dict:
    return {
        "passed": passed,
        "right": right,
        "precision": round(right / passed, 3) if passed else 0.0,
        "interval": [round(x, 3) for x in wilson(right, passed)],
    }


def _tally(rows: Sequence[tuple[str, bool]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for key, ok in sorted(rows):
        got = out.setdefault(key, {"n": 0, "right": 0})
        got["n"] += 1
        got["right"] += ok
    return out


def _where_linked(
    skill: str,
    code: str,
    linked: Mapping[str, frozenset[str]],
    names: Mapping[str, str],
    strand: Mapping[str, str],
) -> str:
    """Where people linked `skill` to another activity: with the same name, in the same section, or nowhere alike."""
    others = [o for o, s in linked.items() if o != code and skill in s]
    if any(names.get(o) and names.get(o) == names.get(code) for o in others):
        return "same_name"
    if any(strand.get(o) and strand.get(o) == strand.get(code) for o in others):
        return "same_section"
    return "nowhere_alike"


def why(
    made: Sequence[Proposal],
    linked: Mapping[str, frozenset[str]],
    names: Mapping[str, str],
    strand: Mapping[str, str],
) -> dict:
    """The passes in `made` against what people `linked`, as counts."""
    rows = []
    for p in made:
        raw = p.proposal.get("skills")
        if p.kind != "skill" or p.status != "auto_passed" or not isinstance(raw, list):
            continue
        proposed, gold = frozenset(str(s) for s in raw), linked.get(p.subject_code, frozenset())
        rows.append((p, proposed, gold, bool(proposed) and proposed <= gold))
    adds = [(p, pr, g) for p, pr, g, ok in rows if pr & g and not ok]
    where = [
        _where_linked(s, p.subject_code, linked, names, strand) for p, pr, g in adds for s in sorted(pr - g)
    ]
    single = [ok for _, pr, _, ok in rows if len(pr) == 1]
    return {
        "passed": len(rows),
        "right": sum(ok for *_, ok in rows),
        "by_skills": _tally([("1" if len(pr) == 1 else "2+", ok) for _, pr, _, ok in rows]),
        "by_confidence": _tally([(f"{math.floor(p.confidence * 10) / 10:.1f}", ok) for p, _, _, ok in rows]),
        "adds": {
            "proposals": len(adds),
            "extra_skills": len(where),
            "extra_linked_to_a_same_name_activity": where.count("same_name"),
            "extra_linked_in_the_same_section": where.count("same_section"),
            "extra_linked_nowhere_alike": where.count("nowhere_alike"),
            "extra_in_a_family_people_linked": sum(
                family(s) in {family(x) for x in g} for _, pr, g in adds for s in pr - g
            ),
        },
        "if": {
            "one_skill_only": _share(len(single), sum(single)),
            "adds_offered": _share(len(rows), sum(ok for *_, ok in rows) + len(adds)),
        },
    }
