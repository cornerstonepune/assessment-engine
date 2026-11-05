"""The K2 screens' read calls (task M1-03): one call, one answer. Only wiring, as `voice.py` is: what is asked and how
it is worked out is `w3_read/k2_reads.py`. The site calls with the engine's key and the signed-in educator's email as
`actor`; every call refuses while `voice.screens_enabled` is off, as the voice data it reads does. The answers are
models, so their schema (in /openapi.json) shows every field a screen can be given: no name, no "not willing", no
internal label."""

from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from engine.api.deps import get_conn, require_engine_key
from engine.w2_print import educator_gate
from engine.w3_read import k2_picture_reads, k2_reads, voice_intake, voice_store

router = APIRouter(dependencies=[Depends(require_engine_key)])


class Who(BaseModel):
    actor: str


class NoteRow(BaseModel):
    note_id: str
    activity: str | None
    activity_name: str | None
    received_at: str
    age_hours: int
    state: str


class Group(BaseModel):
    count: int
    rows: list[NoteRow]


class Groups(BaseModel):
    to_confirm: Group
    fix_this: Group
    left_unconfirmed: Group
    being_read: Group


class Todo(BaseModel):
    groups: Groups


class CoordinatorRow(NoteRow):
    # a class, by its grade and section; never a person
    class_: str = Field(alias="class")


class Counts(BaseModel):
    late: int
    unplanned: int | None
    unplanned_why: str
    children_without_notes: int
    class_days_without_notes: int


class Coordinator(BaseModel):
    rows: list[CoordinatorRow]
    counts: Counts


class Class(Who):
    class_id: str


class Child(Class):
    roll_no: str


class Cell(BaseModel):
    state: str
    words: str
    colour: str
    level: int | None
    last_seen: str


class Skill(BaseModel):
    code: str
    name: str


class PictureRow(BaseModel):
    roll_no: str
    cells: dict[str, Cell]  # by skill code; no cell where the child was not seen


class ClassRef(BaseModel):
    id: str
    grade: str
    section: str


class Classes(BaseModel):
    classes: list[ClassRef]


class Picture(BaseModel):
    class_: str = Field(alias="class")
    skills: list[Skill]
    children: list[PictureRow]


class PageSkill(Skill, Cell):
    sentence: str | None
    sentence_note: str | None  # why there is none, when there is one to withhold


class Month(BaseModel):
    month: str
    level: int
    days: int


class Growth(BaseModel):
    skill: Skill
    first_seen: str
    last_seen: str
    by_month: list[Month]
    trend: Literal["up", "steady", "down", "too_few"]  # a trend, never a score


class Because(BaseModel):
    before: Skill
    strength: str


class ReadyNext(BaseModel):
    skill: Skill
    because: list[Because]


class Page(BaseModel):
    class_: str = Field(alias="class")
    roll_no: str
    skills: list[PageSkill]
    growth: list[Growth]
    ready_next: list[ReadyNext]


def _on(conn) -> None:
    if not voice_intake.enabled(conn):
        raise HTTPException(status_code=403, detail="Voice notes are not switched on.")


def _on_or_preview(conn, actor: str) -> None:
    """The picture and a child's page answer the staff preview while the switch is off (D-076, `educator_gate`): a member of
    staff whose open grant is in a role `educator.preview_roles` names. A preview only looks, and both calls only read."""
    if voice_intake.enabled(conn):
        return
    try:
        staff = voice_intake.staff_of(conn, actor)
    except voice_store.Refused:
        staff = None
    if staff is None or not educator_gate.previews(conn, staff):
        raise HTTPException(status_code=403, detail="Voice notes are not switched on.")


def _refused(no: voice_store.Refused) -> HTTPException:
    return HTTPException(status_code=no.status, detail=str(no))


@router.post("/k2/todo", response_model=Todo)
def todo(body: Who, conn=Depends(get_conn, scope="function")):
    _on(conn)
    try:
        return k2_reads.todo(conn, body.actor)
    except voice_store.Refused as no:
        raise _refused(no) from no


@router.post("/k2/coordinator", response_model=Coordinator)
def coordinator(body: Who, conn=Depends(get_conn, scope="function")):
    _on(conn)
    try:
        return k2_reads.coordinator(conn, body.actor)
    except voice_store.Refused as no:
        raise _refused(no) from no


@router.post("/k2/classes", response_model=Classes)
def classes(body: Who, conn=Depends(get_conn, scope="function")):
    """Her classes; the staff preview, who holds none, is offered every class whose timetable is in force today."""
    _on_or_preview(conn, body.actor)
    try:
        staff = voice_intake.staff_of(conn, body.actor)
    except voice_store.Refused as no:
        raise _refused(no) from no
    every = (
        educator_gate.timetabled_classes(conn, educator_gate.school_today(conn))
        if educator_gate.previews(conn, staff)
        else []
    )
    return {"classes": k2_picture_reads.classes(conn, staff, every)}


@router.post("/k2/picture", response_model=Picture)
def picture(body: Class, conn=Depends(get_conn, scope="function")):
    _on_or_preview(conn, body.actor)
    try:
        return k2_picture_reads.class_picture(conn, body.actor, body.class_id)
    except voice_store.Refused as no:
        raise _refused(no) from no


@router.post("/k2/child", response_model=Page)
def child(body: Child, conn=Depends(get_conn, scope="function")):
    _on_or_preview(conn, body.actor)
    try:
        return k2_picture_reads.child_page(conn, body.actor, body.class_id, body.roll_no)
    except voice_store.Refused as no:
        raise _refused(no) from no
