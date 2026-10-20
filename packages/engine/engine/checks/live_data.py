"""Do the live rows say what the website shows? `engine live data` — read only, safe on the live database.

The site can be up and still wrong: on 2026-09-23 a child's page showed one skill because `bank rehome` had
refused its questions and 454 signed-off answers sat on rungs no taught skill shows. Each check here is one
way the rows and the pages can part company, asked of the database in a read-only session, so it can run
against live (`LIVE_READONLY_DATABASE_URL`) without changing a row.
"""

import os
from datetime import date

from engine.core import db

MIGRATIONS = db.REPO_ROOT / "supabase" / "migrations"


def url() -> str:
    """The read-only address when it is set, else the engine's own."""
    return os.getenv("LIVE_READONLY_DATABASE_URL") or db.dsn()


def unapplied(files, applied):
    """Migration files whose version the database has not recorded, in order."""
    done = set(applied)
    return sorted(f for f in files if f.split("_", 1)[0] not in done)


def _migrations(conn):
    files = [p.name for p in MIGRATIONS.glob("*.sql")]
    applied = [
        r["version"] for r in conn.execute("select version from supabase_migrations.schema_migrations")
    ]
    return [f"not applied: {f}" for f in unapplied(files, applied)]


def _off_the_map(conn):
    """Signed-off answers on a rung no skill set holds at all: lost to every page. Answers on a skill whose topic is
    not taught yet (multiplication, explaining a method) are hidden on purpose and kept; `hidden` counts them."""
    rows = conn.execute(
        "select e.placed_rung, count(*) as n, count(distinct e.child_id) as children"
        " from evidence_placed e where e.confirmed_by is not null and not exists ("
        "  select 1 from skill_set ss where ss.tenant_id = e.tenant_id and ss.rung_code = e.placed_rung)"
        " group by 1 order by 2 desc"
    ).fetchall()
    return [
        f"{r['n']} signed-off answers of {r['children']} children on {r['placed_rung']}, which no skill holds"
        " — run `engine bank levels --apply`, `engine bank relabel`, `engine bank rehome`, `engine graph`"
        for r in rows
    ]


def hidden(conn):
    """{skill set: signed-off answers} on skills the child's class has not been taught yet — kept, not shown
    (goals/f1f-taught-per-class.yaml, goals/t1-topics-are-operations.yaml)."""
    return {
        r["code"]: r["n"]
        for r in conn.execute(
            "select ss.code, count(*) as n from evidence_placed e"
            " join child c on c.id = e.child_id"
            " join skill_set ss on ss.tenant_id = e.tenant_id and ss.rung_code = e.placed_rung"
            " where e.confirmed_by is not null and not skill_taught_in(ss.tenant_id, ss.code, c.section)"
            " group by 1 order by 1"
        )
    }


def _stale_graph(conn):
    r = conn.execute(
        "with fresh as ("
        "  select e.child_id, e.skill_code, e.placed_rung as rung_code,"
        "         count(*) filter (where e.correct is not null) as n_events,"
        "         count(*) filter (where e.correct) as n_correct"
        "  from evidence_placed e"
        "  left join item_result r on r.id = e.item_result_id left join capture c on c.id = r.capture_id"
        "  where e.confirmed_by is not null and (c.id is null or c.superseded_by is null)"
        "  group by 1, 2, 3)"
        " select count(*) filter (where s.child_id is null) as missing,"
        "        count(*) filter (where f.child_id is null) as stale,"
        "        count(*) filter (where f.n_events <> s.n_events or f.n_correct <> s.n_correct) as differ"
        " from fresh f full join child_skill_state s using (child_id, skill_code, rung_code)"
    ).fetchone()
    if not any(r.values()):
        return []
    return [
        f"child_skill_state is not what the answers say: {r['missing']} missing, {r['stale']} stale,"
        f" {r['differ']} with other counts — run `engine graph`"
    ]


def _marking(conn):
    """A paper counts each answer its printed questions ask for once: a question asking for several (a grid's cells,
    an estimate and its exact answer, goals/md0a-every-answer-counts.yaml) has one result per answer, each its own
    `rid`. Counted twice is the same answer to the same question on two live captures of one paper."""
    rows = conn.execute(
        "with asked as ("
        "  select t.id, count(*) as printed,"
        "         sum(greatest(coalesce(jsonb_array_length(i.responses), 0), 1)) as asked"
        "  from sheet_template t cross join unnest(t.item_ids) q(item_id) join item i on i.id = q.item_id"
        "  group by t.id)"
        " select si.qr_code, coalesce(a.printed, 0) as printed, coalesce(a.asked, 0) as asked, count(r.id) as answers,"
        "        count(r.id) - count(distinct (r.item_id, coalesce(r.rid, i.responses -> 0 ->> 'rid', ''))) as twice"
        " from sheet_instance si"
        " left join asked a on a.id = si.sheet_template_id"
        " join capture c on c.sheet_instance_id = si.id and c.superseded_by is null"
        " join item_result r on r.capture_id = c.id join item i on i.id = r.item_id"
        " group by si.id, si.qr_code, a.printed, a.asked"
        " having count(r.id) <> count(distinct (r.item_id, coalesce(r.rid, i.responses -> 0 ->> 'rid', '')))"
        "     or count(r.id) > coalesce(a.asked, 0)"
    ).fetchall()
    return [
        f"paper {r['qr_code']}: {r['answers']} answers counted for {r['asked']} asked by {r['printed']} questions"
        " printed" + (f", {r['twice']} counted twice" if r["twice"] else "")
        for r in rows
    ]


CHECKS = (
    ("every migration is applied", _migrations),
    ("every signed-off answer counts on a skill", _off_the_map),
    ("each child's skills are rebuilt from their answers", _stale_graph),
    ("Marking counts each printed question once", _marking),
)


def check(address: str | None = None):
    """(ok, lines). One line per check, and one per problem under it."""
    ok, lines = True, []
    with db.connect(address or url()) as conn:
        conn.read_only = True
        for name, run in CHECKS:
            problems = run(conn)
            ok &= not problems
            lines.append(f"  {'ok  ' if not problems else 'FAIL'}  {name}")
            lines += [f"        {p}" for p in problems]
        kept = hidden(conn)
        if kept:
            lines.append(
                "  note  kept but not shown, their topic not taught yet: "
                + ", ".join(f"{c} {n} answers" for c, n in kept.items())
            )
        conn.rollback()
    return ok, lines


def week_now() -> str:
    """This ISO week as the website names it (`apps/web/lib/week.ts`): "2026-W39"."""
    y, w, _ = date.today().isocalendar()
    return f"{y}-W{w:02d}"


def homes(address: str | None = None, week: str | None = None):
    """Each child's home paper for the week, as Make papers proposes it: section, roll, then the skill, level and
    questions — or the paper already approved, or why there is none. Read only; names never printed."""
    from engine.w2_print import focus_paper

    week = week or week_now()
    out = []
    with db.connect(address or url()) as conn:
        conn.read_only = True
        kids = conn.execute(
            "select c.id, c.section, c.roll_no, (select count(*) from answer_placed a"
            "  where a.child_id = c.id and a.confirmed_by is not null) as answers"
            " from child c where c.active order by c.section, roll_order(c.roll_no), c.roll_no"
        ).fetchall()
        for c in kids:
            done = focus_paper.approved(conn, str(c["id"]), week)
            if done:
                what = f"approved {done['qr']}"
            else:
                p = focus_paper.plan(conn, str(c["id"]), week)
                what = (
                    " + ".join(f"{a['skill_set']} {a['level']} ×{len(a['questions'])}" for a in p["areas"])
                    or "nothing to work on"
                )
            out.append((c["section"], c["roll_no"], f"{c['answers']:>4} answers signed off · {what}"))
        conn.rollback()
    return week, out
