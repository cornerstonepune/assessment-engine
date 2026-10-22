"""N8 by upload (goals/n8-upload-on-marking.yaml, ADR 0092): an educator puts a scan in on Marking and the browser sends
it here itself — a Vercel function takes at most 4.5 MB, and a class's scan is tens. Not behind `require_engine_key`:
the browser holds a token the site signed for that person (`require_upload_token`), never the engine's key. Only
wiring: what is taken and refused is `inbox.take`'s, and the reading is the one a Drive link starts (`inbox.read`)."""

import pymupdf
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from engine.api import deps
from engine.api.deps import require_upload_token
from engine.api.models import UploadResponse
from engine.w3_read import inbox

router = APIRouter()
_ROOM = 1024 * 1024  # the form's own bytes around the files: boundaries, names


@router.post("/read/upload", response_model=UploadResponse)
async def read_upload(
    request: Request,
    background: BackgroundTasks,
    actor: str = Depends(require_upload_token),
):
    """One upload — a PDF, or the photos of one paper — saved in the inbox and read after this answers, as a Drive
    link's file is. A file too large is refused before it is taken in, where the browser says how large it is."""
    if int(request.headers.get("content-length") or 0) > inbox.MOST + _ROOM:
        raise HTTPException(
            status_code=413,
            detail=f"that is larger than any scan of a class ({inbox.MOST // 2**20} MB at most)",
        )
    form = await request.form(max_files=200)
    files = [(f.filename or "scan", await f.read()) for f in form.getlist("file") if not isinstance(f, str)]
    try:
        path = await run_in_threadpool(inbox.take, files)
    except inbox.Refused as no:
        raise HTTPException(status_code=no.status, detail=str(no)) from no
    finally:
        await form.close()
    with pymupdf.open(path) as doc:
        pages = len(doc)
    run_id = inbox.start(await run_in_threadpool(deps.tenant_now), path, actor, pages=pages)
    background.add_task(inbox.read, run_id, path, actor)
    return {"run_id": run_id, "pages": pages, "file": path.name}
