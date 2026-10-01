"""/health needs no key — it is what a container orchestrator or n8n's own health check polls
before anything is configured. /runs/{id} is how a coordinator (or n8n, on a failure notification)
looks at what one flow_run actually did; it does need the key, like every other route."""

from fastapi import APIRouter, Depends, HTTPException

from engine.api.deps import get_conn, require_engine_key
from engine.api.models import RunResponse
from engine.core import db

health_router = APIRouter()
runs_router = APIRouter(dependencies=[Depends(require_engine_key)])


@health_router.get("/health")
def health(conn=Depends(get_conn)):
    conn.execute("select 1")
    return {"ok": True}


@runs_router.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str, conn=Depends(get_conn)):
    row = conn.execute(
        "select id, flow, trigger, status, error, tokens, cost_inr from flow_run where id = %s", (run_id,)
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail=f"no run {run_id}")
    return {
        **row,
        "id": str(row["id"]),
        "cost_inr": float(row["cost_inr"]) if row["cost_inr"] is not None else None,
    }


def orphaned() -> int:
    """Every run still marked running when the engine starts died with the process before it: a background task, or a
    command run in the same container, and this process is new. Marked so, whatever the flow, instead of "running"
    forever (2026-09-25 and 26: two readings died under a deploy and said "running" until someone looked). → how many."""
    with db.connect() as conn:
        return conn.execute(
            "update flow_run set status = 'error', finished_at = now(), updated_at = now(),"
            " error = 'the engine restarted while this was running; start it again' where status = 'running'"
        ).rowcount
