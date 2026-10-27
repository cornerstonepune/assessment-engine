"""A child's paper reviewed, a question removed or added, and the paper approved, over HTTP
(goals/paper_review_add_remove.yaml). Thin: the rules are `w2_print.edit_paper`."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from engine.api.deps import get_conn, require_engine_key
from engine.w2_print import edit_paper

router = APIRouter(dependencies=[Depends(require_engine_key)])


class Edit(BaseModel):
    by: str
    item_id: str = Field(pattern=r"^[0-9a-f-]{36}$")
    at: int | None = None  # where an added question goes, 1 the first; the end when not said


class By(BaseModel):
    by: str


def _said(run):
    """The edit's answer, or its refusal in words: 404 no such paper or question, 423 a paper that may not change
    (printed, replaced, a library worksheet), 409 an edit past a limit."""
    try:
        return run()
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except PermissionError as e:
        raise HTTPException(status_code=423, detail=str(e)) from None
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.get("/paper/{qr}/review")
def paper_review(qr: str, conn=Depends(get_conn, scope="function")) -> dict:
    """The paper's questions in order, what it covers, its state and whether it may change. Writes nothing."""
    return _said(lambda: edit_paper.review(conn, qr))


@router.get("/paper/{qr}/bank")
def paper_bank(
    qr: str,
    topic: str | None = None,
    skill: str | None = None,
    level: str | None = None,
    kind: str | None = None,
    conn=Depends(get_conn, scope="function"),
) -> dict:
    """The add dropdowns' options, each narrowing the next. Writes nothing."""
    return _said(lambda: edit_paper.bank(conn, qr, topic, skill, level, kind))


@router.post("/paper/{qr}/remove")
def paper_remove(qr: str, body: Edit, conn=Depends(get_conn, scope="function")) -> dict:
    return _said(lambda: edit_paper.remove(conn, qr, body.item_id, body.by))


@router.post("/paper/{qr}/add")
def paper_add(qr: str, body: Edit, conn=Depends(get_conn, scope="function")) -> dict:
    return _said(lambda: edit_paper.add(conn, qr, body.item_id, body.by, body.at))


@router.post("/paper/{qr}/approve")
def paper_approve(qr: str, body: By, conn=Depends(get_conn, scope="function")) -> dict:
    return _said(lambda: edit_paper.approve(conn, qr, body.by))
