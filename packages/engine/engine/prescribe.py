"""W4's decision, made per child: which skill set, at which difficulty, and why.

The teacher's declaration says what was taught, so the skill set is an input. What this module
decides is how hard each child's paper should be — and it must always be able to say which rule
fired, because a teacher who disagrees needs something to disagree with.
"""
from engine import db
from engine.assess import graph

RULES = {
    "band_default": "not enough of their own work yet, so this is the starting level for their grade",
    "from_state": "from what this child's last papers showed",
    "override": "a teacher set this by hand",
}


def _config(conn, key, default=None):
    row = conn.execute("select value from config where key = %s", (key,)).fetchone()
    return row["value"] if row else default


def for_class(conn, section: str, week: str, skill_set: str, kind: str = "practice") -> list[dict]:
    """One prescription per active child in the section. Idempotent: running it twice on the same
    week and kind updates the rows rather than adding a second set."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    children = conn.execute(
        "select id, roll_no, band from child where section = %s and active order by"
        " coalesce(nullif(regexp_replace(roll_no, '\\D', '', 'g'), '')::int, 9999), roll_no",
        (section,),
    ).fetchall()
    if not children:
        raise ValueError(f"no active children in section {section!r}")
    if not conn.execute("select 1 from skill_set where code = %s", (skill_set,)).fetchone():
        raise ValueError(f"no skill set {skill_set!r}")

    defaults = _config(conn, "prescribe.band_default", {})
    out = []
    for c in children:
        difficulty, rule, targets = graph.next_difficulty(conn, c["id"], skill_set)
        if difficulty is None:
            difficulty = defaults.get(c["band"], "Medium")
            rule = "band_default"
        row = conn.execute(
            "insert into prescription (tenant_id, child_id, week, kind, skill_set_code, difficulty,"
            " rule_fired, misconception_targets, strand) values (%s,%s,%s,%s,%s,%s,%s,%s,'NUM')"
            " on conflict (tenant_id, child_id, week, kind) do update set"
            " skill_set_code = excluded.skill_set_code, difficulty = excluded.difficulty,"
            " rule_fired = excluded.rule_fired, misconception_targets = excluded.misconception_targets,"
            " updated_at = now()"
            " where prescription.override_by is null"   # a teacher's override is never overwritten
            " returning id, difficulty, rule_fired",
            (tenant, c["id"], week, kind, skill_set, difficulty, rule, targets),
        ).fetchone()
        kept = row or conn.execute(
            "select id, difficulty, rule_fired from prescription where child_id = %s and week = %s"
            " and kind = %s", (c["id"], week, kind)).fetchone()
        out.append({"child_id": c["id"], "roll_no": c["roll_no"], "band": c["band"],
                    "difficulty": kept["difficulty"], "rule": kept["rule_fired"],
                    "prescription_id": kept["id"]})
    return out


def override(conn, prescription_id: str, difficulty: str, by: str, reason: str) -> None:
    """A teacher disagrees. The reason is required and is kept: the next prescriber reads the
    override and leaves the row alone."""
    if not reason.strip():
        raise ValueError("an override needs a reason")
    if difficulty not in graph.ORDER:
        raise ValueError(f"{difficulty!r} is not one of {', '.join(graph.ORDER)}")
    conn.execute(
        "update prescription set difficulty = %s, rule_fired = 'override', override_by = %s,"
        " override_reason = %s, updated_at = now() where id = %s",
        (difficulty, by, reason.strip(), prescription_id),
    )
