"""The educator's timetable (M1-06 part 2): her day, her week, one period. Only wiring: what is read is
`k2_day`'s. From the site with the engine's key and her email as `actor`, as the voice routes are; every call refuses
while `educator.timetable_enabled` is off, and answers only for a class she holds."""

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from engine.api.deps import get_conn, require_engine_key
from engine.w2_print import k2_day
from engine.w3_read import voice_intake, voice_store

keyed = APIRouter(dependencies=[Depends(require_engine_key)])


class Ask(BaseModel):
    actor: str
    class_id: str | None = None
    day: dt.date | None = None
    week_of: dt.date | None = None
    period_id: str | None = None


def _mine(conn, body: Ask, on: dt.date) -> tuple[dict, list[dict]]:
    if not k2_day.enabled(conn):
        raise HTTPException(status_code=403, detail="The timetable is not switched on.")
    try:
        staff = voice_intake.staff_of(conn, body.actor)
        classes = k2_day.my_classes(conn, staff, on)
        return k2_day.chosen(classes, body.class_id), classes
    except (voice_store.Refused, k2_day.Refused) as no:
        raise HTTPException(status_code=no.status, detail=str(no)) from no


@keyed.post("/timetable/day")
def day(body: Ask, conn=Depends(get_conn, scope="function")):
    on = body.day or dt.date.today()
    klass, classes = _mine(conn, body, on)
    return k2_day.day(conn, klass, classes, on)


@keyed.post("/timetable/week")
def week(body: Ask, conn=Depends(get_conn, scope="function")):
    on = body.week_of or body.day or dt.date.today()
    klass, classes = _mine(conn, body, on)
    return k2_day.week(conn, klass, classes, on)


@keyed.post("/timetable/period")
def period(body: Ask, conn=Depends(get_conn, scope="function")):
    if not (body.day and body.period_id):
        raise HTTPException(status_code=422, detail="Name the day and the period.")
    klass, classes = _mine(conn, body, body.day)
    try:
        return k2_day.period(conn, klass, classes, body.day, body.period_id)
    except k2_day.Refused as no:
        raise HTTPException(status_code=no.status, detail=str(no)) from no
