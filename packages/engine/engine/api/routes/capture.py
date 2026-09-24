"""N3/N9, over HTTP: ingest a scan, mark it again if the rule changed, commit a child's confirmed
answers as evidence. Every route is a thin idempotent wrapper over the same functions the CLI
calls (`engine/legacy.py`) — no logic lives here, only request/response shaping (rule 3, extended
to this HTTP layer: it orchestrates, it does not decide)."""

from pathlib import Path

import pymupdf
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Response

from engine.api.deps import get_conn, get_tenant_id, require_engine_key
from engine.api.idempotency import derive_key, run_idempotent
from engine.api.models import (
    CommitRequest,
    CommitResponse,
    CorrectRequest,
    CorrectResponse,
    IngestRequest,
    IngestResponse,
    MarkRequest,
    MarkResponse,
    ReadFileRequest,
    ReadFileResponse,
)
from engine.w3_read import inbox, legacy, marking

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
            conn,
            body.path,
            body.paper_code,
            body.child_id,
            body.actor,
            pages=body.pages,
            masks=body.masks,
            narrative=body.narrative,
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
        conn,
        tenant_id,
        "mark",
        key,
        body.model_dump(),
        lambda: {"changed": marking.remark(conn, body.child_id)},
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
        conn,
        tenant_id,
        "commit",
        key,
        body.model_dump(),
        lambda: {"confirmed": marking.confirm(conn, body.child_id, body.by)},
    )
    return {**result, "already": already}


@router.post("/capture/correct", response_model=CorrectResponse)
def correct(body: CorrectRequest, conn=Depends(get_conn)) -> dict:
    """A person says what a child actually wrote, and the answer is marked again from it.

    Not idempotency-wrapped: a second correction of the same answer is a SECOND fact, not a repeat
    of the first — a teacher who looks again and changes their mind must leave both rows behind
    (rule 4). The append-only table is what makes that safe.
    """
    return marking.correct(conn, body.result_id, body.human_read, body.by)


@router.get("/capture/{capture_id}/page/{page_no}.jpg")
def capture_page(capture_id: str, page_no: int, box: str = "", conn=Depends(get_conn)) -> Response:
    """The photograph a reading came from — the whole page, or the patch one answer sits in.

    The approval screen's whole reason for existing: a teacher confirms what a child wrote by
    looking at what the child wrote, not by trusting a row. The scan itself never enters git or the
    database (rule 6) — it stays on the school's disk and is served from there, by the one process
    that already knows how to open it.
    """
    row = conn.execute("select path from capture where id = %s", (capture_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="no such capture")
    path = Path(row["path"]).expanduser()
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"the scan is not on this machine: {row['path']}")
    try:
        want = [float(v) for v in box.split(",")] if box else None
    except ValueError:
        raise HTTPException(status_code=400, detail="box must be left,top,right,bottom") from None
    if want is not None and len(want) != 4:
        raise HTTPException(status_code=400, detail="box must be left,top,right,bottom")
    return Response(content=legacy.page_crop(path, page_no, want), media_type="image/jpeg")


@router.post("/read/file", response_model=ReadFileResponse)
def read_file(
    body: ReadFileRequest,
    background: BackgroundTasks,
    conn=Depends(get_conn),
    tenant_id: str = Depends(get_tenant_id),
):
    """N8: a scan arrives as a Drive link. The file is fetched into the engine's inbox now, and read after this
    answers (`inbox.read`, its own connection): sorting sixteen photographed pages and reading every box on them
    takes minutes, and the caller — the site, or the n8n Drive flow — waits seconds. Whose the answers are is the
    code on each page's; a copy printed bare is reported, never guessed."""
    try:
        path = inbox.fetch(body.url)
    except ValueError as why:
        raise HTTPException(status_code=400, detail=str(why)) from why
    with pymupdf.open(path) as doc:
        pages = len(doc)
    run_id = inbox.start(conn, tenant_id, path, body.actor)
    background.add_task(inbox.read, run_id, path, body.actor)
    return {"run_id": run_id, "pages": pages}
