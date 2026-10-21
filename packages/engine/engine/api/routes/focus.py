"""A child's own paper: the home paper the graph proposes, or one a teacher asks for (Make papers). Thin: the
plan and the paper are `w2_print.focus_paper`; the website reads a plan here and asks for the paper here."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, Field

from engine.api.deps import get_conn, require_engine_key
from engine.w2_print import focus_paper, seen

# "different questions" (goals/preview-before-print.yaml): the same paper drawn again; 0 is the first draw
Draw = Field(0, ge=0)

router = APIRouter(dependencies=[Depends(require_engine_key)])


class MakeFocus(BaseModel):
    week: str
    by: str
    replaces: str | None = None  # the week's home assessment the educator saw, if one was made
    draw: int = Draw
    seen: str  # the questions the educator saw (`seen.of`): a paper prints only as it was shown


class Area(BaseModel):
    skill_set: str
    level: str
    n: int


class Ask(BaseModel):
    week: str
    areas: list[Area]
    draw: int = Draw


class SeeAsked(Ask):
    by: str


class MakeAsked(SeeAsked):
    seen: str


def _child(child_id: str) -> str:
    try:
        return str(uuid.UUID(child_id))
    except ValueError:
        raise HTTPException(status_code=404, detail="no such child") from None


@router.get("/child/{child_id}/focus")
def focus_plan(
    child_id: str, week: str, draw: int = Query(0, ge=0), conn=Depends(get_conn, scope="function")
) -> dict:
    """The areas the child lags in, why, and the questions their next paper would hold (`draw`: drawn again), the
    code that names them (`seen`), and the paper already approved this week if there is one. Writes nothing."""
    child = _child(child_id)
    p = focus_paper.plan(conn, child, week, draw=draw)
    return {**p, "seen": seen.of([p]), "approved": focus_paper.approved(conn, child, week)}


def _made(make) -> dict:
    try:
        made = make()
    except seen.Changed as e:  # the paper shown is no longer what would print: shown again, never printed
        raise HTTPException(status_code=412, detail=str(e)) from None
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    return {"qr": made["qr"], "pages": made["pages"], "questions": made["questions"]}


@router.post("/child/{child_id}/focus")
def focus_make(child_id: str, body: MakeFocus, conn=Depends(get_conn, scope="function")) -> dict:
    """`by` approves the plan they saw: it prints as the child's paper, with its QR, in their name; made again the
    same week, the newest is the week's."""
    child, b = _child(child_id), body
    return _made(lambda: focus_paper.make(conn, child, b.week, b.by, None, b.replaces, b.draw, b.seen))


def _pdf(see) -> Response:
    try:
        pdf = see()
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    return Response(
        pdf, media_type="application/pdf", headers={"content-disposition": "inline; filename=paper.pdf"}
    )


@router.get("/child/{child_id}/focus/paper.pdf")
def focus_see(
    child_id: str, week: str, by: str, draw: int = Query(0, ge=0), conn=Depends(get_conn, scope="function")
) -> Response:
    """The home paper the graph proposes, as it will print, before anyone approves it. Writes nothing."""
    child = _child(child_id)
    return _pdf(lambda: focus_paper.preview(conn, child, week, by, draw=draw))


def _ask(body: Ask) -> list[dict]:
    if not body.areas:
        raise HTTPException(status_code=422, detail="ask for at least one skill")
    return [a.model_dump() for a in body.areas]


@router.post("/child/{child_id}/paper/plan")
def paper_plan(child_id: str, body: Ask, conn=Depends(get_conn, scope="function")) -> dict:
    """What a paper a teacher asks for would hold, question by question, and the code that names them (`seen`).
    Writes nothing; refused in words when the bank cannot fill it."""
    try:
        p = focus_paper.plan(conn, _child(child_id), body.week, _ask(body), draw=body.draw)
        return {**p, "seen": seen.of([p])}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post("/child/{child_id}/paper")
def paper_make(child_id: str, body: MakeAsked, conn=Depends(get_conn, scope="function")) -> dict:
    """`by` approves the paper they asked for and saw: it prints for the child, with its QR, in their name."""
    child, ask, b = _child(child_id), _ask(body), body
    return _made(lambda: focus_paper.make(conn, child, b.week, b.by, ask, draw=b.draw, seen=b.seen))


@router.post("/child/{child_id}/paper/plan.pdf")
def paper_see(child_id: str, body: SeeAsked, conn=Depends(get_conn, scope="function")) -> Response:
    """The paper a teacher asks for, as it will print, before they approve it. Writes nothing."""
    child, ask = _child(child_id), _ask(body)
    return _pdf(lambda: focus_paper.preview(conn, child, body.week, body.by, ask, body.draw))
