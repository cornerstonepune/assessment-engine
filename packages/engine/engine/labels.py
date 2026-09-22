"""A question's derived labels, recomputed from the question (ADR 0030). `engine bank relabel`.

A label on a question — the skills it uses — is a measurement of the question, not a fact about it. The
question itself (its numbers, its words, its answer) is never changed here; only what code reads off it,
the way a paper entered again is re-read (ADR 0030). Old papers' questions (`source = 'legacy'`) carry
the skill a person gave them and are never relabelled.
"""

from engine.assess import skills as S

RULE_KEYS = {"by_operation": "skills.by_operation", "by_kind": "skills.by_kind", "by_symbol": "skills.by_symbol"}


def rules(conn):
    rows = {r["key"]: r["value"] for r in conn.execute("select key, value from config where key like 'skills.%'")}
    missing = [key for key in RULE_KEYS.values() if key not in rows]
    if missing:
        raise RuntimeError(f"config has no {', '.join(missing)} — run `engine load`")
    return {name: rows[key] for name, key in RULE_KEYS.items()}


def _generated(conn):
    return conn.execute(
        "select i.id, i.fmt, i.spec, i.stem, i.skill_codes, r.skill_codes as rung_skills"
        " from item i join rung r on r.tenant_id = i.tenant_id and r.code = i.rung_code"
        " where i.source = 'generated'"
    ).fetchall()


def _wanted(row, rs):
    return S.used(row["fmt"], row["spec"], row["stem"], list(row["rung_skills"]), rs)


def mislabelled(conn):
    """Every generated question whose skills are not the ones it uses — `engine audit`'s invariant."""
    rs = rules(conn)
    return [f"{r['id']}: {list(r['skill_codes'])} ≠ {w}" for r in _generated(conn) if list(r["skill_codes"]) != (w := _wanted(r, rs))]


def relabel(conn):
    """Recompute every generated question's skills; return how many changed. The caller commits."""
    rs = rules(conn)
    changes = [(r["id"], w) for r in _generated(conn) if list(r["skill_codes"]) != (w := _wanted(r, rs))]
    if changes:
        with conn.cursor() as cur:
            cur.executemany("update item set skill_codes = %s, updated_at = now() where id = %s", [(w, i) for i, w in changes])
    return {"skills": len(changes)}
