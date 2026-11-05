"""Skill proposals waiting for a person, listed and answered (task M1-12c). Only wiring: what waits and what an answer
does are `w1_bank/skill_offers.py`. The site calls with the engine's key and the signed-in member of staff's email as
`actor`; a sign-in that is not on the staff list is refused. A yes adds that proposal's skills to the activity as the
machine's links (revertible with `engine curriculum revert`); a no closes it. Both are kept with the person's id."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from engine.api.deps import curriculum_staff, get_conn, get_tenant_id, require_engine_key
from engine.w1_bank import skill_offers

router = APIRouter(prefix="/curriculum/offers", dependencies=[Depends(require_engine_key)])


class Who(BaseModel):
    actor: str


class Answer(Who):
    id: UUID
    yes: bool
    why: str = ""


class Activity(BaseModel):
    code: str
    name: str
    section: str


class Skill(BaseModel):
    code: str
    name: str


class Offer(BaseModel):
    id: str
    kind: str  # "offer": a skill no nearest example carried; "skill": a proposal under the confidence bar
    activity: Activity
    skills: list[Skill]  # what is asked to be added
    also: list[Skill]  # for an offer: the skills proposed beside it that did pass
    confidence: float
    reason: str


class Offers(BaseModel):
    offers: list[Offer]


def _staff(conn, who: Who, writes: bool = False) -> UUID:
    return curriculum_staff(conn, who.actor, writes=writes)


@router.post("/list", response_model=Offers)
def waiting(body: Who, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)):
    _staff(conn, body)
    return {"offers": skill_offers.waiting(conn, UUID(str(tenant_id)))}


@router.post("/answer", response_model=Offers)
def answer(body: Answer, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)):
    """Yes adds the skills; no closes the proposal. The list that is left comes back."""
    staff, tenant = _staff(conn, body, writes=True), UUID(str(tenant_id))
    try:
        skill_offers.answer(conn, tenant, staff, str(body.id), body.yes, body.why)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from None
    return {"offers": skill_offers.waiting(conn, tenant)}
