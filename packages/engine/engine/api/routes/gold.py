"""The sheet of drafted K2 pages for people to mark, as a download (task M1-11h). Only wiring: the sheet is
`w1_bank/k2_gold.py`. It holds the school's lesson text and this repository's logs are public, so it is sent to a person's
browser and nowhere else: the site calls with the engine's key and the signed-in member of staff's email as `by`, and a
sign-in that is not on the staff list is refused."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from engine.api.deps import get_conn, get_tenant_id, require_engine_key
from engine.core import db
from engine.w1_bank import k2_checkers, k2_gold
from engine.w1_bank.k2_upload import config

router = APIRouter(prefix="/curriculum", dependencies=[Depends(require_engine_key)])


@router.get("/gold-sheet.csv")
def gold_sheet_csv(
    by: str,
    pages: int = Query(30, ge=1, le=100),
    conn=Depends(get_conn, scope="function"),
    tenant_id: str = Depends(get_tenant_id),
):
    if db.one(conn, "select public.staff_of_email(%s) as id", (by,))["id"] is None:
        raise HTTPException(status_code=403, detail="This sign-in is not on the staff list.")
    rows = k2_gold.sheet(conn, UUID(str(tenant_id)), config()["band"], pages)
    return Response(
        k2_gold.to_csv(rows),
        media_type="text/csv; charset=utf-8",
        headers={
            "content-disposition": 'attachment; filename="k2-drafts-to-mark.csv"',
            "cache-control": "no-store",
        },
    )


@router.get("/checkers.csv")
def checkers_csv(
    by: str,
    stage: str = "dev_eval",
    conn=Depends(get_conn, scope="function"),
    tenant_id: str = Depends(get_tenant_id),
):
    """Two checkers on the same drafts, a row a page with both sets of faults and the school's words beside the draft."""
    if db.one(conn, "select public.staff_of_email(%s) as id", (by,))["id"] is None:
        raise HTTPException(status_code=403, detail="This sign-in is not on the staff list.")
    rows = k2_checkers.rows(conn, UUID(str(tenant_id)), stage)
    return Response(
        k2_checkers.to_csv(rows),
        media_type="text/csv; charset=utf-8",
        headers={
            "content-disposition": 'attachment; filename="k2-two-checkers.csv"',
            "cache-control": "no-store",
        },
    )
