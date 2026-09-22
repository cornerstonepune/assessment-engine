"""A question's derived labels, recomputed from the question (ADR 0030). `engine bank relabel`.

A label on a question — the skills it uses — is a measurement of the question, not a fact about it. The
question itself (its numbers, its words, its answer) is never changed here; only what code reads off it,
the way a paper entered again is re-read (ADR 0030). Old papers' questions (`source = 'legacy'`) carry
the skill a person gave them and are never relabelled.
"""

import json

from engine.assess import skills as S

RULE_KEYS = {
    "by_operation": "skills.by_operation",
    "by_kind": "skills.by_kind",
    "by_symbol": "skills.by_symbol",
    "charges_by_kind": "skills.charges_by_kind",
}


def rules(conn):
    rows = {r["key"]: r["value"] for r in conn.execute("select key, value from config where key like 'skills.%'")}
    missing = [key for key in RULE_KEYS.values() if key not in rows]
    if missing:
        raise RuntimeError(f"config has no {', '.join(missing)} — run `engine load`")
    return {name: rows[key] for name, key in RULE_KEYS.items()}


def vocabulary(conn):
    """{(code, op): (skill_from, skill_code)} — what each named mistake charges (step 8b)."""
    return {
        (r["code"], r["op"]): (r["skill_from"], r["skill_code"])
        for r in conn.execute("select code, op, skill_from, skill_code from misconception")
    }


def _generated(conn):
    return conn.execute(
        "select i.id, i.fmt, i.spec, i.stem, i.responses, i.skill_codes, i.mistake_skills,"
        " r.skill_codes as rung_skills"
        " from item i join rung r on r.tenant_id = i.tenant_id and r.code = i.rung_code"
        " where i.source = 'generated'"
    ).fetchall()


def measure(fmt, spec, stem, responses, rung_skills, rs, vocab):
    """(skills, mistake_skills) for one question: the labels `relabel` keeps and `bank.fill` writes."""
    skills = S.used(fmt, spec, stem, list(rung_skills), rs)
    codes = sorted({c for r in responses for c in (r.get("misconceptions") or {})})
    return skills, S.charges(fmt, spec, stem, skills, codes, vocab, rs)


def _drift(conn):
    rs, vocab = rules(conn), vocabulary(conn)
    for r in _generated(conn):
        skills, charged = measure(r["fmt"], r["spec"], r["stem"], r["responses"], r["rung_skills"], rs, vocab)
        yield r, skills, charged


def mislabelled(conn):
    """Every generated question whose labels are not the ones it measures — `engine audit`'s invariant."""
    out = []
    for r, skills, charged in _drift(conn):
        if list(r["skill_codes"]) != skills:
            out.append(f"{r['id']}: skills {list(r['skill_codes'])} ≠ {skills}")
        elif r["mistake_skills"] != charged:
            out.append(f"{r['id']}: mistakes charge {r['mistake_skills']} ≠ {charged}")
    return out


def relabel(conn):
    """Recompute every generated question's labels; return how many of each changed. The caller commits."""
    skill_changes, charge_changes = [], []
    for r, skills, charged in _drift(conn):
        if list(r["skill_codes"]) != skills:
            skill_changes.append((skills, r["id"]))
        if r["mistake_skills"] != charged:
            charge_changes.append((json.dumps(charged), r["id"]))
    with conn.cursor() as cur:
        if skill_changes:
            cur.executemany("update item set skill_codes = %s, updated_at = now() where id = %s", skill_changes)
        if charge_changes:
            cur.executemany("update item set mistake_skills = %s, updated_at = now() where id = %s", charge_changes)
    return {"skills": len(skill_changes), "mistake_skills": len(charge_changes)}
