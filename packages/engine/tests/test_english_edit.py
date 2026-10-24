"""An educator changes an English sample, or the kinds a level asks (goals/edt_edit_samples_and_kinds.yaml). Nimish,
2026-10-24: "What happens if he wants to make any changes there? … Is that capability here, or is it just blue?"

A save is checked first and refused in words when it fails; one that passes is a new version that supersedes the last,
never an overwrite, and withdraws that level's approval and no other; a level keeps three samples of every kind it
asks; a kind is added only with three samples that pass, and a load does not bring back a kind a person took away.
Each test runs on the local copy and rolls back what it writes.
"""

import os

import pytest

from engine.core import db, english
from engine.w1_bank import english_edit as ed
from engine.w1_bank import english_form as ef

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs the local copy (bin/testdb)")
BY = "Ayush (English)"
# the rows a test wrote: its transaction began at now(), and a ledger row is stamped by the clock (the copy keeps others')
MINE = "created_at >= now()"


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def one(conn, sql, *params):
    return next(iter(conn.execute(sql, params or None).fetchone().values()))


def choose_slot(conn):
    """A Hard English choice question, and its skill approved at every level, as an approver leaves it."""
    row = conn.execute(
        "select skill_code, difficulty, question_type, ord from english_sample_now where difficulty = 'Hard'"
        " and question_type = 'ENG.CHOOSE' and passage_code is null order by skill_code, ord limit 1"
    ).fetchone()
    conn.execute(
        "update skill set level_approved = (select jsonb_object_agg(k, jsonb_build_object('by', 'Achal', 'at', now()))"
        " from jsonb_object_keys(difficulty) k) where code = %s",
        (row["skill_code"],),
    )
    return row


def as_saved(conn, slot):
    s = ed.current(conn, slot["skill_code"], slot["difficulty"], slot["question_type"], slot["ord"])
    return {
        "fields": ef.to_form(slot["question_type"], s),
        "wrong": s["wrong"],
        "passage_code": s["passage_code"],
    }


def approved(conn, code):
    return one(conn, "select level_approved from skill where code = %s", code)


def test_a_sample_that_fails_a_check_is_refused_in_words_and_nothing_is_stored(conn):
    slot = choose_slot(conn)
    form = as_saved(conn, slot)
    form["wrong"] = [
        {**form["wrong"][0], "answer": form["fields"]["answer"]}
    ]  # a wrong answer that is the right one
    got = ed.save(
        conn, slot["skill_code"], slot["difficulty"], slot["question_type"], slot["ord"], BY, **form
    )
    assert not got["saved"] and "is a right answer" in " ".join(got["faults"]["wrong.0"])
    assert one(conn, f"select count(*) from english_sample_edit where {MINE}") == 0
    assert set(approved(conn, slot["skill_code"])) == set(
        one(conn, "select difficulty from skill where code = %s", slot["skill_code"])
    )


def test_a_saved_sample_is_a_new_version_and_withdraws_only_its_levels_approval(conn):
    slot = choose_slot(conn)
    before = ed.current(conn, slot["skill_code"], slot["difficulty"], slot["question_type"], slot["ord"])
    form = as_saved(conn, slot)
    options = ef.lines(form["fields"]["options"])
    # one wrong answer left, and a printed option that was not one where there is such an option
    unused = [
        o for o in options if o != form["fields"]["answer"] and o not in {w["answer"] for w in form["wrong"]}
    ]
    other = (unused or [form["wrong"][0]["answer"]])[0]
    form["wrong"] = [{"answer": other, "mistake_code": form["wrong"][-1]["mistake_code"]}]
    got = ed.save(
        conn, slot["skill_code"], slot["difficulty"], slot["question_type"], slot["ord"], BY, **form
    )
    assert got == {"saved": True, "ord": slot["ord"], "faults": {}}
    now = ed.current(conn, slot["skill_code"], slot["difficulty"], slot["question_type"], slot["ord"])
    assert [w["answer"] for w in now["wrong"]] == [other] and now["edited_by"] == BY
    edit = conn.execute(f"select replaced, edited_by from english_sample_edit where {MINE}").fetchone()
    assert edit["replaced"]["wrong"] == before["wrong"], "what it replaced is kept"
    left = approved(conn, slot["skill_code"])
    assert slot["difficulty"] not in left and len(left) >= 1, "only the edited level waits for approval again"
    assert one(conn, "select status from skill where code = %s", slot["skill_code"]) == "draft"


def test_history_is_kept_and_never_changed(conn):
    slot = choose_slot(conn)
    form = as_saved(conn, slot)
    had = ed.current(conn, slot["skill_code"], slot["difficulty"], slot["question_type"], slot["ord"])
    kept_before = had["earlier"] + (1 if had["edited_by"] else 0)  # versions an earlier run left
    for ask in ("Tick the best word.", "Tick the word that fits best."):
        form["fields"]["ask"] = ask
        assert ed.save(
            conn, slot["skill_code"], slot["difficulty"], slot["question_type"], slot["ord"], BY, **form
        )["saved"]
    rows = conn.execute(
        f"select sample ->> 'ask' as ask, replaced ->> 'ask' as was from english_sample_edit where {MINE} order by created_at"
    ).fetchall()
    assert [r["ask"] for r in rows] == ["Tick the best word.", "Tick the word that fits best."]
    assert rows[1]["was"] == "Tick the best word."
    assert (
        ed.current(conn, slot["skill_code"], slot["difficulty"], slot["question_type"], slot["ord"])[
            "earlier"
        ]
        == kept_before + 1
    )
    with pytest.raises(Exception, match="kept|forbid|not be changed|cannot"):
        conn.execute("update english_sample_edit set edited_by = 'someone else'")


def test_a_sample_is_added_and_removed_but_a_level_keeps_three_of_each_kind(conn):
    slot = choose_slot(conn)
    form = as_saved(conn, slot)
    form["fields"]["ask"] = "Tick the one word that fits."
    added = ed.save(conn, slot["skill_code"], slot["difficulty"], slot["question_type"], None, BY, **form)
    assert added["saved"] and added["ord"] == 4
    assert ed.remove(conn, slot["skill_code"], slot["difficulty"], slot["question_type"], 4, BY) == {
        "removed": True,
        "why": "",
    }
    assert ed.current(conn, slot["skill_code"], slot["difficulty"], slot["question_type"], 4) is None
    refused = ed.remove(conn, slot["skill_code"], slot["difficulty"], slot["question_type"], 1, BY)
    assert not refused["removed"] and "three" in refused["why"]


RULED = {
    "answer_letters",
    "answer_words",
    "pattern",
    "answer_from",
    "answer_in_passage",
    "text_words",
    "passage_words",
}


def bare_level(conn):
    """An English level that does not ask "Write the word", whose rule says nothing of a written word."""
    for r in conn.execute(
        "select l.skill_code, l.difficulty, l.rule from skill_level l join skill s on s.tenant_id = l.tenant_id"
        " and s.code = l.skill_code join topic t on t.tenant_id = s.tenant_id and t.code = s.topic_code"
        " where t.subject_code = 'ENG' and not exists (select 1 from skill_level_question_type k where"
        " k.skill_code = l.skill_code and k.difficulty = l.difficulty and k.question_type = 'ENG.WRITE_WORD')"
        " order by l.skill_code, l.difficulty"
    ):
        if not set(r["rule"]) & RULED:
            return r["skill_code"], r["difficulty"]
    raise AssertionError("no English level to add a kind to")


def test_a_kind_is_added_to_a_level_only_with_three_samples_that_pass(conn):
    code, level = bare_level(conn)
    kind = "ENG.WRITE_WORD"
    conn.execute(
        "insert into question_type_approval (tenant_id, question_type, approved_by) select tenant_id, code, 'Achal'"
        " from question_type where code = %s on conflict do nothing",
        (kind,),
    )
    conn.execute(
        "update skill set level_approved = jsonb_build_object(%s::text, jsonb_build_object('by', 'Achal',"
        " 'at', now())) where code = %s",
        (level, code),
    )
    mistake = one(conn, "select misconception_code from skill_mistake where skill_code = %s limit 1", code)
    three = [
        {
            "fields": {"ask": "Write the word that names a young animal.", "answer": w},
            "wrong": [{"answer": "kiten", "mistake_code": mistake}],
        }
        for w in ("kitten", "puppy", "calf")
    ]
    short = ed.add_kind(conn, code, level, kind, three[:2], BY)
    assert not short["saved"] and "three" in short["why"]
    assert kind not in ed.level_kinds(conn, code, level)
    bad = ed.add_kind(conn, code, level, kind, [*three[:2], {**three[2], "wrong": []}], BY)
    assert not bad["saved"] and bad["faults"][2]["wrong"], "each of the three is checked"
    got = ed.add_kind(conn, code, level, kind, three, BY)
    assert got["saved"], got
    assert kind in ed.level_kinds(conn, code, level) and level not in approved(conn, code)
    took = ed.remove_kind(conn, code, level, kind, BY)
    assert took["removed"] and kind not in ed.level_kinds(conn, code, level)
    t = one(conn, "select id from tenant limit 1")
    english.level_kinds(conn, t)
    assert kind not in ed.level_kinds(conn, code, level), (
        "a load does not bring back a kind a person took away"
    )


def test_only_an_approved_kind_is_added(conn):
    code, level = bare_level(conn)
    conn.execute("delete from question_type_approval where question_type = 'ENG.WRITE_WORD'")
    got = ed.add_kind(conn, code, level, "ENG.WRITE_WORD", [], BY)
    assert not got["saved"] and "approved" in got["why"]


def test_a_level_keeps_at_least_one_kind(conn):
    slot = choose_slot(conn)
    code, level = slot["skill_code"], slot["difficulty"]
    kinds = ed.level_kinds(conn, code, level)
    for k in kinds[:-1]:
        assert ed.remove_kind(conn, code, level, k, BY)["removed"]
    last = ed.remove_kind(conn, code, level, kinds[-1], BY)
    assert not last["removed"] and "one kind" in last["why"]


def test_a_maths_skill_has_no_samples_to_edit(conn):
    maths = one(
        conn,
        "select s.code from skill s join topic t on t.tenant_id = s.tenant_id and t.code = s.topic_code"
        " where t.subject_code <> 'ENG' limit 1",
    )
    got = ed.save(conn, maths, "Easy", "ENG.CHOOSE", None, BY, fields={"ask": "x", "answer": "y"}, wrong=[])
    assert not got["saved"] and "Maths" in " ".join(got["faults"]["skill"])


def test_the_website_route_answers_a_failed_check_in_words_and_stores_nothing(monkeypatch):
    """The website sends the form's words to the engine; a fault comes back by field, and no row is written."""
    from fastapi.testclient import TestClient

    from engine.api.app import app

    monkeypatch.setenv("ENGINE_KEY", "k")
    with db.connect() as c:
        slot = c.execute(
            "select skill_code, difficulty, question_type, ord from english_sample_now where question_type = 'ENG.CHOOSE'"
            " order by skill_code limit 1"
        ).fetchone()
        before = one(c, "select count(*) from english_sample_edit")
    body = {"level": slot["difficulty"], "kind": slot["question_type"], "ord": slot["ord"], "by": BY,
            "fields": {"ask": "Tick one.", "options": "red\nrun", "answer": "blue"}, "wrong": []}  # fmt: skip
    with TestClient(app, headers={"X-Engine-Key": "k"}) as client:
        got = client.post(f"/skill/{slot['skill_code']}/sample", json=body).json()
    assert got["saved"] is False and "not one of the options" in got["faults"]["answer"][0]
    with db.connect() as c:
        assert one(c, "select count(*) from english_sample_edit") == before


def test_a_sample_is_saved_only_to_a_kind_its_level_asks(conn):
    slot = choose_slot(conn)
    form = as_saved(conn, slot)
    asked = ed.level_kinds(conn, slot["skill_code"], slot["difficulty"])
    other = next(k for k in ("ENG.DICTATION", "ENG.WRITE_WORD", "ENG.TABLE") if k not in asked)
    got = ed.save(conn, slot["skill_code"], slot["difficulty"], other, None, BY, **form)
    assert not got["saved"] and "does not ask" in got["faults"]["skill"][0]


def test_a_save_when_the_spelling_list_cannot_be_read_is_refused_in_words(conn, monkeypatch):
    from engine.w1_bank import english_words

    def gone(word):
        raise english_words.NoDictionary("no network")

    monkeypatch.setattr(english_words, "known", gone)
    slot = choose_slot(conn)
    got = ed.save(
        conn,
        slot["skill_code"],
        slot["difficulty"],
        slot["question_type"],
        slot["ord"],
        BY,
        **as_saved(conn, slot),
    )
    assert not got["saved"] and "spelling list" in got["faults"]["skill"][0]
    assert one(conn, f"select count(*) from english_sample_edit where {MINE}") == 0
