"""The K2 educator's materials list (task M1-10; D-070, D-071). Built by code from the materials of the activities the
class has planned in a range, one line for each catalogue item with its quantities added up, under the first day it is
needed and tied to the activity it is first needed for. Never written by a model. The educator adds from the catalogue,
changes a quantity and removes a line; every change is kept with who made it (`materials_line_edit`), and a rebuild
brings back nothing she removed and changes no quantity she set. A quantity the plan does not give stays empty."""

import datetime as dt
import json
from decimal import Decimal
from typing import Any
from uuid import UUID

from engine.core import db, settings
from engine.w2_print import educator_gate, materials_send, materials_text


class NotInCatalogue(Exception):
    """A line may only be a catalogue item: free text is never a line (D-071)."""


class AlreadyOnList(Exception):
    pass


class LineRemoved(Exception):
    """A removed line has no quantity to change; she adds it back first."""


def num(q: Decimal | None) -> int | float | None:
    if q is None:
        return None
    return int(q) if q == q.to_integral_value() else float(q)


def _source_rows(conn: db.Conn, class_id: UUID, lo: dt.date, hi: dt.date) -> list[dict[str, Any]]:
    return conn.execute(
        "select s.id as session_id, d.on_date, a.code as activity_code, am.material_code, am.quantity, mi.unit"
        " from session s join school_day d on d.id = s.school_day_id"
        " join plan_entry p on p.id = s.plan_entry_id"
        " join activity a on a.id = p.activity_id"
        " join activity_material am on am.tenant_id = a.tenant_id and am.activity_code = a.code"
        " join material_item mi on mi.tenant_id = am.tenant_id and mi.code = am.material_code"
        " where s.school_class_id = %s and s.planned and d.on_date between %s and %s"
        " order by d.on_date, am.ord, a.code",
        (class_id, lo, hi),
    ).fetchall()


def build(conn: db.Conn, class_id: UUID, period: str, lo: dt.date, hi: dt.date) -> UUID:
    """Make or refresh the list for the class over `lo`..`hi`; returns its id. Safe to run again."""
    if hi < lo:
        raise ValueError("The last day is before the first day.")
    klass = db.one(conn, "select tenant_id from school_class where id = %s", (class_id,))
    lst = db.one(
        conn,
        "insert into materials_list (tenant_id, school_class_id, period, from_on, to_on, built_at)"
        " values (%s, %s, %s, %s, %s, now()) on conflict (school_class_id, period, from_on, to_on)"
        " do update set built_at = now(), updated_at = now() returning id",
        (klass["tenant_id"], class_id, period, lo, hi),
    )
    lid, tenant = lst["id"], klass["tenant_id"]
    wanted: dict[str, list[dict[str, Any]]] = {}
    for r in _source_rows(conn, class_id, lo, hi):
        wanted.setdefault(r["material_code"], []).append(r)
    have = {
        r["material_code"]: r for r in conn.execute("select * from materials_line where list_id = %s", (lid,))
    }
    touched = {
        r["line_id"]: r["kinds"]
        for r in conn.execute(
            "select line_id, array_agg(kind) as kinds from materials_line_edit where list_id = %s group by line_id",
            (lid,),
        )
    }
    for code, rows in wanted.items():
        first = rows[0]
        qty = None if any(r["quantity"] is None for r in rows) else sum(r["quantity"] for r in rows)
        ex = have.get(code)
        if ex is None:
            line = db.one(
                conn,
                "insert into materials_line (tenant_id, list_id, material_code, unit, quantity, needed_on, activity_code)"
                " values (%s, %s, %s, %s, %s, %s, %s) returning id",
                (tenant, lid, code, first["unit"], qty, first["on_date"], first["activity_code"]),
            )["id"]
        elif ex["removed_at"] is not None:
            continue  # she removed it: it stays removed
        else:
            line = ex["id"]
            if ex["source"] == "school":
                keep = "quantity" in touched.get(line, [])  # a quantity she set is hers
                conn.execute(
                    "update materials_line set unit = %s, quantity = case when %s then quantity else %s end,"
                    " needed_on = %s, activity_code = %s, updated_at = now() where id = %s",
                    (first["unit"], keep, qty, first["on_date"], first["activity_code"], line),
                )
        conn.execute("delete from materials_line_source where line_id = %s", (line,))
        for r in rows:
            conn.execute(
                "insert into materials_line_source (line_id, session_id, activity_code, on_date, quantity)"
                " values (%s,%s,%s,%s,%s)",
                (line, r["session_id"], r["activity_code"], r["on_date"], r["quantity"]),
            )
    for code, ex in have.items():  # the plan no longer needs it, and nobody has touched it
        if code not in wanted and ex["source"] == "school" and ex["id"] not in touched:
            conn.execute("delete from materials_line where id = %s", (ex["id"],))
    return lid


def _label(group_by: str, d: dt.date, fortnights: list[dict[str, Any]]) -> tuple[Any, str]:
    if group_by == "day":
        return d, materials_text.day(d)
    if group_by == "week":
        mon = d - dt.timedelta(days=d.weekday())
        return mon, f"Week of {mon.day} {mon:%b}"
    for f in fortnights:
        if f["starts_on"] <= d <= f["ends_on"]:
            return f["starts_on"], f"Fortnight {f['number']}" if f["number"] else f"From {f['starts_on']}"
    return dt.date.min, "Not in a fortnight"


def read(conn: db.Conn, list_id: UUID, group_by: str | None = None) -> dict[str, Any]:
    lst = db.one(conn, "select * from materials_list where id = %s", (list_id,))
    group_by = group_by or str(lst["period"])
    fortnights = conn.execute(
        "select number, starts_on, ends_on from fortnight where tenant_id = %s and ends_on >= %s and starts_on <= %s",
        (lst["tenant_id"], lst["from_on"], lst["to_on"]),
    ).fetchall()
    rows = conn.execute(
        "select l.id, l.material_code, l.unit, l.quantity, l.needed_on, l.source, l.activity_code,"
        " i.name, i.home, i.unit_value, a.id as activity_id, a.name as activity_name"
        " from materials_line l join material_item i on i.tenant_id = l.tenant_id and i.code = l.material_code"
        " left join activity a on a.tenant_id = l.tenant_id and a.code = l.activity_code"
        " where l.list_id = %s and l.removed_at is null order by l.needed_on, i.name",
        (list_id,),
    ).fetchall()
    groups: dict[Any, dict[str, Any]] = {}
    for r in rows:
        key, label = _label(group_by, r["needed_on"], fortnights)
        g = groups.setdefault(key, {"label": label, "lines": []})
        g["lines"].append(
            {
                "line_id": r["id"],
                "item": r["name"],
                "material_code": r["material_code"],
                "quantity": num(r["quantity"]),
                "unit": r["unit"],
                "needed_on": r["needed_on"],
                "activity": {"id": r["activity_id"], "code": r["activity_code"], "name": r["activity_name"]}
                if r["activity_code"]
                else None,
                "source": r["source"],
                "home": r["home"],
                "tracked": r["unit_value"] is not None,
            }
        )
    return {
        "list_id": list_id,
        "class_id": lst["school_class_id"],
        "period": lst["period"],
        "from": lst["from_on"],
        "to": lst["to_on"],
        "state": lst["state"],
        "group_by": group_by,
        "last_send": _last_send(conn, list_id),
        "groups": [groups[k] for k in sorted(groups)],
    }


def _last_send(conn: db.Conn, list_id: UUID) -> dict[str, Any] | None:
    """The latest send that went out, whether the team has it, and whether the list reads differently now."""
    last = conn.execute(
        "select s.id as send_id, s.route, s.at, s.text,"
        " exists (select 1 from materials_send_ack a where a.send_id = s.id) as team_has_it"
        " from materials_send s where s.list_id = %s and s.status = any(%s) order by s.at desc limit 1",
        (list_id, list(materials_send.SENT)),
    ).fetchone()
    if last is None:
        return None
    now = materials_send.current_text(conn, list_id)
    return {k: last[k] for k in ("send_id", "route", "at", "team_has_it")} | {"changed": now != last["text"]}


def _edit(conn: db.Conn, line: dict[str, Any], kind: str, who: UUID, before: Any, after: Any) -> None:
    conn.execute(
        "insert into materials_line_edit (tenant_id, list_id, line_id, kind, who, before, after)"
        " values (%s, %s, %s, %s, %s, %s, %s)",
        (line["tenant_id"], line["list_id"], line["id"], kind, who, json.dumps(before), json.dumps(after)),
    )


def _line(conn: db.Conn, line_id: UUID) -> dict[str, Any]:
    return db.one(conn, "select * from materials_line where id = %s for update", (line_id,))


def _check_quantity(quantity: float | None) -> None:
    if quantity is not None and quantity <= 0:
        raise ValueError("a quantity is more than nothing; remove the line instead")


def set_quantity(conn: db.Conn, line_id: UUID, quantity: float | None, who: UUID) -> None:
    _check_quantity(quantity)
    line = _line(conn, line_id)
    if line["removed_at"] is not None:
        raise LineRemoved(line_id)
    before, after = num(line["quantity"]), (None if quantity is None else Decimal(str(quantity)))
    if line["quantity"] == after:
        return
    conn.execute(
        "update materials_line set quantity = %s, updated_at = now() where id = %s", (after, line_id)
    )
    _edit(conn, line, "quantity", who, {"quantity": before}, {"quantity": num(after)})


def remove(conn: db.Conn, line_id: UUID, who: UUID) -> None:
    line = _line(conn, line_id)
    if line["removed_at"] is not None:
        return
    conn.execute("update materials_line set removed_at = now(), updated_at = now() where id = %s", (line_id,))
    _edit(
        conn,
        line,
        "remove",
        who,
        {"quantity": num(line["quantity"]), "needed_on": str(line["needed_on"])},
        {"removed": True},
    )


def add(
    conn: db.Conn,
    list_id: UUID,
    material_code: str,
    quantity: float | None,
    needed_on: dt.date,
    activity_code: str | None,
    who: UUID,
    via: str | None = None,
) -> UUID:
    lst = db.one(conn, "select tenant_id from materials_list where id = %s", (list_id,))
    item = conn.execute(
        "select unit from material_item where tenant_id = %s and code = %s", (lst["tenant_id"], material_code)
    ).fetchone()
    if item is None:
        raise NotInCatalogue(material_code)
    _check_quantity(quantity)
    qty = None if quantity is None else Decimal(str(quantity))
    have = conn.execute(
        "select * from materials_line where list_id = %s and material_code = %s for update",
        (list_id, material_code),
    ).fetchone()
    if have is not None and have["removed_at"] is None:
        raise AlreadyOnList(material_code)
    if have is None:
        line = db.one(
            conn,
            "insert into materials_line (tenant_id, list_id, material_code, unit, quantity, needed_on, activity_code,"
            " source) values (%s,%s,%s,%s,%s,%s,%s,'educator') returning *",
            (lst["tenant_id"], list_id, material_code, item["unit"], qty, needed_on, activity_code),
        )
    else:  # she removed it, and now wants it back
        line = db.one(
            conn,
            "update materials_line set removed_at = null, quantity = %s, needed_on = %s, activity_code = %s,"
            " source = 'educator', updated_at = now() where id = %s returning *",
            (qty, needed_on, activity_code, have["id"]),
        )
    _edit(
        conn,
        line,
        "add",
        who,
        None,
        {"quantity": num(qty), "needed_on": str(needed_on)} | ({"via": via} if via else {}),
    )
    return line["id"]


def propose_item(conn: db.Conn, tenant: UUID, name: str, unit: str, who: UUID) -> str:
    """A catalogue entry for a new item: no home and no value, which is what makes it wait for a person (M1-11). An
    item already in the catalogue under that name, in any case or spacing, is that item, not a second. The proposal
    names who added it and that it needs a person (`material_item_proposal`)."""
    name = " ".join(name.split())
    if not name:
        raise ValueError("a new item needs a name")
    conn.execute("select pg_advisory_xact_lock(hashtext('material_item.code'))")
    found = conn.execute(
        "select code from material_item where tenant_id = %s and lower(name) = lower(%s)", (tenant, name)
    ).fetchone()
    if found:
        return found["code"]
    last = db.one(
        conn,
        "select max(substr(code, 5)::int) as n from material_item where tenant_id = %s and code ~ '^MAT-[0-9]+$'",
        (tenant,),
    )["n"]
    code = f"MAT-{(last or 0) + 1:04d}"
    conn.execute(
        "insert into material_item (tenant_id, code, name, unit) values (%s, %s, %s, %s)",
        (tenant, code, name, unit.strip() or "piece"),
    )
    conn.execute(
        "insert into material_item_proposal (tenant_id, material_code, who) values (%s, %s, %s)",
        (tenant, code, who),
    )
    return code


def enabled(conn: db.Conn) -> bool:
    """Whether the K2 educator's timetable and materials list are switched on for her: off until Nimish shows her both
    together (D-070). A missing row is off."""
    return educator_gate.switched_on(conn)


def held_classes(conn: db.Conn, staff: UUID, today: dt.date) -> list[UUID]:
    """The classes she holds on the school's `today`: an open grant in a role the timetable names
    (`educator.timetable_roles`, a config row). The one rule for who may build, edit, send and be reminded."""
    roles = list(settings.config(conn, "educator.timetable_roles", ["class_teacher", "cover_educator"]))
    return [
        r["school_class_id"]
        for r in conn.execute(
            "select distinct school_class_id from staff_role_grant where staff_id = %s and role_code = any(%s)"
            " and school_class_id is not null and valid_from <= %s and (valid_to is null or valid_to >= %s)",
            (staff, roles, today, today),
        )
    ]


def may_edit(conn: db.Conn, staff: UUID, class_id: UUID, today: dt.date) -> bool:
    return class_id in held_classes(conn, staff, today)
