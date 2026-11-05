# ruff: noqa: F811, F401  (fixtures are imported by name and used as arguments)
"""The staff preview of the educator's screens (D-076): while `educator.timetable_enabled` is off, a member of staff
whose open grant is in a role `educator.preview_roles` names (head, coordinator) sees them; nobody else does. A
previewer who holds no class sees every class with a timetable. One rule (`w2_print/educator_gate.py`) for the
timetable and the materials routes. Placeholder people only; the database is the local copy, rolled back."""

import uuid

from tests.test_k2_day import call, conn, world


def _switch(w, on: bool):
    w["conn"].execute(
        "update config set value = %s::jsonb where key = 'educator.timetable_enabled'",
        ("true" if on else "false",),
    )


def _head(w, role="head") -> str:
    """A member of staff with a campus-wide grant (no class) in `role`; their email."""
    c, k = w["conn"], w["k"]
    campus = c.execute("select campus_id from school_class where id = %s", (k["class"],)).fetchone()[
        "campus_id"
    ]
    staff = c.execute(
        "insert into staff (tenant_id, campus_id) values (%s, %s) returning id", (k["tenant"], campus)
    ).fetchone()["id"]
    email = f"placeholder.head.{uuid.uuid4().hex[:6]}@example.test"
    c.execute(
        "insert into pii.staff (tenant_id, staff_id, name, email) values (%s, %s, 'Placeholder Head', %s)",
        (k["tenant"], staff, email),
    )
    c.execute(
        "insert into staff_role_grant (tenant_id, staff_id, role_code, valid_from, granted_by)"
        " values (%s, %s, %s, current_date - 1, 'test')",
        (k["tenant"], staff, role),
    )
    return email


def test_with_the_switch_off_the_educator_is_refused_and_a_head_previews_her_classes_timetable(world):
    _switch(world, False)
    refused = call(world, "day", day="2026-11-23")
    assert (refused.status_code, refused.json()["detail"]) == (403, "The timetable is not switched on.")
    head = _head(world)
    seen = call(world, "day", actor=head, day="2026-11-23", class_id=world["k"]["class"])
    assert seen.status_code == 200, seen.text
    assert seen.json()["class"]["id"] == world["k"]["class"] and len(seen.json()["periods"]) == 15
    assert any(
        c["id"] == world["k"]["class"]
        for c in call(world, "week", actor=head, day="2026-11-23").json()["classes"]
    )


def test_a_role_not_named_previews_nothing_and_the_roles_are_a_config_row(world):
    _switch(world, False)
    ops = _head(world, "ops")
    assert call(world, "day", actor=ops, day="2026-11-23").status_code == 403
    world["conn"].execute(
        "insert into config (tenant_id, key, value, description) values (%s, 'educator.preview_roles', '[\"ops\"]', 't')"
        " on conflict (tenant_id, key) do update set value = excluded.value",
        (world["k"]["tenant"],),
    )
    assert call(world, "day", actor=ops, day="2026-11-23", class_id=world["k"]["class"]).status_code == 200


def test_with_the_switch_on_the_educator_sees_her_own_class_as_before(world):
    _switch(world, True)
    r = call(world, "day", day="2026-11-23")
    assert r.status_code == 200 and r.json()["class"]["id"] == world["k"]["class"]


def test_the_materials_routes_open_to_a_previewer_and_stay_shut_to_the_educator_while_the_switch_is_off(
    world,
):
    _switch(world, False)
    post = lambda actor: world["client"].post("/materials/catalogue/list", json={"actor": actor})  # noqa: E731
    assert post(world["k"]["email"]).status_code == 403
    assert post(_head(world)).status_code == 200


def test_once_switched_on_a_head_sees_only_classes_they_hold_and_a_preview_adds_no_catalogue_item(world):
    _switch(world, True)
    head = _head(world)
    assert (
        call(world, "day", actor=head, day="2026-11-23").status_code == 403
    )  # holds none, and the preview is over
    _switch(world, False)
    r = world["client"].post("/materials/catalogue/propose", json={"actor": head, "name": "Placeholder glue"})
    assert (r.status_code, r.json()["detail"]) == (
        403,
        "The timetable is not switched on.",
    )  # a preview changes nothing


def test_a_preview_offers_only_classes_whose_timetable_is_in_force_on_the_day_asked(world):
    _switch(world, False)
    head = _head(world)
    world["conn"].execute(
        "update timetable_slot set valid_to = valid_from where school_class_id = %s", (world["k"]["class"],)
    )
    r = call(world, "day", actor=head, day="2026-11-25")  # after every slot ended
    assert r.status_code == 403 or all(c["id"] != world["k"]["class"] for c in r.json()["classes"])


def test_the_site_can_ask_whether_the_educators_screens_are_open_to_this_person(world):
    """One question for a screen that reads no timetable (the activity page): open or not, and whether as a preview."""
    _switch(world, False)
    assert call(world, "open").status_code == 403
    assert call(world, "open", actor=_head(world)).json() == {"previewing": True}
    assert call(world, "open", actor="nobody@example.test").status_code == 403
    _switch(world, True)
    assert call(world, "open").json() == {"previewing": False}


def _materials_rows(c) -> dict[str, int]:
    """How many rows each materials table holds: a preview must leave every one as it was."""
    names = [
        r["table_name"]
        for r in c.execute(
            "select table_name from information_schema.tables where table_schema = 'public'"
            " and table_name like 'materials%%' and table_type = 'BASE TABLE' order by 1"
        ).fetchall()
    ]
    return {n: c.execute(f"select count(*) as n from {n}").fetchone()["n"] for n in names}  # noqa: S608


def _a_material(w):
    """A catalogue item of the test's own for an activity Fortnight 10 plans (the dustbin, week B)."""
    w["conn"].execute(
        "insert into material_item (tenant_id, code, name, unit) values (%s, 'MAT-PV-1', 'Placeholder dustbin', 'piece')"
        " on conflict do nothing",
        (w["k"]["tenant"],),
    )
    w["conn"].execute(
        "insert into activity_material (tenant_id, activity_code, material_code, quantity, ord)"
        " select %s, a.code, 'MAT-PV-1', 1, 1 from activity a join plan_entry pe on pe.activity_id = a.id"
        " where pe.school_class_id = %s limit 1 on conflict do nothing",
        (w["k"]["tenant"], w["k"]["class"]),
    )


def test_a_previewer_sees_a_class_and_the_schools_list_worked_out_and_nothing_is_saved(world):
    """While switched off, the preview is shown real lists: worked out as they would be built, then not kept."""
    _switch(world, False)
    _a_material(world)
    head, conn = _head(world), world["conn"]
    before = _materials_rows(conn)
    span = {"from": "2026-11-23", "to": "2026-12-06"}
    got = world["client"].post(
        "/materials/build",
        json={
            "actor": head,
            "class_id": str(world["k"]["class"]),
            "period": "fortnight",
            "group_by": "day",
            **span,
        },
    )
    assert got.status_code == 200, got.text
    assert any(ln["item"] == "Placeholder dustbin" for g in got.json()["groups"] for ln in g["lines"])
    school = world["client"].post("/materials/school/build", json={"actor": head, **span})
    assert school.status_code == 200, school.text
    assert any(ln["item"] == "Placeholder dustbin" for ln in school.json()["lines"])
    assert _materials_rows(conn) == before  # nothing kept: no list, no line, no reminder, no school list


def test_the_educator_still_cannot_build_a_list_while_the_switch_is_off(world):
    _switch(world, False)
    r = world["client"].post(
        "/materials/build",
        json={
            "actor": world["k"]["email"],
            "class_id": str(world["k"]["class"]),
            "period": "day",
            "from": "2026-11-23",
            "to": "2026-11-23",
        },
    )
    assert (r.status_code, r.json()["detail"]) == (403, "The timetable is not switched on.")
