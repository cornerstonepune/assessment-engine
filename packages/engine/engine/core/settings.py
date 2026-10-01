"""The rows the engine reads as settings — prompts, thresholds, config — each upserted from its seed. Every deploy
loads them (`engine load --settings`, deploy-engine.yml), so a setting merged with the code that reads it is live with
that code; `loaders.load_all` loads them with everything else. Split from `loaders.py` on 2026-09-29, when a prompt row
gained its model's effort and the loader stood at its frozen ceiling.
"""

import json
from typing import Any

from engine.core import db

SEED = db.REPO_ROOT / "supabase" / "seed"


def seed(name: str, key: str) -> Any:
    return json.loads((SEED / name).read_text())[key]


def load_prompts(conn: db.Conn, t: db.Id) -> None:
    for p in seed("prompts.json", "prompts"):
        text = (SEED / p["text_file"]).read_text() if p.get("text_file") else p["text"]
        conn.execute(
            "insert into prompt (tenant_id, purpose, version, text, model, json_schema, active, subject, effort)"
            " values (%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, purpose, coalesce(subject, ''), version) do update set text=excluded.text,"
            " model=excluded.model, json_schema=excluded.json_schema, active=excluded.active,"
            " effort=excluded.effort, updated_at=now()",
            (
                t,
                p["purpose"],
                p["version"],
                text,
                p["model"],
                json.dumps(p["json_schema"]),
                p.get("active", False),
                p.get("subject"),
                p.get("effort"),  # how hard the model thinks; none is its own default (llm.EFFORTS)
            ),
        )


def load_thresholds(conn: db.Conn, t: db.Id) -> None:
    for r in seed("thresholds.json", "thresholds"):
        key, value, unit, note = r["key"], r["value"], r["unit"], r["description"]
        conn.execute(
            "insert into threshold (tenant_id, key, value, unit, description)"
            " values (%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, key) do update set value=excluded.value,"
            " unit=excluded.unit, description=excluded.description, updated_at=now()",
            (t, key, value, unit, note),
        )


def load_config(conn: db.Conn, t: db.Id) -> None:
    """A row marked `seed_once` belongs to the app after its first load — `app.staff` holds the
    password hashes `engine set-password` writes, and re-seeding it took every one of them away."""
    for c in seed("config.json", "config"):
        on_conflict = (
            "do nothing"
            if c.get("seed_once")
            else "do update set value=excluded.value, description=excluded.description, updated_at=now()"
        )
        conn.execute(
            "insert into config (tenant_id, key, value, description) values (%s,%s,%s,%s)"
            f" on conflict (tenant_id, key) {on_conflict}",
            (t, c["key"], json.dumps(c["value"]), c.get("description", "")),
        )


def load(conn: db.Conn, t: db.Id) -> None:
    for step in (load_prompts, load_thresholds, load_config):
        step(conn, t)


def config(conn: db.Conn, key: str, default: Any = None) -> Any:
    """A config row's value, or `default` when there is no such row. The one reader every workflow uses."""
    row = conn.execute("select value from config where key = %s", (key,)).fetchone()
    return row["value"] if row else default


def threshold(conn: db.Conn, key: str, default: float) -> float:
    """A threshold row's value, or `default` when there is no such row."""
    row = conn.execute("select value from threshold where key = %s", (key,)).fetchone()
    return float(row["value"]) if row else default
