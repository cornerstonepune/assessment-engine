"""W1/N2 — top up the question bank for one skill set × difficulty, over HTTP; and one question on
its own: how it prints, and a person's correction to it."""

from fastapi import APIRouter, Depends, Header, HTTPException, Response

from engine import bank, question, review
from engine.api.deps import get_conn, get_tenant_id, require_engine_key
from engine.api.idempotency import derive_key, run_idempotent
from engine.api.models import (
    BankCorrectRequest,
    BankCorrectResponse,
    BankCoverageRow,
    BankFillRequest,
    BankFillResponse,
    BankRemoveRequest,
    BankRemoveResponse,
    BankReviewRequest,
    BankReviewResponse,
)

router = APIRouter(dependencies=[Depends(require_engine_key)])


@router.get("/bank/coverage", response_model=list[BankCoverageRow])
def coverage(short_only: bool = False, conn=Depends(get_conn)):
    """The unit grid. `short_only=true` returns just the units below their target, with the
    shortfall — which is exactly what an orchestrator needs to decide what to top up, so the
    deciding stays here and n8n only forwards the answer (CLAUDE.md rule 3)."""
    rows = [
        {
            "code": r["code"],
            "difficulty": r["difficulty"],
            "n": r["n"],
            "target": r["target"],
            "shortfall": max(0, r["target"] - r["n"]),
        }
        for r in bank.coverage(conn)
    ]
    return [r for r in rows if r["shortfall"] > 0] if short_only else rows


@router.post("/bank/review", response_model=BankReviewResponse)
def review_unit(
    body: BankReviewRequest,
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    conn=Depends(get_conn),
    tenant_id: str = Depends(get_tenant_id),
):
    """One reviewer over one unit's rule and a ≤5 % sample. Advisory — nothing is retired."""
    key = idempotency_key or derive_key(body.model_dump())

    def run():
        verdicts, meta = review.review_unit(conn, body.skill_set, body.difficulty, body.reviewer)
        return {
            "skill_set": body.skill_set,
            "difficulty": body.difficulty,
            "reviewer": body.reviewer,
            "judged": len(verdicts),
            "not_passed": sum(1 for v in verdicts if v["verdict"] != "pass"),
            "model": meta.get("model"),
            "cost_inr": float(meta.get("cost_inr") or 0),
        }

    result, already = run_idempotent(conn, tenant_id, "bank_review", key, body.model_dump(), run)
    return {**result, "already": already}


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


@router.get("/bank/item/{item_key}/printed.png")
def printed_question(item_key: str, conn=Depends(get_conn)) -> Response:
    """One question exactly as a paper prints it, for the question page."""
    png = question.printed(conn, item_key)
    if png is None:
        raise HTTPException(status_code=404, detail="no such question in the bank")
    return Response(content=png, media_type="image/png")


@router.post("/bank/item/{item_key}/correct", response_model=BankCorrectResponse)
def correct_question(item_key: str, body: BankCorrectRequest, conn=Depends(get_conn)):
    """A person rewords a question. Not idempotency-wrapped: the same correction sent twice is
    refused the second time, because the first one retired the wording it corrected."""
    try:
        return question.correct(conn, item_key, body.stem, body.by, body.reason)
    except LookupError:
        raise HTTPException(status_code=404, detail="no such question in the bank") from None
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None


@router.post("/bank/item/{item_key}/remove", response_model=BankRemoveResponse)
def remove_question(item_key: str, body: BankRemoveRequest, conn=Depends(get_conn)):
    """A person takes a question out of the bank. The worksheets it was on are retired and replaced
    in the same transaction (ADR 0026)."""
    try:
        return question.remove(conn, item_key, body.by, body.note)
    except LookupError:
        raise HTTPException(status_code=404, detail="no such question in the bank") from None
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from None
