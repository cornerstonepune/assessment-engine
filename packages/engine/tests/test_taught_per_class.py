"""Taught is said for each class (goals/f1f-taught-per-class.yaml, ADR 0073 D5), skill by skill
(goals/t1-topics-are-operations.yaml, ADR 0076).

Nimish, 2026-10-14: "people who are there for one thing like educator only see something that's relevant for their
class and their students." Each class has its own word on each skill, with who said it and when (`class_skill`); a
class no one has spoken for follows the school's word on the skill (`skill_set.taught`). Switching a topic for a class
says it of every skill in the topic (`say_taught`). One rule in the database, `skill_taught_in(tenant, skill, class)`,
read by the engine and the site alike; a topic is taught in a class when any of its skills is (`taught_in`).

MUL.MODELS (in Multiplication, not taught in the school's rows) is Grade 2's at Easy, with questions in the bank.
"""

import os

import pytest

from engine.checks import live_data
from engine.core import db, settings, topics
from engine.w2_print import focus_paper, maker, shelf

WEEK = "T3W1-taught-test"
MODELS = [{"skill_set": "MUL.MODELS", "level": "Easy", "n": 4}]
ADDING = [{"skill_set": "ADD.2D1D", "level": "Easy", "n": 4}]
BY = "F1F Educator"


@pytest.fixture
def conn():
    if not os.getenv("DATABASE_URL"):
        pytest.skip("needs DATABASE_URL (see .env.example)")
    with db.connect() as c:
        yield c
        c.rollback()


def _tenant(conn):
    return conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]


def _child(conn, roll, section, band="G2"):
    return str(
        conn.execute(
            "insert into child (tenant_id, roll_no, section, band) values (%s,%s,%s,%s) returning id",
            (_tenant(conn), roll, section, band),
        ).fetchone()["id"]
    )


def _say(conn, section, topic, taught, skill=None):
    """What an educator's switch on Curriculum writes: this class has (or has not) been taught this topic — every
    skill in it — or, with `skill`, this one skill of it."""
    conn.execute(
        "select say_taught(%s, %s, %s, %s, %s, %s)", (_tenant(conn), section, topic, skill, taught, BY)
    )


def _rule(conn, skill, section):
    return conn.execute(
        "select skill_taught_in(%s, %s, %s) as t", (_tenant(conn), skill, section)
    ).fetchone()["t"]


def test_a_topic_taught_in_one_class_is_on_its_papers_and_refused_in_another(conn):
    """Two Grade 2 classes; one has been taught multiplication's models. Its papers draw on them; the other's are
    refused in words that name the class — whichever way the paper is made — and the school's switch is unchanged."""
    yes = [_child(conn, str(r), "F1F-YES") for r in (1, 2)]
    no = [_child(conn, str(r), "F1F-NO") for r in (1, 2)]
    _say(conn, "F1F-YES", "MUL", True)

    made = maker.plan(conn, "F1F-YES", yes, WEEK, "assessment", "same", MODELS)
    assert not made["refused"] and len(made["papers"]) == 2, "the class taught it is given it"

    with pytest.raises(ValueError, match=r"MUL\.MODELS is not taught in F1F-NO yet"):
        maker.plan(conn, "F1F-NO", no, WEEK, "assessment", "same", MODELS)
    each = maker.plan(conn, "F1F-NO", no, WEEK, "assessment", "each", MODELS)
    assert not each["papers"] and all("not taught in F1F-NO" in r["why"] for r in each["refused"]), each[
        "refused"
    ]

    assert {c["code"] for c in shelf.catalog(conn, "F1F-YES")} >= {"MUL.MODELS"}
    assert "MUL.MODELS" not in {c["code"] for c in shelf.catalog(conn, "F1F-NO")}
    taught = conn.execute("select taught from skill_set where code = 'MUL.MODELS'").fetchone()["taught"]
    assert taught is False, "one class's word is not the school's switch"


def test_a_class_no_one_has_spoken_for_follows_the_schools_switch(conn):
    """Nothing changes on the day: a class with no word of its own is taught what the school's switch says. Its own
    word, once said, is what counts for it — and for no other class."""
    fresh = [_child(conn, str(r), "F1F-NEW") for r in (1, 2)]
    other = [_child(conn, str(r), "F1F-OTHER") for r in (1, 2)]
    assert not maker.plan(conn, "F1F-NEW", fresh, WEEK, "assessment", "same", ADDING)["refused"], (
        "addition is taught in the school, so in a class no one has spoken for"
    )
    with pytest.raises(ValueError, match=r"MUL\.MODELS is not taught in F1F-NEW yet"):
        maker.plan(conn, "F1F-NEW", fresh, WEEK, "assessment", "same", MODELS)

    _say(conn, "F1F-NEW", "ADDSUB", False)
    with pytest.raises(ValueError, match=r"ADD\.2D1D is not taught in F1F-NEW yet"):
        maker.plan(conn, "F1F-NEW", fresh, WEEK, "assessment", "same", ADDING)
    assert not maker.plan(conn, "F1F-OTHER", other, WEEK, "assessment", "same", ADDING)["refused"]

    rule = conn.execute(
        "select taught_in(%s, 'ADDSUB', 'F1F-NEW') as new, taught_in(%s, 'ADDSUB', 'F1F-OTHER') as other,"
        " skill_taught_in(%s, 'MUL.MODELS', 'F1F-OTHER') as models",
        (_tenant(conn),) * 3,
    ).fetchone()
    assert (rule["new"], rule["other"], rule["models"]) == (False, True, False), (
        "the one rule, in the database"
    )


def test_a_childs_own_paper_reads_their_own_class(conn):
    """A paper chosen for one child, like a class paper, is drawn from what their own class was taught."""
    yes, no = _child(conn, "1", "F1F-YES"), _child(conn, "1", "F1F-NO")
    _say(conn, "F1F-YES", "MUL", True)
    assert focus_paper.plan(conn, yes, WEEK, MODELS)["areas"], "taught in their class"
    with pytest.raises(ValueError, match=r"MUL\.MODELS is not taught in F1F-NO yet"):
        focus_paper.plan(conn, no, WEEK, MODELS)


def test_answers_kept_out_of_sight_are_those_on_topics_their_own_class_was_not_taught(conn):
    """`live_data.hidden`: a signed-off answer on a skill whose topic a child's class has not been taught is kept and
    noted, not shown. One class taught it, the other not: only the other's answer is out of sight."""
    before = live_data.hidden(conn).get("MUL.MODELS", 0)
    tenant = _tenant(conn)
    for section in ("F1F-YES", "F1F-NO"):
        conn.execute(
            "insert into evidence_event (tenant_id, child_id, skill_code, rung_code, correct, misconception_codes,"
            " channel, observed_at, confirmed_by) values (%s,%s,'NUM.OPS.03','R41',true,'{}','item',now(),'test')",
            (tenant, _child(conn, "1", section)),
        )
    _say(conn, "F1F-YES", "MUL", True)
    assert live_data.hidden(conn).get("MUL.MODELS", 0) == before + 1


def test_a_class_is_taught_skill_by_skill(conn):
    """ADR 0076: switching Multiplication on for a class switches on every skill in it; an educator can then leave one
    off — column multiplication, until next term — and that skill alone is refused on the class's papers, in words that
    name the class. The topic still shows as taught there; switching the topic on again switches the skill back on."""
    kids = [_child(conn, str(r), "T1-SKILL", "G3") for r in (1, 2)]
    _say(conn, "T1-SKILL", "MUL", True)
    _say(conn, "T1-SKILL", "MUL", False, skill="MUL.2D1D")

    codes = {c["code"] for c in shelf.catalog(conn, "T1-SKILL")}
    assert {"MUL.MODELS", "MUL.FACTS"} <= codes and "MUL.2D1D" not in codes, codes
    with pytest.raises(ValueError, match=r"MUL\.2D1D is not taught in T1-SKILL yet"):
        maker.plan(
            conn,
            "T1-SKILL",
            kids,
            WEEK,
            "assessment",
            "same",
            [{"skill_set": "MUL.2D1D", "level": "Easy", "n": 4}],
        )
    tenant = _tenant(conn)
    topic = conn.execute("select taught_in(%s, 'MUL', 'T1-SKILL') as t", (tenant,)).fetchone()["t"]
    assert (topic, _rule(conn, "MUL.MODELS", "T1-SKILL"), _rule(conn, "MUL.2D1D", "T1-SKILL")) == (
        True,
        True,
        False,
    )

    _say(conn, "T1-SKILL", "MUL", True)
    assert _rule(conn, "MUL.2D1D", "T1-SKILL") is True, "the topic's switch says it of every skill again"


def test_regrouping_the_topics_changes_no_classs_paper(conn):
    """ADR 0076, decision 3: every word "taught" is said of a skill — the school's on the skill set, each class's in
    `class_skill` — so a load that moves a skill to another topic, or drops the topic it sat in, changes no class's
    paper. (On the day the topics were regrouped, migration 20261113090000 wrote each word said of a topic onto the
    skills it held; this is what keeps it true at every load after.)

    In small: three skills of what is now Multiplication, each in an old topic of its own — equal groups taught by
    the rows, models not taught, columns switched on for the school by the coordinator. One class said columns not
    taught; another said equal groups not taught and models taught; a third no one has spoken for."""
    tenant = _tenant(conn)
    old = [("T1.BEGUN", "MUL.GROUPS"), ("T1.MODELS", "MUL.MODELS"), ("T1.COLS", "MUL.2D1D")]
    for i, (code, skill) in enumerate(old):
        conn.execute(
            "insert into topic (tenant_id, code, subject_code, name, ord) values (%s, %s, 'NUM', %s, %s)",
            (tenant, code, code, 90 + i),
        )
        conn.execute("update skill_set set topic_code = %s where code = %s", (code, skill))
    conn.execute(
        "update skill_set set taught = true, taught_by = 'The coordinator', taught_at = now() where code = 'MUL.2D1D'"
    )
    conn.execute("delete from class_skill where section in ('T1-A', 'T1-B', 'T1-NEW')")
    _child(conn, "T1-A-1", "T1-A")
    _child(conn, "T1-B-1", "T1-B")
    _say(conn, "T1-A", "T1.COLS", False)
    _say(conn, "T1-B", "T1.BEGUN", False)
    _say(conn, "T1-B", "T1.MODELS", True)
    skills = [s for _, s in old]
    sections = ("T1-A", "T1-B", "T1-NEW")

    was = {(k, c): _rule(conn, k, c) for k in skills for c in sections}
    assert was == {
        ("MUL.GROUPS", "T1-A"): True, ("MUL.GROUPS", "T1-B"): False, ("MUL.GROUPS", "T1-NEW"): True,
        ("MUL.MODELS", "T1-A"): False, ("MUL.MODELS", "T1-B"): True, ("MUL.MODELS", "T1-NEW"): False,
        ("MUL.2D1D", "T1-A"): False, ("MUL.2D1D", "T1-B"): True, ("MUL.2D1D", "T1-NEW"): True,
    }  # fmt: skip

    topics.load(conn, tenant, settings.seed)

    now = {(k, c): _rule(conn, k, c) for k in skills for c in sections}
    assert now == was, {k: (was[k], now[k]) for k in was if was[k] != now[k]}
    homes = conn.execute(
        "select array_agg(distinct topic_code) as t from skill_set where code = any(%s)", (skills,)
    ).fetchone()["t"]
    gone = conn.execute("select count(*) as n from topic where code like 'T1.%%'").fetchone()["n"]
    assert (homes, gone) == (["MUL"], 0), (
        "the old topics are gone; each skill sits under Multiplication, its words on it"
    )
