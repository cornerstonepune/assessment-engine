"""A K2 child's growth and what is ready next (task M1-17). Pure functions: no database, no model.

Growth is movement over time, a trend and never a score: the level reached in each month the child was seen on a skill,
and whether the latest month is above, level with or below the one before it. A month nobody saw the child is a gap,
not a zero. Nothing is summed or averaged.

Ready next reads confirmed links only (the caller passes `skill_link_confirmed`'s rows). A skill is ready when every
hard link before it is done and at least one confirmed link before it is. The answer holds only what is ready: it has no
"not ready", because a child not yet seen on a skill is not seen, which is not "not secure" (D-008).
"""

import datetime as dt


def growth(seen: list[tuple[dt.date, int]], min_months: int) -> dict | None:
    """`seen`: (school day, level reached) for each named, confirmed, current observation of one child on one skill.
    `min_months` (a config row) is how many months seen a trend needs; with fewer it reads "too_few"."""
    if not seen:
        return None
    months: dict[str, dict] = {}
    for day, level in sorted(seen):
        m = months.setdefault(f"{day.year:04d}-{day.month:02d}", {"level": level, "days": set()})
        m["level"] = max(m["level"], level)
        m["days"].add(day)
    by_month = [{"month": k, "level": v["level"], "days": len(v["days"])} for k, v in sorted(months.items())]
    trend = "too_few"
    if len(by_month) >= max(min_months, 2):
        before, latest = by_month[-2]["level"], by_month[-1]["level"]
        trend = "up" if latest > before else "down" if latest < before else "steady"
    days = sorted(day for day, _ in seen)
    return {"first_seen": days[0], "last_seen": days[-1], "by_month": by_month, "trend": trend}


def ready_next(links: list[dict], states: dict[str, str], done_states: set[str]) -> list[dict]:
    """`links`: confirmed links as {skill, before, strength}; `states`: this child's state by skill code (a skill not
    seen is absent); `done_states`: the states that count as done (a config row). Returns the skills ready to work on,
    each with the done skills before it that make it ready, in code order."""
    done = {s for s, state in states.items() if state in done_states}
    by_skill: dict[str, list[dict]] = {}
    for link in links:
        by_skill.setdefault(link["skill"], []).append(link)
    ready = []
    for skill in sorted(by_skill):
        if skill in done:
            continue
        before = by_skill[skill]
        if any(b["strength"] == "hard" and b["before"] not in done for b in before):
            continue
        because = [{"before": b["before"], "strength": b["strength"]} for b in before if b["before"] in done]
        if because:
            ready.append({"skill": skill, "because": because})
    return ready
