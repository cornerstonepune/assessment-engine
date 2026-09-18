"""N10 — the nightly (or on-confirm) rebuild, over HTTP. Rebuilding is safe to repeat (Ring B is
a pure function of Ring A's evidence — the same evidence always rebuilds to the same states), so
idempotency here guards against a retried HTTP call doing needless work, not against a
correctness risk. A caller that needs two genuinely different rebuilds on the same body (say, one
per confirm event on the same day) must pass its own distinguishing Idempotency-Key — deriving
one from the body alone, as every other route does, cannot tell "the same event retried" from
"a new event with an identical body" apart, and guessing at that here would be worse than not
guessing."""
from fastapi import APIRouter, Depends, Header

from engine.api.deps import get_conn, get_tenant_id, require_engine_key
from engine.api.idempotency import derive_key, run_idempotent
from engine.api.models import GraphRebuildRequest, GraphRebuildResponse
from engine.assess import graph as skill_graph  # avoids shadowing this route module's own name

router = APIRouter(dependencies=[Depends(require_engine_key)])


@router.post("/graph/rebuild", response_model=GraphRebuildResponse)
def rebuild(
    body: GraphRebuildRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    conn=Depends(get_conn),
    tenant_id: str = Depends(get_tenant_id),
):
    key = idempotency_key or derive_key(body.model_dump())
    result, already = run_idempotent(
        conn, tenant_id, "graph_rebuild", key, body.model_dump(),
        lambda: {"states": skill_graph.rebuild(conn, body.child_id)},
    )
    return {**result, "already": already}
