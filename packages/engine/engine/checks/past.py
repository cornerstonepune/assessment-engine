"""Are past results the same as they were? `engine past` (goals/b2-question-types-are-rows.yaml, decided by Nimish
2026-10-21: "nothing will change for any of the past assessments, scoring etc. right?").

A fingerprint of what a child's past assessments left: the evidence (its count and a checksum of every row), every
child's states and every scored answer. Run before and after a change to the curriculum's tables; the two must be equal.
Read only, and it prints counts and checksums, never a row: safe on a copy of live, where the rehearsal runs it.
"""

from typing import Any, LiteralString

import typer

from engine.core import db

# What each part reads; the checksum takes the rows in order. A child's state leaves out when it was last computed, which every rebuild of
# the graph moves; what it says about the child is the rest.
PARTS: dict[str, LiteralString] = {
    "evidence": "select e::text as r from evidence_event e",
    "states": "select concat_ws('|', child_id, skill_code, rung_code, state, n_events, n_correct,"
    " repeating_misconception, last_seen) as r from child_skill_state",
    "scored": "select concat_ws('|', id, capture_id, item_id, rid, raw_read, status, misconception_codes,"
    " working_shown, state, confirmed_by, confirmed_at) as r from item_result",
}


def fingerprint(conn: db.Conn) -> dict[str, dict[str, Any]]:
    """{part: {n, checksum}} for the evidence, the children's states and the scored answers."""
    return {
        part: dict(
            db.one(
                conn,
                f"select count(*)::int as n, md5(coalesce(string_agg(r, chr(10) order by r), '')) as checksum"
                f" from ({sql}) x",
            )
        )
        for part, sql in PARTS.items()
    }


def past() -> None:
    """The evidence, the children's states and the scored answers, each as a count and a checksum."""
    with db.connect() as conn:
        for part, f in fingerprint(conn).items():
            typer.echo(f"{part:<9} {f['n']:>8} rows  checksum {f['checksum']}")
