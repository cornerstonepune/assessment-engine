"""The consent and data register (C6): what the school keeps about a child, why, how long and who sees it, in a
parent's words, from supabase/seed/data_register.json. A load upserts every entry, so a word changed in the file is
changed on the next load, and a consent given before it then reads as given to the register as it was."""

from collections.abc import Callable
from typing import Any

from engine.core import db


def load(conn: db.Conn, tenant: db.Id, seed: Callable[[str, str], Any]) -> None:
    for i, e in enumerate(seed("data_register.json", "data_register")):
        conn.execute(
            "insert into data_register (tenant_id, code, ord, what, why, how_long, who_sees, tables)"
            " values (%s,%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set ord=excluded.ord, what=excluded.what, why=excluded.why,"
            " how_long=excluded.how_long, who_sees=excluded.who_sees, tables=excluded.tables, updated_at=now()",
            (tenant, e["code"], i, e["what"], e["why"], e["how_long"], e["who_sees"], e["tables"]),
        )
