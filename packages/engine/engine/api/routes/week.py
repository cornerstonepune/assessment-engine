"""W2/N5–N7 — the week's papers over HTTP: prescribe, assemble, render, and one printed page.

Thin, like every route here. The decisions — which difficulty a child gets, which questions are
still unseen, how many spares, who could not be filled — all live in `prescribe` and `assemble`,
which is what the CLI and the tests call too. F2 forwards answers; it never computes one.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from fastapi.responses import FileResponse

from engine.api.deps import get_conn, get_tenant_id, require_engine_key
from engine.api.idempotency import derive_key, run_idempotent
from engine.api.models import (
    WeekApproveRequest,
    WeekApproveResponse,
    WeekAssembleRequest,
    WeekAssembleResponse,
    WeekPrescribeRequest,
    WeekPrescribeResponse,
    WeekRenderRequest,
    WeekRenderResponse,
)
from engine.core import db
from engine.w2_print import assemble, pack, prescribe
from engine.w3_read import legacy

router = APIRouter(dependencies=[Depends(require_engine_key)])


def _short(built):
    """The children who could not be given a paper, as JSON — ids and counts only (rule 6), the
    child's id as text: the result is stored for replay, and a UUID there failed the whole assembly."""
    return [{**s, "child_id": str(s["child_id"])} for s in built["short"]]


@router.post("/week/prescribe", response_model=WeekPrescribeResponse)
def prescribe_class(
    body: WeekPrescribeRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    conn=Depends(get_conn),
    tenant_id: str = Depends(get_tenant_id),
):
    """One prescription per child in the section, each carrying the rule that chose it."""
    key = idempotency_key or derive_key(body.model_dump())

    def run():
        rows = prescribe.for_class(conn, body.section, body.week, body.skill_set, body.kind)
        return {
            "section": body.section,
            "week": body.week,
            "kind": body.kind,
            "prescribed": len(rows),
            "by_rule": {r: sum(1 for x in rows if x["rule"] == r) for r in {x["rule"] for x in rows}},
            "by_difficulty": {
                d: sum(1 for x in rows if x["difficulty"] == d) for d in {x["difficulty"] for x in rows}
            },
        }

    result, already = run_idempotent(conn, tenant_id, "week_prescribe", key, body.model_dump(), run)
    return {**result, "already": already}


@router.post("/week/assemble", response_model=WeekAssembleResponse)
def assemble_week(
    body: WeekAssembleRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    conn=Depends(get_conn),
    tenant_id: str = Depends(get_tenant_id),
):
    """Every child's own paper plus the spares. A child the bank cannot dress is returned by name,
    never given a short paper — which is the one thing F2 must be able to tell a person about."""
    key = idempotency_key or derive_key(body.model_dump())

    def run():
        built = assemble.for_week(conn, body.section, body.week, body.kind)
        return {
            "section": body.section,
            "week": body.week,
            "kind": body.kind,
            "sheets": len(built["sheets"]),
            "spares": len(built["spares"]),
            "short": _short(built),
            "qr_codes": [s["qr"] for s in built["sheets"] + built["spares"]],
        }

    result, already = run_idempotent(conn, tenant_id, "week_assemble", key, body.model_dump(), run)
    return {**result, "already": already}


@router.post("/week/render", response_model=WeekRenderResponse)
def render_week(
    body: WeekRenderRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    conn=Depends(get_conn),
    tenant_id: str = Depends(get_tenant_id),
):
    """The printable pack, in roll order, one key per sheet. Names are read through the logging
    accessor and printed on the child's own page only (`roster.names`)."""
    key = idempotency_key or derive_key(body.model_dump())

    def run():
        built = assemble.made(conn, body.section, body.week, body.kind)
        out = assemble.render(conn, built, db.REPO_ROOT / body.out, body.week, body.actor, body.kind)
        return {
            "section": body.section,
            "week": body.week,
            "kind": body.kind,
            "pack_path": str(out.get("pack") or ""),
            "pages": int(out.get("pages") or 0),
            "sheets": len(built["sheets"]),
            "spares": len(built["spares"]),
            "short": _short(built),
        }

    result, already = run_idempotent(conn, tenant_id, "week_render", key, body.model_dump(), run)
    return {**result, "already": already}


@router.post("/week/approve", response_model=WeekApproveResponse)
def approve_week(
    body: WeekApproveRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    conn=Depends(get_conn),
    tenant_id: str = Depends(get_tenant_id),
):
    """The human gate, over HTTP so the app and a flow use one implementation. Approving is safe to repeat —
    only sheets still `new` move — so a call without an Idempotency-Key simply runs. Keyed on its body, as the
    other routes are, a teacher approving a pack remade since an earlier approval was handed that earlier answer
    and nothing moved; a key sent by a retrying flow still returns the first answer."""

    def run():
        return pack.approve(conn, body.section, body.week, body.kind, body.by)

    if not idempotency_key:
        return {**run(), "already": False}
    result, already = run_idempotent(conn, tenant_id, "week_approve", idempotency_key, body.model_dump(), run)
    return {**result, "already": already}


@router.get("/week/{section}/{week}/{kind}/pack.pdf")
def pack_pdf(section: str, week: str, kind: str, conn=Depends(get_conn)) -> FileResponse:
    """The approved pack as one PDF for the Papers page to hand on. Refused, in words, while it waits."""
    try:
        out = pack.pdf(conn, section, week, kind, db.REPO_ROOT / "data" / "packs")
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except (PermissionError, FileNotFoundError) as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    return FileResponse(out, media_type="application/pdf", filename=out.name)


@router.get("/sheet/{qr}/page/{page_no}.jpg")
def sheet_page(qr: str, page_no: int, conn=Depends(get_conn)) -> Response:
    """One page of a paper exactly as it was printed — the QR in its corner — for the paper view.

    Served from the PDF the render wrote, like a scan is served from the school's disk: a person
    sees the page itself, not a second drawing of it that could disagree with what was handed out.
    """
    row = conn.execute("select pdf_path from sheet_instance where qr_code = %s", (qr,)).fetchone()
    if not row or not row["pdf_path"]:
        raise HTTPException(status_code=404, detail="this paper has not been rendered")
    path = Path(row["pdf_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"the paper is not on this machine: {path}")
    return Response(content=legacy.page_crop(path, page_no), media_type="image/jpeg")
