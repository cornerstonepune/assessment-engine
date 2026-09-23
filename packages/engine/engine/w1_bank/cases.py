"""Every taxonomy case, counted in the bank. `engine bank taxonomy`.

A case (`taxonomy_case`) is a combination of tags; a question is one when its stored tags satisfy it
(`assess/taxonomy.py`). A case is covered when the active bank holds at least `min_items` such
questions — one worksheet's worth — thin below that, missing at none.
"""

from collections import Counter, defaultdict

from engine.assess import taxonomy, verify


def matches(conn, codes=None):
    """{case code: match} — every case, or the ones named."""
    rows = conn.execute(
        "select code, match from taxonomy_case" + (" where code = any(%s)" if codes is not None else ""),
        (list(codes),) if codes is not None else (),
    ).fetchall()
    return {r["code"]: r["match"] for r in rows}


def for_level(conn, check):
    """{case code: match} for one level's cases, each on the level's own numbers when its skill has a shape."""
    return {c: taxonomy.within(m, check.get("within")) for c, m in matches(conn, check["cases"]).items()}


def of(fmt, tags, all_matches):
    """The taxonomy cases a question is, as measured: every case whose match its tags satisfy."""
    return sorted(c for c, m in all_matches.items() if taxonomy.matches(m, fmt, tags))


def count(conn):
    cases = conn.execute(
        "select code, section, section_name, label, match, min_items from taxonomy_case order by id"
    ).fetchall()
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
            dict(
                c,
                n=n,
                state=state,
                vertical=layout[c["code"]]["VERTICAL"],
                horizontal=layout[c["code"]]["HORIZONTAL"],
                where=held[c["code"]].most_common(3),
            )
        )
    return out


def propose_levels(conn, codes=None):
    """The seed's levels and kinds onto the skill sets already in the database (step 8h).

    `engine load` never overwrites a skill set — a person may have edited it on the screen — so a
    rewritten level reaches an existing row only through this, on purpose. The words a person approved
    (name, outcome) are kept; only `difficulty` and `formats` change, and the versioning trigger
    withdraws the ratification, so every changed skill waits on the Skill Map for one approval.
    Returns the codes that changed."""
    import json

    from engine.core import loaders

    seed = {s["code"]: s for s in loaders._seed("skill_sets.json", "skill_sets")}
    changed = []
    for r in conn.execute("select code, difficulty, formats from skill_set order by code").fetchall():
        s = seed.get(r["code"])
        if not s or (codes and r["code"] not in codes):
            continue
        if s["difficulty"] != r["difficulty"] or list(s["formats"]) != list(r["formats"]):
            conn.execute(
                "update skill_set set difficulty = %s, formats = %s where code = %s",
                (json.dumps(s["difficulty"]), list(s["formats"]), r["code"]),
            )
            changed.append(r["code"])
    return changed


def outside_their_level(conn):
    """Every active generated question the rule of its own level no longer holds — re-measured against
    that level's region, not only its own arithmetic (BUILD-ORDER gate 4, amended; step 8h) — or keyed by
    a rule its kind has since corrected (`verify.key_problems`)."""
    regions = {
        (s["code"], band): spec.get("check", {})
        for s in conn.execute("select code, difficulty from skill_set").fetchall()
        for band, spec in s["difficulty"].items()
    }
    case_matches = matches(conn)
    out = []
    for r in conn.execute(
        "select id, tenant_id, item_key, fmt, tags, spec, skill_set_code, difficulty from item"
        " where status = 'active' and source = 'generated' and skill_set_code is not null"
    ).fetchall():
        region = regions.get((r["skill_set_code"], r["difficulty"]))
        why = verify.dimension_problems(r["tags"], region, r["fmt"], case_matches) if region else []
        if why := why + verify.key_problems(r["fmt"], r["spec"]):
            out.append(dict(r, why=why))
    return out


def placed(conn):
    """Where every taxonomy case sits among the levels in use (goals/s13-levels-by-taxonomy.yaml): the levels
    that name it, or — for a section the `taxonomy.across_levels` row names — the rule those levels climb.
    Returns [(code, section, [(skill, level), ...], 'placed' | 'pattern' | 'unplaced')], in the document's order."""
    row = conn.execute("select value from config where key = 'taxonomy.across_levels'").fetchone()
    across = set((row["value"] if row else {}).get("sections", []))
    named = defaultdict(list)
    for s in conn.execute("select code, difficulty from skill_set order by code"):
        for level, spec in s["difficulty"].items():
            for c in spec.get("check", {}).get("cases", []):
                named[c].append((s["code"], level))
    out = []
    for c in conn.execute(
        "select code, section from taxonomy_case order by string_to_array(section, '.')::int[], code"
    ):
        where = named.get(c["code"], [])
        state = "placed" if where else ("pattern" if c["section"] in across else "unplaced")
        out.append((c["code"], c["section"], where, state))
    return out
