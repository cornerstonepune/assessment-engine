"""Which classes the school's materials list covers, and why it is short of the rest (task M1-16). A class is expected to
have a plan when its grade has activities and the month falls in its school year. The shortness is read from the stored
build, so what is said about it always matches the lines of that same build."""

import datetime as dt
from typing import Any
from uuid import UUID

from engine.core import db

# why a class is short, by the name `short_of` gives it
WHY = {
    "no_plan": "no plan to build from",
    "no_fortnight": "planned on days no school fortnight covers",
    "no_materials": "its plan asks for no materials",
}


def class_names(conn: db.Conn, tenant: UUID) -> dict[UUID, str]:
    return {
        r["id"]: f"{r['grade_code']} {r['section'] or ''}".strip()
        for r in conn.execute(
            "select id, grade_code, section from school_class where tenant_id = %s", (tenant,)
        )
    }


def planned_classes(conn: db.Conn, tenant: UUID, lo: dt.date, hi: dt.date) -> list[UUID]:
    """The classes expected to have a plan for the month: a grade that has activities, in a school year the month
    touches. A class of a grade the activity list does not cover is not short of a plan, it has none to give."""
    return [
        r["id"]
        for r in conn.execute(
            "select c.id from school_class c join academic_year y on y.id = c.academic_year_id"
            " where c.tenant_id = %s and y.starts_on <= %s and y.ends_on >= %s"
            " and exists (select 1 from activity a where a.tenant_id = c.tenant_id and a.band = c.grade_code)"
            " order by c.grade_code, c.section, c.id",
            (tenant, hi, lo),
        )
    ]


def with_sessions(conn: db.Conn, tenant: UUID, lo: dt.date, hi: dt.date) -> set[UUID]:
    """The classes that have at least one planned session of a mapped activity in the range."""
    return {
        r["school_class_id"]
        for r in conn.execute(
            "select distinct s.school_class_id from session s join school_day d on d.id = s.school_day_id"
            " join plan_entry p on p.id = s.plan_entry_id"
            " where s.tenant_id = %s and s.planned and p.activity_id is not null and d.on_date between %s and %s",
            (tenant, lo, hi),
        )
    }


def classes_in(conn: db.Conn, cid: UUID) -> set[UUID]:
    """The classes that give something to the school list's latest build."""
    return {
        r["class_id"]
        for r in conn.execute(
            "select distinct class_id from materials_consolidated_source s join materials_consolidated c"
            " on c.id = s.consolidated_id and c.latest_build = s.build where s.consolidated_id = %s",
            (cid,),
        )
    }


def short_of(
    conn: db.Conn,
    tenant: UUID,
    lo: dt.date,
    hi: dt.date,
    cid: UUID,
    expected: list[UUID] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """Which classes the school list `cid` is short of, and why (`WHY`): `no_plan`, `no_fortnight` (planned, but on days
    no school fortnight covers, so no list could be made) and `no_materials` (a list was made and its plan asks for
    none). Each is named, so a person can read it."""
    names, planned, giving = (
        class_names(conn, tenant),
        with_sessions(conn, tenant, lo, hi),
        classes_in(conn, cid),
    )
    expected = planned_classes(conn, tenant, lo, hi) if expected is None else expected
    listed = {
        r["school_class_id"]
        for r in conn.execute(
            "select distinct school_class_id from materials_list"
            " where tenant_id = %s and from_on <= %s and to_on >= %s",
            (tenant, hi, lo),
        )
    }

    def named(ids: list[UUID]) -> list[dict[str, Any]]:
        return [{"class_id": c, "class": names[c]} for c in ids]

    return {
        "no_plan": named([c for c in expected if c not in planned]),
        "no_fortnight": named([c for c in expected if c in planned and c not in listed]),
        "no_materials": named([c for c in expected if c in listed and c not in giving]),
    }
