"""A child's own paper: the home paper the graph proposes, or one a teacher asks for (Make papers). Thin: the
plan and the paper are `w2_print.focus_paper`; the website reads a plan here and asks for the paper here."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel

from engine.api.deps import get_conn, require_engine_key
from engine.w2_print import focus_paper

router = APIRouter(dependencies=[Depends(require_engine_key)])


class MakeFocus(BaseModel):
    week: str
    by: str


class Area(BaseModel):
    skill_set: str
    level: str
    n: int


class Ask(BaseModel):
    week: str
    areas: list[Area]


class MakeAsked(Ask):
    by: str


def _child(child_id: str) -> str:
    try:
        return str(uuid.UUID(child_id))
    except ValueError:
        raise HTTPException(status_code=404, detail="no such child") from None


@router.get("/child/{child_id}/focus")
def focus_plan(child_id: str, week: str, conn=Depends(get_conn)) -> dict:
    """The areas the child lags in, why, and the questions their next paper would hold, and the paper already
    approved this week if there is one. Writes nothing."""
    child = _child(child_id)
    return {**focus_paper.plan(conn, child, week), "approved": focus_paper.approved(conn, child, week)}


@router.post("/child/{child_id}/focus")
def focus_make(child_id: str, body: MakeFocus, conn=Depends(get_conn)) -> dict:
    """`by` approves that plan: it prints as the child's paper, with its QR, in their name; once a week."""
    try:
        made = focus_paper.make(conn, _child(child_id), body.week, body.by)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    return {"qr": made["qr"], "pages": made["pages"], "questions": made["questions"]}


def _pdf(see) -> Response:
    try:
        pdf = see()
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    return Response(
        pdf, media_type="application/pdf", headers={"content-disposition": "inline; filename=paper.pdf"}
    )


@router.get("/child/{child_id}/focus/paper.pdf")
def focus_see(child_id: str, week: str, by: str, conn=Depends(get_conn)) -> Response:
    """The home paper the graph proposes, as it will print, before anyone approves it. Writes nothing."""
    child = _child(child_id)
    return _pdf(lambda: focus_paper.preview(conn, child, week, by))


def _ask(body: Ask) -> list[dict]:
    if not body.areas:
        raise HTTPException(status_code=422, detail="ask for at least one skill")
    return [a.model_dump() for a in body.areas]


@router.post("/child/{child_id}/paper/plan")
def paper_plan(child_id: str, body: Ask, conn=Depends(get_conn)) -> dict:
    """What a paper a teacher asks for would hold, question by question. Writes nothing; refused in words when
    the bank cannot fill it."""
    try:
        return focus_paper.plan(conn, _child(child_id), body.week, _ask(body))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post("/child/{child_id}/paper")
def paper_make(child_id: str, body: MakeAsked, conn=Depends(get_conn)) -> dict:
    """`by` approves the paper they asked for: it prints for the child, with its QR, in their name."""
    try:
        made = focus_paper.make(conn, _child(child_id), body.week, body.by, _ask(body))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    return {"qr": made["qr"], "pages": made["pages"], "questions": made["questions"]}


@router.post("/child/{child_id}/paper/plan.pdf")
def paper_see(child_id: str, body: MakeAsked, conn=Depends(get_conn)) -> Response:
    """The paper a teacher asks for, as it will print, before they approve it. Writes nothing."""
    child, ask = _child(child_id), _ask(body)
    return _pdf(lambda: focus_paper.preview(conn, child, body.week, body.by, ask))
