"""Referential checks the schema cannot express, because the codes live in arrays: every code a seeded row names is a
row itself, and no two bands of one skill set claim one region. Read once the rows are loaded (`engine load`, `engine
audit`); split from `loaders.py`, which loads them."""

from engine.core import db


def orphans() -> dict[str, list[str]]:
    """Referential checks the schema cannot express, because the codes live in arrays."""
    with db.connect() as conn:
        return {
            "rung skill_codes missing from the registry": [
                r["s"]
                for r in conn.execute(
                    "select distinct s from rung, unnest(skill_codes) s"
                    " where not exists (select 1 from skill k where k.code = s)"
                ).fetchall()
            ],
            "level_rule rungs missing from the ladder": [
                r["s"]
                for r in conn.execute(
                    "select distinct s from level_rule, unnest(rung_codes) s"
                    " where not exists (select 1 from rung g where g.code = s)"
                ).fetchall()
            ],
            "skill_set misconception codes missing from the vocabulary": [
                r["s"]
                for r in conn.execute(
                    "select distinct s from skill_set, unnest(misconception_codes) s"
                    " where not exists (select 1 from misconception m where m.code = s)"
                ).fetchall()
            ],
            # Two bands with one region compete for one pool of items and starve each other
            # (BUILD-ORDER gate 4, amended). A band's region is its `check`; equal checks fail.
            "skill_set bands sharing one region": [
                f"{r['code']} {r['bands']}"
                for r in conn.execute(
                    "select code, string_agg(band, '=' order by band) as bands from ("
                    "  select code, key as band, value->'check' as region"
                    "  from skill_set, jsonb_each(difficulty)) x"
                    " group by code, region having count(*) > 1 order by code"
                ).fetchall()
            ],
        }
