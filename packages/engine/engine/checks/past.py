"""Are past results the same as they were? `engine past` (goals/b2-question-types-are-rows.yaml, decided by Nimish
2026-10-21: "nothing will change for any of the past assessments, scoring etc. right?").

A fingerprint of what a child's past assessments left: the evidence (its count and a checksum of every row), every
child's states and every scored answer. Run before and after a change to the curriculum's tables; the two must be equal.
Read only, and it prints counts and checksums, never a row: safe on a copy of live, where the rehearsal runs it.

When a change is meant to move children's states (goals/gr1-state-from-recent-evidence.yaml, Nimish 2026-11-03: "engine
past must show which children's states change, and why"), `--save-states` keeps every child's states and next levels
before it, and `--states-since` lists each one that moved: the child's id (never a name), the skill, from what to what,
and the numbers the rule decided it on now. Without `--may-change`, any move fails, as the checksums do.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any, LiteralString

import typer

from engine.core import db

# What each part reads; the checksum takes the rows in order. A child's state leaves out when it was last computed, which every rebuild of
# the graph moves; what it says about the child is the rest. The evidence is every column a record held before C2 gave it
# a kind, a mark, who saw it, where and its source: a past row's are what must not move.
PARTS: dict[str, LiteralString] = {
    "evidence": "select row(id, tenant_id, child_id, skill_code, rung_code, correct, misconception_codes, channel,"
    " item_result_id, observed_at, stored_at, confirmed_by, created_at, updated_at)::text as r from evidence_event",
    "states": "select concat_ws('|', child_id, skill_code, rung_code, state, n_events, n_correct,"
    " repeating_misconception, last_seen) as r from child_skill_state",
    "scored": "select concat_ws('|', id, capture_id, item_id, rid, raw_read, status, misconception_codes,"
    " working_shown, state, confirmed_by, confirmed_at) as r from item_result",
}

# What a migration of the curriculum's tables must leave as it was (C1 on): the questions and the skills' levels. Read
# before and after the migrations only; update-live then writes the bank, as it is meant to.
CURRICULUM: dict[str, LiteralString] = {
    "questions": "select i::text as r from item i",
    "levels": "select l::text as r from skill_level l",
}


def fingerprint(conn: db.Conn, parts: dict[str, LiteralString] = PARTS) -> dict[str, dict[str, Any]]:
    """{part: {n, checksum}} for the evidence, the children's states and the scored answers, or the parts given."""
    return {
        part: dict(
            db.one(
                conn,
                f"select count(*)::int as n, md5(coalesce(string_agg(r, chr(10) order by r), '')) as checksum"
                f" from ({sql}) x",
            )
        )
        for part, sql in parts.items()
    }


def past(
    curriculum: bool = typer.Option(False, "--curriculum", help="the questions and levels instead"),
    save_states: Path | None = typer.Option(
        None, "--save-states", help="keep every child's states and next levels"
    ),
    states_since: Path | None = typer.Option(
        None, "--states-since", help="list what moved since a kept snapshot"
    ),
    may_change: bool = typer.Option(False, "--may-change", help="a move is listed, not a failure"),
) -> None:
    """The evidence, the children's states and the scored answers, each as a count and a checksum; or, with
    --save-states / --states-since, which children's states moved and why."""
    if save_states or states_since:
        return past_states(save_states, states_since, may_change)
    with db.connect() as conn:
        for part, f in fingerprint(conn, CURRICULUM if curriculum else PARTS).items():
            typer.echo(f"{part:<9} {f['n']:>8} rows  checksum {f['checksum']}")


# A child's states as the table holds them, and the next paper's level on each skill whose rung they answered on: the
# columns every version of the graph has, so a snapshot taken before a migration reads the same after it.
STATES = (
    "select child_id::text as child, skill_code as skill, rung_code as rung, state, n_events, n_correct,"
    " repeating_misconception as repeating from child_skill_state order by 1, 2, 3"
)
NEXT = (
    "select x.child, x.skill, n.difficulty as level, n.rule from ("
    "  select distinct e.child_id::text as child, e.child_id as id, s.code as skill"
    "  from evidence_event e join skill s on s.tenant_id = e.tenant_id and s.rung_code = e.rung_code"
    "  where e.confirmed_by is not null) x, lateral next_difficulty(x.id, x.skill) n order by 1, 2"
)
# The numbers the rule decides a state on now; absent before goals/gr1's migration, when the rule had none of them.
WHY = (
    "select child_id::text as child, skill_code as skill, rung_code as rung, difficulty, n_events, n_correct, share,"
    " days, latest_share, rechecked, repeating_misconception as repeating from graph_skill_states()"
)


def snapshot(conn: db.Conn) -> dict[str, list[dict[str, Any]]]:
    """Every child's states and next levels, as rows of codes and numbers."""
    return {"states": [dict(r) for r in conn.execute(STATES)], "next": [dict(r) for r in conn.execute(NEXT)]}


def _why(r: dict[str, Any] | None) -> str:
    if r is None:
        return "no answers the graph reads"
    if not r["n_events"]:
        return f"at {r['difficulty'] or 'no level'}: no answer right or wrong"
    return (
        f"at {r['difficulty'] or 'no level'}: {r['n_correct']} of {r['n_events']} right ({float(r['share']):.2f}) on"
        f" {r['days']} day(s), latest day {float(r['latest_share']):.2f},"
        f" {'re-checked' if r['rechecked'] else 'not re-checked'}, repeating {r['repeating'] or 'none'}"
    )


def changes(conn: db.Conn, before: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """What moved since `before`: each state and each next level that differs, with the rule's numbers now."""
    after = snapshot(conn)
    key = lambda r: (r["child"], r["skill"], r["rung"])  # noqa: E731
    was, now = {key(r): r for r in before["states"]}, {key(r): r for r in after["states"]}
    try:
        with conn.transaction():
            why = {key(r): r for r in conn.execute(WHY)}
    except Exception:  # the rule as it was has no window to explain by
        why = {}
    moved = [
        {"child": k[0], "skill": k[1], "rung": k[2], "from": (was.get(k) or {}).get("state"),
         "to": (now.get(k) or {}).get("state"), "why": _why(why.get(k)),
         "repeating_was": (was.get(k) or {}).get("repeating")}
        for k in sorted(was.keys() | now.keys())
        if (was.get(k) or {}).get("state") != (now.get(k) or {}).get("state")
    ]  # fmt: skip
    nkey = lambda r: (r["child"], r["skill"])  # noqa: E731
    nwas, nnow = {nkey(r): r for r in before["next"]}, {nkey(r): r for r in after["next"]}
    levels = [
        {"child": k[0], "skill": k[1], "from": (nwas.get(k) or {}).get("level"), "to": (nnow.get(k) or {}).get("level"),
         "rule": (nnow.get(k) or {}).get("rule")}
        for k in sorted(nwas.keys() | nnow.keys())
        if (nwas.get(k) or {}).get("level") != (nnow.get(k) or {}).get("level")
    ]  # fmt: skip
    return {
        "children": len({r["child"] for r in [*before["states"], *after["states"]]}),
        "states": moved,
        "levels": levels,
    }


def report(c: dict[str, Any]) -> list[str]:
    """The changes in lines: counts first, then each one."""
    kids = {m["child"] for m in c["states"]}
    lines = [
        f"children with a state: {c['children']}; whose state changed: {len(kids)}; skills changed: {len(c['states'])}",
        *(f"  {a or '-'} -> {b or '-'}: {n}" for (a, b), n in Counter((m["from"], m["to"]) for m in c["states"]).most_common()),
        f"children whose next level changed: {len({m['child'] for m in c['levels']})}; skills: {len(c['levels'])}",
        *(f"  {a or 'grade start'} -> {b or 'grade start'}: {n}" for (a, b), n in Counter((m["from"], m["to"]) for m in c["levels"]).most_common()),
        "each state that changed (child id, skill, rung: from -> to, why now):",
        *(f"  {m['child']} {m['skill']} {m['rung']}: {m['from'] or '-'} -> {m['to'] or '-'}, {m['why']}"
          + (f" (was repeating {m['repeating_was']})" if m["repeating_was"] and m["repeating_was"] != m["to"] else "")
          for m in c["states"]),
        "each next level that changed (child id, skill: from -> to):",
        *(f"  {m['child']} {m['skill']}: {m['from'] or 'grade start'} -> {m['to'] or 'grade start'} ({m['rule']})" for m in c["levels"]),
    ]  # fmt: skip
    return lines


def past_states(save: Path | None, since: Path | None, may_change: bool) -> None:
    """`--save-states`: keep the snapshot. `--states-since`: list what moved since it; fail on a move unless allowed."""
    with db.connect() as conn:
        if save:
            save.write_text(json.dumps(snapshot(conn)))
            typer.echo(f"states kept in {save}")
        if since:
            c = changes(conn, json.loads(since.read_text()))
            for line in report(c):
                typer.echo(line)
            if (c["states"] or c["levels"]) and not may_change:
                raise typer.Exit(1)
