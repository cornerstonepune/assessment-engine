"""A skill passes on its own only if an example showed it; the rest are offered (goals/m1-12c-skill-offers.yaml).

The proposer is shown the skills of the activities people mapped that are nearest this one. The dev run's replay found that
a skill it was shown in an example was also linked by people in 87 of 110 cases, one it was not shown in 55 of 84, and its
own confidence told the two apart badly. So the skills that came from the examples stay one proposal, decided as before
(and by a confidence bar of its own, `map.skill_min_confidence`), and each skill that did not is a `skill_offer`: one
proposal for one skill, waiting for a person to add it or not. Pure: no database, no model.
"""

from dataclasses import replace

from engine.w1_bank.map_check import Proposal, Rules

OFFER = "skill_offer"
WHY = "not among the skills of the nearest examples: offered for a person to add"


def shown_in(context: dict[str, object]) -> frozenset[str]:
    """The skills of the examples in the context the proposer was asked with."""
    out: set[str] = set()
    raw = context.get("examples")
    for ex in raw if isinstance(raw, list) else []:
        skills = ex.get("skills") if isinstance(ex, dict) else None
        out |= {str(k) for k in skills} if isinstance(skills, list) else set()
    return frozenset(out)


def split(
    p: Proposal, shown: frozenset[str], rules: Rules, asked: frozenset[tuple[str, str]] = frozenset()
) -> list[Proposal]:
    """The proposals a decided skill proposal becomes. `shown` are the skills of the examples the proposer was shown;
    `asked` are the (activity, skill) pairs already offered or refused, which are never proposed again."""
    raw = p.proposal.get("skills")
    listed = [str(s) for s in raw] if isinstance(raw, list) else []
    if p.kind in ("skill", OFFER):
        listed = [s for s in listed if (p.subject_code, s) not in asked]
        if raw and not listed:
            return []  # everything it names was already offered or refused
        if isinstance(raw, list) and len(listed) != len(raw):
            p = replace(p, proposal={**p.proposal, "skills": listed})  # what is left of it
    if p.kind != "skill" or not rules.from_examples or p.status == "rejected" or not listed:
        return [p]
    kept = [s for s in listed if s in shown]
    offered = [s for s in listed if s not in shown]
    if not offered:
        return [p]
    out = [replace(p, proposal={"skills": kept})] if kept else []
    out += [
        replace(
            p,
            kind=OFFER,
            proposal={"skills": [s], "with": kept},
            problems=[],
            status="needs_person",
            reason=WHY,
        )
        for s in offered
    ]
    return out
