"""The K2 educator's materials list (task M1-10): the routes her pages reach. Only wiring: building, editing, sending and
reminding are `w2_print/materials_*`. The site calls with the engine's key and her email as `actor`, whose staff id the
engine finds (`public.staff_of_email`); she may touch only a class she holds (`educator.timetable_roles`). Every route
refuses while `educator.timetable_enabled` is off, except to the staff preview (`w2_print/educator_gate.py`, D-076),
which may look and change nothing: it is shown a class's list worked out and not kept, a list she holds a class for is
still hers alone to change, and no catalogue item is proposed."""

import datetime as dt
from typing import Literal
from uuid import UUID

import psycopg
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from engine.api.deps import get_conn, get_tenant_id, require_engine_key
from engine.core import db
from engine.w2_print import educator_gate
from engine.w2_print import materials_list as ml
from engine.w2_print import materials_remind as rem
from engine.w2_print import materials_send as send

keyed = APIRouter(prefix="/materials", dependencies=[Depends(require_engine_key)])

GroupBy = Literal["day", "week", "fortnight"]


class Who(BaseModel):
    actor: str


class Build(Who):
    class_id: UUID
    period: GroupBy
    from_: dt.date = Field(alias="from")
    to: dt.date
    group_by: GroupBy | None = None


class Read(Who):
    list_id: UUID
    group_by: GroupBy | None = None


class Quantity(Who):
    line_id: UUID
    quantity: float | None = None


class Line(Who):
    line_id: UUID


class AddLine(Who):
    list_id: UUID
    material_code: str
    quantity: float | None = None
    needed_on: dt.date
    activity_code: str | None = None


class Propose(Who):
    name: str
    unit: str = "piece"


class Send(Who):
    list_id: UUID
    route: Literal["whatsapp", "email"]


class Ack(Who):
    send_id: UUID


class Inbox(Who):
    class_id: UUID | None = None


def staff_of(conn, body: Who, reads: bool = False) -> UUID:
    """Her staff id. Switched off, only the staff preview (D-076, w2_print/educator_gate.py) gets past, and only to a
    route that `reads`: a preview changes nothing. Every route writes unless it says otherwise."""
    sid = db.one(conn, "select public.staff_of_email(%s) as id", (body.actor,))["id"]
    preview = reads and sid is not None and educator_gate.previews(conn, sid)
    if not educator_gate.switched_on(conn) and not preview:
        raise HTTPException(status_code=403, detail="The timetable is not switched on.")
    if sid is None:
        raise HTTPException(status_code=403, detail="This sign-in is not on the staff list.")
    return sid


def unsaved(conn, preview: bool, work):
    """`work()`'s answer. For the staff preview, which changes nothing, the work is done inside a savepoint that is then
    rolled back: the list is worked out exactly as it would be built, and nothing of it is kept."""
    if not preview:
        return work()
    with conn.transaction():
        out = work()
        raise psycopg.Rollback()
    return out


def holds(conn, staff: UUID, class_id: UUID) -> None:
    if not ml.may_edit(conn, staff, class_id, rem.school_today(conn)):
        raise HTTPException(status_code=403, detail="You do not hold this class.")


def list_class(conn, list_id: UUID) -> UUID:
    row = conn.execute("select school_class_id from materials_list where id = %s", (list_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="No such list.")
    return row["school_class_id"]


def _mine_list(conn, body: Who, list_id: UUID, reads: bool = False) -> UUID:
    staff = staff_of(conn, body, reads)
    holds(conn, staff, list_class(conn, list_id))
    return staff


def _line_list(conn, line_id: UUID) -> UUID:
    row = conn.execute("select list_id from materials_line where id = %s", (line_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="No such line.")
    return row["list_id"]


def _mine_line(conn, body: Who, line_id: UUID) -> tuple[UUID, UUID]:
    list_id = _line_list(conn, line_id)
    return _mine_list(conn, body, list_id), list_id


@keyed.post("/build")
def build(body: Build, conn=Depends(get_conn, scope="function")):
    """Make or refresh the class's list and answer it. The staff preview may ask for any class with a timetable in
    force on the first day asked: it is answered the list as it would be built, and nothing is kept."""
    staff = staff_of(conn, body, reads=True)
    preview = educator_gate.previewing(conn, staff)
    today = rem.school_today(conn)
    if not preview:
        holds(conn, staff, body.class_id)
    elif str(body.class_id) not in {c["id"] for c in educator_gate.timetabled_classes(conn, body.from_)}:
        raise HTTPException(status_code=403, detail="You do not hold this class.")

    def work():
        try:
            lid = ml.build(conn, body.class_id, body.period, body.from_, body.to)
        except ValueError as no:
            raise HTTPException(status_code=422, detail=str(no)) from no
        rem.sync(conn, lid, today)
        return ml.read(conn, lid, body.group_by)

    return unsaved(conn, preview, work)


@keyed.post("/read")
def read(body: Read, conn=Depends(get_conn, scope="function")):
    _mine_list(conn, body, body.list_id, reads=True)
    return ml.read(conn, body.list_id, body.group_by)


@keyed.post("/line/quantity")
def quantity(body: Quantity, conn=Depends(get_conn, scope="function")):
    staff, _ = _mine_line(conn, body, body.line_id)
    try:
        ml.set_quantity(conn, body.line_id, body.quantity, staff)
    except ml.LineRemoved as no:
        raise HTTPException(status_code=409, detail="That line was removed: add it back first.") from no
    except ValueError as no:
        raise HTTPException(status_code=422, detail=str(no)) from no
    return {"ok": True}


@keyed.post("/line/remove")
def remove(body: Line, conn=Depends(get_conn, scope="function")):
    staff, list_id = _mine_line(conn, body, body.line_id)
    ml.remove(conn, body.line_id, staff)
    rem.sync(conn, list_id, rem.school_today(conn))
    return {"ok": True}


@keyed.post("/line/add")
def add(body: AddLine, conn=Depends(get_conn, scope="function")):
    staff = _mine_list(conn, body, body.list_id)
    try:
        line = ml.add(
            conn, body.list_id, body.material_code, body.quantity, body.needed_on, body.activity_code, staff
        )
    except ml.NotInCatalogue as no:
        raise HTTPException(
            status_code=422, detail="Add from the catalogue; a new item is proposed first."
        ) from no
    except ml.AlreadyOnList as no:
        raise HTTPException(status_code=409, detail="It is already on the list: change its quantity.") from no
    except ValueError as no:
        raise HTTPException(status_code=422, detail=str(no)) from no
    rem.sync(conn, body.list_id, rem.school_today(conn))
    return {"line_id": line}


@keyed.post("/catalogue/list")
def catalogue(body: Who, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)):
    staff_of(conn, body, reads=True)
    return {
        "items": [
            {
                "code": r["code"],
                "name": r["name"],
                "unit": r["unit"],
                "home": r["home"],
                "tracked": r["unit_value"] is not None,
            }
            for r in conn.execute(
                "select code, name, unit, home, unit_value from material_item order by name"
            )
        ]
    }


@keyed.post("/catalogue/propose")
def propose(body: Propose, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)):
    staff = staff_of(conn, body)
    try:
        return {"code": ml.propose_item(conn, UUID(str(tenant_id)), body.name, body.unit, staff)}
    except ValueError as no:
        raise HTTPException(status_code=422, detail=str(no)) from no


@keyed.post("/send")
def send_list(body: Send, conn=Depends(get_conn, scope="function")):
    staff = _mine_list(conn, body, body.list_id)
    try:
        return send.send(conn, body.list_id, body.route, staff)
    except send.NothingToSend as no:
        raise HTTPException(status_code=422, detail="The list has nothing to send.") from no


@keyed.post("/send/ack")
def ack(body: Ack, conn=Depends(get_conn, scope="function")):
    row = conn.execute("select list_id from materials_send where id = %s", (body.send_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="No such send.")
    staff = _mine_list(conn, body, row["list_id"])
    try:
        send.team_has_it(conn, body.send_id, staff)
    except send.NotSent as no:
        raise HTTPException(status_code=409, detail="Nothing went out with that send.") from no
    return {"ok": True}


@keyed.post("/reminders")
def reminders(body: Inbox, conn=Depends(get_conn, scope="function")):
    staff = staff_of(conn, body, reads=True)
    if body.class_id is not None:
        holds(conn, staff, body.class_id)
    return {"reminders": rem.inbox(conn, rem.school_today(conn), body.class_id, staff)}
