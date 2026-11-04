"""The consolidated list goes to the one inventory person (task M1-16; D-071, D-074: "the inventory person gets a proper
final list"). A structured checklist, one line per item with its total and where it comes from; a line that moved since
the last send says so. One tap opens WhatsApp to the number in `materials.inventory_whatsapp_to`; the engine records
exactly what was sent, who tapped and when. It cannot know the message was read."""

import json
from typing import Any
from uuid import UUID

from engine.core import db, settings
from engine.w2_print import materials_consolidate, materials_coverage, materials_text
from engine.w2_print.materials_send import NothingToSend


def _q(q: Any) -> str:
    return "unknown" if q is None else materials_text.number(q)


def _line(item: dict[str, Any], last: dict[str, Any] | None) -> str:
    what = (
        f"{materials_text.number(item['quantity'])} {item['unit']}"
        if item["quantity"] is not None
        else f"quantity to confirm ({item['unit']})"
    )
    out = f"[ ] {item['item']}: {what}"
    where = ", ".join(sorted({f["class"] for f in item["from"] if f["class"]}))
    if where:
        out += f" ({where})"
    before = None if last is None else last.get(item["material_code"])
    if last is not None and before is None:
        out += "; new"
    elif before is not None and before["quantity"] != item["quantity"]:
        out += f"; changed: was {_q(before['quantity'])}, now {_q(item['quantity'])}"
    return out


def send(conn: db.Conn, cid: UUID, who: UUID) -> dict[str, Any]:
    got = materials_consolidate.read(conn, cid)
    if not got["lines"]:
        raise NothingToSend("the list has no lines")
    prior = conn.execute(
        "select lines from materials_consolidated_send where consolidated_id = %s order by at desc limit 1",
        (cid,),
    ).fetchone()
    last = None if prior is None else {x["material_code"]: x for x in prior["lines"]}
    body = [f"School materials, {materials_text.short(got['from'])} to {materials_text.short(got['to'])}"]
    body += [_line(item, last) for item in got["lines"]]
    tenant = db.one(conn, "select tenant_id from materials_consolidated where id = %s", (cid,))["tenant_id"]
    # the classes absent from the very build the lines above come from (not from today's plans)
    names = materials_coverage.class_names(conn, tenant)
    expected = materials_coverage.planned_classes(conn, tenant, got["from"], got["to"])
    giving = materials_coverage.classes_in(conn, cid)
    missing = [names[c] for c in expected if c not in giving]
    if missing:
        body.append(f"Not included: {', '.join(sorted(missing))} (nothing from them in this list)")
    if last is not None:
        gone = [c for c in last if c not in {x["material_code"] for x in got["lines"]}]
        body += [f"[x] {last[c]['item']}: no longer needed since the last list" for c in gone]
    text = "\n".join(body)
    number = str(settings.config(conn, "materials.inventory_whatsapp_to", "") or "")
    row = db.one(
        conn,
        "insert into materials_consolidated_send (tenant_id, consolidated_id, build, text, lines, status, who)"
        " values ((select tenant_id from materials_consolidated where id = %s), %s, %s, %s, %s, 'opened', %s)"
        " returning id",
        (
            cid,
            cid,
            got["build"],
            text,
            json.dumps(
                [
                    {"material_code": x["material_code"], "item": x["item"], "quantity": x["quantity"]}
                    for x in got["lines"]
                ]
            ),
            who,
        ),
    )
    return {
        "send_id": row["id"],
        "text": text,
        "status": "opened",
        "wa_link": materials_text.whatsapp_link(text, number),
    }
