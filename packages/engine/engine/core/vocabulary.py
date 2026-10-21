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
            "insert into difficulty (tenant_id, code, ord, letter) values (%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set ord=excluded.ord, letter=excluded.letter, updated_at=now()",
            (tenant, d["code"], i, d["letter"]),
        )
    for i, s in enumerate(seed("vocabulary.json", "child_states")):
        conn.execute(
            "insert into child_state (tenant_id, code, ord, words, colour, needs_work) values (%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set ord=excluded.ord, words=excluded.words,"
            " colour=excluded.colour, needs_work=excluded.needs_work, updated_at=now()",
            (tenant, s["code"], i, s["words"], s["colour"], s["needs_work"]),
        )


def levels(conn: db.Conn) -> tuple[str, ...]:
    """The school's levels, easiest first: what every reader outside the maths library takes their names and order
    from (goals/b0c-levels-from-the-table.yaml)."""
    return tuple(r["code"] for r in conn.execute("select code from difficulty order by ord").fetchall())


def letters(conn: db.Conn) -> dict[str, str]:
    """Each level's letter in a worksheet code (R5-M03): a column of its row, one level's alone. A level with none yet
    has no worksheets until the seed gives it one."""
    rows = conn.execute("select code, letter from difficulty where letter is not null").fetchall()
    return {r["code"]: r["letter"] for r in rows}
