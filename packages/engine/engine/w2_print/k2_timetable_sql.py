"""Writing a `Load` (M1-06 part 2): one list of statements, the same whether `apply` runs it on a copy or `sql_file`
hands it to a person to run where this code cannot reach. The class, year and campus are looked up once into a
temporary table; every table is then one `insert … select` from a `values` list joined to it, `on conflict do nothing`,
so run twice the second adds nothing and the file stays small. Values are quoted by psycopg, never joined into text."""

from psycopg import sql

from engine.core import db
from engine.w2_print import k2_timetable_load as ld

TABLES = ("fortnight", "school_day", "period", "timetable_slot", "plan_entry", "session")
S, L = sql.SQL, sql.Literal


class NoSuchClass(Exception):
    """The class, section and year named are not a row: nothing is written."""


def _values(rows: list[tuple]) -> sql.Composed:
    return S(",\n  ").join(S("({})").format(S(", ").join(L(c) for c in r)) for r in rows)


def _context(t: ld.Target) -> list[sql.SQL | sql.Composed]:
    return [
        S("drop table if exists pg_temp.k2_ctx"),
        S(
            "create temp table k2_ctx on commit drop as select t.id as tenant, y.id as year, c.id as klass,"
            " c.campus_id as campus from tenant t left join academic_year y on y.tenant_id = t.id and y.label = {year}"
            " left join school_class c on c.tenant_id = t.id and c.academic_year_id = y.id and c.grade_code = {grade}"
            " and c.section = {section} where t.slug = {tenant}"
        ).format(year=L(t.year), grade=L(t.grade), section=L(t.section), tenant=L(t.tenant)),
    ]  # fmt: skip


def tables(load: ld.Load, t: ld.Target) -> list[tuple[str, sql.Composed]]:
    """One insert per table that has rows, in the order the foreign keys need."""
    g, out = L(t.grade), []
    if load.fortnights:
        out.append(("fortnight", S(
            "insert into fortnight (tenant_id, academic_year_id, number, kind, starts_on, ends_on)\n"
            "select x.tenant, x.year, v.n::int, 'teaching', v.s::date, v.e::date from k2_ctx x cross join (values\n  {rows}\n"
            ") as v(n, s, e)\non conflict do nothing"
        ).format(rows=_values(load.fortnights))))  # fmt: skip
    if load.school_days:
        out.append(("school_day", S(
            "insert into school_day (tenant_id, campus_id, on_date, kind, note)\n"
            "select x.tenant, x.campus, v.d::date, v.k, v.n from k2_ctx x cross join (values\n  {rows}\n"
            ") as v(d, k, n)\non conflict do nothing"
        ).format(rows=_values(load.school_days))))  # fmt: skip
    if load.periods:
        rows = [(p.ord, p.start, p.end or None, p.label, p.fixed) for p in load.periods]
        out.append(("period", S(
            "insert into period (tenant_id, grade_code, ord, starts_at, ends_at, label, fixed)\n"
            "select x.tenant, {g}, v.o::int, v.s::time, v.e::time, v.l, v.f::boolean from k2_ctx x cross join (values\n  {rows}\n"
            ") as v(o, s, e, l, f)\non conflict do nothing"
        ).format(g=g, rows=_values(rows))))  # fmt: skip
    if load.slots:
        out.append(("timetable_slot", S(
            "insert into timetable_slot (tenant_id, school_class_id, period_id, week_code, weekday, kind, subject_code,"
            " text, valid_from)\nselect x.tenant, x.klass, p.id, v.w, v.wd::int, v.k, v.s, v.t, {first}"
            " from k2_ctx x cross join (values\n  {rows}\n) as v(w, wd, st, k, s, t)\n"
            "join period p on p.tenant_id = x.tenant and p.grade_code = {g} and p.starts_at = v.st::time\non conflict do nothing"
        ).format(first=L(min(f[1] for f in load.fortnights)), g=g, rows=_values(load.slots))))  # fmt: skip
    if load.plan_entries:
        rows = [
            (
                e.fortnight,
                e.key,
                e.ord,
                e.text,
                f"{t.source} ({e.block} block)" if e.block else t.source,
                e.week,
            )
            for e in load.plan_entries
        ]
        out.append(("plan_entry", S(
            "insert into plan_entry (tenant_id, school_class_id, fortnight_id, plan_key, ord, text, activity_id, source,"
            " week_code)\nselect x.tenant, x.klass, f.id, v.k, v.o::int, v.t, act.id, v.s, v.w from k2_ctx x cross join"
            " (values\n  {rows}\n) as v(n, k, o, t, s, w)\njoin fortnight f on f.academic_year_id = x.year and f.number = v.n::int\n"
            "left join lateral (select case when count(*) = 1 then min(a.id::text)::uuid end as id from activity a"
            " where a.tenant_id = x.tenant and a.band = {g} and regexp_replace(lower(a.name), '[^a-z0-9]+', '', 'g')"
            " = regexp_replace(lower(v.t), '[^a-z0-9]+', '', 'g')) act on true\non conflict do nothing"
        ).format(g=g, rows=_values(rows))))  # fmt: skip
    if load.sessions:
        rows = [(s.day, s.start, s.subject, s.key, s.ord, s.fortnight, s.text) for s in load.sessions]
        out.append(("session", S(
            "insert into session (tenant_id, school_class_id, school_day_id, period_id, subject_code, state, planned,"
            " plan_entry_id, text)\nselect x.tenant, x.klass, d.id, p.id, v.sub, 'planned', true, pe.id, v.t"
            " from k2_ctx x cross join (values\n  {rows}\n) as v(d, st, sub, k, o, n, t)\n"
            "join school_day d on d.campus_id = x.campus and d.on_date = v.d::date\n"
            "join period p on p.tenant_id = x.tenant and p.grade_code = {g} and p.starts_at = v.st::time\n"
            "left join fortnight f on f.academic_year_id = x.year and f.number = v.n::int\n"
            "left join plan_entry pe on pe.school_class_id = x.klass and pe.fortnight_id = f.id and pe.plan_key = v.k"
            " and pe.ord = v.o::int\non conflict do nothing"
        ).format(g=g, rows=_values(rows))))  # fmt: skip
    return out


def _guard(t: ld.Target) -> sql.Composed:
    words = f"no such class: {t.grade} {t.section} {t.year}"
    return S(
        "do $$ begin if (select klass from k2_ctx) is null then raise exception {words}; end if; end $$"
    ).format(words=L(words))  # fmt: skip


def statements(load: ld.Load, t: ld.Target) -> list[str]:
    """Every statement as text, in the order it runs."""
    return [p.as_string() for p in [*_context(t), _guard(t), *(q for _, q in tables(load, t))]]


def apply(conn: db.Conn, load: ld.Load, t: ld.Target) -> dict[str, int]:
    """Run the statements on this connection; the rows each added (none the second time)."""
    for stmt in _context(t):
        conn.execute(stmt)
    if db.one(conn, "select klass from k2_ctx")["klass"] is None:
        raise NoSuchClass(f"{t.grade} {t.section} {t.year}")
    return dict.fromkeys(TABLES, 0) | {name: conn.execute(q).rowcount for name, q in tables(load, t)}


def linked(conn: db.Conn) -> int:
    """How many of the class's planner lines the SQL linked to exactly one activity (after `apply`, same transaction)."""
    return db.one(
        conn,
        "select count(*) as n from plan_entry where school_class_id = (select klass from k2_ctx) and activity_id is not null",
    )["n"]


COUNTS = S(
    "select 'fortnight' as t, count(*) from fortnight where academic_year_id = (select year from k2_ctx)\n"
    "union all select 'school_day', count(*) from school_day where campus_id = (select campus from k2_ctx)\n"
    "union all select 'period', count(*) from period where tenant_id = (select tenant from k2_ctx)\n"
    "union all select 'timetable_slot', count(*) from timetable_slot where school_class_id = (select klass from k2_ctx)\n"
    "union all select 'plan_entry', count(*) from plan_entry where school_class_id = (select klass from k2_ctx)\n"
    "union all select 'session', count(*) from session where school_class_id = (select klass from k2_ctx)"
)  # fmt: skip


def counts(conn: db.Conn) -> dict[str, int]:
    """The rows the class holds in each of the six tables (same transaction as `apply`, whose context it reads)."""
    return {r["t"]: r["count"] for r in conn.execute(COUNTS).fetchall()}


def sql_file(load: ld.Load, t: ld.Target, sources: dict[str, str]) -> str:
    """One transaction, with the row counts before and after, for a person to run where this code cannot reach."""
    head = [
        "-- Generated by `engine timetable load --sql`. Safe to run twice: every insert is `on conflict do nothing`.",
        *(f"-- source {name}: sha256 {digest}" for name, digest in sorted(sources.items())),
        f"-- target: {t.grade} {t.section} {t.year}; rows planned: {ld.summary(load)}",
        "begin;",
        *(c.as_string() + ";" for c in _context(t)),
        "-- before",
        COUNTS.as_string() + ";",
    ]
    body = [s.as_string() + ";" for s in [_guard(t), *(q for _, q in tables(load, t))]]
    return "\n".join([*head, *body, "-- after", COUNTS.as_string() + ";", "commit;", ""])
