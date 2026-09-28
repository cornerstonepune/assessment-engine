"""How the spine page reads the spine's links: where each one comes from, how strong a path of them is, and the
index of every item's links (docs/spine/spine.json) and fortnights (docs/spine/plan.json).

A link is official when it was imported from NCF-SE or NCERT, the school's when it comes from the school's own map,
and proposed when a subject reviewer, the council or the platform survey drafted it and nobody has signed it yet. A
path is only as strong as its weakest link, and one that joins a unit and an outcome through a competency they share
is inferred. research/spine_steps.py and research/spine_thread.py build the page's threads on these rules.
"""

import collections

KINDS = ("self", "official", "school", "proposed", "inferred")  # strongest first


def source(by):
    """The kind of a link, from who made it (`imported`, `school`, `seat:math`, `council`, `survey`)."""
    return {"imported": "official", "school": "school"}.get(
        by.split(":")[0], "proposed"
    )


def weakest(*kinds):
    return max(kinds, key=KINDS.index)


def strongest(*kinds):
    return min(kinds, key=KINDS.index)


def group(pairs, title=None, **extra):
    """[(id, kind of the path to it)] → a group of distinct ids in order, as strong as its weakest link, or None
    when empty. An id reached twice keeps its stronger path."""
    best = {}
    for i, k in pairs:
        best[i] = strongest(best.get(i, k), k)
    if not best:
        return None
    return {"t": title, "k": weakest(*best.values()), "ids": list(best), **extra}


class Spine:
    """Every item, its links both ways, and where the plan puts it: {item: {grade: {subject slot: [fortnights]}}}."""

    def __init__(self, spine, plan):
        self.node = {n["id"]: n for n in spine["nodes"]}
        self.out = collections.defaultdict(list)
        self.into = collections.defaultdict(list)
        for e in spine["edges"]:
            self.out[e["from"]].append(e)
            self.into[e["to"]].append(e)
        self.names = plan["design"]["slot_names"]
        self.where = collections.defaultdict(dict)
        for g, slots in plan["year"].items():
            for slot, cells in slots.items():
                for f, cell in enumerate(cells, 1):
                    for x, _ in cell:
                        self.where[x].setdefault(int(g), {}).setdefault(
                            slot, []
                        ).append(f)
        self.planned = {int(g) for g in plan["year"]}

    def links(self, item, kind, back=False):
        """[(the other end, its source, its rank)] of an item's links of one kind, in the spine's order."""
        edges = self.into[item] if back else self.out[item]
        end = "from" if back else "to"
        return [
            (e[end], source(e["by"]), e.get("rank")) for e in edges if e["kind"] == kind
        ]

    def layer(self, item):
        return self.node[item]["layer"]

    def only(self, pairs, layer):
        """The pairs whose item is of one layer."""
        return [(i, k) for i, k in pairs if self.layer(i) == layer]

    def placed(self, item):
        """{grade: {slot: [fortnights]}} for an item the plan places, else {}."""
        return self.where.get(item, {})

    def grade(self, item):
        g = self.node[item].get("grade")
        return int(g[1:]) if g and g[1:].isdigit() else None

    def unit_grades(self, unit):
        """The grades a unit is taught in: where the plan places it, else the grades the school's map names."""
        return sorted(self.placed(unit)) or [
            int(b[1:]) for b in self.node[unit].get("bands", [])
        ]

    def stage(self, item):
        return (self.node[item].get("stage") or "").capitalize() or "Any stage"
