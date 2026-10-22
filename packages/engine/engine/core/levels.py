"""A skill's levels, read from their rows (`skill_level`, goals/b1-levels-are-rows.yaml, ADR 0084).

Each level is a row: its level and grade keys, what it looks like, its rule, who approved it. A reader that wants every
level's whole rule — the generator, the mistake list, the cases a level names — reads it here as one object per skill,
{level: {"words": …, …rule}}, built by the database from the rows (`skill_levels`), so it is handed exactly what the
blob on `skill_set` gave it. The blob stays written, and readable, for one deploy after the last reader moves."""

from typing import Any

from engine.core import db

# a skill's levels as one object, from its rows: the column a moved reader selects in place of `skill_set.difficulty`
LEVELS = "public.skill_levels(s.tenant_id, s.code)"
# every skill with its levels from their rows, for `swap`
SKILLS = f"select s.*, {LEVELS} as levels from skill s"


def of(conn: db.Conn, code: str) -> dict[str, Any]:
    """One skill's levels, {level: {"words": …, …rule}}; a skill that is no row has none."""
    row = conn.execute(f"select {LEVELS} as levels from skill s where s.code = %s", (code,)).fetchone()
    return row["levels"] if row else {}


def every(conn: db.Conn) -> dict[str, dict[str, Any]]:
    """Every skill's levels, by its code."""
    return {r["code"]: r["levels"] for r in conn.execute(f"select s.code, {LEVELS} as levels from skill s")}


def skill(conn: db.Conn, code: str) -> dict[str, Any]:
    """A `skill_set` row with its levels read from their rows in place of the blob; a skill that is no row is refused."""
    row = conn.execute(f"{SKILLS} where s.code = %s", (code,)).fetchone()
    if not row:
        raise ValueError(f"no skill set {code!r}")
    return swap(row)


def swap(row: dict[str, Any]) -> dict[str, Any]:
    """A `skill_set` row selected with `LEVELS as levels`: its levels from their rows, in place of the blob."""
    out = {k: v for k, v in row.items() if k != "levels"}
    out["difficulty"] = row["levels"]
    return out
