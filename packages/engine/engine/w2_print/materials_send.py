"""Sending the materials list to the materials team (task M1-10; D-071). WhatsApp is the default: one tap opens it with
the list written out as a checklist, and the engine records exactly what text was sent and who tapped when. It cannot
know the message was read. Email is the second route; the engine has no mail sender, so it is recorded as 'not
configured' and the list stays a draft. A list that has been sent has no more reminders."""

from typing import Any
from uuid import UUID

from engine.core import db, settings
from engine.w2_print import materials_text as text


class NothingToSend(Exception):
    pass


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


def send(conn: db.Conn, list_id: UUID, route: str, who: UUID) -> dict[str, Any]:
    lst = db.one(
        conn,
        "select l.*, c.grade_code, c.section from materials_list l join school_class c on c.id = l.school_class_id"
        " where l.id = %s for update of l",
        (list_id,),
    )
    lines = _lines(conn, list_id)
    if not lines:
        raise NothingToSend("the list has no lines")
    body = text.checklist(
        f"{lst['grade_code']} {lst['section'] or ''}".strip(), lst["from_on"], lst["to_on"], lines
    )
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
    conn.execute(
        "insert into materials_send_ack (send_id, who) values (%s, %s) on conflict do nothing", (send_id, who)
    )
