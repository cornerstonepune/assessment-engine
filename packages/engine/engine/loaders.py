"""Seed JSON to tables.

Every write is an upsert keyed on the natural code, so running the loader twice changes
nothing. That property is the whole gate on Phase 0: if a second run moves a single row, the
registry cannot be trusted as the thing every assessment result joins to.
"""
import json

from engine import db

SEED = db.REPO_ROOT / "supabase" / "seed"

FILLED_TABLES = (
    "tenant", "skill", "milestone", "rung", "level_rule",
    "misconception", "case_dimension", "coverage_target", "prompt", "threshold",
    "config", "skill_set",
)

THRESHOLDS = [
    ("state.min_events", 3, "events", "Below this an estimate stays 'not enough yet'"),
    ("state.min_observers", 2, "observers", "Distinct adults or contexts before a level is claimed"),
    ("next_sheet.promote_at", 0.80, "proportion", "At-band correct over the last two sheets to move to L+"),
    ("next_sheet.demote_below", 0.50, "proportion", "Below this, the next sheet drops to L-"),
    ("exposure.days", 21, "days", "An item a child has seen within this window is not reused"),
    ("item.flag_low_p", 0.20, "proportion", "Below this p_correct the item may be mis-levelled"),
    ("item.flag_high_p", 0.95, "proportion", "Above this p_correct the item may be too easy"),
    ("read.auto_confirm_above", 0.90, "confidence", "Cell reads above this skip the confirm queue"),
    ("marking.agreement_gate", 0.95, "proportion", "Agreement with teacher marking before marks are trusted"),
    ("confirm.queue_minutes", 2, "minutes", "Target time for a teacher to clear one class"),
]


def _seed(name, key):
    return json.loads((SEED / name).read_text())[key]


def _text_array(values):
    """The taxonomy mixes numbers and letters in one dimension (operand digits are 1..4 and N),
    so every allowed value is stored as text rather than forcing a type the source does not have."""
    return [str(v) for v in values]


def _tenant(conn) -> str:
    slug = db.tenant_slug()
    conn.execute(
        "insert into tenant (slug, name) values (%s, %s) on conflict (slug) do nothing",
        (slug, "Cornerstone School, Pune"),
    )
    return conn.execute("select id from tenant where slug = %s", (slug,)).fetchone()["id"]


def _registry(conn, t):
    data = json.loads((SEED / "registry-num.json").read_text())["skills"]
    for code, k in data.items():
        parts = code.split(".")
        conn.execute(
            "insert into skill (tenant_id, code, domain, strand, name, description, source)"
            " values (%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set domain=excluded.domain,"
            " strand=excluded.strand, name=excluded.name, description=excluded.description,"
            " source=excluded.source, updated_at=now()",
            (t, code, parts[0], ".".join(parts[:2]), k["name"], k.get("desc", ""), k.get("src", "")),
        )
        for m in k.get("ms", []):
            conn.execute(
                "insert into milestone (tenant_id, skill_code, band, descriptor, scale, source)"
                " values (%s,%s,%s,%s,%s,%s)"
                " on conflict (tenant_id, skill_code, band) do update set"
                " descriptor=excluded.descriptor, scale=excluded.scale, updated_at=now()",
                (t, code, m["b"], m["d"], m.get("s", "none"), m.get("src", "")),
            )


def _rungs(conn, t):
    for r in _seed("rungs.json", "rungs"):
        conn.execute(
            "insert into rung (tenant_id, code, band, ladder_order, descriptor, skill_codes)"
            " values (%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set band=excluded.band,"
            " ladder_order=excluded.ladder_order, descriptor=excluded.descriptor,"
            " skill_codes=excluded.skill_codes, updated_at=now()",
            (t, r["code"], r["band"], r["ladder_order"], r["descriptor"], r["skill_codes"]),
        )


def _levels(conn, t):
    for lv in _seed("levels.json", "levels"):
        conn.execute(
            "insert into level_rule (tenant_id, band, level, rung_codes,"
            " foundational_rung_code, probe_rung_code) values (%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, band, level) do update set rung_codes=excluded.rung_codes,"
            " foundational_rung_code=excluded.foundational_rung_code,"
            " probe_rung_code=excluded.probe_rung_code, updated_at=now()",
            (t, lv["band"], lv["level"], lv["rung_codes"],
             lv["foundational_rung_code"], lv["probe_rung_code"]),
        )


def _misconceptions(conn, t):
    for m in _seed("misconceptions.json", "misconceptions"):
        conn.execute(
            "insert into misconception (tenant_id, code, op, name, description, repair_hint,"
            " detectable_by, source, external_ref) values (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code, op) do update set name=excluded.name,"
            " description=excluded.description, repair_hint=excluded.repair_hint,"
            " detectable_by=excluded.detectable_by, source=excluded.source,"
            " external_ref=excluded.external_ref, updated_at=now()",
            (t, m["code"], m["op"], m["name"], m.get("description", ""), m["repair_hint"],
             m["detectable_by"], m.get("source", ""), m.get("external_ref")),
        )


def _dimensions(conn, t):
    for i, d in enumerate(_seed("case_dimensions.json", "case_dimensions"), start=1):
        conn.execute(
            "insert into case_dimension (tenant_id, code, name, description, allowed_values,"
            " dimension_order, source) values (%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set name=excluded.name,"
            " description=excluded.description, allowed_values=excluded.allowed_values,"
            " dimension_order=excluded.dimension_order, source=excluded.source, updated_at=now()",
            (t, d["name"], d["name"], d.get("why", ""), _text_array(d["allowed"]), i, d.get("source", "")),
        )


def _coverage(conn, t):
    for c in _seed("coverage_targets.json", "coverage_targets"):
        conn.execute(
            "insert into coverage_target (tenant_id, rung_code, dimension_code, required_values,"
            " min_items, note) values (%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, rung_code, dimension_code) do update set"
            " required_values=excluded.required_values, min_items=excluded.min_items,"
            " note=excluded.note, updated_at=now()",
            (t, c["rung_code"], c["dimension"], _text_array(c["values"]),
             c.get("min_items", 1), c.get("note", "")),
        )


def _prompts(conn, t):
    for p in _seed("prompts.json", "prompts"):
        text = (SEED / p["text_file"]).read_text() if p.get("text_file") else p["text"]
        conn.execute(
            "insert into prompt (tenant_id, purpose, version, text, model, json_schema, active)"
            " values (%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, purpose, version) do update set text=excluded.text,"
            " model=excluded.model, json_schema=excluded.json_schema, active=excluded.active,"
            " updated_at=now()",
            (t, p["purpose"], p["version"], text, p["model"],
             json.dumps(p["json_schema"]), p.get("active", False)),
        )


def _thresholds(conn, t):
    for key, value, unit, note in THRESHOLDS:
        conn.execute(
            "insert into threshold (tenant_id, key, value, unit, description)"
            " values (%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, key) do update set value=excluded.value,"
            " unit=excluded.unit, description=excluded.description, updated_at=now()",
            (t, key, value, unit, note),
        )


def _config(conn, t):
    for c in _seed("config.json", "config"):
        conn.execute(
            "insert into config (tenant_id, key, value, description) values (%s,%s,%s,%s)"
            " on conflict (tenant_id, key) do update set value=excluded.value,"
            " description=excluded.description, updated_at=now()",
            (t, c["key"], json.dumps(c["value"]), c.get("description", "")),
        )


def _skill_sets(conn, t):
    """Status and ratified_by are deliberately not overwritten: Aseem's ratification lives in
    the row, and a reload of the seed must not undo it."""
    for s in _seed("skill_sets.json", "skill_sets"):
        conn.execute(
            "insert into skill_set (tenant_id, code, rung_code, name, learning_objective,"
            " philosophy, formats, misconception_codes, difficulty)"
            " values (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set rung_code=excluded.rung_code,"
            " name=excluded.name, learning_objective=excluded.learning_objective,"
            " philosophy=excluded.philosophy, formats=excluded.formats,"
            " misconception_codes=excluded.misconception_codes, difficulty=excluded.difficulty,"
            " updated_at=now()",
            (t, s["code"], s["rung_code"], s["name"], s["learning_objective"], s["philosophy"],
             s["formats"], s["misconception_codes"], json.dumps(s["difficulty"])),
        )


def load_all() -> dict[str, int]:
    with db.connect() as conn:
        t = _tenant(conn)
        for step in (_registry, _rungs, _levels, _misconceptions,
                     _dimensions, _coverage, _prompts, _thresholds, _config, _skill_sets):
            step(conn, t)
        conn.commit()
        return db.counts(conn, FILLED_TABLES)


def orphans() -> dict[str, list[str]]:
    """Referential checks the schema cannot express, because the codes live in arrays."""
    with db.connect() as conn:
        return {
            "rung skill_codes missing from the registry": [
                r["s"] for r in conn.execute(
                    "select distinct s from rung, unnest(skill_codes) s"
                    " where not exists (select 1 from skill k where k.code = s)").fetchall()],
            "level_rule rungs missing from the ladder": [
                r["s"] for r in conn.execute(
                    "select distinct s from level_rule, unnest(rung_codes) s"
                    " where not exists (select 1 from rung g where g.code = s)").fetchall()],
            "coverage_target rungs missing from the ladder": [
                r["rung_code"] for r in conn.execute(
                    "select distinct rung_code from coverage_target c"
                    " where not exists (select 1 from rung g where g.code = c.rung_code)").fetchall()],
            "coverage_target dimensions missing from the matrix": [
                r["dimension_code"] for r in conn.execute(
                    "select distinct dimension_code from coverage_target c"
                    " where not exists (select 1 from case_dimension d"
                    " where d.code = c.dimension_code)").fetchall()],
            "skill_set misconception codes missing from the vocabulary": [
                r["s"] for r in conn.execute(
                    "select distinct s from skill_set, unnest(misconception_codes) s"
                    " where not exists (select 1 from misconception m where m.code = s)").fetchall()],
        }
