"""The rules the migrations make, and whether live holds them (goals/l3b-live-says-what-went-wrong.yaml).

Live, 2026-10-14 (L3): Make papers refused every paper made for one child. Live recorded the migration that lets a
paper be made for a child, yet its rule (`sheet_template_source_check`) still lacked it, so a recorded migration is no
proof the rule is there. The rules every migration leaves are kept beside the engine (`engine/checks/rules.json`,
written by `engine live rules --write` from a database built from the migrations alone), and the watcher names any
rule live holds otherwise, within ten minutes.
"""

import os

import pytest

from engine.checks import rules, watch
from engine.core import db

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
PLENTY = 10**12  # bytes free: the disk is not what these tests look at


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def test_the_rules_kept_beside_the_engine_are_the_ones_the_migrations_make(conn):
    """The test database is built from the migrations (CI: `bin/testdb fresh`), so its rules are the migrations'."""
    assert rules.drift(conn) == [], (
        "rules.json is not what the migrations make: run `engine live rules --write`"
    )
    assert "sheet_template.sheet_template_source_check" in rules.expected()


def test_the_watcher_names_a_rule_live_holds_otherwise(conn):
    """Live's state on 2026-10-14, made again: the rule for which papers a sheet may be, without a paper for one
    child. The watcher names that rule; it names no child, id or address."""
    assert not [p for p in watch.problems(conn, PLENTY) if "rule" in p]
    conn.execute("alter table sheet_template drop constraint sheet_template_source_check")
    conn.execute(
        "alter table sheet_template add constraint sheet_template_source_check"
        " check (source in ('generated', 'legacy', 'library')) not valid"
    )
    said = [p for p in watch.problems(conn, PLENTY) if "rule" in p]
    assert said and all("sheet_template_source_check" in p for p in said), said
    assert "migrations" in said[0]


ATTIC = db.REPO_ROOT / "supabase" / "migrations" / "20261111090000_a_table_made_by_hand_goes_to_the_attic.sql"


def test_a_table_made_on_live_by_hand_goes_to_the_attic_with_its_rows(conn):
    """Live, 2026-10-15: the watcher's first look named five rules of `item_placement`, a table made on live by hand
    that nothing reads (rule 9; 20261007090000 let go of its hold on skill_set). Nimish: "move item_placement to attic
    too". Where it is absent — every database built from the migrations — nothing happens. Made here as live holds
    it, it moves out of the school's tables with its row, and the watcher names no rule."""
    conn.execute(ATTIC.read_text())
    assert conn.execute("select to_regclass('attic.item_placement') is null as absent").fetchone()["absent"]
    conn.execute(
        "create table public.item_placement (id uuid primary key default gen_random_uuid(),"
        " tenant_id uuid not null references tenant (id), item_id uuid not null references item (id),"
        " skill_set_code text not null, difficulty text not null"
        " check (difficulty in ('Easy', 'Medium', 'Hard', 'Advance')), unique (item_id, skill_set_code, difficulty))"
    )
    conn.execute(
        "insert into item_placement (tenant_id, item_id, skill_set_code, difficulty)"
        " select tenant_id, id, skill_set_code, 'Easy' from item where skill_set_code is not null limit 1"
    )
    assert [p for p in watch.problems(conn, PLENTY) if "item_placement" in p], "live's state, made again"
    conn.execute(ATTIC.read_text())
    assert conn.execute("select to_regclass('public.item_placement') is null as moved").fetchone()["moved"]
    assert conn.execute("select count(*) as n from attic.item_placement").fetchone()["n"] == 1, (
        "its rows are kept"
    )
    assert not [p for p in watch.problems(conn, PLENTY) if "rule" in p]
