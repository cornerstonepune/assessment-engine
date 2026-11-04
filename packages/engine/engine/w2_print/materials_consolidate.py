"""The school's consolidated materials list for a month (task M1-16; D-074: "the system collates requirements from all the
teachers"). Built by code, never a model, from every class's list (M1-10): each catalogue item summed over the classes,
every line keeping which classes and activities it comes from. A class that gives no quantity makes the total unknown
("to confirm"), never a smaller number. Each build is kept, so the next one shows what changed."""

import datetime as dt
from typing import Any
from uuid import UUID

from engine.core import db, settings
from engine.w2_print import materials_coverage as coverage
from engine.w2_print.materials_list import num


def _total(quantities: list[Any]) -> Any:
    """The sum, or None when any part is unknown: a total with a part missing is not a smaller number."""
    return None if None in quantities else sum(quantities)


def _kept_lists(
    conn: db.Conn, tenant: UUID, lo: dt.date, hi: dt.date
) -> tuple[list[dict[str, Any]], list[UUID]]:
    """Each class's lists that touch the month. Two lists of one class that overlap (a week inside a fortnight) would
    count the same need twice: the widest is kept, and any list that overlaps one already kept is skipped and named."""
    lists = conn.execute(
        "select id, school_class_id, from_on, to_on from materials_list where tenant_id = %s"
        " and from_on <= %s and to_on >= %s order by school_class_id, (to_on - from_on) desc, id",
        (tenant, hi, lo),
    ).fetchall()
    kept: list[dict[str, Any]] = []
    skipped: list[UUID] = []
    for lst in lists:
        clash = any(
            k["school_class_id"] == lst["school_class_id"]
            and k["from_on"] <= lst["to_on"]
            and lst["from_on"] <= k["to_on"]
            for k in kept
        )
        if clash:
            skipped.append(lst["id"])
        else:
            kept.append(lst)
    return kept, skipped


def _gather(
    conn: db.Conn, tenant: UUID, lo: dt.date, hi: dt.date
) -> tuple[dict[str, dict[str, Any]], list[UUID]]:
    """{material_code: {unit, quantity | None, from: {class_id: {quantity, activity_codes}}}} and the lists skipped."""
    kept, skipped = _kept_lists(conn, tenant, lo, hi)
    out: dict[str, dict[str, Any]] = {}
    for lst in kept:
        for ln in conn.execute(
            "select l.id, l.material_code, l.quantity, i.unit, coalesce(array_agg(distinct s.activity_code)"
            " filter (where s.activity_code is not null), '{}') as acts, l.activity_code"
            " from materials_line l join material_item i on i.tenant_id = l.tenant_id and i.code = l.material_code"
            " left join materials_line_source s on s.line_id = l.id"
            " where l.list_id = %s and l.removed_at is null and l.needed_on between %s and %s"
            " group by l.id, i.unit",
            (lst["id"], lo, hi),
        ):
            item = out.setdefault(ln["material_code"], {"unit": ln["unit"], "from": {}})
            acts = sorted(set(ln["acts"]) | ({ln["activity_code"]} if ln["activity_code"] else set()))
            mine = item["from"].get(lst["school_class_id"])
            if mine is None:
                item["from"][lst["school_class_id"]] = {"quantity": ln["quantity"], "activity_codes": acts}
            else:  # one class, two lists in the month: its needs add up
                mine["quantity"] = _total([mine["quantity"], ln["quantity"]])
                mine["activity_codes"] = sorted(set(mine["activity_codes"]) | set(acts))
    for item in out.values():
        item["quantity"] = _total([f["quantity"] for f in item["from"].values()])
    return out, skipped


def build(conn: db.Conn, tenant: UUID, lo: dt.date, hi: dt.date) -> UUID:
    """Make a new build of the school's list for `lo`..`hi` (one per call) and note what moved since the one before."""
    if hi < lo:
        raise ValueError("The last day is before the first day.")
    cons = db.one(
        conn,
        "insert into materials_consolidated (tenant_id, from_on, to_on) values (%s, %s, %s)"
        " on conflict (tenant_id, from_on, to_on) do update set updated_at = now() returning id, latest_build, skipped_lists",
        (tenant, lo, hi),
    )
    cid, before, now = cons["id"], cons["latest_build"], cons["latest_build"] + 1
    items, skipped = _gather(conn, tenant, lo, hi)
    if (
        before
        and _shape(items) == _stored_shape(conn, cid, before)
        and skipped == list(cons["skipped_lists"])
    ):
        return cid  # nothing moved: no new build, so no rows and no empty "what changed"
    for code, item in items.items():
        conn.execute(
            "insert into materials_consolidated_line (tenant_id, consolidated_id, build, material_code, unit, quantity,"
            " to_confirm) values (%s, %s, %s, %s, %s, %s, %s)",
            (tenant, cid, now, code, item["unit"], item["quantity"], item["quantity"] is None),
        )
        for klass, f in item["from"].items():
            conn.execute(
                "insert into materials_consolidated_source (consolidated_id, build, material_code, class_id, quantity,"
                " activity_codes) values (%s, %s, %s, %s, %s, %s)",
                (cid, now, code, klass, f["quantity"], f["activity_codes"]),
            )
    if before:
        _note_changes(conn, tenant, cid, before, now)
    conn.execute(
        "update materials_consolidated set latest_build = %s, built_at = now(), skipped_lists = %s where id = %s",
        (now, skipped, cid),
    )
    return cid


def _shape(items: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """What a build says, in a form two builds can be compared in."""
    return {
        code: (
            item["unit"],
            item["quantity"],
            {c: (f["quantity"], tuple(f["activity_codes"])) for c, f in item["from"].items()},
        )
        for code, item in items.items()
    }


def _stored_shape(conn: db.Conn, cid: UUID, build_: int) -> dict[str, Any]:
    out: dict[str, Any] = {
        r["material_code"]: (r["unit"], r["quantity"], {})
        for r in conn.execute(
            "select material_code, unit, quantity from materials_consolidated_line"
            " where consolidated_id = %s and build = %s",
            (cid, build_),
        )
    }
    for r in conn.execute(
        "select material_code, class_id, quantity, activity_codes from materials_consolidated_source"
        " where consolidated_id = %s and build = %s",
        (cid, build_),
    ):
        out[r["material_code"]][2][r["class_id"]] = (r["quantity"], tuple(r["activity_codes"]))
    return out


def _totals(conn: db.Conn, cid: UUID, build_: int) -> dict[str, tuple[Any, dict[UUID, Any]]]:
    totals = {
        r["material_code"]: (r["quantity"], {})
        for r in conn.execute(
            "select material_code, quantity from materials_consolidated_line where consolidated_id = %s and build = %s",
            (cid, build_),
        )
    }
    for r in conn.execute(
        "select material_code, class_id, quantity from materials_consolidated_source"
        " where consolidated_id = %s and build = %s",
        (cid, build_),
    ):
        totals[r["material_code"]][1][r["class_id"]] = r["quantity"]
    return totals


def _note_changes(conn: db.Conn, tenant: UUID, cid: UUID, before: int, now: int) -> None:
    old, new = _totals(conn, cid, before), _totals(conn, cid, now)
    for code in sorted(set(old) | set(new)):
        if code not in old:
            kind, was, is_ = "added", None, new[code][0]
        elif code not in new:
            kind, was, is_ = "removed", old[code][0], None
        elif old[code][0] != new[code][0]:
            kind, was, is_ = "quantity", old[code][0], new[code][0]
        else:
            continue
        was_by, now_by = old.get(code, (None, {}))[1], new.get(code, (None, {}))[1]
        classes = sorted(c for c in was_by.keys() | now_by.keys() if was_by.get(c) != now_by.get(c))
        conn.execute(
            "insert into materials_consolidated_change (tenant_id, consolidated_id, build, material_code, kind, before,"
            " after, class_ids) values (%s, %s, %s, %s, %s, %s, %s, %s)",
            (tenant, cid, now, code, kind, was, is_, classes),
        )


def read(conn: db.Conn, cid: UUID) -> dict[str, Any]:
    cons = db.one(conn, "select * from materials_consolidated where id = %s", (cid,))
    build_ = cons["latest_build"]
    names = coverage.class_names(conn, cons["tenant_id"])
    sources: dict[str, list[dict[str, Any]]] = {}
    for r in conn.execute(
        "select material_code, class_id, quantity, activity_codes from materials_consolidated_source"
        " where consolidated_id = %s and build = %s order by class_id",
        (cid, build_),
    ):
        sources.setdefault(r["material_code"], []).append(
            {
                "class_id": r["class_id"],
                "class": names.get(r["class_id"], ""),
                "quantity": num(r["quantity"]),
                "activity_codes": list(r["activity_codes"]),
            }
        )
    lines = [
        {
            "material_code": r["material_code"],
            "item": r["name"],
            "quantity": num(r["quantity"]),
            "unit": r["unit"],
            "to_confirm": r["to_confirm"],
            "from": sources.get(r["material_code"], []),
        }
        for r in conn.execute(
            "select l.material_code, i.name, l.quantity, l.unit, l.to_confirm from materials_consolidated_line l"
            " join material_item i on i.tenant_id = l.tenant_id and i.code = l.material_code"
            " where l.consolidated_id = %s and l.build = %s order by i.name",
            (cid, build_),
        )
    ]
    changes = [
        {
            "kind": r["kind"],
            "material_code": r["material_code"],
            "item": r["name"],
            "before": num(r["before"]),
            "after": num(r["after"]),
            "class_ids": list(r["class_ids"]),
            "at": r["at"],
        }
        for r in conn.execute(
            "select c.*, i.name from materials_consolidated_change c join material_item i"
            " on i.tenant_id = c.tenant_id and i.code = c.material_code where c.consolidated_id = %s and c.build = %s"
            " order by i.name",
            (cid, build_),
        )
    ]
    return {
        "id": cid,
        "from": cons["from_on"],
        "to": cons["to_on"],
        "build": build_,
        "lines": lines,
        "changes": changes,
        "skipped_lists": list(cons["skipped_lists"]),
    }


def may_consolidate(conn: db.Conn, staff: UUID, today: dt.date) -> bool:
    """Whether she holds an open grant, on the school's `today`, in a role that builds and sends the school's list
    (`materials.consolidate_roles`, a config row). A class is not needed: these are campus-wide roles."""
    roles = list(settings.config(conn, "materials.consolidate_roles", ["coordinator", "head"]))
    held = conn.execute(
        "select 1 from staff_role_grant where staff_id = %s and role_code = any(%s)"
        " and valid_from <= %s and (valid_to is null or valid_to >= %s)",
        (staff, roles, today, today),
    ).fetchone()
    return held is not None
