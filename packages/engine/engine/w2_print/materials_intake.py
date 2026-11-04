"""A free-text or photographed request for materials read into catalogue items (task M1-16; D-074: "some simple, low-cost
model, so that if someone has written pens, it classifies that"). The model only proposes. Code decides: a reading is
confirmed only when its item is in the catalogue, its quantity is a number above zero that the note's own words give, and
its unit is the catalogue's. Code never converts ("2 dozen" is not 24). Anything else goes to a person
(`materials_note_review`) and never into a list. A photograph is read in memory and never stored; the same call must say
whether a person is in it, and a "yes" or a missing answer sends the whole note to a person."""

import datetime as dt
import io
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from PIL import Image, ImageOps

from engine.adapters import llm
from engine.core import db, settings
from engine.w2_print import materials_list

PURPOSE = "materials_read"
NUMBER = re.compile(r"\d+(?:\.\d+)?")


@dataclass(frozen=True)
class Checked:
    status: str  # 'confirmed' | 'needs_person'
    reason: str
    text: str = ""
    item_code: str | None = None
    quantity: float | None = None
    unit: str | None = None


def _person(reading: dict[str, Any], reason: str) -> Checked:
    return Checked("needs_person", reason, str(reading.get("text") or ""))


def check_reading(reading: dict[str, Any], catalogue: list[dict[str, Any]], source_text: str) -> Checked:
    """One model reading against the catalogue and the words it was read from. Pure."""
    item = {c["code"]: c for c in catalogue}.get(str(reading.get("item_code")))
    if item is None:
        return _person(reading, "the item is not in the catalogue")
    quantity = reading.get("quantity")
    if quantity is None:
        return _person(reading, "the note gives no quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, int | float):
        return _person(reading, "the quantity is not a number")
    if quantity <= 0:
        return _person(reading, "a quantity is more than nothing")
    if float(quantity) not in {float(n) for n in NUMBER.findall(source_text)}:
        return _person(reading, "the number is not in the note's own words (code does not convert)")
    if reading.get("unit") != item["unit"]:
        return _person(reading, f"the unit is not the catalogue's ({item['unit']}); code does not convert")
    return Checked("confirmed", "", str(reading.get("text") or ""), item["code"], quantity, item["unit"])


def prepare_photo(data: bytes, max_side: int) -> bytes:
    """The photograph as a plain JPEG no larger than `max_side` on its long edge. Re-encoding drops whatever else the
    file carried (where it was taken, who with)."""
    img = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
    img.thumbnail((max_side, max_side))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=85)
    return out.getvalue()


def _catalogue(conn: db.Conn, tenant: UUID) -> list[dict[str, Any]]:
    return [
        dict(r)
        for r in conn.execute(
            "select code, name, unit from material_item where tenant_id = %s order by code", (tenant,)
        )
    ]


def _review(conn: db.Conn, tenant: UUID, list_id: UUID, who: UUID, got: Checked) -> None:
    conn.execute(
        "insert into materials_note_review (tenant_id, list_id, text, reason, who) values (%s, %s, %s, %s, %s)",
        (tenant, list_id, got.text, got.reason, who),
    )


def read_note(
    conn: db.Conn,
    list_id: UUID,
    note: str,
    who: UUID,
    needed_on: dt.date,
    image: bytes | None = None,
) -> list[Checked]:
    """Read a typed note and/or a photographed one for the class's list. The model gets the note and the catalogue and
    nothing else: never a name. Confirmed readings become lines on the list (as hers, with the note as their source);
    the rest wait for a person."""
    tenant = db.one(conn, "select tenant_id from materials_list where id = %s", (list_id,))["tenant_id"]
    catalogue = _catalogue(conn, tenant)
    answer = llm.generate(
        conn, PURPOSE, {"note": note, "catalogue": catalogue}, images=[image] if image else ()
    )
    if image is not None and answer.get("people_visible") is not False:
        sent = Checked(
            "needs_person", "a person may be in the photograph, so it was not read", "(photograph)"
        )
        _review(conn, tenant, list_id, who, sent)
        return [sent]
    out: list[Checked] = []
    for reading in answer.get("readings") or []:
        # a typed note is the words to check the number against; a photograph has only the model's own copy of them
        words = note if image is None else f"{note}\n{reading.get('text') or ''}"
        got = check_reading(reading, catalogue, words)
        if got.status == "confirmed" and got.item_code is not None:
            try:
                materials_list.add(
                    conn, list_id, got.item_code, got.quantity, needed_on, None, who, via="note"
                )
            except materials_list.AlreadyOnList:
                got = _person(reading, "it is already on the list: change its quantity there")
        if got.status == "needs_person":
            _review(conn, tenant, list_id, who, got)
        out.append(got)
    return out


def photo_max_side(conn: db.Conn) -> int:
    return int(settings.config(conn, "materials.photo_max_side", 1600))
