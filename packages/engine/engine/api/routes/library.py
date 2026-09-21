"""Step 3 — a library worksheet as it prints (ADR 0026). Thin: rendering is `library.pdf`, which
draws the worksheet with the same renderer as a child's paper the first time it is asked for."""

import re

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from engine import library
from engine.api.deps import get_conn, require_engine_key

router = APIRouter(dependencies=[Depends(require_engine_key)])

# R5-H07, M1-E12, X2-A18: the only shape a worksheet code has, so nothing else reaches the disk.
CODE = re.compile(r"^[RMX]\d{1,2}-[EMHA]\d{2,3}$")


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
