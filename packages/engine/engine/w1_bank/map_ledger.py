"""The curriculum mapping agents' ledger: what they proposed, what a person decided, what was applied and reverted
(goals/m1-05-mapping-agents.yaml, supabase/migrations/20261230090000_curriculum_proposal_ledger.sql).

Append-only: a proposal is one row, decided when it is made; a person's yes or no, an apply and a revert are each a
new row naming it (`about`), so where a proposal stands is its newest row. A link made from one is marked `machine` and
the proposal's id, so every machine link can be listed and reverted; every link added or removed lands in the
curriculum's edit history by the database's own trigger, with who did it. Who is always ids: a member of staff by
their id (an email is looked up by the engine, `staff_of_email`), the machine by a fixed code; never a typed name.
"""

import json
import uuid

from psycopg.rows import DictRow
from psycopg.types.json import Jsonb

from engine.core import db
from engine.w1_bank.k2_format import LISTS, render
from engine.w1_bank.k2_gaps import column
from engine.w1_bank.map_agents import Proposal
from engine.w1_bank.map_check import LEVELS


def rules(conn: db.Conn) -> dict[str, float]:
    """The `map.*` threshold rows, by their name after `map.`."""
    rows = conn.execute("select key, value from threshold where starts_with(key, 'map.')").fetchall()
    return {r["key"].removeprefix("map."): float(r["value"]) for r in rows}


def record(conn: db.Conn, tenant: db.Id, made: list[Proposal], staff: db.Id) -> uuid.UUID:
    """Every proposal of one run as a row, the member of staff who ran it by their id and the machine's part by its
    code; the run's id back."""
    run = uuid.uuid4()
    for p in made:
        conn.execute(
            "insert into curriculum_proposal (tenant_id, run_id, kind, subject_code, proposal, confidence, proposer,"
            " validator, problems, verdict, status, reason, staff_id, machine)"
            " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
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
                staff,
                f"proposer:{p.proposer}",
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
        (
            r["kind"],
            r["subject_code"],
            r["proposal"]["skills"][0] if r["kind"] in ("lo_skill", "skill_offer") else "",
        )
        for r in standing(conn, tenant)
        if r["now"] != "rejected"
    }


def asked(conn: db.Conn, tenant: db.Id) -> frozenset[tuple[str, str]]:
    """The (activity, skill) pairs a person has been asked about or has refused: every skill ever offered (whatever became of
    the offer) and every skill of a skill proposal a person turned down. A second run does not propose them again."""
    rows = conn.execute(
        "select p.subject_code, p.proposal from curriculum_proposal p where p.tenant_id = %s and p.about is null"
        " and (p.kind = 'skill_offer' or (p.kind = 'skill' and exists (select 1 from curriculum_proposal d"
        " where d.about = p.id and d.status = 'rejected')))",
        (tenant,),
    ).fetchall()
    return frozenset((r["subject_code"], str(s)) for r in rows for s in r["proposal"].get("skills") or [])


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
    conn: db.Conn,
    tenant: db.Id,
    about: db.Id,
    status: str,
    staff: db.Id | None,
    reason: str,
    machine: str | None = None,
    version: int | None = None,
) -> None:
    conn.execute(
        "insert into curriculum_proposal (tenant_id, about, run_id, kind, subject_code, status, reason, staff_id,"
        " machine, curriculum_version) select tenant_id, id, run_id, kind, subject_code, %s, %s, %s, %s, %s"
        " from curriculum_proposal where tenant_id = %s and id = %s",
        (status, reason, staff, machine, version, tenant, about),
    )


def settle(conn: db.Conn, tenant: db.Id, about: db.Id, yes: bool, staff: db.Id, why: str) -> None:
    """A person's yes or no to a proposal waiting for one."""
    now = {r["id"]: r["now"] for r in standing(conn, tenant, "needs_person")}
    if uuid.UUID(str(about)) not in now:
        raise ValueError(f"{about} is not waiting for a person")
    _follow(conn, tenant, about, "approved" if yes else "rejected", staff, why)


def changed_by(conn: db.Conn, who: str) -> None:
    conn.execute("select set_config('app.changed_by', %s, true)", (who,))


def _link(conn: db.Conn, tenant: db.Id, p: DictRow, only: set[str] | None = None) -> str:
    """The one change a proposal makes, made; what it was, in words."""
    body, code = p["proposal"], p["subject_code"]
    if p["kind"] in ("skill", "skill_offer"):
        for sk in body["skills"]:
            conn.execute(
                "insert into activity_skill (tenant_id, activity_code, skill_code, source, proposal_id)"
                " values (%s,%s,%s,'machine',%s) on conflict do nothing",
                (tenant, code, sk, p["id"]),
            )
        return f"{code} → {', '.join(body['skills']) or 'no skill (a person confirmed none)'}"
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
    if p["kind"] == "page_part":
        return _page_part(conn, tenant, p, only)
    if p["kind"] == "material":
        return _material(conn, tenant, p)
    for f, text in sorted(body["levels"].items()):
        if f not in LEVELS:  # the checks refused it; a column name never comes from a reply
            raise ValueError(f"{f} is not a level")
        conn.execute(
            f"update activity set {f} = %s where tenant_id = %s and code = %s and btrim({f}) = ''",  # noqa: S608
            (text, tenant, code),
        )
    return f"{code} levels {', '.join(sorted(body['levels']))}"


def _page_part(conn: db.Conn, tenant: db.Id, p: DictRow, only: set[str] | None = None) -> str:
    """A drafted page's parts written where they are still empty, or where a machine drafted them earlier (never the
    school's words, never a person's): each marked drafted and naming the proposal. A steps or thinking part is written
    as its list too."""
    # a draft is unreviewed until a person has approved it, whatever the machine's verdict: its status stays in the data
    # for the calibration table, but nothing counts as passed on a model's word alone (Nimish's staff, 2026-11-04)
    code, wrote, doubt = p["subject_code"], [], p["now"] != "approved"
    for part, value in sorted(p["proposal"]["parts"].items()):
        if only is not None and part not in only:
            continue
        col, text, listed = column(part), render(part, value), LISTS.get(part)
        hit = conn.execute(
            f"update activity a set {col} = %s{f', {listed} = %s' if listed else ''} where a.tenant_id = %s and a.code = %s"  # noqa: S608
            f" and (btrim(a.{col}) = '' or exists (select 1 from activity_part_source s where s.tenant_id = a.tenant_id"
            " and s.activity_code = a.code and s.part = %s and s.source = 'drafted')) returning a.code",
            (
                text,
                *((Jsonb(value) if not isinstance(value, str) else None,) if listed else ()),
                tenant,
                code,
                part,
            ),
        ).fetchone()
        if hit:
            conn.execute(
                "insert into activity_part_source (tenant_id, activity_code, part, source, proposal_id, check_me)"
                " values (%s,%s,%s,'drafted',%s,%s) on conflict (tenant_id, activity_code, part)"
                " do update set source = 'drafted', proposal_id = excluded.proposal_id, check_me = excluded.check_me",
                (tenant, code, part, p["id"], doubt),
            )
            wrote.append(part)
    return f"{code} drafted {', '.join(wrote) or 'nothing (every part had words by then)'}"


def _material(conn: db.Conn, tenant: db.Id, p: DictRow) -> str:
    """A materials text's lines: catalogue items found by name or made (no home or value is invented), one line each."""
    code = p["subject_code"]
    for i, it in enumerate(p["proposal"]["items"], 1):
        item = conn.execute(
            "select code from material_item where tenant_id = %s and lower(name) = lower(%s)",
            (tenant, it["name"]),
        ).fetchone()
        mat = item["code"] if item else _new_material(conn, tenant, it, p["id"])
        conn.execute(
            "insert into activity_material (tenant_id, activity_code, material_code, quantity, ord, source, proposal_id)"
            " values (%s,%s,%s,%s,%s,'machine',%s) on conflict do nothing",
            (tenant, code, mat, it["quantity"], i, p["id"]),
        )
    return f"{code} materials: {', '.join(it['name'] for it in p['proposal']['items'])}"


def _new_material(conn: db.Conn, tenant: db.Id, it: dict, proposal: db.Id) -> str:
    n = db.one(
        conn,
        "select coalesce(max(substring(code from '[0-9]+$')::int), 0) + 1 as n from material_item where tenant_id = %s",
        (tenant,),
    )["n"]
    conn.execute(
        "insert into material_item (tenant_id, code, name, unit, proposal_id) values (%s,%s,%s,%s,%s)",
        (tenant, f"MAT-{n:04d}", it["name"], it["unit"], proposal),
    )
    return f"MAT-{n:04d}"


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


WHY_SET_ASIDE = "every part of it is covered by a newer draft of this page, or by a part a person approved"


def _winners(rows: list[DictRow]) -> dict[tuple[str, str], uuid.UUID]:
    """For each part of each page, the draft that is written: the newest still waiting to be applied (one a person turned
    down, or that is already applied or taken back, is not newer), unless a person has approved one, and then the newest
    of those. A newer draft that covers fewer parts takes only the parts it covers."""
    waiting = [
        p
        for p in rows
        if p["kind"] == "page_part" and p["now"] in ("auto_passed", "needs_person", "approved")
    ]
    win: dict[tuple[str, str], uuid.UUID] = {}
    for tier in (
        ("auto_passed", "needs_person"),
        ("approved",),
    ):  # the second overrides the first; oldest first in each
        for p in waiting:
            if p["now"] in tier:
                win |= {(p["subject_code"], part): p["id"] for part in p["proposal"]["parts"]}
    return win


def apply(
    conn: db.Conn,
    tenant: db.Id,
    staff: db.Id,
    write: bool,
    only: uuid.UUID | str | None = None,
    kind: str | None = None,
) -> list[str]:
    """Every proposal that passed on its own or that a person approved, each made, its link naming the proposal,
    each change in the edit history as the machine's, run by that member of staff (ids, never a name); written only
    when `write`. `kind` limits it to one kind of proposal (page_part, material, skill, ...)."""
    version = conn.execute(
        "select max(number) as n from curriculum_version where tenant_id = %s", (tenant,)
    ).fetchone()
    done: list[str] = []
    # a drafted page part waiting for a person is written too, tagged check_me: K2 has no empty part (D-071)
    doubtful = [p for p in standing(conn, tenant, "needs_person") if p["kind"] == "page_part"]
    win = _winners(standing(conn, tenant))
    for p in [*standing(conn, tenant, "auto_passed"), *standing(conn, tenant, "approved"), *doubtful]:
        if (only is not None and str(p["id"]) != str(only)) or (kind is not None and p["kind"] != kind):
            continue
        keep = {n for n in p["proposal"].get("parts", {}) if win.get((p["subject_code"], n)) == p["id"]}
        if p["kind"] == "page_part" and not keep:
            if write:  # every part of it is covered by a newer draft, or one a person approved: set aside, never written
                _follow(conn, tenant, p["id"], "rejected", staff, WHY_SET_ASIDE, "apply")
            continue
        if not write:
            done.append(f"{p['kind']}: {p['subject_code']} {json.dumps(p['proposal'], ensure_ascii=False)}")
            continue
        changed_by(conn, f"machine:{p['id']} staff:{staff}")
        done.append(_link(conn, tenant, p, keep if p["kind"] == "page_part" else None))
        _follow(conn, tenant, p["id"], "applied", staff, "", "apply", version["n"] if version else None)
    return done


def revert(conn: db.Conn, tenant: db.Id, about: db.Id, staff: db.Id | None, why: str) -> str:
    """An applied proposal undone: the links it made removed, level words it wrote emptied where they are still
    its own, and a `reverted` row; the edit history keeps both sides."""
    rows = [r for r in standing(conn, tenant, "applied") if str(r["id"]) == str(about)]
    if not rows:
        raise ValueError(f"{about} is not applied")
    p = rows[0]
    changed_by(conn, f"revert:{p['id']} staff:{staff}")
    for table in ("activity_skill", "activity_objective", "learning_objective_skill", "activity_material"):
        conn.execute(
            f"delete from {table} where tenant_id = %s and proposal_id = %s and source = 'machine'",  # noqa: S608
            (tenant, p["id"]),
        )
    if p["kind"] == "material":
        conn.execute(
            "delete from material_item i where i.tenant_id = %s and i.proposal_id = %s and not exists"
            " (select 1 from activity_material m where m.tenant_id = i.tenant_id and m.material_code = i.code)",
            (tenant, p["id"]),
        )
    if p["kind"] == "page_part":
        for part, value in sorted(p["proposal"]["parts"].items()):
            col, text, listed = column(part), render(part, value), LISTS.get(part)
            conn.execute(
                f"update activity set {col} = ''{f', {listed} = null' if listed else ''}"  # noqa: S608
                f" where tenant_id = %s and code = %s and {col} = %s"
                " and exists (select 1 from activity_part_source s where s.tenant_id = %s and s.activity_code = %s"
                " and s.part = %s and s.proposal_id = %s and s.source = 'drafted')",  # a person's kept words stay
                (tenant, p["subject_code"], text, tenant, p["subject_code"], part, p["id"]),
            )
        conn.execute(
            "delete from activity_part_source where tenant_id = %s and proposal_id = %s and source = 'drafted'",
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
    _follow(conn, tenant, p["id"], "reverted", staff, why, "revert")
    return f"{p['kind']}: {p['subject_code']} reverted"
