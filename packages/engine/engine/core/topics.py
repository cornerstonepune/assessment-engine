"""Topics: the level of the shared tree between a subject and its skills (grade → subject → topic → skill →
level). Rows from supabase/seed/topics.json; which skills a topic holds is that file's, so every skill set is
placed on each load — unlike its words, which belong to the educators once loaded."""


def load(conn, tenant, seed) -> None:
    """Every topic, in its order, and each skill set's topic. A skill set in no topic, or in two, is refused:
    the tree would lose it or show it twice."""
    topics = seed("topics.json", "topics")
    placed: dict[str, str] = {}
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
    seeded = {s["code"] for s in seed("skill_sets.json", "skill_sets")}
    if seeded - placed.keys():
        raise ValueError(f"skill sets in no topic: {', '.join(sorted(seeded - placed.keys()))}")
    for code, topic in placed.items():
        conn.execute(
            "update skill_set set topic_code = %s where tenant_id = %s and code = %s", (topic, tenant, code)
        )
