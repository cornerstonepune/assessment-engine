"""The maker over HTTP (goal m3-the-maker): the website asks what the papers would hold, then for them in an
educator's name, then for them as one PDF. Thin: the papers are `w2_print.maker`."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from engine.api.deps import get_conn, get_tenant_id, require_engine_key
from engine.api.idempotency import derive_key, run_idempotent
from engine.api.routes.focus import Area
from engine.w2_print import maker

router = APIRouter(dependencies=[Depends(require_engine_key)])


class Change(BaseModel):
    """What an educator put in place of a child's own next step; as long as a home paper unless `n` says."""

    skill_set: str
    level: str
    n: int | None = None


class Batch(BaseModel):
    section: str
    week: str
    kind: str
    way: str
    children: list[uuid.UUID]
    areas: list[Area] = []
    changed: dict[uuid.UUID, list[Change]] = {}


class MakeBatch(Batch):
    by: str
    once: str  # the form's own token: the same form sent twice makes its papers once


def _args(b: Batch) -> tuple:
    ask = [a.model_dump() for a in b.areas] or None
    changed = {str(k): [a.model_dump() for a in v] for k, v in b.changed.items()} or None
    return b.section, [str(c) for c in b.children], b.week, b.kind, b.way, ask, changed


@router.post("/papers/plan")
def papers_plan(body: Batch, conn=Depends(get_conn)) -> dict:
    """Each picked child's paper, question by question, and each child whose paper cannot be made, with why.
    Writes nothing."""
    try:
        return maker.plan(conn, *_args(body))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post("/papers/make")
def papers_make(body: MakeBatch, conn=Depends(get_conn), tenant_id: str = Depends(get_tenant_id)) -> dict:
    """`by` approves the papers the plan showed, and each prints with its own code; refused whole, naming each child
    whose paper cannot be made."""
    request = body.model_dump(mode="json")
    section, children, week, kind, way, ask, changed = _args(body)

    def run():
        return maker.make(conn, section, children, week, kind, way, body.by, ask, changed)

    try:
        result, already = run_idempotent(conn, tenant_id, "papers_make", derive_key(request), request, run)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    return {**result, "already": already}


@router.get("/papers/pack.pdf")
def papers_pdf(qr: list[str] = Query(...), conn=Depends(get_conn)) -> Response:
    """The papers as one PDF, in class and roll order, exactly as each was rendered. Writes nothing."""
    try:
        pdf = maker.pdf(conn, qr)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    return Response(
        pdf, media_type="application/pdf", headers={"content-disposition": "inline; filename=papers.pdf"}
    )
