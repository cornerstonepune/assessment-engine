"""The maker over HTTP (goal m3-the-maker): the website asks what the papers would hold, then for them in an
educator's name, then for them as one PDF. Thin: the papers are `w2_print.maker`."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel

from engine.api.deps import get_conn, get_tenant_id, require_engine_key
from engine.api.idempotency import derive_key, run_idempotent
from engine.api.routes.focus import Area, Draw
from engine.w2_print import edit_paper, maker, seen

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
    draw: int = Draw  # "different questions": every paper drawn again (goals/preview-before-print.yaml)


class MakeBatch(Batch):
    by: str
    once: str  # the form's own token: the same form sent twice makes its papers once
    seen: str  # the papers the educator saw (`seen.of`): they print only as they were shown


def _args(b: Batch) -> tuple:
    ask = [a.model_dump() for a in b.areas] or None
    changed = {str(k): [a.model_dump() for a in v] for k, v in b.changed.items()} or None
    return b.section, [str(c) for c in b.children], b.week, b.kind, b.way, ask, changed


@router.post("/papers/plan")
def papers_plan(body: Batch, conn=Depends(get_conn, scope="function")) -> dict:
    """Each picked child's paper, question by question, each child whose paper cannot be made, with why, and the
    code that names the papers shown (`seen`). Writes nothing."""
    try:
        p = maker.plan(conn, *_args(body), draw=body.draw)
        return {**p, "seen": seen.of(p["papers"])}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None


@router.post("/papers/make")
def papers_make(
    body: MakeBatch, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)
) -> dict:
    """`by` approves the papers the plan showed, and each prints with its own code; refused whole, naming each child
    whose paper cannot be made."""
    request = body.model_dump(mode="json")
    section, children, week, kind, way, ask, changed = _args(body)

    def run():
        return maker.make(
            conn, section, children, week, kind, way, body.by, ask, changed, body.draw, body.seen
        )

    try:
        result, already = run_idempotent(conn, tenant_id, "papers_make", derive_key(request), request, run)
    except seen.Changed as e:
        raise HTTPException(status_code=412, detail=str(e)) from None
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    return {**result, "already": already}


@router.get("/papers/pack.pdf")
def papers_pdf(
    qr: list[str] = Query(...), by: str = "", conn=Depends(get_conn, scope="function")
) -> Response:
    """The papers as one PDF, in class and roll order, exactly as each was rendered. It records only that their print
    was opened, by `by`: from then on a paper is printed and is not edited (`edit_paper`)."""
    try:
        pdf = maker.pdf(conn, qr)
        edit_paper.print_opened(conn, qr, by)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    return Response(
        pdf, media_type="application/pdf", headers={"content-disposition": "inline; filename=papers.pdf"}
    )
