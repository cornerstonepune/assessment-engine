"""The rules the migrations make, and whether a database holds them (goals/l3b-live-says-what-went-wrong.yaml).

Live, 2026-10-14 (L3): Make papers refused every paper made for one child. Live recorded the migration that lets a
paper be made for a child, yet its rule still lacked it: a recorded migration is no proof its rule is there. Every
rule the migrations leave on the school's tables — each check, key and reference, as the database itself prints it —
is kept beside the engine in `rules.json`, written by `engine live rules --write` from a database built from the
migrations alone, and the watcher names any rule live holds otherwise (`watch.problems`).
"""

import json
from pathlib import Path

FILE = Path(__file__).with_name("rules.json")


def rules(conn) -> dict[str, str]:
    """{"table.rule": the rule as the database prints it} for every check, key and reference on the school's own
    tables. Only those kinds: a later Postgres may list other things as rules too (a not-null, say), which no
    migration names as one."""
    return {
        f"{r['tbl']}.{r['name']}": " ".join(r["rule"].split())
        for r in conn.execute(
            "select c.conrelid::regclass::text as tbl, c.conname as name, pg_get_constraintdef(c.oid) as rule"
            " from pg_constraint c join pg_class t on t.oid = c.conrelid"
            " where t.relnamespace = 'public'::regnamespace and c.contype in ('c', 'f', 'p', 'u', 'x')"
            " order by 1, 2"
        )
    }


def expected() -> dict[str, str]:
    """The rules the migrations make, as `engine live rules --write` last wrote them."""
    return json.loads(FILE.read_text())


def drift(conn) -> list[str]:
    """Each rule this database holds otherwise than the migrations make it, by name: missing, changed, or one no
    migration makes. Names only, never a row: the watcher's lines go to a public issue."""
    want, have = expected(), rules(conn)
    return (
        [f"{k} is missing" for k in sorted(want.keys() - have.keys())]
        + [
            f"{k} is not the migrations' rule"
            for k in sorted(k for k in want.keys() & have.keys() if want[k] != have[k])
        ]
        + [f"{k} is a rule no migration makes" for k in sorted(have.keys() - want.keys())]
    )


def write(conn) -> int:
    """Write this database's rules as the migrations' — only from a database built from the migrations alone."""
    found = rules(conn)
    FILE.write_text(json.dumps(found, indent=1, sort_keys=True) + "\n")
    return len(found)
