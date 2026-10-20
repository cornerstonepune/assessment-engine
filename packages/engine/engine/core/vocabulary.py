"""The school's words as rows (ADR 0084): its grades, the four levels and the states of a child's map, from
supabase/seed/vocabulary.json, each list in its order. A topic's subject, a question's level and a child's state are
keys into these tables, so a word is a row before anything may use it, and adding one is an insert.

The seed is their source: a load upserts every row, so a word or a colour changed in the file is changed on the next
load. The migration that made the tables inserts the same rows for every school, there now or added later
(tests/test_vocabulary.py keeps the two equal)."""

from collections.abc import Callable
from typing import Any

from engine.core import db


def load(conn: db.Conn, tenant: db.Id, seed: Callable[[str, str], Any]) -> None:
    for i, g in enumerate(seed("vocabulary.json", "grades")):
        conn.execute(
            "insert into grade (tenant_id, code, name, ord) values (%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set name=excluded.name, ord=excluded.ord, updated_at=now()",
            (tenant, g["code"], g["name"], i),
        )
    for i, d in enumerate(seed("vocabulary.json", "difficulties")):
        conn.execute(
            "insert into difficulty (tenant_id, code, ord) values (%s,%s,%s)"
            " on conflict (tenant_id, code) do update set ord=excluded.ord, updated_at=now()",
            (tenant, d["code"], i),
        )
    for i, c in enumerate(seed("vocabulary.json", "state_colours")):
        conn.execute(
            "insert into state_colour (tenant_id, code, ord, words, count_words) values (%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set ord=excluded.ord, words=excluded.words,"
            " count_words=excluded.count_words, updated_at=now()",
            (tenant, c["code"], i, c["words"], c["count_words"]),
        )
    for i, s in enumerate(seed("vocabulary.json", "child_states")):
        conn.execute(
            "insert into child_state (tenant_id, code, ord, words, colour, needs_work, enough, severity, move_up,"
            " nearly, card_group, why) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set ord=excluded.ord, words=excluded.words,"
            " colour=excluded.colour, needs_work=excluded.needs_work, enough=excluded.enough,"
            " severity=excluded.severity, move_up=excluded.move_up, nearly=excluded.nearly,"
            " card_group=excluded.card_group, why=excluded.why, updated_at=now()",
            (
                tenant,
                s["code"],
                i,
                s["words"],
                s["colour"],
                s["needs_work"],
                s["enough"],
                s["severity"],
                s["move_up"],
                s["nearly"],
                s["card_group"],
                s["why"],
            ),
        )


def states(conn: db.Conn) -> list[dict[str, Any]]:
    """The school's states of a child's map, weakest first, each with every rule about it (ADR 0085): what a next
    paper works on (`needs_work`), what waits on too few answers (`enough`), what is ready to move up, what may be
    nearly secure, its group on the class card, the reason a paper prints. Code reads these, never names a state."""
    return conn.execute(
        "select code, ord, words, colour, needs_work, enough, severity, move_up, nearly, card_group, why"
        " from child_state where tenant_id = (select id from tenant where slug = %s) order by ord",
        (db.tenant_slug(),),
    ).fetchall()
