"""N12 over HTTP: a child's parent report — the newest kept draft and whether it is still true, a new draft written
and held to its facts, and an educator's approval (`w4_close/parent_report.py`)."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from engine.api.deps import get_conn, require_engine_key
from engine.api.models import CardConfirmRequest, ParentReportEdit
from engine.w4_close import parent_report

router = APIRouter(dependencies=[Depends(require_engine_key)])


def _child(conn, child_id):
    if not conn.execute("select 1 from child where id::text = %s", (child_id,)).fetchone():
        raise HTTPException(404, f"no child {child_id}")


@router.get("/child/{child_id}/parent-report")
def newest(child_id: str, conn=Depends(get_conn)):
    """The newest kept report (or null), the facts a report written now would rest on, and whether the report's prompt
    has passed its eval and may write one."""
    _child(conn, child_id)
    ready = conn.execute(
        "select 1 from prompt where purpose = %s and active", (parent_report.PURPOSE,)
    ).fetchone()
    return {
        "note": parent_report.latest(conn, child_id),
        "facts": parent_report.facts(conn, child_id),
        "ready": bool(ready),
    }


@router.post("/child/{child_id}/parent-report", status_code=202)
def write(child_id: str, body: CardConfirmRequest, background: BackgroundTasks, conn=Depends(get_conn)):
    """Start writing a new draft from the child's signed-off answers → {run_id}. It is written, held to its facts,
    read against them and kept after this answers (`parent_report.write`); `/runs/{run_id}` says ok, or why not."""
    _child(conn, child_id)
    if parent_report.facts(conn, child_id) is None:
        raise HTTPException(409, "no answer of this child's has been signed off yet")
    run_id = parent_report.start(child_id, body.by)
    background.add_task(parent_report.write, run_id, child_id)
    return {"run_id": run_id, "by": body.by}


@router.post("/child/{child_id}/parent-report/{note_id}/approve")
def approve(child_id: str, note_id: str, body: CardConfirmRequest, conn=Depends(get_conn)):
    _child(conn, child_id)
    try:
        parent_report.approve(conn, child_id, note_id, body.by)
    except LookupError as e:
        raise HTTPException(409, str(e))
    return {"note": parent_report.latest(conn, child_id)}


@router.post("/child/{child_id}/parent-report/{note_id}/edit")
def edit(child_id: str, note_id: str, body: ParentReportEdit, conn=Depends(get_conn)):
    """An educator's own words become the report, held to its facts (422 with what they broke); 409 once approved."""
    _child(conn, child_id)
    try:
        parent_report.edit(conn, child_id, note_id, body.draft, body.by)
    except LookupError as e:
        raise HTTPException(409, str(e))
    except ValueError as e:
        raise HTTPException(422, {"problems": e.args[0]})
    return {"note": parent_report.latest(conn, child_id)}
