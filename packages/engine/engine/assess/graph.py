"""What a child's own evidence says about the next difficulty.

This is the seam W3 fills. Until confirmed evidence exists, every lookup returns "nothing to go
on", the prescriber falls back to the band default, and the prescription says so honestly. The
thresholds are rows, so the rule can be tuned without a deploy.

Evidence is recorded against a rung, not a skill set, so a skill set reads its evidence by
joining on `rung_code` — which is also why two sets on the same rung share a child's history.
"""
ORDER = ["Easy", "Medium", "Hard", "Advance"]


def _threshold(conn, key: str, default: float) -> float:
    row = conn.execute("select value from threshold where key = %s", (key,)).fetchone()
    return float(row["value"]) if row else default


def evidence(conn, child_id: str, skill_set: str) -> dict:
    """Confirmed results for this child on this skill set's rung. Only `confirmed_by` rows count
    (CLAUDE.md rule 4: the graph reads confirmed evidence, never a machine's unreviewed guess)."""
    row = conn.execute(
        "select count(*) filter (where e.correct is not null) as answered,"
        "       count(*) filter (where e.correct) as right_"
        " from evidence_event e"
        " join skill_set s on s.tenant_id = e.tenant_id and s.rung_code = e.rung_code"
        " where e.child_id = %s and s.code = %s and e.confirmed_by is not null",
        (child_id, skill_set),
    ).fetchone()
    return {"answered": row["answered"] or 0, "right": row["right_"] or 0}


def next_difficulty(conn, child_id: str, skill_set: str) -> tuple[str | None, str, list[str]]:
    """Return (difficulty, rule, misconception targets), or (None, …) when there is not enough.

    Enough means `state.min_events` confirmed answers. At or above `next_sheet.promote_at` correct
    the child moves up one difficulty; below `next_sheet.demote_below` they move down; otherwise
    they stay where they were. The targets are the mistakes that recurred, which is what the home
    sheet is later aimed at.
    """
    ev = evidence(conn, child_id, skill_set)
    if ev["answered"] < _threshold(conn, "state.min_events", 3):
        return None, "band_default", []

    share = ev["right"] / ev["answered"]
    last = conn.execute(
        "select difficulty from prescription where child_id = %s and skill_set_code = %s"
        " and difficulty is not null order by created_at desc limit 1",
        (child_id, skill_set),
    ).fetchone()
    at = (last["difficulty"] if last else None) or "Medium"
    i = ORDER.index(at) if at in ORDER else ORDER.index("Medium")

    if share >= _threshold(conn, "next_sheet.promote_at", 0.80):
        return ORDER[min(i + 1, len(ORDER) - 1)], "from_state", []
    if share < _threshold(conn, "next_sheet.demote_below", 0.50):
        return ORDER[max(i - 1, 0)], "from_state", targets(conn, child_id, skill_set)
    return at, "from_state", targets(conn, child_id, skill_set)


def targets(conn, child_id: str, skill_set: str, limit: int = 3) -> list[str]:
    """The mistakes this child's confirmed answers matched more than once."""
    rows = conn.execute(
        "select code, count(*) as n from evidence_event e"
        " join skill_set s on s.tenant_id = e.tenant_id and s.rung_code = e.rung_code,"
        " unnest(e.misconception_codes) as code"
        " where e.child_id = %s and s.code = %s and e.confirmed_by is not null"
        " group by code having count(*) > 1 order by n desc, code limit %s",
        (child_id, skill_set, limit),
    ).fetchall()
    return [r["code"] for r in rows]
