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
