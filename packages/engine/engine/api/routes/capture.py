"""N3/N9, over HTTP: ingest a scan, mark it again if the rule changed, commit a child's confirmed
answers as evidence. Every route is a thin idempotent wrapper over the same functions the CLI
calls (`engine/legacy.py`) — no logic lives here, only request/response shaping (rule 3, extended
to this HTTP layer: it orchestrates, it does not decide)."""
from fastapi import APIRouter, Depends, Header

from engine import legacy
from engine.api.deps import get_conn, get_tenant_id, require_engine_key
from engine.api.idempotency import derive_key, run_idempotent
from engine.api.models import (
    CommitRequest,
    CommitResponse,
    IngestRequest,
    IngestResponse,
    MarkRequest,
    MarkResponse,
)

router = APIRouter(dependencies=[Depends(require_engine_key)])


@router.post("/ingest", response_model=IngestResponse)
def ingest(
    body: IngestRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    conn=Depends(get_conn),
    tenant_id: str = Depends(get_tenant_id),
):
    key = idempotency_key or derive_key(body.model_dump())

    def run():
        summary = legacy.import_scan(
            conn, body.path, body.paper_code, body.child_id, body.actor,
            pages=body.pages, masks=body.masks, narrative=body.narrative,
        )
        return {
            "capture_id": str(summary["capture_id"]),
            "pages": summary["pages"],
            "n_results": len(summary["results"]),
            "n_unmatched": len(summary["unmatched"]),
            "n_notes": len(summary["notes"]),
        }

    result, already = run_idempotent(conn, tenant_id, "ingest", key, body.model_dump(), run)
    return {**result, "already": already}


@router.post("/mark", response_model=MarkResponse)
def mark(
    body: MarkRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    conn=Depends(get_conn),
    tenant_id: str = Depends(get_tenant_id),
):
    key = idempotency_key or derive_key(body.model_dump())
    result, already = run_idempotent(
        conn, tenant_id, "mark", key, body.model_dump(),
        lambda: {"changed": legacy.remark(conn, body.child_id)},
    )
    return {**result, "already": already}


@router.post("/commit", response_model=CommitResponse)
def commit(
    body: CommitRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    conn=Depends(get_conn),
    tenant_id: str = Depends(get_tenant_id),
):
    key = idempotency_key or derive_key(body.model_dump())
    result, already = run_idempotent(
        conn, tenant_id, "commit", key, body.model_dump(),
        lambda: {"confirmed": legacy.confirm(conn, body.child_id, body.by)},
    )
    return {**result, "already": already}
