"""What each of the spine page's five steps shows for a set of items: the capabilities they build (why), the
competencies under their curricular goals (what NCF-SE asks), the outcomes and units by grade (in the grade), the
fortnights (when) and the engine's skills and rungs (how we check). Every group says how strong its links are, by the
rules in research/spine_links.py; research/spine_thread.py puts the steps together into each item's thread.
"""

import collections

from spine_links import group, strongest, weakest


def capabilities(sp, via):
    """Why: the capabilities that competencies or goals feed, `via` [(item, kind of the path to it)]: mainly
    (rank 1) and also (ranks 2-3), the most-fed first."""
    count = {1: collections.Counter(), 2: collections.Counter()}
    kind = {}
    for item, k in via:
        for cap, s, rank in sp.links(item, "feeds"):
            count[1 if rank == 1 else 2][cap] += 1
            kind[cap] = strongest(kind.get(cap, weakest(k, s)), weakest(k, s))
    main = [(c, kind[c]) for c, _ in count[1].most_common()]
    also = [(c, kind[c]) for c, _ in count[2].most_common() if c not in count[1]]
    return [g for g in (group(main, "Mainly builds"), group(also, "Also builds")) if g]


def why_of(sp, item, via):
    """Why, for a unit or an outcome: its capabilities, or the reason the spine gives for it having none."""
    groups = capabilities(sp, via)
    if not groups and sp.node[item].get("why"):
        groups.append(
            {"t": "Why it reaches no capability", "note": sp.node[item]["why"]}
        )
    return groups


def by_goal(sp, comps):
    """What NCF-SE asks: competencies [(id, kind)] under their curricular goal, as NCF-SE groups them."""
    heads = collections.defaultdict(list)
    for c, k in comps:
        goals = sp.links(c, "has_competency", back=True)
        heads[goals[0][0] if goals else None].append((c, weakest(k, "official")))
    return [
        group(pairs, None, head=goal) if goal else group(pairs, "Competencies")
        for goal, pairs in heads.items()
    ]


def served(sp, item, kind):
    """The competencies (and goals) a unit builds toward or an outcome is evidence of: [(id, kind)]."""
    return [(c, s) for c, s, _ in sp.links(item, kind)]


def fortnights(sp, pairs, grade=None):
    """When: the fortnights of units and outcomes [(id, kind)], one group per grade and subject, with the items
    it places (`on`) so the page can mark them in that grade's year."""
    at = collections.defaultdict(lambda: (set(), [], {}))
    for item, k in pairs:
        for g, slots in sp.placed(item).items():
            if grade in (None, g):
                for slot, fs in slots.items():
                    at[(g, slot)][0].update(fs)
                    at[(g, slot)][1].append(k)
                    at[(g, slot)][2][item] = True
    return [
        {
            "t": f"Grade {g} · {sp.names.get(slot, slot)}",
            "k": weakest("proposed", *ks),
            "g": g,
            "slot": slot,
            "f": sorted(fs),
            "on": list(on),
        }
        for (g, slot), (fs, ks, on) in sorted(at.items())
    ]


def checks(sp, units, direct=()):
    """How we check: the engine's skills that units [(id, kind)] build, and skills that evidence the item
    directly, with the rungs that test them."""
    skills = [
        (s, weakest(k, src)) for u, k in units for s, src, _ in sp.links(u, "builds")
    ]
    skills += list(direct)
    rungs = [
        (r, weakest(k, src))
        for s, k in skills
        for r, src, _ in sp.links(s, "tests", back=True)
    ]
    found = (
        group(skills, "Skills the engine tracks"),
        group(rungs, "Rungs on the engine's ladder"),
    )
    return [g for g in found if g]


def per_grade(sp, pairs, title):
    """[(unit or outcome, kind)] → one group per grade; a unit sits under every grade it is taught in."""
    at = collections.defaultdict(list)
    for item, k in pairs:
        grades = sp.unit_grades(item) if sp.layer(item) == "unit" else [sp.grade(item)]
        for g in grades:
            if g is not None:
                at[g].append((item, k))
    return [group(at[g], f"Grade {g} · {title}", g=g) for g in sorted(at)]


def direct_skills(sp, item):
    """Skills the school's skill map says are evidence of a competency or a goal."""
    return sp.only(
        [(s, src) for s, src, _ in sp.links(item, "evidences", back=True)], "skill"
    )


def below(sp, comps, direct=()):
    """In the grade, when and how we check, for competencies [(id, kind)]: the outcomes and units that serve
    them, their fortnights, and their skills."""
    outcomes = [
        (o, weakest(k, s))
        for c, k in comps
        for o, s, _ in sp.links(c, "evidences", back=True)
    ]
    outcomes = sp.only(outcomes, "outcome")
    units = [
        (u, weakest(k, s))
        for c, k in comps
        for u, s, _ in sp.links(c, "builds_toward", back=True)
    ]
    grade = per_grade(sp, outcomes, "NCERT expects") + per_grade(sp, units, "We teach")
    grade.sort(key=lambda g: (g["g"], g["t"]))
    return {
        "grade": grade,
        "when": fortnights(sp, outcomes + units),
        "check": checks(sp, units, direct),
    }
