"""Topics: the level of the shared tree between a subject and its skills (grade → subject → topic → skill →
level). Rows from supabase/seed/topics.json; which skills a topic holds is that file's, so every skill set is
placed on each load — unlike its words, which belong to the educators once loaded. A topic is an operation
(Addition & subtraction, Multiplication, …; ADR 0076): a kind of question is never one. A topic the file no longer
has is removed, with every class's word on it, so no page names an empty topic.

Whether a skill has been taught is said skill by skill: the school's word (`skill_set.taught`, from the file's
`taught` list) and each class's (`class_skill`); the rule is the database's `skill_taught_in`. The file decides the
school's word only until a person says it: a load never switches back what a person switched (goals/ny1-needs-you.yaml,
goals/t1-topics-are-operations.yaml)."""

from collections.abc import Callable
from typing import Any

from engine.core import db


def load(conn: db.Conn, tenant: db.Id, seed: Callable[[str, str], Any]) -> None:
    """Every topic, in its order; each skill set's topic and the school's word on it; and no topic the rows have
    dropped. A skill set in no topic, or in two, is refused: the tree would lose it or show it twice."""
    topics = seed("topics.json", "topics")
    placed: dict[str, str] = {}
    taught: set[str] = set()
    for i, t in enumerate(topics):
        conn.execute(
            "insert into topic (tenant_id, code, subject_code, name, ord) values (%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set subject_code=excluded.subject_code,"
            " name=excluded.name, ord=excluded.ord, updated_at=now()",
            (tenant, t["code"], t["subject"], t["name"], i),
        )
        for code in t["skill_sets"]:
            if code in placed:
                raise ValueError(f"{code} is in two topics: {placed[code]} and {t['code']}")
            placed[code] = t["code"]
        taught |= set(t.get("taught", []))
    seeded = {s["code"] for s in seed("skill_sets.json", "skill_sets")}
    if seeded - placed.keys():
        raise ValueError(f"skill sets in no topic: {', '.join(sorted(seeded - placed.keys()))}")
    for code, topic in placed.items():
        conn.execute(
            "update skill_set set topic_code = %s,"
            " taught = case when taught_by is null then %s else taught end"
            " where tenant_id = %s and code = %s",
            (topic, code in taught, tenant, code),
        )
    conn.execute(
        "delete from topic where tenant_id = %s and not (code = any(%s))",
        (tenant, [t["code"] for t in topics]),
    )
