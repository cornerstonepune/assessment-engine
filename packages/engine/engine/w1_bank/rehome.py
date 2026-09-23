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

from engine.assess import placing, tags
from engine.assess.items import Item
from engine.core import loaders
from engine.w1_bank import cases

ACTOR = "engine (taxonomy-shaped skills)"


def replaced(seed=None):
    """{old skill set: the new ones that replace it} — from the seed, where a person wrote it."""
    out = {}
    for s in seed if seed is not None else loaders._seed("skill_sets.json", "skill_sets"):
        for old in s.get("replaces", []):
            out.setdefault(old, []).append(s["code"])
    return out


def shaped(conn):
    """The skills in use that have a shape, with their levels' checks and rung."""
    return placing.shaped(
        conn.execute(
            "select code, rung_code, version, difficulty from skill_set where status <> 'retired' order by code"
        ).fetchall()
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
        home = placing.place(r["fmt"], r["tags"], skills, case_matches)
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
    return {
        "retired_sets": retired,
        "moved": moved,
        "no_place": no_place,
        "old_papers": _old_papers(conn, skills, case_matches),
    }


def _old_papers(conn, skills, case_matches):
    """An old paper's sums (W3, `legacy`) onto the skill whose shape they have, as `legacy.rung_for` now files
    them: the rung their answers count on in a child's graph. Returns how many moved."""
    n = 0
    for r in conn.execute(
        "select id, rung_code, spec from item where source = 'legacy' and spec ? 'a' and spec ? 'b' and spec ? 'op'"
    ).fetchall():
        sp = r["spec"]
        if sp["op"] not in ("+", "-") or (sp["op"] == "-" and sp["a"] < sp["b"]):
            continue
        t = tags.derive(
            Item("", "", "", [], "", "bare_sum", False, "", {"a": sp["a"], "b": sp["b"], "op": sp["op"]}, [])
        )
        home = placing.place("bare_sum", t, skills, case_matches)
        if home and home[0]["rung_code"] != r["rung_code"]:
            conn.execute("update item set rung_code = %s where id = %s", (home[0]["rung_code"], r["id"]))
            n += 1
    return n
