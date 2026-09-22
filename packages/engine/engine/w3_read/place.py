"""Which skill sets an old paper's question counts for (N3 → N5, ADR 0034). `engine legacy place`.

A question from a paper set before the QR sheets carries the rung a person gave it, and a rung is not a
skill set: R9 holds 3-digit addition *and* subtraction, while its one skill set, ADD.3D.REG, practises
addition — so grouping answers by rung charged a child's subtraction mistakes to her addition paper and
gave subtraction no next paper at all. A question counts instead for the skill sets whose levels hold
it: its numbers measured (`assess/tags.py`), matched to the team's taxonomy cases (`assess/taxonomy.py`),
each case to the levels that name it. A question whose numbers match no case counts for the skill set on
its own rung whose questions use its skill. One that matches neither is returned, never dropped.
A generated question needs none of this: it was made for one skill set and level (`item.skill_set_code`).
"""

from engine.assess import tags as T
from engine.assess import taxonomy
from engine.assess.items import Item


def placements(row, kind_as, case_matches, holders, on_rung):
    """→ [(skill set, level or None, how)] for one old question. Pure.

    `kind_as` reads an old paper's kind as the bank's, `holders` is {case: [(skill set, level)]},
    `on_rung` is {rung: [(skill set, skills its questions use)]}."""
    fmt = kind_as.get(row["fmt"], row["fmt"])
    tags = T.derive(Item("", "", row["rung_code"], [], "", fmt, False, row["stem"], row["spec"], []))
    out = {}
    for case, match in sorted(case_matches.items()):
        if taxonomy.matches(match, fmt, tags):
            for skill_set, level in holders.get(case, []):
                out.setdefault((skill_set, level), f"case:{case}")
    if out:
        return sorted((s, lvl, how) for (s, lvl), how in out.items())
    return [
        (s, None, "rung")
        for s, uses in on_rung.get(row["rung_code"], [])
        if set(uses) & set(row["skill_codes"])
    ]


def _inputs(conn):
    row = conn.execute("select value from config where key = 'legacy.kind_as'").fetchone()
    if not row:
        raise RuntimeError("config has no legacy.kind_as — run `engine load`")
    holders = {}
    for r in conn.execute(  # a level outside the add/sub taxonomy (MUL.1D, WORD.BUDGET …) names no cases
        "select c.code as case, s.code, d.level from skill_set s, jsonb_each(s.difficulty) as d(level, spec),"
        " jsonb_array_elements_text(d.spec -> 'check' -> 'cases') as c(code) order by 2, 3"
    ).fetchall():
        holders.setdefault(r["case"], []).append((r["code"], r["level"]))
    on_rung = {}
    for r in conn.execute(
        "select s.rung_code, s.code, array_agg(distinct sk) as uses from skill_set s"
        " join item i on i.skill_set_code = s.code and i.source = 'generated' and i.status = 'active',"
        " unnest(i.skill_codes) as sk group by 1, 2 order by 1, 2"
    ).fetchall():
        on_rung.setdefault(r["rung_code"], []).append((r["code"], r["uses"]))
    matches = {r["code"]: r["match"] for r in conn.execute("select code, match from taxonomy_case")}
    return row["value"], matches, holders, on_rung


def place(conn):
    """Every old question's placements rewritten from its numbers and today's levels. → the old
    questions that count for no skill set, each for a person to place."""
    kind_as, matches, holders, on_rung = _inputs(conn)
    rows = conn.execute(
        "select id, tenant_id, item_key, fmt, stem, spec, rung_code, skill_codes from item"
        " where source = 'legacy' order by item_key"
    ).fetchall()
    conn.execute("delete from item_placement")
    unplaced = []
    for r in rows:
        found = placements(r, kind_as, matches, holders, on_rung)
        if not found:
            unplaced.append(r)
        with conn.cursor() as cur:
            cur.executemany(
                "insert into item_placement (tenant_id, item_id, skill_set_code, difficulty, placed_by)"
                " values (%s,%s,%s,%s,%s)",
                [(r["tenant_id"], r["id"], s, lvl, how) for s, lvl, how in found],
            )
    return unplaced
