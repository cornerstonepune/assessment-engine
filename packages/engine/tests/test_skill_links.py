"""A level's samples, a skill's mistakes, its registry skills and what comes before it are rows
(goals/b3-samples-mistakes-prerequisites.yaml, ADR 0092).

Nimish, 2026-10-20: "we need proper tables". Each list a skill held where the database never looked is now rows with
real keys, kept equal to the list while the list is still written; three decisions taken by rules a test checks (B3-1
the split of a level's examples, B3-2 which division mistakes stay, B3-3 what comes before a skill).
"""

import json
import os
import random

import psycopg
import pytest

from engine.assess import draw, graph
from engine.checks import links, past
from engine.core import db, loaders, settings
from engine.w1_bank import cases, kinds, spec
from tests.rows import data_steps

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

MIGRATION = (
    db.REPO_ROOT / "supabase/migrations/20261127090000_samples_mistakes_links_and_prerequisites_are_rows.sql"
)


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _refused(conn, sql, params=()):
    """True when the database refuses `sql`; the transaction carries on either way."""
    try:
        with conn.transaction():
            conn.execute(sql, params)
    except psycopg.errors.IntegrityError:
        return True
    return False


def _samples(conn, code, level, card=None):
    return [
        r["sample"]
        for r in conn.execute(
            "select sample from skill_level_sample where skill_code = %s and difficulty = %s"
            " and question_format is not distinct from %s order by ord",
            (code, level, card),
        )
    ]


def test_every_card_example_and_level_example_is_a_sample_row(conn):
    """Nimish: "we need proper tables". Every card kind's example is a row in its place, and every example a level's
    words give is a row; the counts are the seed's own, worked from the seed's files, not from the database."""
    r = links.compare(conn)
    assert r["disagree"] == []
    cards = sum(
        len(v)
        for f in settings.seed("question_formats.json", "question_formats")
        for v in f["examples"].values()
    )
    assert r["card_samples"] == r["card_examples"] == cards == 11
    words = sum(
        len(links.samples(level.get("words")))
        for s in settings.seed("skill_sets.json", "skill_sets")
        for level in s["difficulty"].values()
    )
    assert r["word_samples"] == words > 200
    assert _samples(conn, "MUL.THREE", "Easy", "MUL3.SUM") == ["2 × 3 × 2 = □", "5 × 2 × 2 = □"]


def test_a_levels_samples_are_its_words_own_examples_in_order(conn):
    """Nimish: "we need proper tables". Decision B3-1, by the rule the words follow: the examples after their colon, each
    a number sentence, in the words' order; a piece in words stays words; the words themselves never change; a person
    changing a level's words changes its samples."""
    for r in conn.execute(
        "select l.skill_code, l.difficulty, l.looks_like, array_agg(x.sample order by x.ord) as got"
        " from skill_level l join skill_level_sample x on x.tenant_id = l.tenant_id and x.skill_code = l.skill_code"
        "  and x.difficulty = l.difficulty and x.question_format is null group by 1, 2, 3"
    ):
        tail, at = r["looks_like"].rsplit(":", 1)[1], 0
        for sample in r["got"]:
            at = tail.index(sample, at) + len(sample)  # each is the words' own text, in their order
            assert not any(c.isalpha() for c in sample.replace(" r ", " ")), (r["skill_code"], sample)
    assert _samples(conn, "MUL.FACTS", "Easy") == ["2 × 7", "5 × 6", "10 × 4"]
    assert _samples(conn, "MUL.MODELS", "Easy") == ["5, 10, 15, 20, □"]
    assert _samples(conn, "DIV.FACTS", "Advance")[-1] == "3 ÷ 5 = 0 r 3"
    advance = _samples(conn, "MUL.2D1D", "Advance")
    assert "2□ × 4 = 92" in advance and not any("found wrong" in s for s in advance)
    blob = conn.execute(
        "select difficulty -> 'Easy' ->> 'words' as w from skill where code = 'MUL.FACTS'"
    ).fetchone()
    assert (
        blob["w"]
        == conn.execute(
            "select looks_like from skill_level where skill_code = 'MUL.FACTS' and difficulty = 'Easy'"
        ).fetchone()["looks_like"]
    )
    conn.execute(
        "update skill set difficulty = jsonb_set(difficulty, '{Easy,words}', to_jsonb('The 2 table: 2 × 3, 2 × 9.'::text))"
        " where code = 'MUL.FACTS'"
    )
    assert _samples(conn, "MUL.FACTS", "Easy") == ["2 × 3", "2 × 9"]


def test_every_code_a_skill_names_is_a_key_the_database_checks(conn):
    """Nimish: "we need proper tables". A mistake, a registry skill or a prerequisite that is no row is refused, and a
    mistake a skill names cannot be taken out from under it; the website cannot write the mirrors behind the lists."""
    assert _refused(
        conn,
        "update skill set misconception_codes = misconception_codes || '{M_NOT_A_MISTAKE}' where code = 'MUL.FACTS'",
    )
    assert _refused(
        conn,
        "update skill set registry_codes = registry_codes || '{NOT.A.SKILL}' where rung_code = 'R36'",
    )
    assert _refused(conn, "delete from misconception where code = 'M_DIV_SUBTRACTED'")
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    assert _refused(
        conn,
        "insert into skill_prerequisite (tenant_id, skill_code, before_code) values (%s, 'MUL.FACTS', 'NOT.A.SKILL')",
        (tenant,),
    )
    assert _refused(
        conn,
        "insert into skill_level_sample (tenant_id, skill_code, difficulty, ord, sample)"
        " values (%s, 'MUL.FACTS', 'Expert', 1, '2 × 2')",
        (tenant,),
    )
    grants = {
        r["table_name"]
        for r in conn.execute(
            "select distinct table_name from information_schema.role_table_grants where grantee = 'app_web'"
            " and privilege_type in ('INSERT', 'UPDATE', 'DELETE')"
            " and table_name in ('skill_level_sample', 'skill_mistake', 'skill_registry_link')"
        )
    }
    assert grants == set()


def test_mistakes_and_registry_links_equal_the_skills_lists(conn):
    """Nimish: "we need proper tables". Every skill's mistake rows are its list's codes, each written for every
    operation it shows in, and its registry links are its rung's; on a database from the seed, the seed's lists."""
    seed = {s["code"]: s for s in settings.seed("skill_sets.json", "skill_sets")}
    rungs = {r["code"]: r for r in settings.seed("rungs.json", "rungs")}
    for r in conn.execute(
        "select s.code, s.rung_code, s.misconception_codes,"
        " (select array_agg(distinct misconception_code) from skill_mistake k where k.skill_code = s.code) as mistakes,"
        " (select array_agg(registry_skill) from skill_registry_link l where l.skill_code = s.code) as links"
        " from skill s"
    ):
        assert set(r["misconception_codes"]) == set(r["mistakes"] or []), r["code"]
        if r["code"] in seed:
            assert set(r["misconception_codes"]) == set(seed[r["code"]]["misconception_codes"]), r["code"]
            assert set(r["links"]) == set(rungs[r["rung_code"]]["skill_codes"]), r["code"]
    ops = conn.execute(
        "select array_agg(op) as ops from skill_mistake where skill_code = 'MUL.FACTS' and misconception_code = 'M_WRONG_OP'"
    ).fetchone()["ops"]
    assert sorted(ops) == sorted(
        r["op"] for r in conn.execute("select op from misconception where code = 'M_WRONG_OP'")
    )
    assert conn.execute("select count(*) as n from skill_registry_link").fetchone()["n"] == sum(
        len(rungs[s["rung_code"]]["skill_codes"]) for s in seed.values()
    )


def test_the_division_mistakes_on_multiplication_facts_stay_where_a_division_computes_them(conn):
    """Nimish: "we need proper tables". Decision B3-2: a division mistake stays on a skill where the mistake's own rule
    computes a wrong answer on a division that skill's questions ask. All 8 on Multiplication facts do, each on a box of
    its Advance fact family that asks a division ("30 ÷ 10 = □"), its answer there not the right one. A sample can show
    that a mistake happens, never that it cannot, so no list is shortened on a sample's word."""
    division = {
        r["code"]
        for r in conn.execute("select code from misconception group by code having bool_and(op = '÷')")
    }
    s = spec.row(conn, "MUL.FACTS")
    named = set(s["misconception_codes"]) & division
    assert len(named) == 8
    check = kinds.resolve(conn, s["difficulty"]["Advance"]["check"])
    on_division = set()
    for _, item in draw.level(random.Random(1), check, cases.for_level(conn, check), s["rung_code"], 168):
        for box in item.responses:
            if "÷" in (box.label or ""):
                for code, wrong in (box.misconceptions or {}).items():
                    if code in division:
                        assert str(wrong) != str(box.answer), (box.label, code)
                        on_division.add(code)
    assert on_division == named


def test_prerequisites_come_from_the_ladders_grades_and_no_skill_comes_before_itself(conn):
    """Nimish: "everything is now getting built in a proper, scalable way, not as some one-time random effort".
    Decision B3-3: a skill comes after every skill of its topic on the nearest grade below its own, worked out here from
    the database's own topics and grades; no skill comes before itself, however long the way round."""
    skills = conn.execute(
        "select s.code, s.topic_code, g.ord from skill s"
        " join grade g on g.tenant_id = s.tenant_id and g.code = s.grade"
        " join topic o on o.tenant_id = s.tenant_id and o.code = s.topic_code where o.subject_code <> 'ENG'"  # E0: English's own
    ).fetchall()
    expected = set()
    for s in skills:
        below = [t["ord"] for t in skills if t["topic_code"] == s["topic_code"] and t["ord"] < s["ord"]]
        if below:
            expected |= {
                (s["code"], t["code"])
                for t in skills
                if t["topic_code"] == s["topic_code"] and t["ord"] == max(below)
            }
    rows = {
        (r["skill_code"], r["before_code"])
        for r in conn.execute(
            "select p.skill_code, p.before_code from skill_prerequisite p join skill s on s.tenant_id = p.tenant_id"
            " and s.code = p.skill_code join topic o on o.tenant_id = s.tenant_id and o.code = s.topic_code"
            " where o.subject_code <> 'ENG'"
        )
    }
    assert rows == expected and len(rows) == 167
    assert ("MUL.FACTS", "MUL.GROUPS") in rows and ("ADD.2D1D", "ADD.1D1D") in rows
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    add = "insert into skill_prerequisite (tenant_id, skill_code, before_code) values (%s, %s, %s)"
    assert _refused(conn, add, (tenant, "MUL.FACTS", "MUL.FACTS"))
    assert _refused(
        conn, add, (tenant, "MUL.GROUPS", "MUL.FACTS")
    )  # MUL.FACTS already comes after MUL.GROUPS
    assert _refused(conn, add, (tenant, "ADD.1D1D", "SUB.4D"))  # the long way round, through every grade


def test_a_new_sample_mistake_or_link_is_an_insert(conn):
    """Nimish: "everything is now getting built in a proper, scalable way, not as some one-time random effort". A new
    mistake, card example, registry skill or prerequisite is an insert into rows, no code; and a prerequisite a person
    removed stays removed when the seed is loaded again."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    conn.execute(
        "insert into misconception (tenant_id, code, op, name, detectable_by) values (%s, 'M_TEST_NEW', '×', 'A test', 'teacher')",
        (tenant,),
    )
    conn.execute(
        "update skill set misconception_codes = misconception_codes || '{M_TEST_NEW}' where code = 'MUL.FACTS'"
    )
    conn.execute(
        "insert into misconception (tenant_id, code, op, name, detectable_by) values (%s, 'M_TEST_NEW', '÷', 'A test', 'teacher')",
        (tenant,),
    )
    assert sorted(
        conn.execute(
            "select array_agg(op) as ops from skill_mistake where misconception_code = 'M_TEST_NEW'"
        ).fetchone()["ops"]
    ) == ["×", "÷"]
    conn.execute(
        "update question_format set kind = jsonb_set(kind, '{examples,Easy}', kind -> 'examples' -> 'Easy' || '[\"3 × 3 × 3 = □\"]')"
        " where code = 'MUL3.SUM'"
    )
    assert _samples(conn, "MUL.THREE", "Easy", "MUL3.SUM")[-1] == "3 × 3 × 3 = □"
    other = conn.execute(
        "select code from registry_skill"
        " where code <> all(select unnest(registry_codes) from skill where rung_code = 'R36') limit 1"
    ).fetchone()["code"]
    conn.execute(
        "update skill set registry_codes = registry_codes || %s::text where rung_code = 'R36'", (other,)
    )
    assert conn.execute(
        "select 1 from skill_registry_link where skill_code = 'MUL.FACTS' and registry_skill = %s", (other,)
    ).fetchone()
    conn.execute(
        "delete from skill_prerequisite where skill_code = 'MUL.FACTS' and before_code = 'MUL.GROUPS'"
    )
    loaders._prerequisites(conn, tenant)
    assert not conn.execute(
        "select 1 from skill_prerequisite where skill_code = 'MUL.FACTS' and before_code = 'MUL.GROUPS'"
    ).fetchone()
    conn.execute(
        "insert into skill_prerequisite (tenant_id, skill_code, before_code) values (%s, 'MUL.FACTS', 'MUL.GROUPS')",
        (tenant,),
    )


def test_past_results_are_the_same_before_and_after(conn):
    """Nimish: "nothing will change for any of the past assessments, scoring etc. right?". The evidence (its count and
    checksum), every child's states and every scored answer are the same before and after B3's migration, run again on
    a database that has them; and the fingerprint does see a change, so its sameness means something."""
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    child = conn.execute(
        "insert into child (tenant_id, roll_no, section, band) values (%s, '1', 'LINKTEST', 'G3') returning id",
        (tenant,),
    ).fetchone()["id"]
    add = (
        "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, channel, observed_at,"
        " confirmed_by, misconception_codes) values (%s, %s, 'NUM.OPS.01', 'R45', %s, 'item', now(), 'test', %s)"
    )
    for right, codes in ((True, []), (False, ["M_DIV_TENS_ZERO_EXTRA"]), (True, [])):
        conn.execute(add, (tenant, child, right, codes))
    graph.rebuild(conn, str(child))
    before = past.fingerprint(conn)
    assert before["evidence"]["n"] >= 3 and before["states"]["n"] >= 1
    conn.execute(data_steps(MIGRATION))
    graph.rebuild(conn, str(child))
    assert past.fingerprint(conn) == before
    conn.execute(add, (tenant, child, False, []))
    assert past.fingerprint(conn)["evidence"] != before["evidence"]


def test_the_seeds_prerequisites_name_only_skills_the_seed_has():
    """The draft the loader inserts names only skills the seed makes, so a fresh build cannot fail on it."""
    codes = {s["code"] for s in settings.seed("skill_sets.json", "skill_sets")}
    pairs = settings.seed("skill_prerequisites.json", "skill_prerequisites")
    assert pairs and {p["skill"] for p in pairs} | {p["after"] for p in pairs} <= codes
    assert len({json.dumps(p, sort_keys=True) for p in pairs}) == len(pairs)
