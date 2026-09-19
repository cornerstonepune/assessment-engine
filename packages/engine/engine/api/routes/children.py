"""Resolving a folder name to a child id — the one lookup a workflow needs before it can call
/ingest. A pure read (roster.find already logs it, like every pii read); no idempotency wrapper:
running a lookup twice writes two access_log rows, which is the honest and correct behaviour."""

from fastapi import APIRouter, Depends, HTTPException

from engine import roster
from engine.api.deps import get_conn, require_engine_key
from engine.api.models import FindChildRequest, FindChildResponse

router = APIRouter(dependencies=[Depends(require_engine_key)])


@router.post("/children/find", response_model=FindChildResponse)
def find(body: FindChildRequest, conn=Depends(get_conn)):
    try:
        child_id = roster.find(conn, body.section, body.first_name, body.actor)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    return {"child_id": child_id}
