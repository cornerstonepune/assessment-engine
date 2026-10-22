"""Topics (engine/core/topics.py): the tree's level between a subject and its skills. Pure: a fake seed and a
connection that records what it is asked."""

import json
import os
from pathlib import Path

import pytest

from engine.core import topics

SEED = Path(__file__).resolve().parents[3] / "supabase" / "seed"


class Recorder:
    def __init__(self):
        self.calls = []

    def execute(self, sql, params=()):
        self.calls.append((sql, params))


def _seed(tops, sets):
    return lambda name, key: {"topics.json": tops, "skill_sets.json": [{"code": c} for c in sets]}[name]


def test_every_skill_in_the_seed_sits_in_exactly_one_topic():
    tops = json.loads((SEED / "topics.json").read_text())["topics"]
    sets = [s["code"] for s in json.loads((SEED / "skill_sets.json").read_text())["skill_sets"]]
    placed = [c for t in tops for c in t["skill_sets"]]
    assert sorted(placed) == sorted(sets), "every skill set once, and no topic names one that does not exist"


def test_a_skill_in_no_topic_or_in_two_is_refused():
    one = [{"code": "A", "subject": "NUM", "name": "A", "skill_sets": ["X"]}]
    with pytest.raises(ValueError, match="in no topic: Y"):
        topics.load(Recorder(), "t", _seed(one, ["X", "Y"]))
    two = one + [{"code": "B", "subject": "NUM", "name": "B", "skill_sets": ["X"]}]
    with pytest.raises(ValueError, match="X is in two topics"):
        topics.load(Recorder(), "t", _seed(two, ["X"]))


def test_each_skill_is_placed_under_its_topic_in_the_topics_order():
    tops = [
        {"code": "A", "subject": "NUM", "name": "First", "skill_sets": ["X"]},
        {"code": "B", "subject": "NUM", "name": "Second", "skill_sets": ["Y"]},
    ]
    conn = Recorder()
    topics.load(conn, "t", _seed(tops, ["X", "Y"]))
    inserted = [p for s, p in conn.calls if s.startswith("insert into topic")]
    assert [(p[1], p[4]) for p in inserted] == [("A", 0), ("B", 1)]
    placed = {p[3]: p[0] for s, p in conn.calls if s.startswith("update skill")}
    assert placed == {"X": "A", "Y": "B"}


def test_the_topics_are_the_operations_and_a_kind_of_question_is_never_one():
    """Nimish, 2026-10-15: "These are types of problems. The topics are core addition, subtraction, multiplication,
    division, and factors." Six topics by operation (ADR 0076). Addition and subtraction stay one topic: missing digit,
    inverse and the stories use both. Skills that mix x and / sit under Division, taught only once division is.
    Estimating, a story, an equation, mental methods and reasoning are kinds of question a skill asks, never topics."""
    tops = json.loads((SEED / "topics.json").read_text())["topics"]
    assert [t["name"] for t in tops] == [
        "Addition & subtraction",
        "Multiplication",
        "Division",
        "Multiples & factors",
        "Number sense",
        "Data handling",
    ]
    holds = {code: t["name"] for t in tops for code in t["skill_sets"]}
    assert {
        c: holds[c] for c in ("ESTIMATE.ROUND10", "WORD.1_2STEP", "MISSING.DIGIT", "REASON.EXPLAIN")
    } == dict.fromkeys(
        ("ESTIMATE.ROUND10", "WORD.1_2STEP", "MISSING.DIGIT", "REASON.EXPLAIN"), "Addition & subtraction"
    )
    assert {
        holds[c] for c in ("MUL.GROUPS", "MUL.MODELS", "MUL.FACTS", "MUL.TENS", "MUL.THREE", "MUL.2D1D")
    } == {"Multiplication"}
    assert {
        holds[c] for c in ("DIV.GROUPS", "DIV.2D1D", "MD.MENTAL", "MD.ESTIMATE", "MD.EQUALITY", "MD.WORD")
    } == {"Division"}
    assert {holds[c] for c in ("MD.MULTIPLES", "MUL.NTH")} == {"Multiples & factors"}
    assert (holds["NUM.SEQUENCE"], holds["DATA.TALLY"]) == ("Number sense", "Data handling")
    kinds = ("estimat", "word", "stor", "equation", "mental", "reason", "model", "column", "facts", "strateg")
    assert not [t["name"] for t in tops if any(k in t["name"].lower() for k in kinds)]


def test_multiplication_begun_in_grade_1_is_taught_and_column_multiplication_is_not():
    """Nimish, 2026-09-23: "I'm surprised we haven't even started teaching multiplication" — Grade 3's multiplication
    in columns, still untaught. Grade 1's educator, 2026-10-06: "Multiplication as beginners with repeated addition"
    and "Tally marks" were taught to September. Both are now in Multiplication; the school's word is said skill by
    skill (`taught`: the skills of the topic the school has taught), so one topic holds both."""
    tops = json.loads((SEED / "topics.json").read_text())["topics"]
    taught = {code for t in tops for code in t.get("taught", [])}
    assert {"MUL.GROUPS", "DATA.TALLY"} <= taught and "MUL.2D1D" not in taught
    assert all(set(t.get("taught", [])) <= set(t["skill_sets"]) for t in tops), (
        "a topic says only its own skills"
    )


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
def test_every_taxonomy_case_sits_in_a_taught_skill_and_nothing_else_is_taught():
    """The taxonomy of addition and subtraction is what the school gave: every case in it is on the site, and a skill
    that holds none of its cases is not — so hiding what is not taught never hides a piece of it. The one addition is
    Grade 1's own list of what it taught to September (2026-10-06), which that taxonomy does not hold: tally marks
    and equal groups. Multiplication and division's cases are rows too (goals/md1-taxonomy-rows.yaml), drafted by the
    engine; they are taught when an educator says a grade has been taught them, never because a question holds one."""
    from engine.core import db

    with db.connect() as conn:
        rows = conn.execute(
            "select s.code, s.taught, exists (select 1 from item i where i.skill_set_code = s.code"
            "   and i.status = 'active' and i.case_codes && (select array_agg(code) from taxonomy_case"
            "   where taxonomy = 'ADD_SUB')) as holds_cases"
            " from skill s where s.taught_by is null"
        ).fetchall()
    assert rows
    grade_1_beyond_the_taxonomy = {"DATA.TALLY", "MUL.GROUPS"}
    assert {r["code"] for r in rows if r["holds_cases"]} | grade_1_beyond_the_taxonomy == {
        r["code"] for r in rows if r["taught"]
    }


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
def test_a_skill_a_person_switched_stays_as_they_left_it():
    """Nimish, 2026-10-10: "I'm not seeing any of the multiplication, division". A skill the rows leave off is switched
    on by a person, in their own name, and a reload of the rows never switches it back: the rows decide a skill only
    until a person has. One changed in the database with no name on it is no one's decision, and follows the rows."""
    from engine.core import db, settings

    with db.connect() as conn:
        tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
        conn.execute(
            "update skill set taught = true, taught_by = 'An educator', taught_at = now() where code = 'DIV.2D1D'"
        )
        conn.execute(
            "update skill set taught = true, taught_by = null, taught_at = null where code = 'DIV.FACTS'"
        )
        topics.load(conn, tenant, settings.seed)
        got = {
            r["code"]: (r["taught"], r["taught_by"], r["taught_at"] is not None)
            for r in conn.execute(
                "select code, taught, taught_by, taught_at from skill where code in ('DIV.2D1D', 'DIV.FACTS')"
            ).fetchall()
        }
        conn.rollback()
    assert got == {"DIV.2D1D": (True, "An educator", True), "DIV.FACTS": (False, None, False)}


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
def test_a_topic_the_rows_drop_is_gone_after_a_load():
    """Live on 2026-10-15 still had "Number sense & strategies", "Estimation" and "Word problems": topics the rows
    dropped on 2026-09-23, which a load updated nothing in and never removed, so they stayed switched on and on every
    page's chips. A load now removes a topic the rows no longer have; every word said of a skill stays on the skill."""
    from engine.core import db, settings

    with db.connect() as conn:
        tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
        conn.execute(
            "insert into topic (tenant_id, code, subject_code, name, ord) values (%s, 'ESTIMATE', 'NUM',"
            " 'Estimation', 99) on conflict (tenant_id, code) do nothing",
            (tenant,),
        )
        conn.execute("update skill set topic_code = 'ESTIMATE' where code = 'MD.ESTIMATE'")
        conn.execute(
            "insert into class_skill (tenant_id, section, skill_set_code, taught, taught_by) values"
            " (%s, 'T1-OLD', 'MD.ESTIMATE', true, 'An educator') on conflict do nothing",
            (tenant,),
        )
        topics.load(conn, tenant, settings.seed)
        left = conn.execute(
            "select (select count(*) from topic where code = 'ESTIMATE') as topic,"
            " (select topic_code from skill where code = 'MD.ESTIMATE') as home,"
            " skill_taught_in(%s, 'MD.ESTIMATE', 'T1-OLD') as said,"
            " (select array_agg(code order by ord) from topic) as codes",
            (tenant,),
        ).fetchone()
        seeded = [t["code"] for t in settings.seed("topics.json", "topics")]
        conn.rollback()
    assert (left["topic"], left["home"]) == (0, "DIV"), (
        "the old topic is gone; its skill sits under its operation"
    )
    assert left["said"] is True, "the class's word on the skill outlives the topic it sat in"
    assert left["codes"] == seeded, "exactly the rows' topics, in their order"


@pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")
def test_the_topic_is_no_longer_the_switch():
    """ADR 0076: the word "taught" is a skill's. The topic's own switch (`topic.taught`), each class's word on a topic
    (`class_topic`) and the one-time move of both onto the skills (`internal.topic_words_to_skills`) went with the
    migration after the one that moved them, so no code can read a word nothing writes any more."""
    from engine.core import db

    with db.connect() as conn:
        left = conn.execute(
            "select to_regclass('public.class_topic') is not null as words,"
            " exists (select 1 from information_schema.columns where table_schema = 'public'"
            "   and table_name = 'topic' and column_name like 'taught%%') as switch,"
            " to_regprocedure('internal.topic_words_to_skills()') is not null as move"
        ).fetchone()
    assert dict(left) == {"words": False, "switch": False, "move": False}
