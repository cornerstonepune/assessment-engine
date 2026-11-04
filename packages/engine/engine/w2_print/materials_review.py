"""What a person does with a note the system could not confirm (task M1-16, brick 2): put it on the class's list, or set it
aside with a reason; and approve a word or a unit so the next note needs no one. Putting it on the list goes through
`materials_list.add` like any other line, so every rule of a line holds. Nothing here asks a model."""

import datetime as dt
import math
from typing import Any
from uuid import UUID

from engine.core import db
from engine.w2_print import materials_list as ml


class NotWaiting(Exception):
    """The note is already cleared (or is not this school's): nothing is added a second time."""


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


def _open(conn: db.Conn, note_id: UUID) -> dict[str, Any]:
    row = conn.execute(
        "select id, list_id, state from materials_note_review where id = %s for update", (note_id,)
    ).fetchone()
    if row is None or row["state"] != "needs_person":
        raise NotWaiting(str(note_id))
    return dict(row)


def resolve(
    conn: db.Conn, note_id: UUID, material_code: str, quantity: float, needed_on: dt.date, who: UUID
) -> UUID:
    """Add what the note asked for to its list, as a line a person chose, and close the note. If the add is refused (not
    in the catalogue, already on the list, a bad quantity) the note stays waiting and nothing changes. Returns the list."""
    if isinstance(quantity, bool) or not math.isfinite(quantity) or quantity <= 0:
        raise ValueError("a quantity is a number above zero")
    note = _open(conn, note_id)
    ml.add(conn, note["list_id"], material_code, quantity, needed_on, None, who, via="note")
    conn.execute(
        "update materials_note_review set state = 'added', resolved_by = %s, resolved_at = clock_timestamp(),"
        " resolved_code = %s, resolved_quantity = %s where id = %s",
        (who, material_code, quantity, note_id),
    )
    return UUID(str(note["list_id"]))


def dismiss(conn: db.Conn, note_id: UUID, why: str, who: UUID) -> None:
    why = " ".join(why.split())
    if not why:
        raise ValueError("a note set aside needs a reason")
    _open(conn, note_id)
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
    word = " ".join(alias.lower().split())
    if not word:
        raise ValueError("a word is needed")
    _item_unit(conn, tenant, material_code)
    conn.execute("select pg_advisory_xact_lock(hashtext('material_alias'))")
    have = conn.execute(
        "select material_code from material_alias where tenant_id = %s and alias = %s", (tenant, word)
    ).fetchone()
    if have is not None:
        if have["material_code"] != material_code:
            raise AliasTaken(word)
        return
    conn.execute(
        "insert into material_alias (tenant_id, alias, material_code, approved_by) values (%s, %s, %s, %s)",
        (tenant, word, material_code, who),
    )


def approve_conversion(
    conn: db.Conn, tenant: UUID, material_code: str, unit: str, factor: float, who: UUID
) -> None:
    """`factor` of the item's own unit make one `unit` ("dozen" -> 12 piece). Approving again changes the factor."""
    word = " ".join(unit.lower().split())
    if not word:
        raise ValueError("a unit is needed")
    if isinstance(factor, bool) or not math.isfinite(factor) or factor <= 0:
        raise ValueError("a factor is a number above zero")
    if word == " ".join(_item_unit(conn, tenant, material_code).lower().split()):
        raise ValueError("the item's own unit needs no conversion")
    conn.execute(
        "insert into material_unit_conversion (tenant_id, material_code, from_unit, factor, approved_by)"
        " values (%s, %s, %s, %s, %s)"
        " on conflict (tenant_id, material_code, from_unit) do update"
        " set factor = excluded.factor, approved_by = excluded.approved_by, approved_at = clock_timestamp()",
        (tenant, material_code, word, factor, who),
    )
