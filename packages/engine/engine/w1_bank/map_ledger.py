"""The curriculum mapping agents' ledger: what they proposed, what a person decided, what was applied and reverted
(goals/m1-05-mapping-agents.yaml, supabase/migrations/20261230090000_curriculum_proposal_ledger.sql).

Append-only: a proposal is one row, decided when it is made; a person's yes or no, an apply and a revert are each a
new row naming it (`about`), so where a proposal stands is its newest row. A link made from one is marked `machine` and
the proposal's id, so every machine link can be listed and reverted; every link added or removed lands in the
curriculum's edit history by the database's own trigger, with who did it.
"""

import json
import uuid

from psycopg.rows import DictRow

from engine.core import db
from engine.w1_bank.map_agents import Proposal
from engine.w1_bank.map_check import LEVELS


def rules(conn: db.Conn) -> dict[str, float]:
    """The `map.*` threshold rows, by their name after `map.`."""
    rows = conn.execute("select key, value from threshold where starts_with(key, 'map.')").fetchall()
    return {r["key"].removeprefix("map."): float(r["value"]) for r in rows}


def record(conn: db.Conn, tenant: db.Id, made: list[Proposal], by: str) -> uuid.UUID:
    """Every proposal of one run as a row; the run's id back."""
    run = uuid.uuid4()
    for p in made:
        conn.execute(
            "insert into curriculum_proposal (tenant_id, run_id, kind, subject_code, proposal, confidence, proposer,"
            " validator, problems, verdict, status, reason, made_by) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (
                tenant,
                run,
                p.kind,
                p.subject_code,
                json.dumps(p.proposal, ensure_ascii=False),
                p.confidence,
                p.proposer,
                p.validator,
                p.problems,
                p.verdict,
                p.status,
                p.reason,
                by,
            ),
        )
    return run


def standing(conn: db.Conn, tenant: db.Id, status: str | None = None) -> list[DictRow]:
    """Each proposal with where it stands now (its newest row's status), oldest first; only those at `status` if
    one is named."""
    return conn.execute(
        "select p.*, n.status as now from curriculum_proposal p join lateral (select status from curriculum_proposal"
        " x where x.tenant_id = p.tenant_id and (x.id = p.id or x.about = p.id) order by x.created_at desc, x.id"
        " limit 1) n on true where p.tenant_id = %s and p.about is null and (%s::text is null or n.status = %s)"
        " order by p.created_at, p.id",
        (tenant, status, status),
    ).fetchall()


def proposed(conn: db.Conn, tenant: db.Id) -> set[tuple[str, str, str]]:
    """{(kind, code, skill or '')} of every proposal not turned down: a second run does not propose them again."""
    return {
        (r["kind"], r["subject_code"], r["proposal"]["skills"][0] if r["kind"] == "lo_skill" else "")
        for r in standing(conn, tenant)
        if r["now"] != "rejected"
    }


def stopped(conn: db.Conn, tenant: db.Id, at_most: float, least: float) -> frozenset[str]:
    """The kinds whose audit sample people turned down too often (more than `at_most` of at least `least`
    decided): they stop passing on their own."""
    rows = conn.execute(
        "select p.kind, count(*) as n, count(*) filter (where d.status = 'rejected') as no from curriculum_proposal p"
        " join curriculum_proposal d on d.about = p.id and d.status in ('approved', 'rejected')"
        " where p.tenant_id = %s and p.reason = 'audit sample' group by p.kind",
        (tenant,),
    ).fetchall()
    return frozenset(r["kind"] for r in rows if r["n"] >= least and r["no"] / r["n"] > at_most)


def _follow(
    conn: db.Conn, tenant: db.Id, about: db.Id, status: str, by: str, reason: str, version: int | None = None
) -> None:
    conn.execute(
        "insert into curriculum_proposal (tenant_id, about, run_id, kind, subject_code, status, reason, made_by,"
        " curriculum_version) select tenant_id, id, run_id, kind, subject_code, %s, %s, %s, %s"
        " from curriculum_proposal where tenant_id = %s and id = %s",
        (status, reason, by, version, tenant, about),
    )


def settle(conn: db.Conn, tenant: db.Id, about: db.Id, yes: bool, by: str, why: str) -> None:
    """A person's yes or no to a proposal waiting for one."""
    now = {r["id"]: r["now"] for r in standing(conn, tenant, "needs_person")}
    if uuid.UUID(str(about)) not in now:
        raise ValueError(f"{about} is not waiting for a person")
    _follow(conn, tenant, about, "approved" if yes else "rejected", by, why)


def _changed_by(conn: db.Conn, who: str) -> None:
    conn.execute("select set_config('app.changed_by', %s, true)", (who,))


def _link(conn: db.Conn, tenant: db.Id, p: DictRow) -> str:
    """The one change a proposal makes, made; what it was, in words."""
    body, code = p["proposal"], p["subject_code"]
    if p["kind"] == "skill":
        for sk in body["skills"]:
            conn.execute(
                "insert into activity_skill (tenant_id, activity_code, skill_code, source, proposal_id)"
                " values (%s,%s,%s,'machine',%s) on conflict do nothing",
                (tenant, code, sk, p["id"]),
            )
        return f"{code} → {', '.join(body['skills'])}"
    if p["kind"] == "lo_skill":
        conn.execute(
            "insert into learning_objective_skill (tenant_id, lo_code, skill_code, source, proposal_id)"
            " values (%s,%s,%s,'machine',%s) on conflict do nothing",
            (tenant, code, body["skills"][0], p["id"]),
        )
        return f"{code} → {body['skills'][0]}"
    if p["kind"] == "objective":
        lo = body.get("objective_code") or _new_objective(conn, tenant, code, body["objective_text"])
        conn.execute(
            "insert into activity_objective (tenant_id, activity_code, lo_code, ord, source, proposal_id)"
            " select %s, %s, %s, coalesce(max(ord), 0) + 1, 'machine', %s from activity_objective"
            " where tenant_id = %s and activity_code = %s on conflict do nothing",
            (tenant, code, lo, p["id"], tenant, code),
        )
        return f"{code} → {lo}"
    for f, text in sorted(body["levels"].items()):
        if f not in LEVELS:  # the checks refused it; a column name never comes from a reply
            raise ValueError(f"{f} is not a level")
        conn.execute(
            f"update activity set {f} = %s where tenant_id = %s and code = %s and btrim({f}) = ''",  # noqa: S608
            (text, tenant, code),
        )
    return f"{code} levels {', '.join(sorted(body['levels']))}"


def _new_objective(conn: db.Conn, tenant: db.Id, activity: str, title: str) -> str:
    """A new objective for an activity, coded as the K2 upload codes its own (LO-<band>-<number>-<n>)."""
    a = db.one(
        conn, "select band, strand from activity where tenant_id = %s and code = %s", (tenant, activity)
    )
    head = f"LO-{a['band']}-{activity.rsplit('-', 1)[1]}-"
    n = conn.execute(
        "select count(*) as n from learning_objective where tenant_id = %s and starts_with(code, %s)",
        (tenant, head),
    ).fetchone()
    lo = f"{head}{(n['n'] if n else 0) + 1}"
    conn.execute(
        "insert into learning_objective (tenant_id, code, band, subject, unit, title, signal)"
        " values (%s,%s,%s,%s,%s,%s,'')",
        (tenant, lo, a["band"], a["strand"], a["strand"], title),
    )
    return lo


def apply(conn: db.Conn, tenant: db.Id, by: str, write: bool) -> list[str]:
    """Every proposal that passed on its own or that a person approved, each made, its link naming the proposal,
    each change in the edit history as the machine's for `by`; written only when `write`."""
    version = conn.execute(
        "select max(number) as n from curriculum_version where tenant_id = %s", (tenant,)
    ).fetchone()
    done: list[str] = []
    for p in [*standing(conn, tenant, "auto_passed"), *standing(conn, tenant, "approved")]:
        if not write:
            done.append(f"{p['kind']}: {p['subject_code']} {json.dumps(p['proposal'], ensure_ascii=False)}")
            continue
        _changed_by(conn, f"machine:{p['id']} for {by}")
        done.append(_link(conn, tenant, p))
        _follow(conn, tenant, p["id"], "applied", by, "", version["n"] if version else None)
    return done


def revert(conn: db.Conn, tenant: db.Id, about: db.Id, by: str, why: str) -> str:
    """An applied proposal undone: the links it made removed, level words it wrote emptied where they are still
    its own, and a `reverted` row; the edit history keeps both sides."""
    rows = [r for r in standing(conn, tenant, "applied") if str(r["id"]) == str(about)]
    if not rows:
        raise ValueError(f"{about} is not applied")
    p = rows[0]
    _changed_by(conn, f"revert of machine:{p['id']} by {by}")
    for table in ("activity_skill", "activity_objective", "learning_objective_skill"):
        conn.execute(
            f"delete from {table} where tenant_id = %s and proposal_id = %s and source = 'machine'",  # noqa: S608
            (tenant, p["id"]),
        )
    if p["kind"] == "levels":
        for f, text in sorted(p["proposal"]["levels"].items()):
            if f not in LEVELS:
                raise ValueError(f"{f} is not a level")
            conn.execute(
                f"update activity set {f} = '' where tenant_id = %s and code = %s and {f} = %s",  # noqa: S608
                (tenant, p["subject_code"], text),
            )
    _follow(conn, tenant, p["id"], "reverted", by, why)
    return f"{p['kind']}: {p['subject_code']} reverted"
