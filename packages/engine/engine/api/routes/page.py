"""A K2 page read and answered by staff (task M1-12b): read it, confirm a drafted part, edit it, take it back. Only
wiring: what a page is and what each answer does are `w1_bank/k2_page.py` and `k2_review.py`. The site calls with the
engine's key and the signed-in member of staff's email as `actor`; a sign-in that is not on the staff list is refused.
Only a part marked drafted can be answered: the school's own words are never changed through here."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from engine.api.deps import curriculum_reviews, curriculum_staff, get_conn, get_tenant_id, require_engine_key
from engine.w1_bank import k2_page, k2_review

router = APIRouter(prefix="/curriculum/page", dependencies=[Depends(require_engine_key)])


class Who(BaseModel):
    actor: str


class Ref(Who):
    code: str


class PartRef(Ref):
    part: str


class Slip(BaseModel):
    keyword: str
    spot: str


class Edit(PartRef):
    """Their own words: `text` for any part; `items` for the steps; `idea` and `slips` for the thinking."""

    text: str | None = None
    items: list[str] | None = None
    idea: str | None = None
    slips: list[Slip] | None = None


class Part(BaseModel):
    part: str
    kind: str  # bullets (the steps), thinking (an idea and slips) or text
    source: str  # school, drafted or person; empty when the part has no words
    check_me: bool
    text: str
    items: list[str]  # the steps, one bullet each (empty for any other part)
    idea: str | None  # the thinking's idea line (empty when the thinking is the school's prose)
    slips: list[Slip]


class MaterialItem(BaseModel):
    name: str
    quantity: float | None
    unit: str


class Materials(BaseModel):
    text: str  # the school's own words
    items: list[MaterialItem]


class Draft(BaseModel):
    maker: str
    checker: str
    verdict: str  # agree, disagree or empty
    reason: str
    status: str
    history: list[dict]


class Page(BaseModel):
    code: str
    name: str
    section: str
    parts: list[Part]
    materials: Materials
    draft: Draft | None


def _staff(conn, who: Who, writes: bool = False) -> UUID:
    return curriculum_staff(conn, who.actor, writes=writes)


def _page(conn, tenant_id: str, code: str) -> dict:
    try:
        return k2_page.read(conn, UUID(str(tenant_id)), code)
    except LookupError:
        raise HTTPException(status_code=404, detail="No such activity.") from None


def _answer(conn, tenant_id: str, body: PartRef, act) -> dict:
    try:
        act(conn, UUID(str(tenant_id)), _staff(conn, body, writes=True), body.code, body.part)
    except ValueError as e:
        taken = "not a drafted part" in str(e)
        raise HTTPException(status_code=409 if taken else 422, detail=str(e)) from None
    return _page(conn, tenant_id, body.code)


class Gate(BaseModel):
    reviews: bool  # may keep, edit, send back and answer offers; false: the staff preview, who looks only


@router.post("/gate", response_model=Gate)
def gate(body: Who, conn=Depends(get_conn, scope="function")):
    """Whether this sign-in may review (the site asks before it shows the buttons); refused when the screens are not open
    to them at all."""
    return Gate(reviews=curriculum_reviews(conn, _staff(conn, body)))


@router.post("/read", response_model=Page)
def read(body: Ref, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)):
    _staff(conn, body)
    return _page(conn, tenant_id, body.code)


@router.post("/confirm", response_model=Page)
def confirm(body: PartRef, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)):
    """Keep the draft as it is: it becomes this person's, and its doubt is cleared."""
    return _answer(conn, tenant_id, body, k2_review.keep)


@router.post("/revert", response_model=Page)
def revert(body: PartRef, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)):
    """Take the draft back: the part is empty again and carries no mark."""
    return _answer(conn, tenant_id, body, k2_review.reject)


@router.post("/edit", response_model=Page)
def edit(body: Edit, conn=Depends(get_conn, scope="function"), tenant_id: str = Depends(get_tenant_id)):
    """Their own words in place of the draft's; the part is then theirs."""
    value: object = body.text
    if body.items is not None:
        value = body.items
    elif body.idea is not None or body.slips is not None:
        value = {"idea": body.idea, "slips": [s.model_dump() for s in body.slips or []]}
    staff = _staff(conn, body, writes=True)
    try:
        k2_review.change(conn, UUID(str(tenant_id)), staff, body.code, body.part, value)
    except ValueError as e:
        taken = "not a drafted part" in str(e)
        raise HTTPException(status_code=409 if taken else 422, detail=str(e)) from None
    return _page(conn, tenant_id, body.code)
