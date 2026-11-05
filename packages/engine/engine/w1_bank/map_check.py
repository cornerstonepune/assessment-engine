"""The code half of the curriculum mapping validator (goals/m1-05-mapping-agents.yaml, ADR 0005's rule: a model may
propose, code checks, and a model is never the last word).

Nimish, 2026-11-03: "one agent that develops for all the places where you don't have descriptions, the right learning
objectives, or the skill mapping … another validation agent is also needed". A proposal for one gap of one activity is
read here against what the database already holds: every code exists in the band, a skill's family is one people
have linked to that subject, nothing is named twice or already linked, level words only where the sheet has none.
Any problem rejects the proposal outright. Pure: no database, no model.
"""

from dataclasses import dataclass

LEVELS = ("level_0", "level_1", "level_2", "level_3")
Reply = dict[str, object]
# The kinds whose words a person must read: nothing exists to score new words against (the gold set holds codes).
NEW_WORDS = frozenset({"levels"})


@dataclass(frozen=True)
class Known:
    """What the band already holds: its skills and their families, the families people linked to each subject, and
    its objectives' codes."""

    skills: dict[str, str]
    families: dict[str, frozenset[str]]
    objectives: frozenset[str]


@dataclass(frozen=True)
class Gap:
    """One activity as it stands: its subject (the sheet's strand), its links, the level fields the sheet filled."""

    activity: str
    strand: str
    skills: frozenset[str]
    objectives: frozenset[str]
    levels: frozenset[str]


def asked_levels(levels: object, gap: Gap) -> object:
    """A reply held to a fixed form names all four levels, "" for each one not asked for: that is no proposal. A level
    the sheet lacks is kept even when empty, and `problems` says so."""
    if not isinstance(levels, dict):
        return levels
    return {k: v for k, v in levels.items() if k not in gap.levels or str(v).strip()}


def _skills(proposal: dict[str, object], gap: Gap, known: Known) -> list[str]:
    raw = proposal.get("skills")
    codes = [str(c) for c in raw] if isinstance(raw, list) else []
    if not codes:  # "none": an activity may be coverage only; a person confirms it (`decide`)
        return []
    out: list[str] = []
    seen: set[str] = set()
    for code in codes:
        if code in seen:
            out.append(f"{code} named twice")
            continue
        seen.add(code)
        family = known.skills.get(code)
        if family is None:
            out.append(f"invented code {code}: not a skill of this band")
        elif family not in known.families.get(gap.strand, frozenset()):
            out.append(f"{code} is {family}, a family people never linked to a {gap.strand} activity")
        elif code in gap.skills:
            out.append(f"{code} is already linked")
    return out


def _objective(proposal: dict[str, object], gap: Gap, known: Known) -> list[str]:
    code = str(proposal.get("objective_code") or "").strip()
    text = str(proposal.get("objective_text") or "").strip()
    if code and text:
        return ["an existing objective or new words, not both"]
    if not code and not text:
        return ["no objective proposed"]
    if code and code not in known.objectives:
        return [f"invented code {code}: not an objective of this band"]
    if code in gap.objectives:
        return [f"{code} is already linked"]
    return []


def _levels(proposal: dict[str, object], gap: Gap) -> list[str]:
    raw = proposal.get("levels")
    words = {str(k): str(v) for k, v in raw.items()} if isinstance(raw, dict) else {}
    if not words:
        return ["no level words proposed"]
    out: list[str] = []
    for field, text in sorted(words.items()):
        if field not in LEVELS:
            out.append(f"{field} is not a level")
        elif field in gap.levels:
            out.append(f"{field} already has the sheet's words")
        elif not text.strip():
            out.append(f"{field} is empty")
    return out


def problems(kind: str, proposal: dict[str, object], gap: Gap, known: Known) -> list[str]:
    """Every way one proposal for one gap fails the code checks, in words; empty when it passes them all."""
    if kind in ("skill", "lo_skill"):
        return _skills(proposal, gap, known)
    if kind == "objective":
        return _objective(proposal, gap, known)
    if kind == "levels":
        return _levels(proposal, gap)
    return [f"{kind} is not a kind of gap"]


def decide(
    kind: str,
    found: list[str],
    verdict: str,
    confidence: float,
    *,
    min_confidence: float,
    sampled: bool,
    new_words: bool = False,
    none: bool = False,
    kind_stopped: bool = False,
    checker: bool = True,
) -> str:
    """Where a checked proposal goes. Code's problems reject it; new words, a validator that disagrees, a confidence
    under the bar (a validator that is switched off is not asked), a "none", the audit sample and a kind whose audit failed all go to a person; the rest pass on their own."""
    if found:
        return "rejected"
    if (
        kind in NEW_WORDS
        or new_words
        or none
        or (checker and verdict != "agree")
        or confidence < min_confidence
        or sampled
        or kind_stopped
    ):
        return "needs_person"
    return "auto_passed"


@dataclass(frozen=True)
class Proposal:
    """One proposal for one gap, as decided: what it says, what code found, the validator's verdict, where it goes."""

    kind: str
    subject_code: str
    proposal: Reply
    confidence: float
    proposer: str
    validator: str
    problems: list[str]
    verdict: str
    status: str
    reason: str


@dataclass(frozen=True)
class Rules:
    """The numbers the decision reads, every one a threshold row (`map.*`), and the kinds whose audit failed."""

    min_confidence: float
    audit_share: float
    examples: int
    stopped: frozenset[str] = frozenset()
    skill_confidence: float | None = (
        None  # `map.skill_min_confidence`: the bar for a skill once it must come from the examples
    )
    from_examples: bool = (
        False  # `map.require_examples`: a skill passes only if an example showed it; the rest are offered
    )
    use_checker: bool = True  # `map.use_checker`: the second model's verdict is asked for and must agree

    def bar(self, kind: str) -> float:
        """The confidence a proposal of this kind must reach to pass on its own."""
        if kind == "skill" and self.from_examples and self.skill_confidence is not None:
            return self.skill_confidence
        return self.min_confidence
