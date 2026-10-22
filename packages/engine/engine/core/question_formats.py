"""Kinds of question: rows from supabase/seed/question_formats.json (ADR 0075). A kind is drafted once by the seed and
is the educators' after that, as a skill set is: a load inserts the kinds it does not have and never overwrites one.
The question types (B2, supabase/seed/question_types.json) are kinds of question too, and load here."""

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


def load_types(conn: db.Conn, tenant: db.Id, seed: Callable[[str, str], Any]) -> None:
    """Each question type's words, how it reaches the child and how it is marked (B2), in one statement, so the levels'
    links are made once. A type the seed does not name is left as it is; a new one waits for the coordinator."""
    conn.execute(
        "insert into question_type (tenant_id, code, fmt, words, reaches, marked, own_words)"
        " select %s, x.code, x.fmt, x.words, x.reaches, x.marked::eval_type[], x.own_words from jsonb_to_recordset(%s::jsonb)"
        "   x(code text, fmt text, words text, reaches text, marked text[], own_words boolean)"
        " on conflict (tenant_id, code) do update set fmt = excluded.fmt, words = excluded.words,"
        " reaches = excluded.reaches, marked = excluded.marked, own_words = excluded.own_words"
        " where row(question_type.fmt, question_type.words, question_type.reaches, question_type.marked,"
        " question_type.own_words) is distinct from row(excluded.fmt, excluded.words, excluded.reaches,"
        " excluded.marked, excluded.own_words)",
        (tenant, json.dumps(seed("question_types.json", "question_types"))),
    )
