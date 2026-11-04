"""The school-wide materials list and the notes behind it (task M1-16): the routes the coordinator's and the educators'
pages reach. Only wiring: consolidating, sending and reading a note are `w2_print/materials_*`. As the class routes
(`materials.py`): the site calls with the engine's key and her email as `actor`, and every route refuses while
`educator.timetable_enabled` is off. The school's list is for a role in `materials.consolidate_roles`; a note is for
a class's educator. A photograph is made a plain JPEG here, read, and dropped: it is never written anywhere."""

import datetime as dt
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import Field

from engine.adapters import llm
from engine.api.deps import get_conn, get_tenant_id, require_engine_key
from engine.api.routes.materials import Who, _holds, _list_class, _staff
from engine.core import settings
from engine.w2_print import materials_consolidate as mc
from engine.w2_print import materials_intake as mi
from engine.w2_print import materials_inventory as inv
from engine.w2_print import materials_remind as rem
from engine.w2_print.materials_send import NothingToSend

keyed = APIRouter(prefix="/materials", dependencies=[Depends(require_engine_key)])


class Build(Who):
    from_: dt.date = Field(alias="from")
    to: dt.date


class Ref(Who):
    consolidated_id: UUID


def _coordinator(conn, body: Who) -> UUID:
    staff = _staff(conn, body)
    if not mc.may_consolidate(conn, staff, rem.school_today(conn)):
        raise HTTPException(status_code=403, detail="This is for the coordinator.")
    return staff


@keyed.post("/school/build")
def build(body: Build, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)):
    _coordinator(conn, body)
    if body.to < body.from_:
        raise HTTPException(status_code=422, detail="The last day is before the first day.")
    return mc.read(conn, mc.build(conn, UUID(str(tenant_id)), body.from_, body.to))


def _ours(conn, body: Ref, tenant_id: str) -> None:
    """The list is this school's; otherwise it is not found."""
    found = conn.execute(
        "select 1 from materials_consolidated where id = %s and tenant_id = %s",
        (body.consolidated_id, tenant_id),
    ).fetchone()
    if found is None:
        raise HTTPException(status_code=404, detail="No such list.")


@keyed.post("/school/read")
def read(body: Ref, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)):
    _coordinator(conn, body)
    _ours(conn, body, tenant_id)
    return mc.read(conn, body.consolidated_id)


@keyed.post("/school/send")
def send(body: Ref, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)):
    staff = _coordinator(conn, body)
    _ours(conn, body, tenant_id)
    try:
        return inv.send(conn, body.consolidated_id, staff)
    except NothingToSend as no:
        raise HTTPException(status_code=422, detail="The list has nothing to send.") from no


@keyed.post("/note")
async def note(request: Request, conn=Depends(get_conn, scope="function")):
    """A typed note and/or one photograph for a class's list, read into catalogue items. What code confirms is added to
    the list; the rest waits for a person."""
    form = await request.form(max_files=1)
    actor, list_id, needed_on = form.get("actor"), form.get("list_id"), form.get("needed_on")
    text, upload = form.get("note"), form.get("file")
    if not (isinstance(actor, str) and isinstance(list_id, str) and isinstance(needed_on, str)):
        raise HTTPException(status_code=422, detail="Not sent. Try again.")
    try:
        the_list, the_day = UUID(list_id), dt.date.fromisoformat(needed_on)
    except ValueError as no:
        raise HTTPException(status_code=422, detail="Choose the list and the day it is needed.") from no
    staff = _staff(conn, Who(actor=actor))
    _holds(conn, staff, _list_class(conn, the_list))
    typed = text if isinstance(text, str) else ""
    photo = None
    if upload is not None and not isinstance(upload, str):
        data = await upload.read()
        if len(data) > int(settings.config(conn, "materials.photo_max_bytes", 10_000_000)):
            raise HTTPException(
                status_code=422, detail="That picture is too big. Take it again, or send a smaller one."
            )
        try:
            photo = mi.prepare_photo(data, mi.photo_max_side(conn))
        except Exception as no:  # an unreadable file: Pillow raises its own kinds of error
            raise HTTPException(status_code=422, detail="That is not a picture the system can read.") from no
    if not typed.strip() and photo is None:
        raise HTTPException(status_code=422, detail="Write the note or take a picture of it.")
    try:
        got = mi.read_note(conn, the_list, typed, staff, the_day, photo)
    except llm.LLMBudgetError as no:
        raise HTTPException(
            status_code=429,
            detail="This month's money for reading notes is spent. A person will read your note.",
        ) from no
    except llm.LLMError as no:
        raise HTTPException(status_code=503, detail="The note could not be read just now. Try again.") from no
    return {"readings": [r.__dict__ for r in got]}
