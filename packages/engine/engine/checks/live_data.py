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
    rows = conn.execute(
        "select e.placed_rung, count(*) as n, count(distinct e.child_id) as children"
        " from evidence_placed e where e.confirmed_by is not null and not exists ("
        "  select 1 from skill_set ss join topic t on t.tenant_id = ss.tenant_id and t.code = ss.topic_code"
        "  where ss.tenant_id = e.tenant_id and ss.rung_code = e.placed_rung and t.taught)"
        " group by 1 order by 2 desc"
    ).fetchall()
    return [
        f"{r['n']} signed-off answers of {r['children']} children on {r['placed_rung']}, which no taught skill"
        " shows — run `engine bank relabel`, `engine bank rehome`, `engine graph`"
        for r in rows
    ]


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
    rows = conn.execute(
        "select si.qr_code, coalesce(array_length(t.item_ids, 1), 0) as printed,"
        "       count(r.id) as answers, count(r.id) - count(distinct r.item_id) as twice"
        " from sheet_instance si"
        " join sheet_template t on t.id = si.sheet_template_id"
        " join capture c on c.sheet_instance_id = si.id and c.superseded_by is null"
        " join item_result r on r.capture_id = c.id"
        " group by si.id, si.qr_code, t.item_ids"
        " having count(r.id) <> count(distinct r.item_id) or count(r.id) > coalesce(array_length(t.item_ids, 1), 0)"
    ).fetchall()
    return [
        f"paper {r['qr_code']}: {r['answers']} answers counted for {r['printed']} questions printed"
        + (f", {r['twice']} counted twice" if r["twice"] else "")
        for r in rows
    ]


CHECKS = (
    ("every migration is applied", _migrations),
    ("every signed-off answer counts on a skill the site shows", _off_the_map),
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
            "select id, section, roll_no from child where active order by section, roll_no ~ '^[0-9]+$' desc,"
            " case when roll_no ~ '^[0-9]+$' then roll_no::int end, roll_no"
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
            out.append((c["section"], c["roll_no"], what))
        conn.rollback()
    return week, out
