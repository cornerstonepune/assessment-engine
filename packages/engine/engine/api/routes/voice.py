"""K2 voice notes (task M1-01): the routes the educator's Record and Confirm pages reach. Only wiring: what is kept,
read, found and written is `voice_intake`'s and `voice_confirm`'s. The recording comes from her browser with the token
the site signed for her (`require_upload_token`, as a scan does); everything else from the site with the engine's key
and her email as `actor`, whose staff id the engine finds (`public.staff_of_email`). Every route refuses while
`voice.screens_enabled` is off."""

import datetime as dt
import mimetypes
import os
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from engine.adapters import speech
from engine.api.deps import get_conn, require_engine_key, require_upload_token
from engine.core import db
from engine.w3_read import voice_confirm, voice_intake, voice_note, voice_store

Section = Literal["above", "below", "not_willing", "absent"]


class Who(BaseModel):
    actor: str


class NoteRef(Who):
    note_id: str


class ClassDay(Who):
    class_id: str
    day: dt.date | None = None


class Confirm(Who):
    activity: str
    level: int = Field(ge=0, le=3)
    lists: dict[Section, list[str]] = Field(default_factory=dict)
    rest: bool = False
    day: dt.date | None = None


class NoteConfirm(Confirm):
    note_id: str


class FormSave(Confirm):
    class_id: str


class Correction(Who):
    observation_id: str
    outcome: Literal["above", "as_expected", "below", "not_willing", "absent"]
    reason: str = Field(min_length=1, max_length=300)


router = APIRouter()
keyed = APIRouter(dependencies=[Depends(require_engine_key)])


def _on(conn) -> None:
    if not voice_intake.enabled(conn):
        raise HTTPException(status_code=403, detail="Voice notes are not switched on.")


def _recording(conn) -> None:
    """A recording is taken or given only with both switches on (D-065): the screens, and recording itself."""
    _on(conn)
    if not voice_intake.recording_enabled(conn):
        raise HTTPException(status_code=403, detail="Recording is not switched on.")


def _refused(no: voice_store.Refused) -> HTTPException:
    return HTTPException(status_code=no.status, detail=str(no))


def _transcribe(note_id: str) -> None:
    """After the answer: the words, when the service is set up; otherwise the note waits as received."""
    if not os.environ.get("SARVAM_API_KEY"):
        return
    with db.connect() as conn:
        try:
            voice_intake.transcribe(conn, note_id)
        except speech.SpeechError:
            conn.rollback()


@router.post("/voice/notes")
async def send_note(
    request: Request, background: BackgroundTasks, actor: str = Depends(require_upload_token)
):
    """One recording from her phone, kept on the private side; it is read after this answers."""
    form = await request.form(max_files=1)
    upload, class_id = form.get("file"), form.get("class_id")
    if isinstance(upload, str) or upload is None or not isinstance(class_id, str):
        raise HTTPException(status_code=422, detail="Not sent. Try again.")
    with db.connect() as conn:
        _recording(conn)
        try:
            note = voice_intake.receive(conn, actor, class_id, upload.filename or "", await upload.read())
        except voice_store.Refused as no:
            raise _refused(no) from no
    background.add_task(_transcribe, str(note["id"]))
    return {"note_id": str(note["id"]), "status": note["status"]}


@keyed.post("/voice/queue")
def queue(body: Who, conn=Depends(get_conn, scope="function")):
    _on(conn)
    try:
        staff = voice_intake.staff_of(conn, body.actor)
    except voice_store.Refused as no:
        raise _refused(no) from no
    return {
        "notes": [{k: str(v) for k, v in n.items()} for n in voice_intake.queue(conn, str(staff))],
        "classes": voice_intake.classes_of(conn, str(staff), dt.date.today()),
        "recording": voice_intake.recording_enabled(conn),
    }


def _mine(conn, body: NoteRef) -> dict:
    try:
        staff = voice_intake.staff_of(conn, body.actor)
    except voice_store.Refused as no:
        raise _refused(no) from no
    try:
        note_id = voice_intake.valid_id(body.note_id)
    except voice_store.Refused as no:
        raise _refused(no) from no
    note = conn.execute("select * from pii.educator_note where id = %s", (note_id,)).fetchone()
    if note is None or note["staff_id"] != staff:
        raise HTTPException(status_code=404, detail="This is not one of your notes.")
    return note


@keyed.post("/voice/notes/draft")
def draft(body: NoteRef, conn=Depends(get_conn, scope="function")):
    """Each draft line beside the words it came from, its numbers found in the class, and every problem."""
    _on(conn)
    note = _mine(conn, body)
    found = voice_intake.resolve(conn, note)
    lines = [
        {"section": x.section, "words": x.words, "numbers": list(x.numbers), "text": x.text, "said": x.said,
         "problems": list(x.problems), "notes": list(x.notes)}
        for x in found.draft.lines
    ]  # fmt: skip
    return {
        "note_id": str(note["id"]), "status": note["status"], "received_at": note["received_at"].isoformat(),
        "kind": found.draft.kind, "taught_on": found.taught_on.isoformat(), "activity": found.activity,
        "level": found.draft.expected_level(voice_note.template()), "day_problems": list(found.draft.day_problems),
        "heard": bool((note["transcript"] or "").strip()),
        "lines": lines, "problems": [*found.draft.problems, *found.problems], "children": found.children,
        "enrolled": sorted(found.enrolled, key=lambda r: (len(r), r)), "count": found.count_line(),
        "blocked": found.blocked,
    }  # fmt: skip


@keyed.post("/voice/notes/audio")
def audio(body: NoteRef, conn=Depends(get_conn, scope="function")):
    """Her own recording, to play beside her note; nobody else's."""
    _recording(conn)
    key = _mine(conn, body)["audio_key"]
    try:
        data = voice_store.read(key)
    except voice_store.Refused as no:
        raise _refused(no) from no
    return Response(content=data, media_type=mimetypes.guess_type(key)[0] or "application/octet-stream")


@keyed.post("/voice/class")
def class_roll(body: ClassDay, conn=Depends(get_conn, scope="function")):
    """The class's roll numbers enrolled that day, for the grid she picks a child from."""
    _on(conn)
    day = body.day or dt.date.today()
    return {"rolls": sorted(voice_intake.enrolled(conn, body.class_id, day), key=lambda r: (len(r), r))}


def _final(body: Confirm) -> voice_confirm.Confirmed:
    return voice_confirm.Confirmed(
        body.activity, body.level, {k: list(v) for k, v in body.lists.items()}, body.rest, body.day
    )


@keyed.post("/voice/notes/confirm")
def confirm(body: NoteConfirm, conn=Depends(get_conn, scope="function")):
    _on(conn)
    try:
        return {
            "confirmation_id": str(voice_confirm.confirm_note(conn, body.note_id, body.actor, _final(body)))
        }
    except voice_store.Refused as no:
        raise _refused(no) from no


@keyed.post("/voice/form")
def form_save(body: FormSave, conn=Depends(get_conn, scope="function")):
    _on(conn)
    try:
        return {
            "confirmation_id": str(voice_confirm.save_form(conn, body.actor, body.class_id, _final(body)))
        }
    except voice_store.Refused as no:
        raise _refused(no) from no


@keyed.post("/voice/observations/correct")
def correct(body: Correction, conn=Depends(get_conn, scope="function")):
    _on(conn)
    try:
        new = voice_confirm.correct(conn, body.observation_id, body.actor, body.outcome, body.reason)
    except voice_store.Refused as no:
        raise _refused(no) from no
    return {"observation_id": str(new)}
