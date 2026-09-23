"""A child's next paper chosen from their own graph (goal s11-focus-paper). Thin: the plan and the paper
are `w2_print.focus_paper`; the Growth page reads the plan here and asks for the paper here."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from engine.api.deps import get_conn, require_engine_key
from engine.w2_print import focus_paper

router = APIRouter(dependencies=[Depends(require_engine_key)])


class MakeFocus(BaseModel):
    week: str
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
