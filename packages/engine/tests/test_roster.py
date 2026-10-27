"""The class list (`core/roster.py`): the grade a class works at, and what loading the list changes. Nimish,
2026-09-30: "G3 roll 5 should be band G3, fix it". The database is the local copy, rolled back."""

import json
import os
import uuid
from contextlib import contextmanager

import pytest

from engine.core import db, roster

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
MIGRATION = db.REPO_ROOT / "supabase" / "migrations" / "20261018090000_g3_roll_5_is_grade_3.sql"


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _class(conn, section, bands):
    """A class in a tenant of its own, one child per band in the order given, rolls 1 up → the tenant's id."""
    tenant = conn.execute(
        "insert into tenant (slug, name) values (%s, 't') returning id", (f"t-{uuid.uuid4()}",)
    ).fetchone()["id"]
    for roll, band in enumerate(bands, 1):
        conn.execute(
            "insert into child (tenant_id, roll_no, section, band) values (%s, %s, %s, %s)",
            (tenant, str(roll), section, band),
        )
    return tenant


def _bands(conn, tenant):
    rows = conn.execute("select roll_no, band from child where tenant_id = %s", (tenant,)).fetchall()
    return {r["roll_no"]: r["band"] for r in rows}


def test_g3_roll_5_is_band_g3_once_the_migration_has_run(conn):
    """Nimish, 2026-09-30: "G3 roll 5 should be band G3, fix it". The migration moves that one child, only while they
    are still G4, and nobody else; run again, it changes nothing."""
    tenant = _class(conn, "G3", ["G3", "G3", "G3", "G3", "G4"])
    conn.execute(MIGRATION.read_text())
    assert _bands(conn, tenant) == dict.fromkeys(("1", "2", "3", "4", "5"), "G3")
    other = _class(conn, "G4", ["G4", "G4", "G4", "G4", "G4"])
    conn.execute(MIGRATION.read_text())
    assert _bands(conn, other) == dict.fromkeys(("1", "2", "3", "4", "5"), "G4"), (
        "class G4's roll 5 is not touched"
    )


def test_a_class_works_at_the_grade_most_of_its_children_are_in(conn):
    """The week's declaration took its class's grade from whichever child came first, so one child entered in the
    wrong grade could move the whole class. The class's grade is its children's most common one, the same every time:
    the slip entered first here, as G3 roll 5's might have been, does not win."""
    section = f"CLASS-{uuid.uuid4().hex[:8]}"
    tenant = _class(conn, section, ["G4", "G3", "G3", "G3", "G3"])
    assert roster.class_band(conn, section) == "G3"
    conn.execute(
        "update child set band = 'G2' where tenant_id = %s and roll_no in ('2', '3', '4')", (tenant,)
    )
    assert roster.class_band(conn, section) == "G2"
    conn.execute("update child set band = 'G3' where tenant_id = %s and roll_no = '2'", (tenant,))
    assert roster.class_band(conn, section) == "G2", "two in G2, and one each in G3 and G4"
    conn.execute("update child set active = false where tenant_id = %s", (tenant,))
    assert roster.class_band(conn, section) is None, "a class with no child in it has no grade"


def test_loading_the_class_list_names_each_child_whose_grade_it_changes(conn, tmp_path, monkeypatch):
    """The class list is the only thing that sets a child's grade. Loaded again unchanged, the list that carried the
    slip would put G4 back; the load names every grade it changes, so that cannot happen unseen."""

    class Shared:
        def __getattr__(self, name):
            return getattr(conn, name)

        def commit(self):
            pass

    monkeypatch.setattr(roster.db, "connect", contextmanager(lambda *a, **k: (yield Shared())))
    section, path = f"CLASS-{uuid.uuid4().hex[:8]}", tmp_path / "roster.json"

    def load(band):
        kids = [
            {"roll_no": r, "section": section, "band": b, "first_name": f"Kid{r}"}
            for r, b in (("1", "G3"), ("5", band))
        ]
        path.write_text(json.dumps({"children": kids}))
        return roster.load(path)

    nothing = {"kept as changed on the site": []}
    assert load("G3") == {"added": 2, "already known": 0, "grade changed": [], **nothing}
    assert load("G4") == {
        "added": 0,
        "already known": 2,
        "grade changed": [f"{section} roll 5: G3 → G4"],
        **nothing,
    }
    assert load("G4")["grade changed"] == [], "only a change is named"


def test_a_class_has_one_grade_and_the_database_says_it(conn):
    """goals/ux2-one-count-one-thing.yaml: the website took a class's grade three ways — most of its children's, the
    lowest of them, a paper's own — so a Grade 2 class's papers said "Grade 1". The rule is the database's
    (`class_band`), the engine asks it, and the two never differ: most children's grade, the lower on a tie, none for a
    class with no child."""
    section = f"CLASS-{uuid.uuid4().hex[:8]}"
    tenant = _class(conn, section, ["G4", "G3", "G3", "G2"])

    def said():
        return conn.execute("select class_band(%s, %s) as b", (tenant, section)).fetchone()["b"]

    assert said() == roster.class_band(conn, section) == "G3"
    conn.execute("update child set band = 'G2' where tenant_id = %s and roll_no = '2'", (tenant,))
    assert said() == roster.class_band(conn, section) == "G2", "two in G2, one each in G3 and G4"
    conn.execute("update child set band = 'G4' where tenant_id = %s and roll_no = '3'", (tenant,))
    assert said() == roster.class_band(conn, section) == "G2", "a tie, G2 and G4: the lower"
    conn.execute("update child set active = false where tenant_id = %s", (tenant,))
    assert said() is None and roster.class_band(conn, section) is None, "a class with no child has no grade"


def _loaded_from(conn, tmp_path, monkeypatch):
    """`roster.load` on the test's own transaction → a function that loads a list of (section, roll, grade, first name)."""

    class Shared:
        def __getattr__(self, name):
            return getattr(conn, name)

        def commit(self):
            pass

    monkeypatch.setattr(roster.db, "connect", contextmanager(lambda *a, **k: (yield Shared())))

    def load(kids):
        path = tmp_path / "roster.json"
        path.write_text(
            json.dumps(
                {
                    "children": [
                        {"section": s, "roll_no": r, "band": b, "first_name": n} for s, r, b, n in kids
                    ]
                }
            )
        )
        return roster.load(path)

    return load


def test_a_list_that_would_undo_a_grade_changed_on_the_site_is_told_so_and_leaves_it(
    conn, tmp_path, monkeypatch
):
    """goals/mov_move_a_child.yaml: the list sets a child's grade, so one loaded again after a coordinator changed a
    grade on the site would put the old one back unseen (as G3 roll 5's slip once could). It says so, and leaves it."""
    load = _loaded_from(conn, tmp_path, monkeypatch)
    section = f"CLASS-{uuid.uuid4().hex[:8]}"
    load([(section, "5", "G3", "Kid")])
    child = conn.execute("select id from child where section = %s and roll_no = '5'", (section,)).fetchone()[
        "id"
    ]
    assert conn.execute(
        "select move_child(%s, 'G4', %s, '5', 'coordinator@cornerstone.test', '') as r", (child, section)
    )
    said = load([(section, "5", "G3", "Kid")])
    assert conn.execute("select band from child where id = %s", (child,)).fetchone()["band"] == "G4", (
        "left as set"
    )
    [line] = said["kept as changed on the site"]
    assert line.startswith(f"{section} roll 5: set to G4 on ") and "the file says G3" in line
    assert said["grade changed"] == []
    # the list brought up to date says nothing
    assert load([(section, "5", "G4", "Kid")])["kept as changed on the site"] == []


def test_a_list_that_still_names_the_place_a_child_moved_from_makes_no_second_child(
    conn, tmp_path, monkeypatch
):
    """Loading matches on class and roll, so the old list would make a new child where the moved one used to sit,
    with the same name and none of their answers. It is told, and no row is made."""
    load = _loaded_from(conn, tmp_path, monkeypatch)
    old, new = (f"CLASS-{uuid.uuid4().hex[:8]}" for _ in range(2))
    load([(old, "7", "G3", "Kid"), (new, "1", "G4", "Other")])
    child = conn.execute("select id from child where section = %s and roll_no = '7'", (old,)).fetchone()["id"]
    conn.execute("select move_child(%s, 'G4', %s, '12', 'coordinator@cornerstone.test', '')", (child, new))
    before = conn.execute("select count(*) as n from child").fetchone()["n"]
    said = load([(old, "7", "G3", "Kid"), (new, "1", "G4", "Other")])
    assert conn.execute("select count(*) as n from child").fetchone()["n"] == before
    [line] = said["kept as changed on the site"]
    assert line.startswith(f"{old} roll 7: moved to {new} roll 12 (G4) on ")
    assert said["added"] == 0
