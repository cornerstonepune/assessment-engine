"""What a person does with a note the system could not confirm (task M1-16, brick 2): put it on the class's list, or set it
aside with a reason; and approve a word or a unit so the next note needs no one. Putting it on the list goes through
`materials_list.add` like any other line, so every rule of a line holds. Nothing here asks a model."""

import datetime as dt
import math
from decimal import Decimal
from typing import Any
from uuid import UUID

from engine.core import db
from engine.w2_print import materials_list as ml
from engine.w2_print.materials_text import norm


class NoSuchNote(Exception):
    """There is no such note in this school."""


class NotWaiting(Exception):
    """The note is already cleared: nothing is added a second time."""


class AliasTaken(Exception):
    """The word already means a different item."""


def waiting(conn: db.Conn, tenant: UUID) -> list[dict[str, Any]]:
    return [
        dict(r)
        for r in conn.execute(
            "select id, list_id, text, reason, at from materials_note_review"
            " where tenant_id = %s and state = 'needs_person' order by at, id",
            (tenant,),
        )
    ]


def _open(conn: db.Conn, tenant: UUID, note_id: UUID) -> dict[str, Any]:
    row = conn.execute(
        "select id, list_id, state from materials_note_review where id = %s and tenant_id = %s for update",
        (note_id, tenant),
    ).fetchone()
    if row is None:
        raise NoSuchNote(str(note_id))
    if row["state"] != "needs_person":
        raise NotWaiting(str(note_id))
    return dict(row)


def resolve(
    conn: db.Conn,
    tenant: UUID,
    note_id: UUID,
    material_code: str,
    quantity: float,
    needed_on: dt.date,
    who: UUID,
) -> UUID:
    """Add what the note asked for to its list, as a line a person chose, and close the note. If the add is refused (not
    in the catalogue, already on the list, a bad quantity) the note stays waiting and nothing changes. Returns the list."""
    if isinstance(quantity, bool) or not math.isfinite(quantity) or quantity <= 0:
        raise ValueError("a quantity is a number above zero")
    note = _open(conn, tenant, note_id)
    ml.add(conn, note["list_id"], material_code, quantity, needed_on, None, who, via="note_review")
    conn.execute(
        "update materials_note_review set state = 'added', resolved_by = %s, resolved_at = clock_timestamp(),"
        " resolved_code = %s, resolved_quantity = %s where id = %s",
        (who, material_code, quantity, note_id),
    )
    return note["list_id"]


def dismiss(conn: db.Conn, tenant: UUID, note_id: UUID, why: str, who: UUID) -> None:
    why = norm(why)
    if not why:
        raise ValueError("a note set aside needs a reason")
    _open(conn, tenant, note_id)
    conn.execute(
        "update materials_note_review set state = 'dismissed', resolved_by = %s, resolved_at = clock_timestamp(),"
        " why = %s where id = %s",
        (who, why, note_id),
    )


def _item_unit(conn: db.Conn, tenant: UUID, code: str) -> str:
    row = conn.execute(
        "select unit from material_item where tenant_id = %s and code = %s", (tenant, code)
    ).fetchone()
    if row is None:
        raise ml.NotInCatalogue(code)
    return str(row["unit"])


def approve_alias(conn: db.Conn, tenant: UUID, alias: str, material_code: str, who: UUID) -> None:
    word = norm(alias)
    if not word:
        raise ValueError("a word is needed")
    _item_unit(conn, tenant, material_code)
    conn.execute(
        "insert into material_alias (tenant_id, alias, material_code, approved_by) values (%s, %s, %s, %s)"
        " on conflict (tenant_id, alias) do nothing",
        (tenant, word, material_code, who),
    )
    mine = db.one(
        conn, "select material_code from material_alias where tenant_id = %s and alias = %s", (tenant, word)
    )["material_code"]
    if mine != material_code:
        raise AliasTaken(word)


def approve_conversion(
    conn: db.Conn, tenant: UUID, material_code: str, unit: str, factor: float, who: UUID
) -> None:
    """`factor` of the item's own unit make one `unit` ("dozen" -> 12 piece). A different factor is a new row (the latest is used)."""
    word = norm(unit)
    if not word:
        raise ValueError("a unit is needed")
    if isinstance(factor, bool) or not math.isfinite(factor) or factor <= 0:
        raise ValueError("a factor is a number above zero")
    if word == norm(_item_unit(conn, tenant, material_code)):
        raise ValueError("the item's own unit needs no conversion")
    conn.execute(
        "select pg_advisory_xact_lock(hashtext('material_unit_conversion'), hashtext(%s))", (str(tenant),)
    )
    latest = conn.execute(
        "select factor from material_unit_conversion where tenant_id = %s and material_code = %s and from_unit = %s"
        " order by approved_at desc, id limit 1",
        (tenant, material_code, word),
    ).fetchone()
    if latest is not None and latest["factor"] == Decimal(str(factor)):
        return
    conn.execute(
        "insert into material_unit_conversion (tenant_id, material_code, from_unit, factor, approved_by)"
        " values (%s, %s, %s, %s, %s)",
        (tenant, material_code, word, factor, who),
    )
