"""Questions the engine drafts for a person to answer (goals/ny1-needs-you.yaml). Rows, `supabase/seed/asks.json`, each
whose a role on the staff list is, answered on the site: agreed as drafted, or corrected in the person's own words. A
load rewords a question no one has answered and never touches one that has been: an answer stands on the words it was
given to. `report` is what `engine asks` prints, so whoever builds next reads what a person said."""

from collections.abc import Callable
from typing import Any

from engine.core import db


def load(conn: db.Conn, tenant: db.Id, seed: Callable[[str, str], Any]) -> None:
    """Every question, in the order the rows draft them; one already answered keeps its words and its answer."""
    for i, a in enumerate(seed("asks.json", "asks")):
        conn.execute(
            "insert into ask (tenant_id, code, ord, for_role, question, drafted, why, source, link)"
            " values (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            " on conflict (tenant_id, code) do update set ord = excluded.ord, for_role = excluded.for_role,"
            " question = excluded.question, drafted = excluded.drafted, why = excluded.why, source = excluded.source,"
            " link = excluded.link, updated_at = now() where ask.answer is null",
            (
                tenant,
                a["code"],
                i,
                a["for_role"],
                a["question"],
                a["drafted"],
                a.get("why"),
                a["source"],
                a.get("link"),
            ),
        )


def report(conn: db.Conn, waiting: bool = False) -> list[str]:
    """One line a question, in the order drafted: its code, whose it is, and its answer — agreed or corrected, by whom
    and when, a correction in full on the line under it — or that it still waits. `waiting` keeps only those."""
    rows = conn.execute(
        "select code, for_role, question, answer, correction, answered_by, answered_at from ask"
        + (" where answer is null" if waiting else "")
        + " order by ord, code"
    ).fetchall()
    out: list[str] = []
    for r in rows:
        head = f"  {r['code']:<34} {r['for_role']:<12}"
        if r["answer"] is None:
            out.append(f"{head} waiting    {r['question']}")
            continue
        out.append(
            f"{head} {r['answer']:<10} by {r['answered_by']}, {r['answered_at']:%Y-%m-%d}  {r['question']}"
        )
        if r["correction"]:
            out.append(f"      it should say: {r['correction']}")
    return out
