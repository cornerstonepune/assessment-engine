"""Every English sample is stored whole, so an educator reads a level's questions before approving it
(goals/smp_skill_shows_its_samples.yaml). Nimish, 2026-10-23: "How will the educator approve without having sample
questions?"

The seed's samples, passages, rubrics and wrong answers are counted against the tables `engine load` fills; a second load
moves nothing; a load never touches a level a person approved; the load a deploy runs adds them too. Each test runs on
the local copy and rolls back what it writes.
"""

import os

import pytest

from engine.core import db, english, loaders

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs the local copy (bin/testdb)")


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def one(conn, sql, *params):
    return next(iter(conn.execute(sql, params or None).fetchone().values()))


def samples():
    return english.seed("skill_level_sample.json", "samples")


def test_every_sample_passage_rubric_and_wrong_answer_of_the_seed_is_loaded_and_a_second_load_moves_nothing(
    conn,
):
    first = loaders.load_all()
    assert first["english_sample"] == len(samples()) == 2499
    assert first["passage"] == len(english.seed("passage.json", "passages")) == 253
    assert first["rubric"] == len(english.seed("rubric.json", "rubrics")) == 7
    assert first["english_sample_wrong"] == sum(len(s["wrong"]) for s in samples()) == 4366
    stamp = (
        "select max(updated_at) from (select updated_at from english_sample union all select updated_at from"
        " english_sample_wrong union all select updated_at from passage union all select updated_at from rubric) u"
    )
    when = one(conn, stamp)
    assert loaders.load_all() == first, "a second load moved a row"
    with db.connect() as again:
        assert one(again, stamp) == when, "a second load rewrote a row"


def test_a_sample_is_stored_whole(conn):
    loaders.load_all()
    s = next(x for x in samples() if x["question_type"] == "ENG.CHOOSE" and x["wrong"])
    row = conn.execute(
        "select ask, text, options, answer, passage_code from english_sample where skill_code = %s and difficulty = %s"
        " and question_type = %s and ord = %s",
        (s["skill_code"], s["difficulty"], s["question_type"], s["n"]),
    ).fetchone()
    assert (row["ask"], row["text"], row["options"], row["answer"], row["passage_code"]) == (
        s["ask"],
        s["text"],
        s["options"],
        s["answer"],
        s["passage"],
    )
    wrong = conn.execute(
        "select w.answer, w.mistake_code, m.name from english_sample_wrong w join english_sample e on e.id = w.sample_id"
        " join misconception m on m.tenant_id = w.tenant_id and m.code = w.mistake_code and m.op = w.op"
        " where e.skill_code = %s and e.difficulty = %s and e.question_type = %s and e.ord = %s",
        (s["skill_code"], s["difficulty"], s["question_type"], s["n"]),
    ).fetchall()
    assert {w["answer"]: w["mistake_code"] for w in wrong} == s["wrong"]
    assert all(w["name"] for w in wrong), "every wrong answer names a mistake in words"


def test_a_load_leaves_an_approved_level_as_it_was(conn):
    s = samples()[0]
    conn.execute(
        "update skill_level set confirmed_by = 'An Educator', confirmed_at = '2026-10-23' where skill_code = %s"
        " and difficulty = %s",
        (s["skill_code"], s["difficulty"]),
    )
    conn.commit()
    try:
        loaders.load_all()
        loaders.load_settings()
        with db.connect() as c:
            row = c.execute(
                "select confirmed_by, confirmed_at::date::text as at from skill_level where skill_code = %s"
                " and difficulty = %s",
                (s["skill_code"], s["difficulty"]),
            ).fetchone()
        assert (row["confirmed_by"], row["at"]) == ("An Educator", "2026-10-23")
    finally:
        conn.execute(
            "update skill_level set confirmed_by = null, confirmed_at = null where skill_code = %s and difficulty = %s",
            (s["skill_code"], s["difficulty"]),
        )
        conn.commit()


def test_the_load_a_deploy_runs_adds_the_samples(conn):
    loaders.load_all()
    conn.execute("delete from english_sample")
    conn.execute("delete from passage")
    conn.execute("delete from rubric")
    conn.commit()
    counts = loaders.load_settings()
    assert (
        counts["english_sample"],
        counts["english_sample_wrong"],
        counts["passage"],
        counts["rubric"],
    ) == (
        2499,
        4366,
        253,
        7,
    )
