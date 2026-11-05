"""The timetable's rules (M1-14 part a): read them, change one. Only wiring: the checks and the writing are
`tt_rules`'s. From the site with the engine's key and the person's email as `actor`. These are the staff's setup
screens, so the educator switch (`educator.timetable_enabled`) does not gate them; a sign-in not on the staff list is
refused (403) and nothing is written."""

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from engine.api.deps import get_conn, require_engine_key
from engine.w2_print import tt_rules
from engine.w3_read import voice_intake, voice_store

keyed = APIRouter(dependencies=[Depends(require_engine_key)])


class Ask(BaseModel):
    actor: str
    class_id: str | None = None


class Change(Ask):
    rule: str
    action: str
    id: str | None = None
    period_id: str | None = None
    starts_at: dt.time | None = None
    ends_at: dt.time | None = None
    label: str | None = None
    on_date: dt.date | None = None
    weekday: int | None = None
    week_code: str | None = None
    reason: str | None = None
    subject_code: str | None = None
    span: str | None = None
    fewest: int | None = None
    most: int | None = None
    text: str | None = None


def _staff(conn, email: str):
    try:
        return voice_intake.staff_of(conn, email)
    except voice_store.Refused as no:
        raise HTTPException(status_code=no.status, detail=str(no)) from no


@keyed.post("/timetable/rules/read")
def read(body: Ask, conn=Depends(get_conn, scope="function")):
    staff = _staff(conn, body.actor)
    try:
        return tt_rules.read(conn, body.class_id, staff)
    except tt_rules.Refused as no:
        raise HTTPException(status_code=no.status, detail=str(no)) from no


@keyed.post("/timetable/rules/change")
def change(body: Change, conn=Depends(get_conn, scope="function")):
    staff = _staff(conn, body.actor)
    fields = body.model_dump(exclude={"actor", "class_id"})
    try:
        return tt_rules.change(
            conn,
            staff,
            body.class_id,
            tt_rules.Change(**fields),
            voice_intake.school_day(conn, dt.datetime.now(dt.UTC)),
        )
    except tt_rules.Refused as no:
        raise HTTPException(status_code=no.status, detail=str(no)) from no
