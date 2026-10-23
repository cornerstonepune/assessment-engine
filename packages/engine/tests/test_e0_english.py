"""English, Grades 3 and 4, in the system as drafts (goals/e0-english-in-the-system.yaml, BUILD-ORDER "E0").

Nimish, 2026-10-22: "Ayush is a part of Cornerstone... he'll log into the system and all his responses will be logged in
properly". The seed rows of PR #254 and #272 are counted against the tables `engine load` fills, an English kind or level
is never drawn before a person approves it, and an approval keeps the person's name and the date. Each test runs on the
local copy and rolls back what it writes.
"""

import json
import os

import pytest

from engine.core import db, english, loaders
from engine.w1_bank import question_types

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs the local copy (bin/testdb)")

SEED = db.REPO_ROOT / "supabase" / "seed"


def rows(name: str, key: str) -> list[dict]:
    return english.seed(name, key)


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def one(conn, sql, *params):
    return next(iter(conn.execute(sql, params or None).fetchone().values()))


def test_every_row_of_the_seed_that_a_table_can_hold_is_loaded_and_loading_twice_moves_nothing(conn):
    before = loaders.load_all()
    assert loaders.load_all() == before, "a second load moved a row"
    eng = "from skill s join topic o on o.tenant_id = s.tenant_id and o.code = s.topic_code where o.subject_code = 'ENG'"
    paper = [q for q in rows("question_type.json", "question_types") if q["reaches"] != "observed"]
    assert one(conn, "select count(*) from subject where code = 'ENG'") == 1
    assert (
        one(conn, "select count(*) from topic where subject_code = 'ENG'")
        == len(rows("topic.json", "topics"))
        == 8
    )
    assert one(conn, f"select count(*) {eng}") == len(rows("skill.json", "skills")) == 109
    assert one(conn, f"select count(*) {eng} and s.status = 'draft'") == 109, "every English skill is a draft"
    assert (
        one(
            conn,
            f"select count(*) from skill_level l join skill s on s.code = l.skill_code {eng.split('from skill s', 1)[1]}",
        )
        == len(rows("skill_level.json", "skill_levels"))
        == 436
    )
    assert (
        one(conn, "select count(*) from skill_level where skill_code like 'EN%' and confirmed_at is not null")
        == 0
    )
    assert one(conn, "select count(*) from question_type where code like 'ENG.%'") == len(paper) == 15
    assert one(conn, "select count(*) from skill_level_question_type where skill_code like 'EN%'") == 833
    assert (
        one(conn, "select count(*) from misconception where code like 'M_ENG_%'")
        == len(rows("misconception.json", "misconceptions"))
        == 340
    )
    assert (
        one(conn, "select count(*) from skill_mistake where skill_code like 'EN%'")
        == len(rows("skill_mistake.json", "skill_mistakes"))
        == 405
    )
    assert (
        one(conn, "select count(*) from skill_prerequisite where skill_code like 'EN%'")
        == len(rows("skill_prerequisite.json", "skill_prerequisites"))
        == 115
    )
    assert one(
        conn, "select count(*) from question_type_approval where question_type like 'ENG.%'"
    ) == 0 or os.getenv("ENG_APPROVED_ON_COPY")


def test_the_levels_say_what_the_seed_says_and_the_open_kinds_say_a_person_reads_them(conn):
    for lv in rows("skill_level.json", "skill_levels")[::37]:
        got = conn.execute(
            "select grade, looks_like, rule from skill_level where skill_code = %s and difficulty = %s",
            (lv["skill_code"], lv["difficulty"]),
        ).fetchone()
        assert (got["grade"], got["looks_like"], got["rule"]) == (lv["grade"], lv["looks_like"], lv["rule"])
    for q in rows("question_type.json", "question_types"):
        if q["reaches"] == "observed":
            continue
        marked = one(conn, "select marked::text[] from question_type where code = %s", q["code"])
        assert (marked == ["open_response"]) == (q["answer"] == "open"), q["code"]


def test_an_unapproved_english_kind_or_level_is_never_drawn(conn):
    skill, level, kind = "EN3.SPELL.VERBEND", "Easy", "ENG.WRITE_WORD"
    tenant = one(conn, "select id from tenant limit 1")
    conn.execute("delete from question_type_approval where question_type = %s", (kind,))
    conn.execute(
        "update skill_level set confirmed_by = null, confirmed_at = null where skill_code = %s", (skill,)
    )
    # Every question names its registry skill (C1); no English skill is linked to the registry yet, so no real English
    # question can be written: this one names the registry's own spelling rule, as one will.
    conn.execute(
        "insert into item (tenant_id, item_key, template, rung_code, skill_codes, signal, fmt, spec, responses,"
        " skill_set_code, difficulty, status, source) values (%s, 'E0.TEST.1', %s, %s, '{LIT.GRM.04}', 'Foundational',"
        " %s, '{}', '[]', %s, %s, 'active', 'generated')",
        (tenant, kind, skill, kind, skill, level),
    )

    def drawn():
        return one(conn, "select count(*) from drawable_item where item_key = 'E0.TEST.1'")

    assert drawn() == 0, "neither the kind nor the level is approved"
    question_types.approve(conn, kind, "Ayush Test")
    assert drawn() == 0, "the kind alone is not enough: the level waits"
    conn.execute(
        "update skill set level_approved = level_approved || jsonb_build_object(%s::text,"
        " jsonb_build_object('by', 'Ayush Test'::text, 'at', now())) where code = %s",
        (level, skill),
    )
    assert drawn() == 1, "approved kind and approved level: now it may be drawn"
    conn.execute("delete from question_type_approval where question_type = %s", (kind,))
    assert drawn() == 0, "a kind withdrawn is not drawn"


def test_an_approval_of_a_kind_records_the_name_and_the_date(conn):
    kind = "ENG.CHOOSE"
    conn.execute("delete from question_type_approval where question_type = %s", (kind,))
    assert question_types.state(conn, kind)["approved"] is False
    got = question_types.approve(conn, kind, "Ayush Test")
    assert got["approved"] and got["by"] == "Ayush Test" and got["at"] is not None
    skill, level = "EN3.PHON.SOUNDS", "Easy"
    conn.execute(
        "update skill set level_approved = level_approved || jsonb_build_object(%s::text,"
        " jsonb_build_object('by', 'Ayush Test'::text, 'at', now())) where code = %s",
        (level, skill),
    )
    lv = conn.execute(
        "select confirmed_by, confirmed_at from skill_level where skill_code = %s and difficulty = %s",
        (skill, level),
    ).fetchone()
    assert lv["confirmed_by"] == "Ayush Test" and lv["confirmed_at"] is not None


def test_the_maths_is_exactly_as_it_was(conn):
    maths = "from skill s join topic o on o.tenant_id = s.tenant_id and o.code = s.topic_code where o.subject_code <> 'ENG'"
    sets = json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]
    assert one(conn, f"select count(*) {maths}") == len(sets)
    assert one(conn, "select count(*) from skill_prerequisite where skill_code not like 'EN%'") == len(
        json.loads((SEED / "skill_prerequisites.json").read_text())["skill_prerequisites"]
    )
    assert one(conn, "select count(*) from misconception where code not like 'M_ENG_%'") == len(
        json.loads((SEED / "misconceptions.json").read_text())["misconceptions"]
    )
    assert one(conn, "select count(*) from topic where subject_code = 'NUM'") == len(
        json.loads((SEED / "topics.json").read_text())["topics"]
    )


def test_a_question_type_written_later_does_not_take_the_englishes_links_for_good(conn):
    """Writing a question type re-makes only the links the bank holds (C1); the bank holds no English question, so the
    curriculum's English links stay, with no load to put them back."""
    tenant = one(conn, "select id from tenant limit 1")
    assert one(conn, "select count(*) from skill_level_question_type where skill_code like 'EN%'") == 833
    conn.execute(
        "insert into question_type (tenant_id, code, fmt, words, marked) values (%s, 'TEST.E0', 'TEST.E0', 'x',"
        " array['closed_set']::eval_type[])",
        (tenant,),
    )
    assert one(conn, "select count(*) from skill_level_question_type where skill_code like 'EN%'") == 833


def test_the_audit_asks_nothing_of_english_that_only_a_bank_could_give(conn):
    """English is drafts a person reads: no generator, no bank, so the checks that ask a skill to be approved, to make a
    question or to meet a bank's target are about the maths alone, and still ask it."""
    from engine.checks import audit

    said = [
        f"{name}: {v}"
        for name, vs in audit.run(conn)
        for v in vs
        if "EN3." in v or "EN4." in v or "M_ENG_" in v
    ]
    assert said == []
