"""Each item's thread through the spine's five steps, for the spine page (research/spine_page.py).

Nimish, 2026-09-28: "i am getting lost in the artifact". The page shows everything on the same five steps, top to
bottom: why (the capabilities, and the three words they show), what NCF-SE asks (curricular goals and their
competencies), in the grade (NCERT's outcomes and the school's units), when (the plan's fortnights) and how we check
(the engine's skills and rungs). An item's thread is what it reaches on each step, and a unit, taught in several
grades, has a thread per grade. Each group of links says where it comes from (research/spine_links.py). Built by code
from docs/spine/spine.json and docs/spine/plan.json; no model is called.
"""

import collections

from spine_links import Spine, group, weakest
from spine_steps import (
    below,
    by_goal,
    capabilities,
    checks,
    direct_skills,
    fortnights,
    per_grade,
    served,
    why_of,
)

STEPS = ("why", "asks", "grade", "when", "check")
HOME = {
    "word": "why",
    "capability": "why",
    "behaviour": "why",
    "goal": "asks",
    "competency": "asks",
    "outcome": "grade",
    "unit": "grade",
    "skill": "check",
    "rung": "check",
}
EMPTY = {
    "why": "It reaches no capability yet.",
    "asks": "It is linked to no NCF-SE competency yet.",
    "grade": "No grade's outcome or unit is linked to it yet.",
    "when": "It is not in a fortnight: the plan covers Grades 1-7.",
    "check": "The engine tracks no skill for it yet.",
}


def key(item, grade=None):
    """A unit's thread is per grade (`unit.313~3`); anything else is its own key."""
    return item if grade is None else f"{item}~{grade}"


def itself(item, title=None, **extra):
    return {"t": title, "k": "self", "ids": [item], **extra}


def by_stage(sp, pairs, title):
    stages = collections.defaultdict(list)
    for i, k in pairs:
        stages[sp.stage(i)].append((i, k))
    return [group(v, f"{st} · {title}") for st, v in stages.items()]


def unit_thread(sp, unit, g):
    comps = served(sp, unit, "builds_toward")
    slot = next(iter(sp.placed(unit).get(g, {})), None)
    shared = collections.Counter(
        o
        for c, _ in comps
        for o, _, _ in sp.links(c, "evidences", back=True)
        if sp.layer(o) == "outcome" and sp.grade(o) == g
    )
    title = f"Grade {g} · {sp.names.get(slot, slot)}" if slot else f"Grade {g}"
    return {
        "why": why_of(sp, unit, comps),
        "asks": by_goal(sp, sp.only(comps, "competency"))
        + [group([p], "Curricular goal") for p in sp.only(comps, "goal")],
        "grade": [
            itself(unit, title, grades=[x for x in sp.unit_grades(unit) if x != g]),
            group(
                [(o, "inferred") for o, _ in shared.most_common()],
                f"NCERT expects in Grade {g}",
            ),
        ],
        "when": fortnights(sp, [(unit, "proposed")], g),
        "check": checks(sp, [(unit, "school")]),
    }


def outcome_thread(sp, outcome):
    g, comps = sp.grade(outcome), served(sp, outcome, "evidences")
    subject = sp.node.get(f"subject.{sp.node[outcome].get('subject')}", {}).get(
        "label", ""
    )
    units = collections.Counter(
        u
        for c, _ in comps
        for u, _, _ in sp.links(c, "builds_toward", back=True)
        if g in sp.placed(u)
    )
    units = [(u, "inferred") for u, _ in units.most_common()]
    steps = {
        "why": why_of(sp, outcome, comps),
        "asks": by_goal(sp, comps),
        "grade": [
            itself(outcome, f"Grade {g} · {subject}"),
            group(units, f"We teach in Grade {g}", g=g),
        ],
        "when": fortnights(sp, [(outcome, "proposed"), *units], g),
        "check": checks(sp, units),
    }
    if g not in sp.planned:
        steps["when"] = [
            {"note": f"Grade {g} is outside this plan, which covers Grades 1-7."}
        ]
    elif g >= 5:
        note = f"The school's own map for Grade {g} is not written yet, so NCERT's outcomes stand in."
        steps["grade"].append({"note": note})
    return steps


def competency_thread(sp, comp):
    goal = sp.links(comp, "has_competency", back=True)
    mine = [(comp, "official")]
    return {
        "why": capabilities(sp, [(comp, "self")]),
        "asks": [
            group(mine, None, head=goal[0][0]) if goal else group(mine, "Competency")
        ],
        **below(sp, [(comp, "self")], direct_skills(sp, comp)),
    }


def goal_thread(sp, goal):
    comps = [(c, s) for c, s, _ in sp.links(goal, "has_competency")]
    return {
        "why": capabilities(sp, [(goal, "self")]),
        "asks": [
            group(comps, None, head=goal)
            or {"t": None, "k": "self", "ids": [], "head": goal}
        ],
        **below(sp, comps, direct_skills(sp, goal)),
    }


def capability_thread(sp, cap):
    behaviours = [(b, s) for b, s, _ in sp.links(cap, "shown_by")]
    words = collections.Counter(
        w for b, _ in behaviours for w, _, _ in sp.links(b, "evidence_for")
    )
    main = [(c, s) for c, s, rank in sp.links(cap, "feeds", back=True) if rank == 1]
    main = sp.only(main, "competency")
    rest = below(sp, main)
    return {
        "why": [
            itself(cap),
            group(
                [(w, "proposed") for w, _ in words.most_common()], "The words it shows"
            ),
        ]
        + by_stage(sp, behaviours, "what an educator sees"),
        "asks": by_stage(sp, main, "competencies that mainly build it"),
        "grade": rest["grade"],
        "when": [
            {"note": "Pick a unit or an outcome to see the fortnights it is taught in."}
        ],
        "check": rest["check"],
    }


def word_thread(sp, word):
    behaviours = [(b, s) for b, s, _ in sp.links(word, "evidence_for", back=True)]
    caps = collections.Counter(
        c for b, _ in behaviours for c, _, _ in sp.links(b, "shown_by", back=True)
    )
    follow = {"note": "Pick a capability to follow it down to the grades."}
    return {
        "why": [
            itself(word),
            group(
                [(c, "proposed") for c, _ in caps.most_common()],
                "Capabilities that show it",
            ),
        ]
        + by_stage(sp, behaviours, "what an educator sees"),
        **{s: [follow] for s in STEPS[1:]},
    }


def behaviour_thread(sp, beh):
    note = {
        "note": "What an educator sees is recorded across the day; it is not tied to one unit or outcome."
    }
    return {
        "why": [
            group(
                [(c, s) for c, s, _ in sp.links(beh, "shown_by", back=True)],
                "Shows the capability",
            ),
            group(
                [(w, s) for w, s, _ in sp.links(beh, "evidence_for")], "Evidence for"
            ),
            itself(beh, f"{sp.stage(beh)} · what an educator sees"),
        ],
        **{s: [note] for s in STEPS[1:]},
    }


def skill_thread(sp, skill):
    units = [(u, s) for u, s, _ in sp.links(skill, "builds", back=True)]
    direct = [(x, s) for x, s, _ in sp.links(skill, "evidences")]
    comps = [
        (c, weakest(k, s)) for u, k in units for c, s, _ in sp.links(u, "builds_toward")
    ]
    tests = [(r, s) for r, s, _ in sp.links(skill, "tests", back=True)]
    return {
        "why": capabilities(sp, direct + comps),
        "asks": [group(direct, "The skill map says it is evidence of")]
        + by_goal(sp, sp.only(comps, "competency")),
        "grade": per_grade(sp, units, "We teach"),
        "when": fortnights(sp, units),
        "check": [itself(skill), group(tests, "Rungs that test it")],
    }


def rung_thread(sp, rung):
    skills = [(s, src) for s, src, _ in sp.links(rung, "tests")]
    at = [
        g.removeprefix("grade.G") for g, _, _ in sp.links(rung, "at_grade", back=True)
    ]
    grades = {int(g) for g in at if g.isdigit()}
    units = [
        (u, weakest(k, s))
        for sk, k in skills
        for u, s, _ in sp.links(sk, "builds", back=True)
        if not grades or grades & set(sp.unit_grades(u))
    ]
    comps = [
        (c, weakest(k, s)) for u, k in units for c, s, _ in sp.links(u, "builds_toward")
    ]
    return {
        "why": capabilities(sp, comps),
        "asks": by_goal(sp, sp.only(comps, "competency")),
        "grade": [
            g
            for g in per_grade(sp, units, "We teach")
            if not grades or g["g"] in grades
        ],
        "when": [g for g in fortnights(sp, units) if not grades or g["g"] in grades],
        "check": [itself(rung), group(skills, "Skills it tests")],
    }


BUILDERS = {
    "outcome": outcome_thread,
    "competency": competency_thread,
    "goal": goal_thread,
    "capability": capability_thread,
    "word": word_thread,
    "behaviour": behaviour_thread,
    "skill": skill_thread,
    "rung": rung_thread,
}


def finish(item, grade, steps):
    """Every step in order, no empty group, and a sentence where a step has nothing."""
    out = {s: [g for g in steps.get(s, []) if g] for s in STEPS}
    return {
        "id": item,
        "g": grade,
        "steps": {s: groups or [{"note": EMPTY[s]}] for s, groups in out.items()},
    }


def build(spine, plan):
    """→ ({thread key: thread}, {item: the key the page opens for it})."""
    sp = Spine(spine, plan)
    threads, opened = {}, {}
    for item, n in sp.node.items():
        if n["layer"] == "unit":
            grades = sp.unit_grades(item) or [None]
            for g in grades:
                threads[key(item, g)] = finish(item, g, unit_thread(sp, item, g))
            opened[item] = key(item, grades[0])
        elif n["layer"] in BUILDERS:
            threads[item] = finish(item, sp.grade(item), BUILDERS[n["layer"]](sp, item))
            opened[item] = item
    return threads, opened
