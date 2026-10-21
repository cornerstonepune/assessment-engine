"""The paper an educator saw before it printed (goals/preview-before-print.yaml).

Nimish, 2026-10-21: "a teacher can only see the assessment when they print". A paper is shown first, as its plan
(`focus_paper.plan`, `maker.plan`), which writes nothing; "different questions" is the same plan drawn again with the
next `draw`. What was shown is named by `of` — a short code for its children and questions, in order — and printing
names it back: the paper prints only when its plan is still exactly that (`check`), never as a fresh draw.
"""

import hashlib
import json

CHANGED = (
    "The questions changed since you saw them: a paper was made for this child meanwhile, or the bank changed."
    " Nothing was printed; see the paper again."
)


class Changed(ValueError):
    """The paper would print other questions than the ones the educator saw."""


def of(papers: list[dict]) -> str:
    """A short code for what `papers` (each a plan's paper: its child and its areas' questions) show, in order."""
    shown = [[p.get("child_id"), [q["id"] for a in p["areas"] for q in a["questions"]]] for p in papers]
    return hashlib.sha256(json.dumps(shown).encode()).hexdigest()[:16]


def check(papers: list[dict], seen: str | None) -> None:
    """Refuses `papers` unless they are what the educator saw (`seen`, from `of`); None: no one saw them (the CLI)."""
    if seen is not None and of(papers) != seen:
        raise Changed(CHANGED)
