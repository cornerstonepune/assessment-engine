"""Questions made from an educator's sample (goals/gen_from_a_sample.yaml). Nimish, 2026-10-26: "The capability to edit a
certain level in a skill by putting in the sample questions, and the ability for the system to then generate a certain
number of questions of that pattern."

English: a model writes them, and every one passes #323's checks before it is stored; the rest are thrown away and the
educator told why. The model is replaced here by fixed replies: what is tested is the code that decides. Maths: code
measures the sample and makes more of its case, or keeps it as a sample only. Whatever is made is a draft: it says
what it was made from, and its level waits for approval. Each test rolls back.
"""

import copy
import os

import pytest

from engine.core import db
from engine.w1_bank import english_edit as ed
from engine.w1_bank import generate

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs the local copy (bin/testdb)")
BY = "Ayush (English)"
MINE = "created_at >= now()"


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def one(conn, sql, *params):
    return next(iter(conn.execute(sql, params or None).fetchone().values()))


def approve_all(conn, code):
    conn.execute(
        "update skill set level_approved = (select jsonb_object_agg(k, jsonb_build_object('by', 'Achal', 'at', now()))"
        " from jsonb_object_keys(difficulty) k) where code = %s",
        (code,),
    )


def a_sample(conn):
    """An Easy English choice question with no passage, and its skill approved at every level."""
    row = conn.execute(
        "select * from english_sample_now where difficulty = 'Easy' and question_type = 'ENG.CHOOSE'"
        " and passage_code is null and jsonb_array_length(wrong) >= 1 order by skill_code, ord limit 1"
    ).fetchone()
    approve_all(conn, row["skill_code"])
    return row


def reply(*questions):
    """The model, replaced: it returns these questions, as the prompt's schema has them."""

    def fake(conn, purpose, variables, images=(), subject=None, meta=None, version=None):
        assert purpose == generate.PURPOSE
        assert variables["sample"] and variables["n"]  # the sample and how many are passed
        if meta is not None:
            meta.update(flow_run_id=None, model="fixed", prompt_id=None, cost_inr=0)
        return {"questions": [copy.deepcopy(q) for q in questions]}

    return fake


def asked(s, text):
    """A question like `s` with another sentence."""
    return {k: s[k] for k in ("ask", "options", "answer", "accept", "key_points", "not_words", "wrong")} | {
        "text": text
    }


def test_english_questions_that_fail_a_check_are_never_stored_and_the_educator_is_told_why(conn, monkeypatch):
    s = a_sample(conn)
    good = asked(s, s["text"].replace(".", " today.", 1))
    right_as_wrong = asked(s, s["text"].replace(".", " again.", 1))
    right_as_wrong["wrong"] = [{"answer": s["answer"], "mistake_code": s["wrong"][0]["mistake_code"]}]
    same = asked(s, s["text"])  # the sample itself, again
    monkeypatch.setattr(generate.llm, "generate", reply(good, right_as_wrong, same))
    got = generate.english(conn, s["skill_code"], s["difficulty"], s["question_type"], s["ord"], 3, BY)
    assert got["made"] and got["returned"] == 3 and got["kept"] == 1
    assert sum(t["n"] for t in got["thrown"]) == 2
    said = " ".join(t["why"] for t in got["thrown"])
    assert "is a right answer" in said and "already" in said
    assert one(conn, f"select count(*) from english_sample_edit where {MINE}") == 1


def test_english_questions_that_pass_are_drafts_made_from_the_sample_and_the_level_waits_for_approval(
    conn, monkeypatch
):
    s = a_sample(conn)
    levels = set(one(conn, "select level_approved from skill where code = %s", s["skill_code"]))
    monkeypatch.setattr(
        generate.llm,
        "generate",
        reply(
            asked(s, s["text"].replace(".", " today.", 1)), asked(s, s["text"].replace(".", " at once.", 1))
        ),
    )
    got = generate.english(conn, s["skill_code"], s["difficulty"], s["question_type"], s["ord"], 2, BY)
    assert got["kept"] == 2, got
    made = conn.execute(
        "select ord, made_from, edited_by from english_sample_now where skill_code = %s and difficulty = %s"
        " and question_type = %s and made_from is not null",
        (s["skill_code"], s["difficulty"], s["question_type"]),
    ).fetchall()
    assert (
        len(made) == 2
        and {m["made_from"] for m in made} == {s["ord"]}
        and {m["edited_by"] for m in made} == {BY}
    )
    assert set(one(conn, "select level_approved from skill where code = %s", s["skill_code"])) == levels - {
        s["difficulty"]
    }
    # each can be taken off on its own, as any sample beyond the three a kind keeps
    assert ed.remove(conn, s["skill_code"], s["difficulty"], s["question_type"], made[0]["ord"], BY)[
        "removed"
    ]


def test_a_maths_sample_of_a_known_case_makes_more_of_that_case_by_code(conn):
    approve_all(conn, "ADD.2D2D")
    before = one(
        conn, "select count(*) from item where skill_set_code = 'ADD.2D2D' and difficulty = 'Medium'"
    )
    got = generate.maths(conn, "ADD.2D2D", "Medium", "47 + 38", "columns", 5, BY)
    assert got["made"] and got["cases"] == ["A19"] and got["kept"] == 5, got
    rows = conn.execute(
        "select i.generator from maths_sample m join item i on i.id = any(m.item_ids) where m.id = %s",
        (got["sample"],),
    ).fetchall()
    assert len(rows) == 5 and {r["generator"] for r in rows} == {"case:A19"}
    assert (
        one(conn, "select count(*) from item where skill_set_code = 'ADD.2D2D' and difficulty = 'Medium'")
        == before + 5
    )
    assert "Medium" not in one(conn, "select level_approved from skill where code = 'ADD.2D2D'")


def test_a_maths_sample_of_no_known_case_is_kept_as_a_sample_and_nothing_is_made(conn):
    approve_all(conn, "ADD.2D2D")
    before = one(conn, "select count(*) from item where skill_set_code = 'ADD.2D2D'")
    got = generate.maths(conn, "ADD.2D2D", "Medium", "6 × 7", "line", 5, BY)
    assert not got["made"] and got["kept"] == 0 and "kept as a sample" in got["why"]
    assert one(conn, "select count(*) from item where skill_set_code = 'ADD.2D2D'") == before
    assert one(conn, f"select count(*) from maths_sample where skill_code = 'ADD.2D2D' and {MINE}") == 1
    assert "Medium" in one(conn, "select level_approved from skill where code = 'ADD.2D2D'")
    got = generate.maths(conn, "ADD.2D2D", "Medium", "forty-seven and some", "line", 5, BY)
    assert not got["made"] and "a sum" in got["why"]


def test_how_many_is_at_most_the_row_and_no_prompt_is_used_until_it_is_active(conn):
    s = a_sample(conn)
    most = generate.most(conn)
    assert most == 20
    got = generate.english(conn, s["skill_code"], s["difficulty"], s["question_type"], s["ord"], most + 1, BY)
    assert not got["made"] and "at most 20" in got["why"]
    assert not generate.maths(conn, "ADD.2D2D", "Medium", "47 + 38", "columns", most + 1, BY)["made"]
    # the prompt is a row, inactive until its eval is recorded (rule 7): the real adapter refuses, nothing is stored
    assert not one(
        conn, "select coalesce(bool_or(active), false) from prompt where purpose = %s", generate.PURPOSE
    )
    assert (
        one(
            conn,
            "select count(*) from prompt where purpose = %s and json_schema is not null",
            generate.PURPOSE,
        )
        == 1
    )
    got = generate.english(conn, s["skill_code"], s["difficulty"], s["question_type"], s["ord"], 3, BY)
    assert not got["made"] and "not switched on yet" in got["why"]
    assert one(conn, f"select count(*) from english_sample_edit where {MINE}") == 0
