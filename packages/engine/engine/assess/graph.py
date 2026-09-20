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


def refresh_item_usage(conn) -> int:
    """`item.times_used` from `item_exposure` — how often each question has actually been handed out.

    Derived, so Ring B owns it (CLAUDE.md: Ring B is a pure function of Ring A, rebuildable at any
    time). `assemble` used to increment it inline and two classes built at the same moment deadlocked
    on those rows; the count lives in the exposures either way, so nothing is lost by computing it
    here instead. Returns how many items' counters moved.
    """
    return conn.execute(
        "with used as (select item_id, count(*) as n from item_exposure group by item_id)"
        " update item i set times_used = coalesce(used.n, 0)"
        " from used where used.item_id = i.id and i.times_used <> used.n"
    ).rowcount


def rebuild(conn, child_id: str | None = None) -> int:
    """Ring B from Ring A: child_skill_state for one child, or for every child with evidence."""
    refresh_item_usage(conn)
    if child_id:
        return conn.execute("select rebuild_child_skill_state(%s) as n", (child_id,)).fetchone()["n"]
    ids = [
        r["child_id"]
        for r in conn.execute(
            "select distinct child_id from evidence_event where confirmed_by is not null"
        ).fetchall()
    ]
    return sum(
        conn.execute("select rebuild_child_skill_state(%s) as n", (cid,)).fetchone()["n"] for cid in ids
    )
