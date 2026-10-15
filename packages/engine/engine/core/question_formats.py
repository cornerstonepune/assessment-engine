"""Kinds of question: rows from supabase/seed/question_formats.json (ADR 0075). A kind is drafted once by the seed and
is the educators' after that, as a skill set is: a load inserts the kinds it does not have and never overwrites one."""

import json
from collections.abc import Callable
from typing import Any

from engine.core import db


def load(conn: db.Conn, tenant: db.Id, seed: Callable[[str, str], Any]) -> None:
    for k in seed("question_formats.json", "question_formats"):
        conn.execute(
            "insert into question_format (tenant_id, code, skill_set_code, name, kind) values (%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do nothing",
            (tenant, k["code"], k["skill_set"], k["name"], json.dumps(k, ensure_ascii=False)),
        )
