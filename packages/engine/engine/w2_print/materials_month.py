"""The month build (task M1-16; D-072: the school's list goes out once every class's has been made). Builds each class's
list for the month, then the school's, and says which classes it is short of, so the school list is not silently the
sum of only the classes whose educator tapped Build. Code only. A class's lists follow the school's fortnights: one list
for each fortnight the class has a planned session in, which the school's list then reads for the days of the month."""

import datetime as dt
from typing import Any
from uuid import UUID

from engine.core import db, settings
from engine.w2_print import materials_consolidate as mc
from engine.w2_print import materials_coverage as coverage
from engine.w2_print import materials_list as ml
from engine.w2_print import materials_remind as rem


def _pairs(
    conn: db.Conn, tenant: UUID, lo: dt.date, hi: dt.date, expected: list[UUID]
) -> list[dict[str, Any]]:
    """Each (class, fortnight) with a planned session of a mapped activity on a day of the month."""
    return conn.execute(
        "select distinct s.school_class_id as class_id, f.id as fortnight_id, f.starts_on, f.ends_on"
        " from session s join school_day d on d.id = s.school_day_id join plan_entry p on p.id = s.plan_entry_id"
        " join school_class c on c.id = s.school_class_id join fortnight f on f.academic_year_id = c.academic_year_id"
        " and d.on_date between f.starts_on and f.ends_on"
        " where s.tenant_id = %s and s.planned and p.activity_id is not null and d.on_date between %s and %s"
        " and c.id = any(%s) order by 1, 3",
        (tenant, lo, hi, expected),
    ).fetchall()


def build_month(conn: db.Conn, tenant: UUID, lo: dt.date, hi: dt.date) -> dict[str, Any]:
    """Build every class's lists for `lo`..`hi`, then the school's. Returns the school list's id, the classes built,
    and the classes it is short of (`no_plan`, `no_fortnight`, `no_materials`: see `materials_coverage.WHY`)."""
    if hi < lo:
        raise ValueError("The last day is before the first day.")
    longest = int(settings.config(conn, "materials.month_build_max_days", 62))
    if (hi - lo).days + 1 > longest:
        raise ValueError(f"A month build is for one month: at most {longest} days.")
    names, today = coverage.class_names(conn, tenant), rem.school_today(conn)
    expected = coverage.planned_classes(conn, tenant, lo, hi)
    pairs = _pairs(conn, tenant, lo, hi, expected)
    for p in pairs:
        rem.sync(conn, ml.build(conn, p["class_id"], "fortnight", p["starts_on"], p["ends_on"]), today)
    cid = mc.build(conn, tenant, lo, hi)
    return {
        "consolidated_id": cid,
        "built": [{"class_id": c, "class": names[c]} for c in dict.fromkeys(p["class_id"] for p in pairs)],
        **coverage.short_of(conn, tenant, lo, hi, cid, expected),
    }
