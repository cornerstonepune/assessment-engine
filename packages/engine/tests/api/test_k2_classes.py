# ruff: noqa: F811, F401  (fixtures are imported by name and used as arguments)
"""M1-17: which classes the K2 pictures list for a person (`POST /k2/classes`). Her own, by her open grants; and for the staff
preview (D-076, `educator.preview_roles`), who holds no class, also every class whose timetable is in force today: the same
rule the timetable preview uses. Reads only. Placeholder people; the database is the local copy, rolled back."""

from tests.test_educator_gate import _head
from tests.test_k2_day import conn, world
from tests.voice_rows import a_k2_class


def _voice(w, on: bool):
    w["conn"].execute(
        "update config set value = %s::jsonb where key = 'voice.screens_enabled'",
        ("true" if on else "false",),
    )


def _in_force_today(w):
    """The loaded fortnight starts later; the preview lists classes whose timetable is in force today."""
    w["conn"].execute(
        "update timetable_slot set valid_from = current_date - 1, valid_to = null where school_class_id = %s",
        (w["k"]["class"],),
    )


def _ids(r) -> list[str]:
    assert r.status_code == 200, r.text
    return [c["id"] for c in r.json()["classes"]]


def test_a_previewer_with_no_class_is_offered_every_class_with_a_timetable_while_the_switch_is_off(world):
    _voice(world, False)
    _in_force_today(world)
    head = _head(world)  # a campus-wide grant, no class of their own
    got = world["client"].post("/k2/classes", json={"actor": head})
    assert world["k"]["class"] in _ids(got)
    one = next(c for c in got.json()["classes"] if c["id"] == world["k"]["class"])
    assert set(one) == {"id", "grade", "section"} and one["grade"] == "K2", "nothing but what a list needs"


def test_an_educator_is_offered_only_her_own_classes_never_another_that_has_a_timetable(world):
    _voice(world, True)
    mine = a_k2_class(world["conn"])  # another educator, with a class of her own and no timetable
    assert _ids(world["client"].post("/k2/classes", json={"actor": mine["email"]})) == [mine["class"]]
    # the first class is timetabled and hers alone: it is not offered to her
    assert world["k"]["class"] not in _ids(world["client"].post("/k2/classes", json={"actor": mine["email"]}))
    assert _ids(world["client"].post("/k2/classes", json={"actor": world["k"]["email"]})) == [
        world["k"]["class"]
    ]


def test_the_switch_off_still_refuses_an_educator_and_a_sign_in_not_on_the_staff_list(world):
    _voice(world, False)
    for actor in (world["k"]["email"], "nobody@example.test"):
        r = world["client"].post("/k2/classes", json={"actor": actor})
        assert (r.status_code, r.json()["detail"]) == (403, "Voice notes are not switched on."), actor


def test_a_previewer_who_also_holds_a_class_gets_it_once(world):
    _voice(world, False)
    _in_force_today(world)
    k = world["k"]
    world["conn"].execute(
        "insert into staff_role_grant (tenant_id, staff_id, role_code, valid_from, granted_by)"
        " values (%s, %s, 'head', current_date - 1, 'test')",
        (k["tenant"], k["staff"]),
    )  # her class, and a preview role besides
    ids = _ids(world["client"].post("/k2/classes", json={"actor": k["email"]}))
    assert ids.count(k["class"]) == 1


def test_a_class_whose_timetable_has_ended_is_not_offered_to_the_preview(world):
    _voice(world, False)
    _in_force_today(world)
    assert world["k"]["class"] in _ids(world["client"].post("/k2/classes", json={"actor": _head(world)}))
    world["conn"].execute(
        "update timetable_slot set valid_to = current_date - 1, valid_from = least(valid_from, current_date - 2)"
        " where school_class_id = %s",
        (world["k"]["class"],),
    )
    assert world["k"]["class"] not in _ids(world["client"].post("/k2/classes", json={"actor": _head(world)}))
