"""One question on its own: every kind in the bank can be printed again, a question's printed block
comes back as an image, and a person can reword a question but never make its key wrong. Against
the real schema, in a transaction that is rolled back.
"""

import os

import pytest
from playwright.sync_api import sync_playwright

from engine.assess import render
from engine.assess.pick import Sheet
from engine.core import db
from engine.w1_bank import inventory, question
from engine.w2_print import library

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

BY = "tester@example.org"


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _row(conn, fmt):
    return conn.execute(
        "select * from item where status = 'active' and source = 'generated' and fmt = %s order by item_key limit 1",
        (fmt,),
    ).fetchone()


def _status(conn, item_id):
    return conn.execute("select status from item where id = %s", (item_id,)).fetchone()["status"]


def test_every_kind_in_the_bank_can_be_printed_again(conn):
    """Eight of the twelve kinds once failed here: a stored question could not be turned back into
    something the printer understands, so no paper could be made from any of them."""
    rows = conn.execute(
        "select distinct on (fmt) * from item where status = 'active' and source = 'generated' order by fmt, item_key"
    ).fetchall()
    assert len(rows) >= 12
    for r in rows:
        it = inventory.item_from_row(r)
        block = render.render_item(Sheet("CS000000", "G3", r["difficulty"], 1, "test", [it]), it, 1)
        assert f'data-item="{r["item_key"]}"' in block, r["fmt"]


def test_a_questions_printed_block_comes_back_as_an_image(conn):
    assert question.printed(conn, _row(conn, "word_2step")["item_key"])[:8] == b"\x89PNG\r\n\x1a\n"
    assert question.printed(conn, "no-such-question") is None


def test_rewording_keeps_every_number_answer_and_mistake_and_retires_the_old_wording(conn):
    old = _row(conn, "word_1step")
    child = conn.execute("select id, tenant_id from child limit 1").fetchone()
    conn.execute(
        "insert into item_exposure (tenant_id, child_id, item_id, week) values (%s, %s, %s, 'test-week')",
        (child["tenant_id"], child["id"], old["id"]),
    )
    reworded = "Read carefully. " + old["stem"]

    out = question.correct(conn, old["item_key"], reworded, BY, "clearer wording")

    new = conn.execute("select * from item where item_key = %s", (out["item_key"],)).fetchone()
    assert new["stem"] == reworded and new["status"] == "active"
    assert (new["spec"], new["responses"], new["tags"]) == (old["spec"], old["responses"], old["tags"])
    assert new["corrected_from"] == old["id"] and new["generator"] == "correction"
    assert _status(conn, old["id"]) == "retired"
    note = conn.execute("select actor, note from item_feedback where item_id = %s", (old["id"],)).fetchone()
    assert note["actor"] == BY and out["item_key"] in note["note"] and "clearer wording" in note["note"]
    seen = conn.execute(
        "select week from item_exposure where item_id = %s and child_id = %s", (new["id"], child["id"])
    ).fetchone()
    assert seen and seen["week"] == "test-week", "a child who saw the old wording has seen this question"


@pytest.mark.parametrize(
    "fmt, reword, reason, refused_for",
    [
        ("word_1step", lambda s: s + " There are 98765 more.", "a reason", "number"),
        ("word_1step", lambda s: s + " Do not borrow.", "a reason", "exchange"),
        ("word_1step", lambda s: s, "a reason", "same"),
        ("word_1step", lambda s: "Read carefully. " + s, " ", "reason"),
        ("bare_sum", lambda s: "Work out:", "a reason", "numbers alone"),
    ],
)
def test_a_correction_that_could_make_the_key_wrong_is_refused_and_changes_nothing(
    conn, fmt, reword, reason, refused_for
):
    old = _row(conn, fmt)
    with pytest.raises(ValueError, match=refused_for):
        question.correct(conn, old["item_key"], reword(old["stem"]), BY, reason)
    assert _status(conn, old["id"]) == "active"
    made = conn.execute("select count(*) as n from item where corrected_from = %s", (old["id"],)).fetchone()
    assert made["n"] == 0


def test_a_removed_question_cannot_be_corrected(conn):
    old = _row(conn, "word_1step")
    inventory.flag(conn, old["item_key"], BY, "removed first")
    with pytest.raises(ValueError, match="ready to print"):
        question.correct(conn, old["item_key"], "Read carefully. " + old["stem"], BY, "too late")


def test_a_number_wall_keeps_every_answer_box_inside_its_brick(conn):
    """24 mm bricks once drew a three-digit answer's four boxes over the neighbouring brick. Measured
    in a browser, on the wall in the bank with the longest answer."""
    row = conn.execute(
        "select i.*, r.band from item i join rung r on r.tenant_id = i.tenant_id and r.code = i.rung_code"
        " where i.fmt = 'number_wall' and i.status = 'active' order by"
        " (select max(length(x ->> 'answer')) from jsonb_array_elements(i.responses) x) desc, i.item_key limit 1"
    ).fetchone()
    it = inventory.item_from_row(row)
    block = render.render_item(Sheet("CS000000", row["band"], row["difficulty"], 1, "test", [it]), it, 1)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        tab = browser.new_page()
        tab.set_content(f"<style>{render.CSS}</style>{block}")
        spills = tab.evaluate(
            """() => [...document.querySelectorAll('.wall .b')].filter(b => {
                 const o = b.getBoundingClientRect();
                 return [...b.querySelectorAll('.cell')].some(c => {
                   const r = c.getBoundingClientRect();
                   return r.left < o.left - 1 || r.right > o.right + 1;
                 });
               }).length"""
        )
        browser.close()
    assert spills == 0


# ---- a question on a worksheet (ADR 0026): the worksheet never holds a question that left the bank


def _on_a_worksheet(conn):
    library.build(conn)
    return conn.execute(
        "select i.item_key, i.id, t.code from item i join sheet_template t on i.id = any(t.item_ids)"
        " where t.source = 'library' and t.retired_at is null and i.fmt = 'word_1step' and i.status = 'active'"
        " and i.skill_set_code = 'ADD.2D2D' and i.difficulty = 'Easy' order by i.item_key limit 1"
    ).fetchone()


def _live_worksheets_of(conn, item_id):
    return [
        r["code"]
        for r in conn.execute(
            "select code from sheet_template where source = 'library' and retired_at is null and %s = any(item_ids)",
            (item_id,),
        ).fetchall()
    ]


def test_rewording_a_question_moves_it_onto_a_new_worksheet_and_retires_the_old_one(conn):
    q = _on_a_worksheet(conn)
    stem = conn.execute("select stem from item where id = %s", (q["id"],)).fetchone()["stem"]
    new = question.correct(
        conn, q["item_key"], stem.replace("How many", "Altogether, how many"), BY, "clearer"
    )
    assert _live_worksheets_of(conn, q["id"]) == []
    new_id = conn.execute("select id from item where item_key = %s", (new["item_key"],)).fetchone()["id"]
    assert len(_live_worksheets_of(conn, new_id)) == 1
    assert library.check(conn)[1] == {}


def test_removing_a_question_retires_its_worksheet_and_every_other_question_stays_on_one(conn):
    q = _on_a_worksheet(conn)
    question.remove(conn, q["item_key"], BY, "a duplicate of another question")
    assert _status(conn, q["id"]) == "retired"
    assert _live_worksheets_of(conn, q["id"]) == []
    assert library.check(conn)[1] == {}
