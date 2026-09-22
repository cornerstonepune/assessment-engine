"""Seed JSON to tables.

Every write is an upsert keyed on the natural code, so running the loader twice changes
nothing. That property is the whole gate on Phase 0: if a second run moves a single row, the
registry cannot be trusted as the thing every assessment result joins to.
"""

import json

from engine import db

SEED = db.REPO_ROOT / "supabase" / "seed"

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
    "coverage_target",
    "taxonomy_case",
    "prompt",
    "threshold",
    "config",
    "skill_set",
    "subject",
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
    (
        "read.route_above_overturn",
        0.25,
        "proportion",
        "A (child, format) pair overturned by the validator more often than this routes to the queue even above auto_confirm_above",
    ),
    ("marking.agreement_gate", 0.95, "proportion", "Agreement with teacher marking before marks are trusted"),
    # How the transcriber finds a child's answer on a page (ADR 0019). Every one of these was tuned
    # against a hand-read page, and every one is a property of how a PAPER is laid out rather than of
    # the code — so the next paper will want them different, and rule 1 says that is a row to edit,
    # not a Python file to change.
    (
        "ocr.min_confidence",
        70,
        "confidence",
        "Below this the engine does not stand behind a reading: it is kept, flagged, and a person"
        " decides. At 0 a stray mark read as a minus sign reached a child's graph unchallenged",
    ),
    (
        "ocr.answer_column",
        0.085,
        "page fraction",
        "How far either side of a question its answer may sit. These papers print four boxes across,"
        " about 0.19 apart, so anything wider reaches into the neighbouring child's answer",
    ),
    (
        "ocr.answer_drop",
        0.095,
        "page fraction",
        "How far below a question its answer may sit, when no following question bounds the region",
    ),
    (
        "ocr.row_band",
        0.02,
        "page fraction",
        "Answers within this of each other vertically are one row, read left to right. The scans sit"
        " a degree off square, so rounding instead of clustering gave every child the next one's answer",
    ),
    (
        "ocr.first_page_mask",
        0.34,
        "page fraction",
        "Top of page one painted out before anything is sent: the name band lives there (rule 6)",
    ),
    (
        "ocr.box_min_width",
        0.04,
        "page fraction",
        "A printed answer box is at least this wide. Narrower rectangles are tick boxes and stray"
        " marks, not fields. Used only on a paper whose row says its answers live in boxes",
    ),
    (
        "ocr.box_min_height",
        0.015,
        "page fraction",
        "And at least this tall. With box_min_width this separates the boxes a paper prints for its"
        " answers from the noise on a photograph of it",
    ),
    (
        "ocr.box_max_width",
        0.35,
        "page fraction",
        "Wider than this is a frame around a number line or a working area, not an answer box. Counting"
        " one as a field handed a slot its neighbour's answer when the count happened to match",
    ),
    (
        "ocr.box_ink_blank",
        0.004,
        "fraction of pixels",
        "A field with more ink than this and no word the transcriber could read is a doubt for a person,"
        " never a blank",
    ),
    (
        "ocr.red_pen_mask",
        1,
        "switch",
        "Paint out red ink before a page is read. The educator marks in red and the child writes in"
        " pencil or blue; a red circle over 5147 read back as 147 at 95%. 0 turns it off",
    ),
    (
        "ocr.reread_dpi",
        500,
        "dots per inch",
        "A flagged answer gets a second look at this resolution. The page itself goes to the"
        " transcriber at 150 dpi, where a 40x25-pixel answer is at the limit of what it can resolve"
        " — a third of everything that reaches a person sits one band under the floor. 0 turns the"
        " second look off",
    ),
    (
        "ocr.reread_pad",
        0.012,
        "page fraction",
        "How much of the page around a doubtful answer goes into its crop. Too tight and the"
        " transcriber has no baseline to read the digits against; too loose and the neighbouring"
        " answer comes with it and the crop is refused for holding two numbers",
    ),
    (
        "ocr.stencil_min_inliers",
        50,
        "matched features",
        "A child's page is read against its paper's rebuilt blank only when at least this many printed"
        " features line the two up. Pages that align measure 300-1000; a page too bare to align reads as"
        " it did before, never against a stencil that is not on it",
    ),
    (
        "ocr.stencil_empty",
        0.03,
        "fraction of pixels",
        "The rebuilt blank counts as empty where fewer than this share of its pixels are dark. A child's"
        " number Textract took for print is given back to the child only where the blank is empty; a"
        " printed word's patch runs 10-25% dark, an empty box's interior under 1%",
    ),
    ("confirm.queue_minutes", 2, "minutes", "Target time for a teacher to clear one class"),
    (
        "llm.daily_budget_inr",
        150,
        "INR",
        "The adapter refuses a new call once today's cost_inr for the tenant passes this. A row, not a limit in code — raise it here.",
    ),
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
    def many(sql, rows):
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
            (
                t,
                lv["band"],
                lv["level"],
                lv["rung_codes"],
                lv["foundational_rung_code"],
                lv["probe_rung_code"],
            ),
        )


def _misconceptions(conn, t):
    for m in _seed("misconceptions.json", "misconceptions"):
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
            (
                t,
                c["rung_code"],
                c["dimension"],
                _text_array(c["values"]),
                c.get("min_items", 1),
                c.get("note", ""),
            ),
        )


def _taxonomy_cases(conn, t):
    for c in _seed("taxonomy_cases.json", "taxonomy_cases"):
        conn.execute(
            "insert into taxonomy_case (tenant_id, code, section, section_name, label, example_text, example,"
            " match, min_items) values (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set section=excluded.section,"
            " section_name=excluded.section_name, label=excluded.label, example_text=excluded.example_text,"
            " example=excluded.example, match=excluded.match, min_items=excluded.min_items, updated_at=now()",
            (
                t,
                c["code"],
                c["section"],
                c["section_name"],
                c["label"],
                c.get("example_text", ""),
                json.dumps(c["example"]),
                json.dumps(c["match"]),
                c.get("min_items", 12),
            ),
        )


def _prompts(conn, t):
    for p in _seed("prompts.json", "prompts"):
        text = (SEED / p["text_file"]).read_text() if p.get("text_file") else p["text"]
        conn.execute(
            "insert into prompt (tenant_id, purpose, version, text, model, json_schema, active, subject)"
            " values (%s,%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, purpose, coalesce(subject, ''), version) do update set text=excluded.text,"
            " model=excluded.model, json_schema=excluded.json_schema, active=excluded.active,"
            " updated_at=now()",
            (
                t,
                p["purpose"],
                p["version"],
                text,
                p["model"],
                json.dumps(p["json_schema"]),
                p.get("active", False),
                p.get("subject"),
            ),
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
    """A row marked `seed_once` belongs to the app after its first load — `app.staff` holds the
    password hashes `engine set-password` writes, and re-seeding it took every one of them away."""
    for c in _seed("config.json", "config"):
        on_conflict = (
            "do nothing"
            if c.get("seed_once")
            else "do update set value=excluded.value, description=excluded.description, updated_at=now()"
        )
        conn.execute(
            "insert into config (tenant_id, key, value, description) values (%s,%s,%s,%s)"
            f" on conflict (tenant_id, key) {on_conflict}",
            (t, c["key"], json.dumps(c["value"]), c.get("description", "")),
        )


def _skill_sets(conn, t):
    """Insert only. The seed is the first draft of a set; after that the row belongs to Neha and
    Achal, who edit it in the app. An upsert here would silently overwrite their words and rules
    on the next `engine load` — and they would have no way to know."""
    for s in _seed("skill_sets.json", "skill_sets"):
        conn.execute(
            "insert into skill_set (tenant_id, code, rung_code, name, learning_objective,"
            " philosophy, formats, misconception_codes, difficulty, eval_type)"
            " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do nothing",
            (
                t,
                s["code"],
                s["rung_code"],
                s["name"],
                s["learning_objective"],
                s["philosophy"],
                s["formats"],
                s["misconception_codes"],
                json.dumps(s["difficulty"]),
                s.get("eval_type", "computable"),
            ),
        )


def _subjects(conn, t):
    for s in _seed("subjects.json", "subjects"):
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
            _coverage,
            _taxonomy_cases,
            _prompts,
            _thresholds,
            _config,
            _skill_sets,
            _subjects,
        ):
            step(conn, t)
        conn.commit()
        return db.counts(conn, FILLED_TABLES)


def orphans() -> dict[str, list[str]]:
    """Referential checks the schema cannot express, because the codes live in arrays."""
    with db.connect() as conn:
        return {
            "rung skill_codes missing from the registry": [
                r["s"]
                for r in conn.execute(
                    "select distinct s from rung, unnest(skill_codes) s"
                    " where not exists (select 1 from skill k where k.code = s)"
                ).fetchall()
            ],
            "level_rule rungs missing from the ladder": [
                r["s"]
                for r in conn.execute(
                    "select distinct s from level_rule, unnest(rung_codes) s"
                    " where not exists (select 1 from rung g where g.code = s)"
                ).fetchall()
            ],
            "coverage_target rungs missing from the ladder": [
                r["rung_code"]
                for r in conn.execute(
                    "select distinct rung_code from coverage_target c"
                    " where not exists (select 1 from rung g where g.code = c.rung_code)"
                ).fetchall()
            ],
            "coverage_target dimensions missing from the matrix": [
                r["dimension_code"]
                for r in conn.execute(
                    "select distinct dimension_code from coverage_target c"
                    " where not exists (select 1 from case_dimension d"
                    " where d.code = c.dimension_code)"
                ).fetchall()
            ],
            "skill_set misconception codes missing from the vocabulary": [
                r["s"]
                for r in conn.execute(
                    "select distinct s from skill_set, unnest(misconception_codes) s"
                    " where not exists (select 1 from misconception m where m.code = s)"
                ).fetchall()
            ],
            # Two bands with one region compete for one pool of items and starve each other
            # (BUILD-ORDER gate 4, amended). A band's region is its `check`; equal checks fail.
            "skill_set bands sharing one region": [
                f"{r['code']} {r['bands']}"
                for r in conn.execute(
                    "select code, string_agg(band, '=' order by band) as bands from ("
                    "  select code, key as band, value->'check' as region"
                    "  from skill_set, jsonb_each(difficulty)) x"
                    " group by code, region having count(*) > 1 order by code"
                ).fetchall()
            ],
        }
