"""Every model eval is held to a bar, and the bar is a row (goals/p1-done-means-every-check.yaml).

A bar is a `threshold` row `eval.<purpose>.<measure>`: the score Nimish set for the purpose, or the one its prompt was
made active on (DECISIONS-LOG.md); each row's description says which. A measure ending `_at_most` is a ceiling, a
count of errors the eval may not exceed; every other measure is a floor. `engine eval` exits 1 below any bar, and an
eval with no bar on record does not pass: a score nothing holds to a bar proves nothing (CLAUDE.md rules 7 and 12).
"""

from engine.core import db

CEILING = "_at_most"


def bars(conn: db.Conn, purpose: str) -> dict[str, float]:
    """{measure: bar} for one purpose's eval, from its threshold rows."""
    head = f"eval.{purpose}."
    rows = conn.execute("select key, value from threshold where starts_with(key, %s)", (head,)).fetchall()
    return {r["key"].removeprefix(head): float(r["value"]) for r in rows}


def short(scores: dict[str, float], held: dict[str, float]) -> list[str]:
    """Each way `scores` falls short of the bars `held`, in words; empty when it meets every one. A bar whose measure
    the eval did not report is short too, and so is an eval with no bar at all."""
    if not held:
        return ["no bar on record: run it, write its score down (DECISIONS-LOG.md), and make that its bar"]
    out: list[str] = []
    for measure, bar in sorted(held.items()):
        score = scores.get(measure.removesuffix(CEILING))
        if score is None:
            out.append(f"{measure}: not measured by this eval")
        elif measure.endswith(CEILING) and score > bar:
            out.append(f"{measure.removesuffix(CEILING)} {score:g}, above its bar of {bar:g}")
        elif not measure.endswith(CEILING) and score < bar:
            out.append(f"{measure} {score:.4g}, below its bar of {bar:g}")
    return out
