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
