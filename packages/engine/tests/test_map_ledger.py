"""The curriculum mapping agents against a database built from the migrations (goals/m1-05-mapping-agents.yaml):
the ledger (supabase/migrations/20261230090000_curriculum_proposal_ledger.sql), a recorded run proposed, decided,
applied and reverted, and the eval scoring a recorded gold-set run.

Every row is a placeholder in a band of the test's own ("KX"), made inside the test's transaction and rolled back.
No model is called: every reply is a recorded one (a file the test writes), as on a machine with no key.
"""

import json
import os
import re

import psycopg
import pytest
from typer.testing import CliRunner

from engine import cli
from engine.core import db
from engine.w1_bank import cli_map, map_ledger
from engine.w1_bank.map_agents import Rules, propose, propose_lo_skills, read_band, recorded_ask
from tests.rows import tenant

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

BAND = "KX"
RULES = Rules(min_confidence=0.8, audit_share=0.0, examples=3)


@pytest.fixture
def conn():
    with db.connect() as c:
        yield c
        c.rollback()


def _activity(conn, t, code, strand, name, skills=(), los=()):
    conn.execute(
        "insert into activity (tenant_id, code, band, strand, name, objective, level_1) values (%s,%s,%s,%s,%s,'',%s)",
        (t, code, BAND, strand, name, "Tries it with help" if skills else ""),
    )
    for s in skills:
        conn.execute(
            "insert into activity_skill (tenant_id, activity_code, skill_code) values (%s,%s,%s)",
            (t, code, s),
        )
    for i, lo in enumerate(los, 1):
        conn.execute(
            "insert into learning_objective (tenant_id, code, band, subject, unit, title, signal)"
            " values (%s,%s,%s,%s,%s,%s,'')",
            (t, lo, BAND, strand, strand, f"The children will {name.lower()}"),
        )
        conn.execute(
            "insert into activity_objective (tenant_id, activity_code, lo_code, ord) values (%s,%s,%s,%s)",
            (t, code, lo, i),
        )


def _staff(conn, t, email="lead@school.invalid"):
    """A member of staff with an email: a placeholder, never a real person."""
    campus = conn.execute("select id from campus where tenant_id = %s limit 1", (t,)).fetchone()["id"]
    sid = conn.execute(
        "insert into staff (tenant_id, campus_id) values (%s, %s) returning id", (t, campus)
    ).fetchone()["id"]
    conn.execute(
        "insert into pii.staff (tenant_id, staff_id, name, email) values (%s, %s, 'A placeholder', %s)",
        (t, sid, email),
    )
    return sid


def _band(conn):
    """Four activities people mapped (the gold), and three with gaps: one missing its skill, one missing everything,
    one in a subject people never mapped."""
    t = tenant(conn)
    conn.execute("insert into grade (tenant_id, code, name, ord) values (%s, %s, 'Test band', 99)", (t, BAND))
    _activity(conn, t, "ACT-KX-0001", "Maths", "Count beads to ten", ["NUM.CNT.01"], ["LO-KX-0001-1"])
    _activity(conn, t, "ACT-KX-0002", "Maths", "Count back from ten", ["NUM.CNT.02"], ["LO-KX-0002-1"])
    _activity(
        conn,
        t,
        "ACT-KX-0003",
        "Maths",
        "Thread beads by count",
        ["NUM.CNT.01", "MOT.FMS.01"],
        ["LO-KX-0003-1"],
    )
    _activity(conn, t, "ACT-KX-0004", "Maths", "Pinch and count seeds", ["MOT.FMS.01"], ["LO-KX-0004-1"])
    _activity(conn, t, "ACT-KX-0101", "Maths", "Count shells in a basket", [], ["LO-KX-0101-1"])
    _activity(conn, t, "ACT-KX-0102", "Maths", "Count steps on the stairs")
    _activity(conn, t, "ACT-KX-0103", "Clay", "Roll clay snakes")
    conn.execute(  # a skill of this band (a milestone at it) that people never linked to Clay
        "insert into milestone (tenant_id, skill_code, band, descriptor, scale, source)"
        " values (%s, 'ART.CLAY.01', %s, 'Rolls clay', 'yes_sometimes_no_na', 'a test')",
        (t, BAND),
    )
    return t


def _replies(tmp_path, extra=None):
    agree = {"verdict": "agree", "why": "the children count"}
    body = {
        "curriculum_map_propose": {
            "ACT-KX-0101": {
                "skills": ["NUM.CNT.01"],
                "objective_code": "",
                "objective_text": "",
                "levels": {},
                "confidence": 0.95,
                "reason": "counting shells",
            },
            "ACT-KX-0102": {
                "skills": ["NUM.CNT.99"],
                "objective_code": "",
                "objective_text": "The children will count steps.",
                "levels": {
                    "level_0": "Watches",
                    "level_1": "Counts to 3",
                    "level_2": "Counts to 6",
                    "level_3": "Counts all the steps",
                },
                "confidence": 0.9,
                "reason": "counting steps",
            },
            "ACT-KX-0103": {
                "skills": ["ART.CLAY.01"],
                "objective_code": "",
                "objective_text": "x",
                "levels": {},
                "confidence": 0.9,
                "reason": "clay",
            },
        },
        "curriculum_map_validate": {c: agree for c in ("ACT-KX-0101", "ACT-KX-0102", "ACT-KX-0103")}
        | {f"LO-KX-{n}-1": agree for n in ("0001", "0002", "0003", "0004")},
    }
    for purpose, more in (extra or {}).items():
        body[purpose] |= more
    path = tmp_path / "replies.json"
    path.write_text(json.dumps(body))
    return path


def _made(conn, tmp_path, t):
    b = read_band(conn, t, BAND)
    ask = recorded_ask(_replies(tmp_path))
    return [*propose(b, sorted(b.gaps), ask, RULES), *propose_lo_skills(b, ask, RULES)]


def test_each_gap_is_proposed_checked_and_sent_where_it_belongs(conn, tmp_path):
    t = _band(conn)
    every = _made(conn, tmp_path, t)
    made = {(p.kind, p.subject_code): p for p in every if p.kind != "lo_skill"}
    assert made[("skill", "ACT-KX-0101")].status == "auto_passed"
    assert made[("skill", "ACT-KX-0102")].status == "rejected"
    assert made[("skill", "ACT-KX-0102")].problems == ["invented code NUM.CNT.99: not a skill of this band"]
    assert made[("skill", "ACT-KX-0103")].problems == [
        "ART.CLAY.01 is ART, a family people never linked to a Clay activity"
    ]
    assert made[("objective", "ACT-KX-0102")].status == "needs_person"  # new words: nothing scores them
    assert made[("levels", "ACT-KX-0102")].status == "needs_person"
    # one objective and one skill on an activity: code links them; two skills on one objective too; never a guess
    assert sorted((p.subject_code, p.proposal["skills"][0]) for p in every if p.kind == "lo_skill") == [
        ("LO-KX-0001-1", "NUM.CNT.01"),
        ("LO-KX-0002-1", "NUM.CNT.02"),
        ("LO-KX-0003-1", "MOT.FMS.01"),
        ("LO-KX-0003-1", "NUM.CNT.01"),
        ("LO-KX-0004-1", "MOT.FMS.01"),
    ]


def test_the_ledger_is_never_edited_or_deleted_and_a_person_answers_with_a_new_row(conn, tmp_path):
    t = _band(conn)
    lead = _staff(conn, t)
    map_ledger.record(conn, t, _made(conn, tmp_path, t), lead)
    waiting = map_ledger.standing(conn, t, "needs_person")
    assert {(r["kind"], r["subject_code"]) for r in waiting} == {
        ("objective", "ACT-KX-0102"),
        ("levels", "ACT-KX-0102"),
        ("objective", "ACT-KX-0103"),
    }
    map_ledger.settle(conn, t, waiting[0]["id"], True, lead, "reads well")
    assert {r["id"] for r in map_ledger.standing(conn, t, "approved")} == {waiting[0]["id"]}
    with pytest.raises(ValueError, match="not waiting"):
        map_ledger.settle(conn, t, waiting[0]["id"], False, lead, "twice")
    conn.execute("savepoint s")
    with pytest.raises(psycopg.errors.RaiseException):
        conn.execute("update curriculum_proposal set status = 'rejected' where tenant_id = %s", (t,))
    conn.execute("rollback to savepoint s")
    with pytest.raises(psycopg.errors.RaiseException):
        conn.execute("delete from curriculum_proposal where tenant_id = %s", (t,))
    conn.execute("rollback to savepoint s")


def test_the_engine_may_add_to_the_ledger_and_never_delete_from_it(conn):
    can = (
        conn.execute(
            "select has_table_privilege('app_engine', 'curriculum_proposal', 'insert') as ins,"
            " has_table_privilege('app_engine', 'curriculum_proposal', 'delete') as del,"
            " has_table_privilege('app_engine', 'curriculum_proposal', 'update') as upd"
        ).fetchone()
        if conn.execute("select 1 from pg_roles where rolname = 'app_engine'").fetchone()
        else None
    )
    if can is None:
        pytest.skip("no app_engine role on this copy")
    assert can == {"ins": True, "del": False, "upd": False}


def test_applying_marks_every_link_as_the_machines_keeps_it_in_the_history_and_a_revert_undoes_it(
    conn, tmp_path
):
    t = _band(conn)
    lead = _staff(conn, t)
    map_ledger.record(conn, t, _made(conn, tmp_path, t), lead)
    done = map_ledger.apply(conn, t, lead, write=True)
    assert "ACT-KX-0101 → NUM.CNT.01" in done
    link = conn.execute(
        "select source, proposal_id from activity_skill where tenant_id = %s and activity_code = 'ACT-KX-0101'",
        (t,),
    ).fetchone()
    assert link["source"] == "machine" and link["proposal_id"] is not None
    assert (
        conn.execute(
            "select count(*) as n from activity_skill where tenant_id = %s and skill_code = 'NUM.CNT.99'",
            (t,),
        ).fetchone()["n"]
        == 0
    ), "an invented code is never applied"
    kept = conn.execute(
        "select before, after, changed_by from curriculum_edit where tenant_id = %s and record = 'activity_skill'"
        " and code = 'ACT-KX-0101'",
        (t,),
    ).fetchall()
    assert [(k["before"], k["after"]) for k in kept] == [("", "NUM.CNT.01")]
    assert kept[0]["changed_by"].startswith("machine:") and kept[0]["changed_by"].endswith(f"staff:{lead}")
    assert map_ledger.apply(conn, t, lead, write=True) == [], "applying twice changes nothing"

    print(map_ledger.revert(conn, t, link["proposal_id"], lead, "wrong skill"))
    assert (
        conn.execute(
            "select count(*) as n from activity_skill where tenant_id = %s and activity_code = 'ACT-KX-0101'",
            (t,),
        ).fetchone()["n"]
        == 0
    )
    assert [
        (k["before"], k["after"])
        for k in conn.execute(
            "select before, after from curriculum_edit where tenant_id = %s and record = 'activity_skill'"
            " and code = 'ACT-KX-0101' order by created_at",
            (t,),
        ).fetchall()
    ] == [("", "NUM.CNT.01"), ("NUM.CNT.01", "")]
    assert [r["now"] for r in map_ledger.standing(conn, t) if r["id"] == link["proposal_id"]] == ["reverted"]


def test_a_link_a_person_removes_is_kept_in_the_history_too(conn):
    t = _band(conn)
    conn.execute("select set_config('app.changed_by', 'A test educator', true)")
    conn.execute("delete from activity_skill where tenant_id = %s and activity_code = 'ACT-KX-0001'", (t,))
    row = conn.execute(
        "select before, after, changed_by from curriculum_edit where tenant_id = %s and record = 'activity_skill'"
        " and code = 'ACT-KX-0001' and after = ''",
        (t,),
    ).fetchone()
    assert row == {"before": "NUM.CNT.01", "after": "", "changed_by": "A test educator"}


def test_the_commands_write_nothing_without_apply_and_by(monkeypatch):
    """--apply without --by is refused before the database is opened (as `engine curriculum k2` is)."""

    def never(*_a, **_k):
        raise AssertionError("the database was opened")

    monkeypatch.setattr(db, "connect", never)
    for command in (["apply"], ["propose"], ["revert", "x", "--why", "y"]):
        run = CliRunner().invoke(cli.app, ["curriculum", *command, "--apply"])
        plain = " ".join(
            re.sub(r"[│╭╮╰╯─]", " ", re.sub(r"\x1b\[[0-9;]*m", "", run.output)).split()
        )  # any colours or wraps
        assert run.exit_code != 0 and "--by is required with --apply" in plain, command
        assert not isinstance(run.exception, AssertionError), command


def test_a_recorded_gold_run_is_held_to_the_bars_before_anything_applies(conn, tmp_path, monkeypatch):
    """The held-out share of the activities people mapped, mapped blind: a run that names the people's own skills
    passes every bar; one that names the wrong skills fails, and the command says so."""
    t = _band(conn)
    conn.execute(
        "update threshold set value = 2 where key = 'map.dev_count'"
    )  # 2 of the 4 for tuning, 2 held out
    conn.execute(
        "update threshold set value = 0 where key = 'map.require_examples'"
    )  # the rules as first written:
    conn.execute(
        "update threshold set value = 1 where key = 'map.use_checker'"
    )  # the validator's verdict decides
    b = read_band(conn, t, BAND)
    gold = {c: s for c, s in b.person_skills.items() if b.objectives.get(c)}
    monkeypatch.setattr(cli_map, "_tenant", lambda c: t)
    monkeypatch.setattr(
        cli_map, "read_band", lambda c, tn, band, hide=frozenset(): read_band(c, tn, BAND, hide)
    )
    agree = {"verdict": "agree", "why": "yes"}
    right = {
        c: {
            "skills": sorted(s),
            "objective_code": "",
            "objective_text": "",
            "levels": {},
            "confidence": 0.95,
            "reason": "as people did",
        }
        for c, s in gold.items()
    }
    good = cli_map.evaluate(
        conn,
        recorded_ask(
            _replies(
                tmp_path,
                {"curriculum_map_propose": right, "curriculum_map_validate": dict.fromkeys(gold, agree)},
            )
        ),
    )
    assert good["skill_all_right"] == 1.0 and good["skill_found"] == 1.0 and good["auto_passed"] == 1.0
    wrong = {
        c: r | {"skills": ["NUM.CNT.02" if "NUM.CNT.01" in r["skills"] else "NUM.CNT.01"]}
        for c, r in right.items()
    }
    bad = cli_map.evaluate(
        conn,
        recorded_ask(
            _replies(
                tmp_path,
                {"curriculum_map_propose": wrong, "curriculum_map_validate": dict.fromkeys(gold, agree)},
            )
        ),
    )
    assert bad["skill_all_right"] < 0.9
    from engine.checks import bars

    assert bars.short(good, bars.bars(conn, "curriculum_map")) == []
    assert bars.short(bad, bars.bars(conn, "curriculum_map"))


def test_the_proposer_sees_the_skills_that_fit_and_the_nearest_activities_people_mapped(conn, tmp_path):
    """What the proposer is given for one activity: the band's skills in the families people linked to its subject
    (never another family's), its gaps, and the activities people mapped nearest it by their words."""
    t = _band(conn)
    seen: dict[str, dict[str, object]] = {}
    replies = recorded_ask(_replies(tmp_path))

    def ask(purpose, about, variables):
        seen.setdefault(f"{purpose}:{about}", variables)
        return replies(purpose, about, variables)

    propose(read_band(conn, t, BAND), ["ACT-KX-0101"], ask, RULES)
    asked = seen["curriculum_map_propose:ACT-KX-0101"]
    assert asked["gaps"] == ["skill", "levels"]
    assert [s.split()[0] for s in asked["skills"]] == ["MOT.FMS.01", "NUM.CNT.01", "NUM.CNT.02"]
    names = [e["name"] for e in asked["examples"]]
    assert len(names) == RULES.examples and set(names) <= {
        "Count beads to ten",
        "Count back from ten",
        "Thread beads by count",
        "Pinch and count seeds",
    }, "only activities people mapped themselves, never the one asked about"
    assert "count" in names[0].lower().split()
    assert "curriculum_map_validate:ACT-KX-0101" in seen, "the validator reads what code passed"


def test_who_is_a_member_of_staffs_id_and_the_machines_code_never_a_typed_name(conn, tmp_path):
    """D-046, rule 6: the ledger is read by the website, so a person is their staff id (an email given to --by is
    looked up by the engine) and the machine a fixed code; an email no one has is refused."""
    t = _band(conn)
    lead = _staff(conn, t, "mapping-lead@school.invalid")
    assert cli_map.staff_of(conn, "Mapping-Lead@school.invalid ") == lead
    with pytest.raises(Exception, match="no one member of staff"):
        cli_map.staff_of(conn, "nobody@school.invalid")
    map_ledger.record(conn, t, _made(conn, tmp_path, t), lead)
    rows = conn.execute(
        "select staff_id, machine from curriculum_proposal where tenant_id = %s", (t,)
    ).fetchall()
    assert {r["staff_id"] for r in rows} == {lead}
    assert {r["machine"] for r in rows} == {"proposer:curriculum_map_propose", "proposer:code"}
    columns = {
        r["column_name"]
        for r in conn.execute(
            "select column_name from information_schema.columns where table_name = 'curriculum_proposal'"
        ).fetchall()
    }
    assert not columns & {"name", "made_by", "email", "by"}


def test_a_held_out_activity_is_never_an_example_the_proposer_sees(conn, tmp_path, monkeypatch):
    """The final score is kept clean (P-08): the activities scored are mapped blind, and the proposer's examples are
    the dev set's only."""
    t = _band(conn)
    conn.execute("update threshold set value = 2 where key = 'map.dev_count'")
    monkeypatch.setattr(cli_map, "_tenant", lambda c: t)
    monkeypatch.setattr(
        cli_map, "read_band", lambda c, tn, band, hide=frozenset(): read_band(c, tn, BAND, hide)
    )
    b = read_band(conn, t, BAND)
    dev, held = cli_map.gold_split(conn, b)
    names = {c: b.words[c]["name"] for c in dev | held}
    seen: list[tuple[str, list[str]]] = []
    reply = {
        "skills": [],
        "objective_code": "",
        "objective_text": "",
        "levels": {},
        "confidence": 0.5,
        "reason": "",
    }

    def ask(purpose, about, variables):
        if purpose == "curriculum_map_propose":
            seen.append((about, [e["name"] for e in variables["examples"]]))
            return reply
        return {"verdict": "agree", "why": ""}

    cli_map.evaluate(conn, ask)
    assert {a for a, _ in seen} == held
    assert all(set(ex) <= {names[c] for c in dev} for _, ex in seen)
