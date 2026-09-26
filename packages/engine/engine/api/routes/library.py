"""Step 3 — a library worksheet as it prints (ADR 0026). Thin: rendering is `library.pdf`, which
draws the worksheet with the same renderer as a child's paper the first time it is asked for."""

import json
import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from engine.api.deps import get_conn, require_engine_key
from engine.core import db
from engine.w2_print import handout, library

router = APIRouter(dependencies=[Depends(require_engine_key)])

# R5-H07, M1-E12, X2-A18: the only shape a worksheet code has, so nothing else reaches the disk.
CODE = re.compile(r"^[RMX]\d{1,2}-[EMHA]\d{2,3}$")
PRINTS = db.REPO_ROOT / "data" / "prints"  # gitignored: a printed copy names its child


@router.get("/worksheet/{code}.pdf")
def worksheet_pdf(code: str, conn=Depends(get_conn)) -> FileResponse:
    if not CODE.match(code):
        raise HTTPException(status_code=404, detail="no such worksheet")
    try:
        path = library.pdf(conn, code)
    except LookupError as missing:
        raise HTTPException(status_code=404, detail=str(missing)) from missing
    return FileResponse(
        path, media_type="application/pdf", filename=f"{code}.pdf", content_disposition_type="inline"
    )


@router.get("/worksheet/{code}/geometry")
def worksheet_geometry(code: str, conn=Depends(get_conn)) -> dict:
    """Where every box and working space of a worksheet prints (`<pdf>.key.json`'s geometry, no answers): what
    the box reader cuts a scan by, for whoever is improving it without the server's disk."""
    if not CODE.match(code):
        raise HTTPException(status_code=404, detail="no such worksheet")
    try:
        path = library.pdf(conn, code)
    except LookupError as missing:
        raise HTTPException(status_code=404, detail=str(missing)) from missing
    key = json.loads(path.with_suffix(".key.json").read_text(encoding="utf-8"))
    return {"code": code, "pages": key.get("pages"), "geometry": key.get("geometry", [])}


class ForChildren(BaseModel):
    children: list[str]
    week: str
    by: str


@router.post("/worksheet/{code}/for.pdf")
def worksheet_for(code: str, body: ForChildren, conn=Depends(get_conn)) -> FileResponse:
    """The worksheet printed for the children picked, one copy each with its own code, in the educator's name."""
    if not CODE.match(code) or not body.children:
        raise HTTPException(status_code=404, detail="no such worksheet, or no child picked")
    out = PRINTS / f"{code}-{body.week}-{uuid.uuid4().hex[:8]}"
    try:
        path = handout.for_children(conn, code, body.children, body.week, body.by, out)
    except LookupError as missing:
        raise HTTPException(status_code=404, detail=str(missing)) from missing
    except ValueError as refused:
        raise HTTPException(status_code=409, detail=str(refused)) from refused
    return FileResponse(
        path, media_type="application/pdf", filename=f"{code}.pdf", content_disposition_type="inline"
    )
