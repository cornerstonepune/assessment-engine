"""W4/N11 over HTTP: Friday's class card, built from the graph and kept as the week's rows, and its confirmation."""

from fastapi import APIRouter, Depends, HTTPException

from engine.api.deps import get_conn, require_engine_key
from engine.api.models import CardConfirmRequest
from engine.w4_close import card

router = APIRouter(dependencies=[Depends(require_engine_key)])


@router.get("/card/{section}/{week}")
def weeks_card(section: str, week: str, conn=Depends(get_conn)):
    """The card as the graph stands now, kept as the week's rows, with who confirmed it last, if anyone."""
    try:
        got = card.build(conn, section)
    except ValueError as e:
        raise HTTPException(404, str(e))
    card.store(conn, section, week, got)
    last = card.confirmed(conn, section, week)
    return {
        **got,
        "week": week,
        "confirmed": last and {"by": last["by"], "at": last["created_at"].isoformat()},
    }


@router.post("/card/{section}/{week}/confirm")
def confirm(section: str, week: str, body: CardConfirmRequest, conn=Depends(get_conn)):
    try:
        row = card.confirm(conn, section, week, body.by, card.build(conn, section))
    except ValueError as e:
        raise HTTPException(404 if "no class" in str(e) else 409, str(e))
    return {"section": section, "week": week, "by": body.by, "at": row["created_at"].isoformat()}
