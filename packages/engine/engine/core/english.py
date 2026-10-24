"""English, Grades 3 and 4, as drafts in the tables that already exist (goals/e0-english-in-the-system.yaml, BUILD-ORDER
"E0"). The rows are the seed's in supabase/seed/english/ (PR #254, #272); this puts them where the maths already is:
subject, topics, skills, their levels, the kinds of question and which a level uses, the named mistakes and which skill
watches for which, and what comes before each skill.

Drafts, and the educator's after that: a skill, its levels and its prerequisites are inserted once and never
overwritten, as a maths skill set is; a kind and a mistake are upserted from the seed, as the maths ones are. Nothing
here approves anything: no level is confirmed and no kind approved, so `drawable_item` offers no English question to a
paper until a person approves both.

The samples are stored whole (goals/smp_skill_shows_its_samples.yaml): each with its passage, the question as printed,
the right answer and its likely wrong answers, each naming a mistake, and the rubric an open answer is read against
(`samples`). What the tables cannot hold is left out, not faked (the note says which slice each waits on): the observed
kinds (`question_type.reaches` allows printed, read aloud and drawn) and the observed skills. Three words of the seed are read in the tables' own (a subject's `mark_mode` is `lookup` or `rubric`; English is marked kind by kind): a mistake a model or the educator
detects is `teacher` (`misconception.detectable_by` has four words), which is who reads an open answer while a kind is
new (BUILD-ORDER, C4 decides when that changes).
"""

import json
from collections.abc import Callable
from typing import Any

from engine.core import db, settings

SUBJECT = "ENG"
FOLDER = "english/"
# the words the table allows, for the words the seed uses
DETECTED_BY = {"model": "teacher", "educator": "teacher"}
MARK_MODE = {"question_type": "lookup"}  # English is marked kind by kind (`question_type.marked`)


def seed(name: str, key: str) -> Any:
    return settings.seed(FOLDER + name, key)


def with_english(maths: Callable[[str, str], Any]) -> Callable[[str, str], Any]:
    """The seed as `topics.load` reads it, with English's topics and skills beside the maths ones, so the tree is
    placed and cleaned once, whole."""

    def read(name: str, key: str) -> Any:
        rows = maths(name, key)
        if name == "topics.json":
            return rows + seed("topic.json", "topics")
        if name == "skill_sets.json":
            return rows + [{"code": s["code"]} for s in seed("skill.json", "skills")]
        return rows

    return read


def _paper_kinds() -> list[dict[str, Any]]:
    """The kinds that go on a paper; the observed ones (read aloud, talk, extended) are for the observation engine."""
    return [q for q in seed("question_type.json", "question_types") if q["reaches"] != "observed"]


def subject(conn: db.Conn, t: db.Id) -> None:
    for s in seed("subject.json", "subjects"):
        conn.execute(
            "insert into subject (tenant_id, code, name, label, verifier, mark_mode) values (%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do update set name=excluded.name, label=excluded.label,"
            " verifier=excluded.verifier, mark_mode=excluded.mark_mode, updated_at=now()",
            (
                t,
                s["code"],
                s["name"],
                s.get("label"),
                s.get("verifier"),
                MARK_MODE.get(s["mark_mode"], s["mark_mode"]),
            ),
        )


def mistakes(conn: db.Conn, t: db.Id) -> None:
    for m in seed("misconception.json", "misconceptions"):
        conn.execute(
            "insert into misconception (tenant_id, code, op, name, description, repair_hint, detectable_by, source)"
            " values (%s,%s,'any',%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code, op) do update set name=excluded.name, description=excluded.description,"
            " repair_hint=excluded.repair_hint, detectable_by=excluded.detectable_by, source=excluded.source,"
            " updated_at=now()",
            (
                t,
                m["code"],
                m["name"],
                m["description"],
                m["repair_hint"],
                DETECTED_BY.get(m["detectable_by"], m["detectable_by"]),
                "English Grades 3 and 4 draft",
            ),
        )


def kinds(conn: db.Conn, t: db.Id) -> None:
    """Each kind's words, how it reaches the child and who marks it. Unapproved: a person approves it."""
    rows = [
        {
            "code": q["code"],
            "fmt": q["code"],
            "words": q["name"],
            "reaches": q["reaches"],
            "marked": ["closed_set" if q["answer"] == "one" else "open_response"],
            "own_words": True,
        }
        for q in _paper_kinds()
    ]
    conn.execute(
        "insert into question_type (tenant_id, code, fmt, words, reaches, marked, own_words)"
        " select %s, x.code, x.fmt, x.words, x.reaches, x.marked::eval_type[], x.own_words from jsonb_to_recordset(%s::jsonb)"
        "   x(code text, fmt text, words text, reaches text, marked text[], own_words boolean)"
        " on conflict (tenant_id, code) do update set fmt = excluded.fmt, words = excluded.words,"
        " reaches = excluded.reaches, marked = excluded.marked, own_words = excluded.own_words"
        " where row(question_type.fmt, question_type.words, question_type.reaches, question_type.marked)"
        " is distinct from row(excluded.fmt, excluded.words, excluded.reaches, excluded.marked)",
        (t, json.dumps(rows)),
    )


def skills(conn: db.Conn, t: db.Id) -> None:
    """Each skill once, with its levels (the database makes `skill_level` from the skill's `difficulty`, and the links
    to its mistakes from `misconception_codes`). A skill's code is also its `rung_code`, the column B4 kept on `skill`."""
    levels: dict[str, dict[str, Any]] = {}
    for lv in seed("skill_level.json", "skill_levels"):
        levels.setdefault(lv["skill_code"], {})[lv["difficulty"]] = {"words": lv["looks_like"], **lv["rule"]}
    watched: dict[str, list[str]] = {}
    for m in seed("skill_mistake.json", "skill_mistakes"):
        watched.setdefault(m["skill_code"], []).append(m["misconception_code"])
    open_kinds = {q["code"] for q in _paper_kinds() if q["answer"] != "one"}
    for s in seed("skill.json", "skills"):
        eval_type = "open_response" if open_kinds & set(s["question_types"]) else "closed_set"
        conn.execute(
            "insert into skill (tenant_id, code, rung_code, name, learning_objective, misconception_codes,"
            " difficulty, eval_type, grade, descriptor) values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"
            " on conflict (tenant_id, code) do nothing",
            (
                t,
                s["code"],
                s["code"],
                s["name"],
                s["learning_objective"],
                sorted(watched.get(s["code"], [])),
                json.dumps(levels[s["code"]]),
                eval_type,
                s["grade"],
                s["learning_objective"],
            ),
        )


def level_kinds(conn: db.Conn, t: db.Id) -> None:
    """Which kinds each level uses. Written after the kinds, because writing a kind clears every level's links to be
    made again from the bank, which holds no English question (they come back on every load)."""
    conn.execute(
        "insert into skill_level_question_type (tenant_id, skill_code, difficulty, question_type)"
        " select %s, x.skill_code, x.difficulty, x.question_type from jsonb_to_recordset(%s::jsonb)"
        "   x(skill_code text, difficulty text, question_type text)"
        " on conflict (tenant_id, skill_code, difficulty, question_type) do nothing",
        (t, json.dumps(seed("skill_level_question_type.json", "skill_level_question_types"))),
    )


def prerequisites(conn: db.Conn, t: db.Id) -> None:
    """Drafted once: only while no English skill has any, so one a person removes stays removed (ADR 0092)."""
    conn.execute(
        "insert into skill_prerequisite (tenant_id, skill_code, before_code)"
        " select %s, x.skill_code, x.before_code from jsonb_to_recordset(%s::jsonb) x(skill_code text, before_code text)"
        " where not exists (select 1 from skill_prerequisite p join skill s"
        "   on s.tenant_id = p.tenant_id and s.code = p.skill_code join topic o"
        "   on o.tenant_id = s.tenant_id and o.code = s.topic_code where p.tenant_id = %s and o.subject_code = %s)",
        (t, json.dumps(seed("skill_prerequisite.json", "skill_prerequisites")), t, SUBJECT),
    )


SAMPLE_TABLES = ("passage", "rubric", "english_sample", "english_sample_wrong")


def samples(conn: db.Conn, t: db.Id) -> None:
    """The passages, the rubrics, and every sample with its wrong answers, upserted from the seed: a row changes only
    when the seed's words do, so a second load moves nothing. A sample whose level or kind is not loaded yet waits for
    the load that brings them (a deploy runs this before anyone has run the full load). Nothing here is an approval."""
    passages = seed("passage.json", "passages")
    conn.execute(
        "insert into passage (tenant_id, code, grade, kind, title, text, facts)"
        " select %s, x.code, x.grade, x.kind, x.title, x.text, x.facts from jsonb_to_recordset(%s::jsonb)"
        "   x(code text, grade text, kind text, title text, text text, facts jsonb)"
        " on conflict (tenant_id, code) do update set grade = excluded.grade, kind = excluded.kind,"
        " title = excluded.title, text = excluded.text, facts = excluded.facts"
        " where row(passage.grade, passage.kind, passage.title, passage.text, passage.facts)"
        " is distinct from row(excluded.grade, excluded.kind, excluded.title, excluded.text, excluded.facts)",
        (t, json.dumps(passages)),
    )
    conn.execute(
        "insert into rubric (tenant_id, code, name, applies_to, criteria, scale, skill_codes)"
        " select %s, x.code, x.name, x.applies_to, x.criteria, x.scale, x.skill_codes from jsonb_to_recordset(%s::jsonb)"
        "   x(code text, name text, applies_to text, criteria jsonb, scale text[], skill_codes text[])"
        " on conflict (tenant_id, code) do update set name = excluded.name, applies_to = excluded.applies_to,"
        " criteria = excluded.criteria, scale = excluded.scale, skill_codes = excluded.skill_codes"
        " where row(rubric.name, rubric.applies_to, rubric.criteria, rubric.scale, rubric.skill_codes)"
        " is distinct from row(excluded.name, excluded.applies_to, excluded.criteria, excluded.scale, excluded.skill_codes)",
        (t, json.dumps(seed("rubric.json", "rubrics"))),
    )
    rows = [
        {
            "skill_code": x["skill_code"],
            "difficulty": x["difficulty"],
            "question_type": x["question_type"],
            "ord": x["n"],
            "ask": x["ask"],
            "passage_code": x["passage"],
            "text": x["text"],
            "options": x["options"],
            "answer": x["answer"],
            "accept": x["accept"],
            "rubric_code": x.get("rubric"),
            "key_points": x.get("key_points"),
            "must_contain": x.get("must_contain"),
            "not_words": x.get("not_words"),
            "worked_out": x.get("check"),
            "wrong": [{"answer": a, "mistake_code": m} for a, m in x["wrong"].items()],
        }
        for x in seed("skill_level_sample.json", "samples")
    ]
    conn.execute(
        "insert into english_sample as e (tenant_id, skill_code, difficulty, question_type, ord, ask, passage_code, text,"
        "   options, answer, accept, rubric_code, key_points, must_contain, not_words, worked_out)"
        " select %s, x.skill_code, x.difficulty, x.question_type, x.ord, x.ask, x.passage_code, x.text, x.options,"
        "   x.answer, x.accept, x.rubric_code, x.key_points, x.must_contain, x.not_words, x.worked_out"
        " from jsonb_to_recordset(%s::jsonb) x(skill_code text, difficulty text, question_type text, ord smallint,"
        "   ask text, passage_code text, text text, options jsonb, answer jsonb, accept jsonb, rubric_code text,"
        "   key_points jsonb, must_contain jsonb, not_words jsonb, worked_out jsonb)"
        " join skill_level l on l.tenant_id = %s and l.skill_code = x.skill_code and l.difficulty = x.difficulty"
        " join question_type q on q.tenant_id = %s and q.code = x.question_type"
        " on conflict (tenant_id, skill_code, difficulty, question_type, ord) do update set ask = excluded.ask,"
        "   passage_code = excluded.passage_code, text = excluded.text, options = excluded.options,"
        "   answer = excluded.answer, accept = excluded.accept, rubric_code = excluded.rubric_code,"
        "   key_points = excluded.key_points, must_contain = excluded.must_contain, not_words = excluded.not_words,"
        "   worked_out = excluded.worked_out"
        " where row(e.ask, e.passage_code, e.text, e.options, e.answer, e.accept, e.rubric_code, e.key_points,"
        "   e.must_contain, e.not_words, e.worked_out) is distinct from row(excluded.ask, excluded.passage_code,"
        "   excluded.text, excluded.options, excluded.answer, excluded.accept, excluded.rubric_code,"
        "   excluded.key_points, excluded.must_contain, excluded.not_words, excluded.worked_out)",
        (t, json.dumps(rows), t, t),
    )
    conn.execute(
        "insert into english_sample_wrong as w (tenant_id, sample_id, answer, mistake_code)"
        " select %s, e.id, y.answer, y.mistake_code"
        " from jsonb_to_recordset(%s::jsonb) x(skill_code text, difficulty text, question_type text, ord smallint,"
        "   wrong jsonb)"
        " join english_sample e on e.tenant_id = %s and e.skill_code = x.skill_code and e.difficulty = x.difficulty"
        "   and e.question_type = x.question_type and e.ord = x.ord"
        " cross join jsonb_to_recordset(x.wrong) y(answer text, mistake_code text)"
        " join misconception m on m.tenant_id = e.tenant_id and m.code = y.mistake_code and m.op = 'any'"
        " on conflict (sample_id, answer) do update set mistake_code = excluded.mistake_code"
        " where w.mistake_code is distinct from excluded.mistake_code",
        (t, json.dumps(rows), t),
    )
