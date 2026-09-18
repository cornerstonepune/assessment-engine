"""/health needs no key — it is what a container orchestrator or n8n's own health check polls
before anything is configured. /runs/{id} is how a coordinator (or n8n, on a failure notification)
looks at what one flow_run actually did; it does need the key, like every other route."""
from fastapi import APIRouter, Depends, HTTPException

from engine.api.deps import get_conn, require_engine_key
from engine.api.models import RunResponse

health_router = APIRouter()
runs_router = APIRouter(dependencies=[Depends(require_engine_key)])


@health_router.get("/health")
def health(conn=Depends(get_conn)):
    conn.execute("select 1")
    return {"ok": True}


@runs_router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str, conn=Depends(get_conn)):
    row = conn.execute(
        "select id, flow, trigger, status, error, tokens, cost_inr from flow_run where id = %s",
        (run_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"no run {run_id}")
    return {**row, "id": str(row["id"]), "cost_inr": float(row["cost_inr"]) if row["cost_inr"] is not None else None}
