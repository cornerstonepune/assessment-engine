"""Sending the materials list to the materials team (task M1-10; D-071). WhatsApp is the default: one tap opens it with
the list written out as a checklist, and the engine records exactly what text was sent and who tapped when. It cannot
know the message was read. Email is the second route; the engine has no mail sender, so it is recorded as 'not
configured' and the list stays a draft. A list that has been sent has no more reminders."""

from typing import Any
from uuid import UUID

from engine.core import db, settings
from engine.w2_print import materials_text as text

SENT = ("opened", "sent")  # a send that went out; 'not configured' and 'failed' did not


class NothingToSend(Exception):
    pass


class NotSent(Exception):
    """The team cannot have what was never sent: an email with no sender behind it is a record of a try."""


def _lines(conn: db.Conn, list_id: UUID) -> list[text.Line]:
    return [
        text.Line(
            r["name"], None if r["quantity"] is None else float(r["quantity"]), r["unit"], r["needed_on"]
        )
        for r in conn.execute(
            "select i.name, l.quantity, l.unit, l.needed_on from materials_line l"
            " join material_item i on i.tenant_id = l.tenant_id and i.code = l.material_code"
            " where l.list_id = %s and l.removed_at is null order by l.needed_on, i.name",
            (list_id,),
        )
    ]


def _compose(conn: db.Conn, list_id: UUID, lock: bool = False) -> tuple[dict[str, Any], str | None]:
    """The list's row and its checklist (None when it has no lines). `lock` holds the row while it is sent."""
    lst = db.one(
        conn,
        "select l.*, c.grade_code, c.section from materials_list l join school_class c on c.id = l.school_class_id"
        f" where l.id = %s{' for update of l' if lock else ''}",
        (list_id,),
    )
    lines = _lines(conn, list_id)
    name = f"{lst['grade_code']} {lst['section'] or ''}".strip()
    return lst, text.checklist(name, lst["from_on"], lst["to_on"], lines) if lines else None


def current_text(conn: db.Conn, list_id: UUID) -> str | None:
    """The checklist as the list reads now, or None when it has no lines."""
    return _compose(conn, list_id)[1]


def send(conn: db.Conn, list_id: UUID, route: str, who: UUID) -> dict[str, Any]:
    lst, body = _compose(conn, list_id, lock=True)
    if body is None:
        raise NothingToSend("the list has no lines")
    link = None
    if route == "whatsapp":
        status = "opened"
        link = text.whatsapp_link(body, str(settings.config(conn, "materials.whatsapp_to", "") or ""))
    else:
        status = "not configured"
    row = db.one(
        conn,
        "insert into materials_send (tenant_id, list_id, route, text, status, who) values (%s,%s,%s,%s,%s,%s)"
        " returning id",
        (lst["tenant_id"], list_id, route, body, status, who),
    )
    if status == "opened":
        conn.execute("update materials_list set state = 'sent', updated_at = now() where id = %s", (list_id,))
        conn.execute(
            "update reminder set state = 'cancelled', updated_at = now() where list_id = %s and state = 'pending'",
            (list_id,),
        )
    return {"send_id": row["id"], "text": body, "status": status, "wa_link": link}


def team_has_it(conn: db.Conn, send_id: UUID, who: UUID) -> None:
    sent = db.one(conn, "select status from materials_send where id = %s", (send_id,))
    if sent["status"] not in SENT:
        raise NotSent(send_id)
    conn.execute(
        "insert into materials_send_ack (send_id, who) values (%s, %s) on conflict do nothing", (send_id, who)
    )
