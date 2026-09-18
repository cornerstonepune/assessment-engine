"""W1/N2 — top up the question bank for one skill set × difficulty, over HTTP."""
from fastapi import APIRouter, Depends, Header

from engine import bank
from engine.api.deps import get_conn, get_tenant_id, require_engine_key
from engine.api.idempotency import derive_key, run_idempotent
from engine.api.models import BankFillRequest, BankFillResponse

router = APIRouter(dependencies=[Depends(require_engine_key)])


@router.post("/bank/fill", response_model=BankFillResponse)
def fill(
    body: BankFillRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    conn=Depends(get_conn),
    tenant_id: str = Depends(get_tenant_id),
):
    key = idempotency_key or derive_key(body.model_dump())

    def run():
        counts, reasons, accepted = bank.fill(conn, body.skill_set, body.difficulty, body.count)
        return {"counts": counts, "reasons": reasons, "accepted_item_keys": [it.item_id for it in accepted]}

    result, already = run_idempotent(conn, tenant_id, "bank_fill", key, body.model_dump(), run)
    return {**result, "already": already}
