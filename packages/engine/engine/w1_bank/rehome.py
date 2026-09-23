"""The bank re-homed onto the taxonomy-shaped skills (goals/s13-levels-by-taxonomy.yaml, ADR 0034).

A calculation skill is one operation and one digit shape (`2-digit + 2-digit`), and its levels are the
taxonomy's own cases on those numbers: Easy, Medium and Hard are straight calculation, Advance mixes them
with missing numbers, stories, lining up and finding the mistake. The seed says which old skill sets each
new one replaces.

Nothing is regenerated. Where a question belongs follows from what it is — its measured tags — and the map,
exactly as its taxonomy cases do (ADR 0030), so it is recomputed, not typed: its skill is the one skill whose
shape it has, its level the hardest of Easy · Medium · Hard it is one of the cases of (a calculation) or
Advance (any other kind). A question with no place stays where it was and is retired with the reason, through
the same path a person's flag takes; it is never deleted. Printed papers point at their own questions and
never change. Running it again moves nothing.
"""

from collections import Counter

from engine.assess import taxonomy, verify
from engine.core import loaders
from engine.w1_bank import cases

ACTOR = "engine (taxonomy-shaped skills)"
CALCULATION = ("bare_sum", "column_grid")
STRAIGHT = ("Hard", "Medium", "Easy")  # hardest first: a carry onto a zero is Hard even if it is one carry


def replaced(seed=None):
    """{old skill set: the new ones that replace it} — from the seed, where a person wrote it."""
    out = {}
    for s in seed if seed is not None else loaders._seed("skill_sets.json", "skill_sets"):
        for old in s.get("replaces", []):
            out.setdefault(old, []).append(s["code"])
    return out


def shaped(conn):
    """The skills in use that have a shape, with their levels' checks and rung."""
    rows = conn.execute(
        "select code, rung_code, version, difficulty from skill_set where status <> 'retired' order by code"
    ).fetchall()
    return [r for r in rows if any("within" in lv.get("check", {}) for lv in r["difficulty"].values())]


def place(fmt, tags, skills, case_matches):
    """(skill, level) for one question, or None. Raises when two skills' shapes both hold it — a map defect."""
    home = [s for s in skills if taxonomy.matches(_shape(s), fmt, tags)]
    if len(home) > 1:
        raise ValueError(f"two skills hold the same question: {', '.join(s['code'] for s in home)}")
    if not home:
        return None
    s = home[0]
    order = STRAIGHT if fmt in CALCULATION else ()
    for level in (*order, "Advance"):
        check = s["difficulty"].get(level, {}).get("check")
        if check and not verify.dimension_problems(tags, check, fmt, case_matches):
            return s, level
    return None


def _shape(skill):
    return next(
        lv["check"]["within"] for lv in skill["difficulty"].values() if "within" in lv.get("check", {})
    )


def rehome(conn, actor=ACTOR):
    """Retire the replaced skill sets, move their questions, retire their library worksheets. The caller
    commits. Returns {'retired_sets': [...], 'moved': Counter{(skill, level)}, 'no_place': Counter{old set}}."""
    old = sorted(replaced())
    retired = [
        r["code"]
        for r in conn.execute(
            "update skill_set set status = 'retired', retired_by = %s, retired_at = now()"
            " where code = any(%s) and status <> 'retired' returning code",
            (actor, old),
        ).fetchall()
    ]
    skills, case_matches = shaped(conn), cases.matches(conn)
    moved, no_place = Counter(), Counter()
    for r in conn.execute(
        "select id, tenant_id, fmt, tags, skill_set_code from item"
        " where status = 'active' and skill_set_code = any(%s)",
        (old,),
    ).fetchall():
        home = place(r["fmt"], r["tags"], skills, case_matches)
        if home is None:
            conn.execute(
                "insert into item_feedback (tenant_id, item_id, actor, verdict, note) values (%s,%s,%s,'retire',%s)",
                (
                    r["tenant_id"],
                    r["id"],
                    actor,
                    "no place in the taxonomy-shaped skills: no skill's shape and level holds it",
                ),
            )
            no_place[r["skill_set_code"]] += 1
            continue
        s, level = home
        conn.execute(
            "update item set skill_set_code = %s, difficulty = %s, rung_code = %s, skill_set_version = %s"
            " where id = %s",
            (s["code"], level, s["rung_code"], s["version"], r["id"]),
        )
        moved[(s["code"], level)] += 1
    conn.execute(
        "update sheet_template set retired_at = now() where source = 'library' and retired_at is null"
        " and skill_set_code = any(%s)",
        (old,),
    )
    return {"retired_sets": retired, "moved": moved, "no_place": no_place}
