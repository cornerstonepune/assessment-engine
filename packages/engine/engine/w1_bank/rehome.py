"""The bank re-homed onto the taxonomy-shaped skills, and the old ladder removed (ADR 0034).

A calculation skill is one operation and one digit shape (`2-digit + 2-digit`), and its levels are the
taxonomy's own cases on those numbers. The seed says which old skill sets each new one replaces.

Nothing is regenerated. Where a question belongs follows from what it is — its measured tags — and the map
(`assess/placing.py`), exactly as its taxonomy cases do (ADR 0030): every question of an old skill set, in use or
retired, moves to its skill and level; an old paper's sums move to their skill's rung. Then the old skill sets,
their rule history, the library worksheets never handed out, and the old rungs nothing names any more are
deleted. A worksheet already printed keeps its questions and says which skill set it was made for; a child's
recorded answers are never touched (rule 4) — the graph reads them through their questions
(`evidence_placed`). A question with no place stops the run and names itself: the map is wrong, and nothing is
deleted until it is right. Running it again changes nothing.
"""

from collections import Counter

from engine.assess import placing, tags, taxonomy
from engine.assess.items import Item
from engine.core import loaders
from engine.w1_bank import cases


def replaced(seed=None):
    """{old skill set: the new ones that replace it} — from the seed, where a person wrote it."""
    out = {}
    for s in seed if seed is not None else loaders._seed("skill_sets.json", "skill_sets"):
        for old in s.get("replaces", []):
            out.setdefault(old, []).append(s["code"])
    return out


def shaped(conn):
    """The skills that have a shape, with their levels' checks and rung."""
    return placing.shaped(
        conn.execute("select code, rung_code, version, difficulty from skill_set order by code").fetchall()
    )


ACTOR = "engine (bank rehome)"
UNLEVELLED = (
    "its numbers put it in this skill, but no level of it holds this kind of question as measured"
    " (a story whose shape the engine cannot name): retired by the rehome, kept, and never on a new paper"
)


def sort_out(rows, skills, case_matches):
    """(moves, unlevelled, homeless). A question goes to the one skill whose numbers it has, at the level its case
    names; one whose skill is plain from its numbers but whose case no level holds as measured — an old story the
    labeller cannot name — goes to that skill retired (`UNLEVELLED`), kept and never dealt again; only a question no
    skill's numbers hold stops the run, since then the map itself is wrong."""
    moves, unlevelled, homeless = [], [], []
    for r in rows:
        home = placing.place(r["fmt"], r["tags"], skills, case_matches)
        if home:
            moves.append((r, home))
            continue
        by_shape = [s for s in skills if taxonomy.matches(placing.shape(s), r["fmt"], r["tags"])]
        (unlevelled if len(by_shape) == 1 else homeless).append((r, by_shape[0] if by_shape else None))
    return moves, unlevelled, homeless


def rehome(conn):
    """Move every question of the replaced skill sets, then remove the old ladder. The caller commits.
    Returns {'moved': Counter{(skill, level)}, 'old_papers': n, 'removed_sets': [...], 'removed_rungs': [...]}."""
    old = sorted(replaced())
    skills, case_matches = shaped(conn), cases.matches(conn)
    rows = conn.execute(
        "select id, tenant_id, item_key, fmt, tags from item where skill_set_code = any(%s)", (old,)
    ).fetchall()
    moves, unlevelled, homeless = sort_out(rows, skills, case_matches)
    if homeless:
        raise ValueError(
            f"{len(homeless)} questions have no place in the new skills, so nothing moved — "
            + unplaced([r for r, _ in homeless])
        )
    moved = Counter()
    for r, (s, level) in moves:
        conn.execute(
            "update item set skill_set_code = %s, difficulty = %s, rung_code = %s, skill_set_version = %s"
            " where id = %s",
            (s["code"], level, s["rung_code"], s["version"], r["id"]),
        )
        moved[(s["code"], level)] += 1
    for r, s in unlevelled:
        conn.execute(
            "update item set skill_set_code = %s, difficulty = 'Advance', rung_code = %s, skill_set_version = %s"
            " where id = %s",
            (s["code"], s["rung_code"], s["version"], r["id"]),
        )
        conn.execute(
            "insert into item_feedback (tenant_id, item_id, actor, verdict, note) values (%s,%s,%s,'retire',%s)",
            (r["tenant_id"], r["id"], ACTOR, UNLEVELLED),
        )
    old_papers = _old_papers(conn, skills, case_matches)
    conn.execute(
        "delete from sheet_template t where t.source = 'library' and t.skill_set_code = any(%s)"
        " and not exists (select 1 from sheet_instance si where si.sheet_template_id = t.id)",
        (old,),
    )
    rungs = [
        r["rung_code"] for r in conn.execute("select rung_code from skill_set where code = any(%s)", (old,))
    ]
    conn.execute("delete from skill_set_version where code = any(%s)", (old,))
    removed_sets = [
        r["code"] for r in conn.execute("delete from skill_set where code = any(%s) returning code", (old,))
    ]
    removed_rungs = [
        r["code"]
        for r in conn.execute(
            "delete from rung r where r.code = any(%s)"
            " and not exists (select 1 from item i where i.tenant_id = r.tenant_id and i.rung_code = r.code)"
            " and not exists (select 1 from skill_set s where s.tenant_id = r.tenant_id and s.rung_code = r.code)"
            " returning code",
            (sorted(set(rungs)),),
        )
    ]
    return {
        "moved": moved,
        "retired": Counter(s["code"] for _, s in unlevelled),
        "old_papers": old_papers,
        "removed_sets": removed_sets,
        "removed_rungs": removed_rungs,
    }


def unplaced(rows):
    """Every kind of question without a place, counted, with one example of each — the whole list in one run."""
    kind = lambda r: (r["fmt"], (r["tags"] or {}).get("structure") or (r["tags"] or {}).get("operation"))  # noqa: E731
    kinds, first = Counter(map(kind, rows)), {}
    for r in rows:
        first.setdefault(kind(r), r["item_key"])
    return "; ".join(
        f"{n} {fmt}{f' {what}' if what else ''} (e.g. {first[(fmt, what)]})"
        for (fmt, what), n in kinds.most_common()
    )


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
