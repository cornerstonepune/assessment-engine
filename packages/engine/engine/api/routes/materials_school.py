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
from engine.api.routes.materials import Who, holds, list_class, staff_of, unsaved
from engine.w2_print import educator_gate
from engine.w2_print import materials_consolidate as mc
from engine.w2_print import materials_intake as mi
from engine.w2_print import materials_inventory as inv
from engine.w2_print import materials_list as ml
from engine.w2_print import materials_month as mm
from engine.w2_print import materials_remind as rem
from engine.w2_print import materials_review as rv
from engine.w2_print.materials_send import NothingToSend

keyed = APIRouter(prefix="/materials", dependencies=[Depends(require_engine_key)])


class Build(Who):
    from_: dt.date = Field(alias="from")
    to: dt.date


class Ref(Who):
    consolidated_id: UUID


class Note(Who):
    note_id: UUID


class Clear(Note):
    material_code: str
    quantity: float
    needed_on: dt.date


class SetAside(Note):
    why: str


class Word(Who):
    word: str
    material_code: str


class Unit(Who):
    material_code: str
    unit: str
    factor: float


def _mine(conn, body: Who, tenant_id: str, consolidated_id: UUID | None = None, reads: bool = False) -> UUID:
    """She may build and send the school's list; if a list is named it is this school's, else not found. A route that
    only `reads` lets the staff preview look while switched off."""
    staff = staff_of(conn, body, reads)
    if not mc.may_consolidate(conn, staff, rem.school_today(conn)):
        raise HTTPException(status_code=403, detail="This is for the coordinator.")
    if consolidated_id is not None:
        found = conn.execute(
            "select 1 from materials_consolidated where id = %s and tenant_id = %s",
            (consolidated_id, tenant_id),
        ).fetchone()
        if found is None:
            raise HTTPException(status_code=404, detail="No such list.")
    return staff


@keyed.post("/school/build")
def build(body: Build, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)):
    """Build the school's list for the range and answer it; the staff preview is answered it worked out, not kept."""
    staff = _mine(conn, body, tenant_id, reads=True)

    def work():
        try:
            got = mm.build_month(conn, UUID(str(tenant_id)), body.from_, body.to)
        except ValueError as no:
            raise HTTPException(status_code=422, detail=str(no)) from no
        return mc.read(conn, got["consolidated_id"]) | {
            k: v for k, v in got.items() if k != "consolidated_id"
        }

    return unsaved(conn, educator_gate.previewing(conn, staff), work)


@keyed.post("/school/read")
def read(body: Ref, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)):
    _mine(conn, body, tenant_id, body.consolidated_id, reads=True)
    return mc.read(conn, body.consolidated_id)


@keyed.post("/school/send")
def send(body: Ref, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)):
    staff = _mine(conn, body, tenant_id, body.consolidated_id)
    try:
        return inv.send(conn, body.consolidated_id, staff)
    except NothingToSend as no:
        raise HTTPException(status_code=422, detail="The list has nothing to send.") from no


@keyed.post("/review/list")
def review_list(body: Who, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)):
    """The notes the system could not confirm, oldest first, for a person to read."""
    _mine(conn, body, tenant_id, reads=True)
    return {
        "notes": [
            {**n, "id": str(n["id"]), "list_id": str(n["list_id"])}
            for n in rv.waiting(conn, UUID(str(tenant_id)))
        ]
    }


@keyed.post("/review/resolve")
def review_resolve(
    body: Clear, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)
):
    """Put what a waiting note asked for on its class's list, as a line a person chose."""
    staff = _mine(conn, body, tenant_id)
    try:
        the_list = rv.resolve(
            conn, UUID(str(tenant_id)), body.note_id, body.material_code, body.quantity, body.needed_on, staff
        )
    except rv.NoSuchNote as no:
        raise HTTPException(status_code=404, detail="No such note.") from no
    except rv.NotWaiting as no:
        raise HTTPException(status_code=409, detail="That note is already cleared.") from no
    except ml.NotInCatalogue as no:
        raise HTTPException(status_code=422, detail="Choose an item from the catalogue.") from no
    except ml.AlreadyOnList as no:
        raise HTTPException(
            status_code=409, detail="It is already on the list: change its quantity there."
        ) from no
    except ValueError as no:
        raise HTTPException(status_code=422, detail=str(no)) from no
    rem.sync(conn, the_list, rem.school_today(conn))
    return {"list_id": str(the_list)}


@keyed.post("/review/dismiss")
def review_dismiss(
    body: SetAside, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)
):
    staff = _mine(conn, body, tenant_id)
    try:
        rv.dismiss(conn, UUID(str(tenant_id)), body.note_id, body.why, staff)
    except rv.NoSuchNote as no:
        raise HTTPException(status_code=404, detail="No such note.") from no
    except rv.NotWaiting as no:
        raise HTTPException(status_code=409, detail="That note is already cleared.") from no
    except ValueError as no:
        raise HTTPException(status_code=422, detail=str(no)) from no
    return {"ok": True}


@keyed.post("/review/alias")
def review_alias(
    body: Word, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)
):
    """A word the school uses for a catalogue item: the model is shown it beside the item from the next note on."""
    staff = _mine(conn, body, tenant_id)
    try:
        rv.approve_alias(conn, UUID(str(tenant_id)), body.word, body.material_code, staff)
    except ml.NotInCatalogue as no:
        raise HTTPException(status_code=422, detail="Choose an item from the catalogue.") from no
    except rv.AliasTaken as no:
        raise HTTPException(status_code=409, detail="That word already means a different item.") from no
    except ValueError as no:
        raise HTTPException(status_code=422, detail=str(no)) from no
    return {"ok": True}


@keyed.post("/review/convert")
def review_convert(
    body: Unit, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)
):
    """A unit that converts to the item's own ("dozen" is 12 piece): from the next note on, code converts with it."""
    staff = _mine(conn, body, tenant_id)
    try:
        rv.approve_conversion(conn, UUID(str(tenant_id)), body.material_code, body.unit, body.factor, staff)
    except ml.NotInCatalogue as no:
        raise HTTPException(status_code=422, detail="Choose an item from the catalogue.") from no
    except ValueError as no:
        raise HTTPException(status_code=422, detail=str(no)) from no
    return {"ok": True}


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
    staff = staff_of(conn, Who(actor=actor))
    holds(conn, staff, list_class(conn, the_list))
    typed = text if isinstance(text, str) else ""
    photo = None
    if upload is not None and not isinstance(upload, str):
        try:
            photo = mi.prepare_upload(conn, await upload.read())
        except mi.TooBig as no:
            raise HTTPException(
                status_code=422, detail="That picture is too big. Take it again, or send a smaller one."
            ) from no
        except mi.Unreadable as no:
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
