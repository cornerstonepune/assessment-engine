"""The educator's timetable (M1-06 part 2): her day, her week, one period. Only wiring: what is read is
`k2_day`'s. From the site with the engine's key and her email as `actor`, as the voice routes are; every call refuses
while `educator.timetable_enabled` is off unless she is the staff preview (`w2_print/educator_gate.py`), and answers
only for a class she holds."""

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from engine.api.deps import get_conn, require_engine_key
from engine.w2_print import educator_gate, k2_day
from engine.w3_read import voice_intake, voice_store

keyed = APIRouter(dependencies=[Depends(require_engine_key)])


class Ask(BaseModel):
    actor: str
    class_id: str | None = None
    day: dt.date | None = None
    week_of: dt.date | None = None
    period_id: str | None = None


def _today(conn) -> dt.date:
    """Today by the school's clock, never the server's."""
    return voice_intake.school_day(conn, dt.datetime.now(dt.UTC))


def _refused(no: Exception) -> HTTPException:
    return HTTPException(status_code=getattr(no, "status", 403), detail=str(no))


def _gate(conn, body: Ask):
    """Her staff id, once the gate lets her past: switched on, or she is the staff preview (D-076). First, before any
    field is checked, so a call while switched off learns nothing more."""
    try:
        staff = voice_intake.staff_of(conn, body.actor)
    except voice_store.Refused as no:
        if not educator_gate.switched_on(conn):
            raise HTTPException(status_code=403, detail="The timetable is not switched on.") from no
        raise _refused(no) from no
    if not educator_gate.open_to(conn, staff):
        raise HTTPException(status_code=403, detail="The timetable is not switched on.")
    return staff


def _mine(conn, body: Ask, on: dt.date, staff=None) -> tuple[dict, list[dict]]:
    """Her class and every class she holds on that day (`staff` when the gate has run already)."""
    staff = staff or _gate(conn, body)
    try:
        classes = k2_day.my_classes(conn, staff, on)
        return k2_day.chosen(classes, body.class_id), classes
    except k2_day.Refused as no:
        raise _refused(no) from no


@keyed.post("/timetable/open")
def open_to(body: Ask, conn=Depends(get_conn, scope="function")):
    """Whether her screens are open to her, for a screen that reads no timetable (the activity page): refused as every
    other call is, else whether she sees them as the staff preview."""
    return {"previewing": educator_gate.previewing(conn, _gate(conn, body))}


@keyed.post("/timetable/day")
def day(body: Ask, conn=Depends(get_conn, scope="function")):
    on = body.day or _today(conn)
    klass, classes = _mine(conn, body, on)
    return k2_day.day(conn, klass, classes, on)


@keyed.post("/timetable/week")
def week(body: Ask, conn=Depends(get_conn, scope="function")):
    on = body.week_of or body.day or _today(conn)
    # her class is the one she holds by the week's last teaching day, so a grant that starts mid-week still shows the week
    klass, classes = _mine(conn, body, on - dt.timedelta(days=on.weekday()) + dt.timedelta(days=4))
    return k2_day.week(conn, klass, classes, on)


@keyed.post("/timetable/period")
def period(body: Ask, conn=Depends(get_conn, scope="function")):
    staff = _gate(conn, body)
    if not (body.day and body.period_id):
        raise HTTPException(status_code=422, detail="Name the day and the period.")
    klass, classes = _mine(conn, body, body.day, staff)
    try:
        return k2_day.period(conn, klass, classes, body.day, body.period_id)
    except k2_day.Refused as no:
        raise _refused(no) from no
