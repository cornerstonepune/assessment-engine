"""Versioned rules and provenance (W1 gate 4, amended; external proposal §15).

"Why did the engine give this child this question on that date?" must be answerable from data
after someone edits a band. That means an edit files the old rule rather than overwriting it,
and every item says which version, generator, prompt and model made it.
"""

import json
import os

import pytest

from engine import bank, db

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

SET = "SUB.2D.EXCH"


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _edit_rule(conn, code, words):
    row = conn.execute("select difficulty from skill_set where code = %s", (code,)).fetchone()
    d = dict(row["difficulty"])
    d["Hard"] = {**d["Hard"], "words": words}
    conn.execute("update skill_set set difficulty = %s where code = %s", (json.dumps(d), code))


def test_editing_a_rule_files_the_old_one_and_bumps_the_version(conn):
    before = conn.execute("select version from skill_set where code = %s", (SET,)).fetchone()["version"]
    _edit_rule(conn, SET, "edited by a test")
    after = conn.execute("select version, difficulty from skill_set where code = %s", (SET,)).fetchone()
    assert after["version"] == before + 1
    filed = conn.execute(
        "select version, difficulty from skill_set_version where code = %s order by version desc limit 1",
        (SET,),
    ).fetchone()
    assert filed["version"] == before
    assert filed["difficulty"]["Hard"]["words"] != "edited by a test", "the OLD rule is what is filed"


def test_editing_a_rule_withdraws_its_ratification(conn):
    """Aseem approved the rule he read. A changed rule has not been approved by anyone."""
    conn.execute("update skill_set set status = 'ratified', ratified_by = 'aseem' where code = %s", (SET,))
    _edit_rule(conn, SET, "changed after ratification")
    row = conn.execute("select status, ratified_by from skill_set where code = %s", (SET,)).fetchone()
    assert (row["status"], row["ratified_by"]) == ("draft", None)


def test_ratifying_is_not_an_edit_and_does_not_bump_the_version(conn):
    before = conn.execute("select version from skill_set where code = %s", (SET,)).fetchone()["version"]
    conn.execute("update skill_set set status = 'ratified', ratified_by = 'aseem' where code = %s", (SET,))
    after = conn.execute("select version from skill_set where code = %s", (SET,)).fetchone()["version"]
    assert after == before, "approving a rule is not writing a new one"


def test_a_generated_item_records_what_made_it(conn):
    counts, accepted = bank.fill_native(conn, "WORD.BUDGET", "Easy", 2)
    assert counts["accepted"] == 2
    row = conn.execute(
        "select skill_set_version, generator, eval_type from item where item_key = %s", (accepted[0].item_id,)
    ).fetchone()
    assert row["skill_set_version"] >= 1
    assert row["generator"] == "native:word_budget"


def test_the_offline_sampler_records_itself_as_the_generator(conn):
    counts, _, accepted = bank.fill(conn, SET, "Hard", 2, offline=True)
    if counts["accepted"] == 0:
        pytest.skip("unit is at its ceiling; nothing new to attribute")
    row = conn.execute(
        "select generator, model from item where item_key = %s", (accepted[0].item_id,)
    ).fetchone()
    assert row["generator"].startswith("sampled:")
    assert row["model"] is None, "no model was called, so no model is claimed"
