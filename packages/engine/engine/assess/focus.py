"""Which areas a child's next paper works on, read from the child's own graph (goal s11-focus-paper).

Pure: no database. The graph (`child_skill_state`, one row per skill per rung) already says how a child
stands; this answers one question — which few areas next, and at what level:

- an area the child lags in is a row in a lagging state: a repeated mistake, fewer than half right, or
  not yet four in five. Weakest first, at most `rule["most"]`.
- an area is one skill set of the bank: the set on the row's rung that is for the row's skill; else the
  nearest set for that skill within `rule["reach"]` rungs; else a set on the rung whose questions use the
  skill. So subtraction mistakes on an addition rung are worked on as subtraction.
- its level follows how often the child was right: below `rule["easy_below"]` Easy, otherwise Medium.

A home paper (`home`) is one area, never a mix: the weakest. A child who lags nowhere is stretched instead — their
strongest skill, one level up, as `rule["stretch"]` says for its state (Nimish, 2026-09-23: "Stretch too").
"""

from dataclasses import dataclass

LAGGING = ("patterned_error", "emerging", "practising")


@dataclass(frozen=True)
class Area:
    skill_set: str
    skill_code: str
    level: str
    right: int
    answered: int
    mistake: str | None
    state: str


def skill_set_for(skill_code, rung_code, catalog, reach):
    """The bank's skill set a weak (skill, rung) is worked on in, or None when the bank has none for it."""
    here = next((c for c in catalog if c["rung"] == rung_code), None)
    order = here["order"] if here else None
    if here and here["own"] == skill_code:
        return here["code"]
    if order is not None:
        near = [
            c
            for c in catalog
            if c["own"] == skill_code and c["order"] is not None and abs(c["order"] - order) <= reach
        ]
        if near:
            return min(near, key=lambda c: (abs(c["order"] - order), c["order"]))["code"]
    if here and skill_code in here["skills"]:
        return here["code"]
    return None


def _weakness(a):
    return (LAGGING.index(a.state), a.right / a.answered if a.answered else 0.0, a.skill_set)


def areas(states, catalog, rule, levels=None):
    """The areas to work on, weakest first. `states` are the child's graph rows. `levels`, when given, is the
    levels of each skill set this child may be given: a lagging child's level is the hardest of those no harder
    than the one their share calls for, and a skill set with none is not theirs to work on."""
    best = {}
    for s in states:
        if s["state"] not in LAGGING:
            continue
        code = skill_set_for(s["skill_code"], s["rung_code"], catalog, rule["reach"])
        if not code:
            continue
        share = s["n_correct"] / s["n_events"] if s["n_events"] else 0.0
        level = "Easy" if share < rule["easy_below"] else "Medium"
        if levels is not None:
            level = _at_most(level, levels.get(code, ())) or _easiest(levels.get(code, ()))
            if not level:
                continue
        area = Area(
            code,
            s["skill_code"],
            level,
            s["n_correct"],
            s["n_events"],
            s["repeating_misconception"],
            s["state"],
        )
        key = (code, s["skill_code"])
        if key not in best or _weakness(area) < _weakness(best[key]):
            best[key] = area
    return sorted(best.values(), key=_weakness)[: rule["most"]]


LEVELS = ("Easy", "Medium", "Hard", "Advance")  # the school's own four, in order


def _at_most(level, defined):
    """The hardest level a skill set defines that is no harder than `level`; None when it defines none."""
    below = [d for d in LEVELS[: LEVELS.index(level) + 1] if d in defined]
    return below[-1] if below else None


def _easiest(defined):
    """The easiest level a skill set defines, or None."""
    return next((d for d in LEVELS if d in defined), None)


def home(states, catalog, rule, levels):
    """The one area a child's home paper works on: the weakest they lag in, or, when they lag nowhere, their
    strongest skill one level up. `levels` is each skill set's defined levels. Empty when the graph shows neither."""
    weak = areas(states, catalog, {**rule, "most": 1}, levels)
    if weak:
        return weak
    strong = []
    for s in states:
        target = rule["stretch"].get(s["state"])
        code = target and skill_set_for(s["skill_code"], s["rung_code"], catalog, rule["reach"])
        level = code and _at_most(target, levels.get(code, ()))
        if level:
            area = Area(code, s["skill_code"], level, s["n_correct"], s["n_events"], None, s["state"])
            strong.append(area)
    strong.sort(key=lambda a: (-(a.right / a.answered if a.answered else 0), -a.answered, a.skill_set))
    return strong[:1]
