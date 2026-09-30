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

    assert load("G3") == {"added": 2, "already known": 0, "grade changed": []}
    assert load("G4") == {"added": 0, "already known": 2, "grade changed": [f"{section} roll 5: G3 → G4"]}
    assert load("G4")["grade changed"] == [], "only a change is named"
