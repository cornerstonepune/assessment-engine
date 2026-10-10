"""Seed JSON to tables.

Every write is an upsert keyed on the natural code, so running the loader twice changes
nothing. That property is the whole gate on Phase 0: if a second run moves a single row, the
registry cannot be trusted as the thing every assessment result joins to.
"""

import json
from typing import Any, LiteralString

from engine.core import asks, db, settings, topics

SEED = settings.SEED

FILLED_TABLES = (
    "tenant",
    "domain",
    "skill",
    "milestone",
    "learning_objective",
    "learning_objective_skill",
    "activity",
    "activity_skill",
    "report_item",
    "trait",
    "rung",
    "level_rule",
    "misconception",
    "case_dimension",
    "taxonomy_case",
    "prompt",
    "threshold",
    "config",
    "skill_set",
    "subject",
    "topic",
    "ask",
)


def _text_array(values: list[Any]) -> list[str]:
    """The taxonomy mixes numbers and letters in one dimension (operand digits are 1..4 and N),
    so every allowed value is stored as text rather than forcing a type the source does not have."""
    return [str(v) for v in values]


def _tenant(conn: db.Conn) -> db.Id:
    slug = db.tenant_slug()
    conn.execute(
        "insert into tenant (slug, name) values (%s, %s) on conflict (slug) do nothing",
        (slug, "Cornerstone School, Pune"),
    )
    return db.one(conn, "select id from tenant where slug = %s", (slug,))["id"]


def _registry(conn: db.Conn, t: db.Id) -> None:
    """The whole skill map — all 14 domains, not the maths slice.

    `registry.json` is generated from the Skill Map Review artifact and never hand-edited; it
    carries the school's own learning objectives, activity plans (with their three-level mastery
    descriptors), report-card lines and traits alongside the skills, because dropping them on
    import only means extracting them again later.
    """
    reg = json.loads((SEED / "registry.json").read_text())

    # 11k rows: `executemany` pipelines them, one statement per table instead of one round trip
    # per row. Loading the whole map takes seconds that way and minutes the other way, and the
    # loader runs three times in the test suite.
    def many(sql: LiteralString, rows: list[tuple[Any, ...]]) -> None:
        if rows:
            conn.cursor().executemany(sql, rows)

    many(
        "insert into domain (tenant_id, code, name) values (%s,%s,%s)"
        " on conflict (tenant_id, code) do update set name=excluded.name, updated_at=now()",
        [(t, d["code"], d["name"]) for d in reg["domains"]],
    )

    many(
        "insert into skill (tenant_id, code, domain, strand, name, description, source,"
        " skill_type, pillar, ncf, cg, authored_by) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        " on conflict (tenant_id, code) do update set domain=excluded.domain,"
        " strand=excluded.strand, name=excluded.name, description=excluded.description,"
        " source=excluded.source, skill_type=excluded.skill_type, pillar=excluded.pillar,"
        " ncf=excluded.ncf, cg=excluded.cg, authored_by=excluded.authored_by, updated_at=now()",
        [
            (
                t,
                code,
                code.split(".")[0],
                ".".join(code.split(".")[:2]),
                k["name"],
                k.get("desc", ""),
                k.get("src", ""),
                k.get("type", ""),
                k.get("pillar", ""),
                k.get("ncf", ""),
                k.get("cg", ""),
                k.get("by", ""),
            )
            for code, k in reg["skills"].items()
        ],
    )

    many(
        "insert into milestone (tenant_id, skill_code, band, descriptor, scale, source)"
        " values (%s,%s,%s,%s,%s,%s)"
        " on conflict (tenant_id, skill_code, band) do update set"
        " descriptor=excluded.descriptor, scale=excluded.scale, updated_at=now()",
        [
            (t, code, m["b"], m["d"], m.get("s", "none"), m.get("src", ""))
            for code, k in reg["skills"].items()
            for m in k.get("ms", [])
        ],
    )

    many(
        "insert into learning_objective (tenant_id, code, band, subject, unit, title, signal,"
        " confidence) values (%s,%s,%s,%s,%s,%s,%s,%s)"
        " on conflict (tenant_id, code) do update set band=excluded.band,"
        " subject=excluded.subject, unit=excluded.unit, title=excluded.title,"
        " signal=excluded.signal, confidence=excluded.confidence, updated_at=now()",
        [
            (
                t,
                lo["code"],
                lo["band"],
                lo["subject"],
                lo["unit"],
                lo["title"],
                lo["signal"],
                lo["confidence"],
            )
            for lo in reg["learning_objectives"]
        ],
    )

    many(
        "insert into learning_objective_skill (tenant_id, lo_code, skill_code)"
        " values (%s,%s,%s) on conflict do nothing",
        [(t, row["lo"], row["skill"]) for row in reg["learning_objective_skills"]],
    )

    many(
        "insert into activity (tenant_id, code, band, strand, name, objective, level_1,"
        " level_2, level_3, confidence, requirement, printable, note, source_file, source_tab,"
        " source_row, source_url) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        " on conflict (tenant_id, code) do update set band=excluded.band,"
        " strand=excluded.strand, name=excluded.name, objective=excluded.objective,"
        " level_1=excluded.level_1, level_2=excluded.level_2, level_3=excluded.level_3,"
        " confidence=excluded.confidence, requirement=excluded.requirement,"
        " printable=excluded.printable, note=excluded.note, source_file=excluded.source_file,"
        " source_tab=excluded.source_tab, source_row=excluded.source_row,"
        " source_url=excluded.source_url, updated_at=now()",
        [
            (
                t,
                a["code"],
                a["band"],
                a["strand"],
                a["name"],
                a["objective"],
                a["level_1"],
                a["level_2"],
                a["level_3"],
                a["confidence"],
                a["requirement"],
                a["printable"],
                a["note"],
                a["source_file"],
                a["source_tab"],
                a["source_row"],
                a["source_url"],
            )
            for a in reg["activities"]
        ],
    )

    many(
        "insert into activity_skill (tenant_id, activity_code, skill_code)"
        " values (%s,%s,%s) on conflict do nothing",
        [(t, row["activity"], row["skill"]) for row in reg["activity_skills"]],
    )

    many(
        "insert into report_item (tenant_id, skill_code, band, title, section)"
        " values (%s,%s,%s,%s,%s)"
        " on conflict (tenant_id, skill_code, band, title) do update set"
        " section=excluded.section, updated_at=now()",
        [(t, r["skill"], r["band"], r["title"], r["section"]) for r in reg["report_items"]],
    )

    many(
        "insert into trait (tenant_id, code, band, label, positive, concern, expected,"
        " exceeding, linked, authored_by, source) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
        " on conflict (tenant_id, code, band) do update set label=excluded.label,"
        " positive=excluded.positive, concern=excluded.concern, expected=excluded.expected,"
        " exceeding=excluded.exceeding, linked=excluded.linked,"
        " authored_by=excluded.authored_by, source=excluded.source, updated_at=now()",
        [
            (
                t,
                tr["code"],
                tr["band"],
                tr["label"],
                tr["positive"],
                tr["concern"],
                tr["expected"],
                tr["exceeding"],
                tr["linked"],
                tr["by"],
                tr["src"],
            )
            for tr in reg["traits"]
        ],
    )


def _rungs(conn: db.Conn, t: db.Id) -> None:
    for r in settings.seed("rungs.json", "rungs"):
        conn.execute(
            "insert into rung (tenant_id, code, band, ladder_order, descriptor, skill_codes)"
            " values (%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set band=excluded.band,"
            " ladder_order=excluded.ladder_order, descriptor=excluded.descriptor,"
            " skill_codes=excluded.skill_codes, updated_at=now()",
            (t, r["code"], r["band"], r["ladder_order"], r["descriptor"], r["skill_codes"]),
        )


def _levels(conn: db.Conn, t: db.Id) -> None:
    for lv in settings.seed("levels.json", "levels"):
        conn.execute(
            "insert into level_rule (tenant_id, band, level, rung_codes,"
            " foundational_rung_code, probe_rung_code) values (%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, band, level) do update set rung_codes=excluded.rung_codes,"
            " foundational_rung_code=excluded.foundational_rung_code,"
            " probe_rung_code=excluded.probe_rung_code, updated_at=now()",
            (
                t,
                lv["band"],
                lv["level"],
                lv["rung_codes"],
                lv["foundational_rung_code"],
                lv["probe_rung_code"],
            ),
        )


def _misconceptions(conn: db.Conn, t: db.Id) -> None:
    for m in settings.seed("misconceptions.json", "misconceptions"):
        conn.execute(
            "insert into misconception (tenant_id, code, op, name, description, repair_hint,"
            " detectable_by, source, external_ref, skill_from, skill_code)"
            " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code, op) do update set name=excluded.name,"
            " description=excluded.description, repair_hint=excluded.repair_hint,"
            " detectable_by=excluded.detectable_by, source=excluded.source,"
            " external_ref=excluded.external_ref, skill_from=excluded.skill_from,"
            " skill_code=excluded.skill_code, updated_at=now()",
            (
                t,
                m["code"],
                m["op"],
                m["name"],
                m.get("description", ""),
                m["repair_hint"],
                m["detectable_by"],
                m.get("source", ""),
                m.get("external_ref"),
                m.get("skill_from", "operation"),
                m.get("skill_code"),
            ),
        )


def _dimensions(conn: db.Conn, t: db.Id) -> None:
    rows = settings.seed("case_dimensions.json", "case_dimensions")
    for i, d in enumerate(rows, start=1):
        conn.execute(
            "insert into case_dimension (tenant_id, code, name, description, allowed_values,"
            " dimension_order, source) values (%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set name=excluded.name,"
            " description=excluded.description, allowed_values=excluded.allowed_values,"
            " dimension_order=excluded.dimension_order, source=excluded.source, updated_at=now()",
            (t, d["name"], d["name"], d.get("why", ""), _text_array(d["allowed"]), i, d.get("source", "")),
        )
    # the seed is the whole vocabulary every case is written in: a dimension it no longer names goes
    names = [d["name"] for d in rows]
    conn.execute("delete from case_dimension where tenant_id = %s and code <> all(%s)", (t, names))


def _taxonomy_cases(conn: db.Conn, t: db.Id) -> None:
    for c in settings.seed("taxonomy_cases.json", "taxonomy_cases"):
        words = (c["section"], c["section_name"], c["label"], c.get("example_text", ""))
        held = (json.dumps(c["example"]), json.dumps(c["match"]), c.get("min_items", 12))
        conn.execute(
            "insert into taxonomy_case (tenant_id, code, taxonomy, section, section_name, label, example_text,"
            " example, match, min_items) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set taxonomy=excluded.taxonomy, section=excluded.section,"
            " section_name=excluded.section_name, label=excluded.label, example_text=excluded.example_text,"
            " example=excluded.example, match=excluded.match, min_items=excluded.min_items, updated_at=now()",
            (t, c["code"], c["taxonomy"], *words, *held),
        )


def _skill_sets(conn: db.Conn, t: db.Id) -> None:
    """Insert only. The seed is the first draft of a set; after that the row belongs to Neha and
    Achal, who edit it in the app. An upsert here would silently overwrite their words and rules
    on the next `engine load` — and they would have no way to know. A level the seed teaches in another grade than
    the skill's own (`level_band`) is first drafted there too; a database loaded before is moved by a migration."""
    for s in settings.seed("skill_sets.json", "skill_sets"):
        own = [s[k] for k in ("code", "rung_code", "name", "learning_objective", "philosophy", "formats")]
        conn.execute(
            "insert into skill_set (tenant_id, code, rung_code, name, learning_objective,"
            " philosophy, formats, misconception_codes, difficulty, eval_type, level_band)"
            " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do nothing",
            (
                t,
                *own,
                s["misconception_codes"],
                json.dumps(s["difficulty"]),
                s.get("eval_type", "computable"),
                json.dumps(s.get("level_band", {})),
            ),
        )


def _subjects(conn: db.Conn, t: db.Id) -> None:
    for s in settings.seed("subjects.json", "subjects"):
        conn.execute(
            "insert into subject (tenant_id, code, name, verifier, mark_mode) values (%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set name=excluded.name,"
            " verifier=excluded.verifier, mark_mode=excluded.mark_mode, updated_at=now()",
            (t, s["code"], s["name"], s.get("verifier"), s.get("mark_mode", "lookup")),
        )


def load_all() -> dict[str, int]:
    with db.connect() as conn:
        t = _tenant(conn)
        for step in (
            _registry,
            _rungs,
            _levels,
            _misconceptions,
            _dimensions,
            _taxonomy_cases,
            settings.load,
            _skill_sets,
            _subjects,
        ):
            step(conn, t)
        topics.load(conn, t, settings.seed)
        asks.load(conn, t, settings.seed)
        conn.commit()
        return db.counts(conn, FILLED_TABLES)


def load_settings() -> dict[str, int]:
    """Only the rows the engine reads as settings — prompts, thresholds, config — each upserted from its seed as
    `load_all` does. Every deploy runs it (`engine load --settings`, deploy-engine.yml), so a setting merged with
    the code that reads it is live with that code; the rest waits for `bin/update-live`."""
    with db.connect() as conn:
        settings.load(conn, _tenant(conn))
        conn.commit()
        return db.counts(conn, ("prompt", "threshold", "config"))
