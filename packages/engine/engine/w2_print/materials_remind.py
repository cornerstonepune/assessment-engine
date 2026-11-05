"""The materials list's reminders as rows (task M1-10; D-070, D-072). The dates are `materials_reminders`'s; this reads
the first day a material is needed, the lead times (setting `materials.reminder_weeks`) and the school's holidays, and
keeps one reminder for the educator and one for the materials team at each lead time. A list that has been sent has none."""

import datetime as dt
from typing import Any
from uuid import UUID

from engine.core import db, settings
from engine.w2_print import materials_list
from engine.w2_print import materials_reminders as dates

AUDIENCES = ("educator", "team")


def school_today(conn: db.Conn) -> dt.date:
    zone = settings.config(conn, "school.time_zone", "Asia/Kolkata")
    return db.one(conn, "select (now() at time zone %s)::date as d", (zone,))["d"]


def _holidays(conn: db.Conn, tenant: UUID, campus: UUID, lo: dt.date, hi: dt.date) -> set[dt.date]:
    out = {
        r["on_date"]
        for r in conn.execute(
            "select on_date from school_day where tenant_id = %s and campus_id = %s and kind = 'holiday'"
            " and on_date between %s and %s",
            (tenant, campus, lo, hi),
        )
    }
    for f in conn.execute(
        "select starts_on, ends_on from fortnight where tenant_id = %s and kind = 'vacation'"
        " and ends_on >= %s and starts_on <= %s",
        (tenant, lo, hi),
    ):
        out |= {
            f["starts_on"] + dt.timedelta(days=i) for i in range((f["ends_on"] - f["starts_on"]).days + 1)
        }
    return out


def sync(conn: db.Conn, list_id: UUID, today: dt.date) -> None:
    """Make the list's pending reminders match its first-needed day and the settings. Sent, or empty: none are pending."""
    lst = db.one(
        conn,
        "select l.tenant_id, l.state, c.campus_id, (select min(needed_on) from materials_line"
        " where list_id = l.id and removed_at is null) as first"
        " from materials_list l join school_class c on c.id = l.school_class_id where l.id = %s",
        (list_id,),
    )
    weeks = [int(w) for w in settings.config(conn, "materials.reminder_weeks", [2, 1])]
    first = lst["first"]
    made: list[dates.Reminder] = []
    if lst["state"] == "draft" and first is not None:
        lo = first - dt.timedelta(weeks=max(weeks, default=0) + 12)
        made = dates.reminder_dates(
            first, weeks, today, _holidays(conn, lst["tenant_id"], lst["campus_id"], lo, first)
        )
    for r in made:
        for who in AUDIENCES:
            conn.execute(
                "insert into reminder (tenant_id, list_id, weeks_before, audience, due_on, at_once)"
                " values (%s, %s, %s, %s, %s, %s) on conflict (list_id, weeks_before, audience) do update"
                " set due_on = excluded.due_on, at_once = excluded.at_once, state = 'pending', updated_at = now()",
                (lst["tenant_id"], list_id, r.weeks_before, who, r.due_on, r.at_once),
            )
    conn.execute(
        "update reminder set state = 'cancelled', updated_at = now() where list_id = %s and state = 'pending'"
        " and weeks_before <> all(%s)",
        (list_id, [r.weeks_before for r in made]),
    )


def inbox(
    conn: db.Conn, today: dt.date, class_id: UUID | None = None, staff: UUID | None = None
) -> list[dict[str, Any]]:
    """What the educator is reminded of today: one message for each unsent list with a reminder due, however many lead
    times are due together. With `staff`, only for classes she holds (`educator.timetable_roles`)."""
    held = None if staff is None else materials_list.held_classes(conn, staff, today)
    rows = conn.execute(
        "select r.list_id, l.school_class_id as class_id, max(r.due_on) as due_on, bool_or(r.at_once) as at_once,"
        " array_agg(r.weeks_before order by r.weeks_before desc) as weeks_before,"
        " (select min(needed_on) from materials_line where list_id = r.list_id and removed_at is null) as first_needed"
        " from reminder r join materials_list l on l.id = r.list_id"
        " where r.state = 'pending' and r.audience = 'educator' and r.due_on <= %s and l.state = 'draft'"
        " and (%s::uuid is null or l.school_class_id = %s)"
        " and (%s::uuid[] is null or l.school_class_id = any(%s))"
        " group by r.list_id, l.school_class_id order by 3, 1",
        (today, class_id, class_id, held, held),
    ).fetchall()
    return list(rows)


def due_counts(conn: db.Conn, today: dt.date, tenant: UUID) -> dict[str, int]:
    """How many pending reminders have come due by `today`. Only counts: it sends and changes nothing."""
    r = db.one(
        conn,
        "select count(*) as reminders, count(distinct list_id) as lists,"
        " count(*) filter (where audience = 'educator') as educator,"
        " count(*) filter (where audience = 'team') as team"
        " from reminder r where tenant_id = %s and state = 'pending' and due_on <= %s"
        " and exists (select 1 from materials_list l where l.id = r.list_id and l.state = 'draft')",
        (tenant, today),
    )
    return dict(r)
