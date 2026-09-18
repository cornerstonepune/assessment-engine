"""What a child's own evidence says about the next difficulty.

The rule itself is `next_difficulty()` in the database (migration 20260918130000), so the web
app's confirm button and this module cannot drift apart. Until confirmed evidence exists every
lookup returns "nothing to go on", the prescriber falls back to the band default, and the
prescription says so honestly. The thresholds are rows, so the rule can be tuned without a deploy.
"""
ORDER = ["Easy", "Medium", "Hard", "Advance"]


def next_difficulty(conn, child_id: str, skill_set: str) -> tuple[str | None, str, list[str]]:
    """Return (difficulty, rule, misconception targets), or (None, "band_default", []) when there
    is not enough confirmed evidence on this skill set's rung."""
    row = conn.execute("select * from next_difficulty(%s, %s)", (child_id, skill_set)).fetchone()
    return row["difficulty"], row["rule"], list(row["targets"] or [])


def rebuild(conn, child_id: str | None = None) -> int:
    """Ring B from Ring A: child_skill_state for one child, or for every child with evidence."""
    if child_id:
        return conn.execute("select rebuild_child_skill_state(%s) as n", (child_id,)).fetchone()["n"]
    ids = [r["child_id"] for r in conn.execute(
        "select distinct child_id from evidence_event where confirmed_by is not null").fetchall()]
    return sum(conn.execute("select rebuild_child_skill_state(%s) as n", (cid,)).fetchone()["n"] for cid in ids)
