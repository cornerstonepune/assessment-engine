"""Every taxonomy case, counted in the bank. `engine bank taxonomy`.

A case (`taxonomy_case`) is a combination of tags; a question is one when its stored tags satisfy it
(`assess/taxonomy.py`). A case is covered when the active bank holds at least `min_items` such
questions — one worksheet's worth — thin below that, missing at none.
"""

from collections import Counter, defaultdict

from engine.assess import taxonomy


def count(conn):
    cases = conn.execute("select code, section, section_name, label, match, min_items from taxonomy_case order by id").fetchall()
    rows = conn.execute(
        "select fmt, tags, skill_set_code, difficulty from item where status = 'active' and skill_set_code is not null"
    ).fetchall()
    held = {c["code"]: Counter() for c in cases}
    layout = defaultdict(Counter)
    for r in rows:
        for c in cases:
            if taxonomy.matches(c["match"], r["fmt"], r["tags"]):
                held[c["code"]][(r["skill_set_code"], r["difficulty"])] += 1
                layout[c["code"]][r["tags"].get("presentation", "")] += 1
    out = []
    for c in cases:
        n = sum(held[c["code"]].values())
        state = "missing" if n == 0 else ("thin" if n < c["min_items"] else "covered")
        out.append(
            dict(c, n=n, state=state, vertical=layout[c["code"]]["VERTICAL"], horizontal=layout[c["code"]]["HORIZONTAL"],
                 where=held[c["code"]].most_common(3))
        )
    return out
