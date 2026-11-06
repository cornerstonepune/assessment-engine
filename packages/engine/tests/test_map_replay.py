"""A dev-set run can be read back from the replies flow_run kept (goals/m1-11d-map-replay.yaml).

2026-11-04: map_dev scored 0.857 right and 0.28 passing on their own, and the replies that explain why were in the
live database with no way to read them. The proposer is deterministic given its replies, so asking again from the rows
rebuilds every decision. Nothing here calls a model.
"""

import json
import os
from datetime import UTC, datetime, timedelta

import pytest
from psycopg.types.json import Json

from engine.adapters import llm
from engine.w1_bank import map_replay as mr
from engine.w1_bank.map_agents import PROPOSE, VALIDATE, Proposal

T0 = datetime(2026, 11, 4, 16, 0, tzinfo=UTC)


def call(minute, purpose=PROPOSE, about="A", outcome="accepted", reply=None, reason=""):
    return (T0 + timedelta(minutes=minute), purpose, about, outcome, reply or {"ok": 1}, reason)


def test_the_latest_run_is_what_follows_the_last_long_pause():
    calls = [call(0), call(1), call(60), call(61), call(62)]
    assert [c[0] for c in mr.last_run(calls, 10)] == [T0 + timedelta(minutes=m) for m in (60, 61, 62)]
    assert len(mr.last_run(calls, 100)) == 5 and mr.last_run([], 10) == []


def test_replies_come_back_in_the_order_they_were_paid_for_each_prompt_apart():
    ask, left = mr.replaying(
        [
            call(0, PROPOSE, "A", reply={"n": 1}),
            call(1, VALIDATE, "A", reply={"v": 1}),
            call(2, PROPOSE, "B", reply={"n": 2}),
        ]
    )
    assert ask(PROPOSE, "A", {}) == {"n": 1} and ask(VALIDATE, "A", {}) == {"v": 1}
    assert ask(PROPOSE, "B", {}) == {"n": 2}
    assert not any(left.values()), "every stored reply was read"


def test_a_refused_reply_is_refused_again_with_the_reason_it_had():
    ask, _ = mr.replaying([call(0, outcome="refused", reason="'confidence_note' was unexpected")])
    with pytest.raises(llm.LLMSchemaError, match="confidence_note"):
        ask(PROPOSE, "A", {})


def test_a_reply_for_another_activity_or_none_left_is_not_the_same_run():
    ask, _ = mr.replaying([call(0, about="A")])
    with pytest.raises(llm.LLMError, match="not the same run"):
        ask(PROPOSE, "B", {})
    ask, _ = mr.replaying([])
    with pytest.raises(llm.LLMError, match="no more"):
        ask(VALIDATE, "A", {})
    ask, _ = mr.replaying([call(0, about="")])  # a row from before the activity was kept: nothing to check
    assert ask(PROPOSE, "ANY", {}) == {"ok": 1}


def test_a_wrong_proposal_says_how_it_is_wrong():
    gold = frozenset({"NUM.CNT.01", "NUM.CNT.02"})
    assert mr.wrong_how(frozenset({"NUM.CNT.01", "NUM.OPS.01"}), gold) == "adds a skill people did not link"
    assert mr.wrong_how(frozenset({"NUM.CNT.09"}), gold) == "a neighbouring skill of the same family"
    assert mr.wrong_how(frozenset({"GEO.SHP.01"}), gold) == "a skill of another family"
    assert mr.wrong_how(frozenset(), gold) == "no skill proposed"


def prop(code, skills, status, confidence=0.9, verdict="agree", reason="", problems=None):
    return Proposal(
        "skill",
        code,
        {"skills": skills},
        confidence,
        PROPOSE,
        VALIDATE,
        problems or [],
        verdict,
        status,
        reason,
    )


def test_each_proposal_is_set_against_what_people_linked_and_the_held_back_are_counted_by_cause():
    gold = {c: frozenset({"NUM.CNT.01"}) for c in "ABCDEF"}
    made = [
        prop("A", ["NUM.CNT.01"], "auto_passed"),
        prop("B", ["NUM.CNT.01", "NUM.OPS.01"], "auto_passed"),
        prop("C", ["NUM.CNT.01"], "needs_person", verdict="disagree", reason="not this skill"),
        prop("D", ["NUM.CNT.01"], "needs_person", confidence=0.6),
        prop("E", ["NUM.CNT.01"], "needs_person", reason="audit sample"),
        prop("F", ["GEO.SHP.01"], "needs_person", verdict="disagree"),
    ]
    got = mr.explain(made, gold, 0.8)
    assert got["passed_wrong"] == {"adds a skill people did not link": 1}
    assert got["held_back"] == {
        "the checker disagreed, would have been right": 1,
        "the checker disagreed, would not have been": 1,
        "confidence under the bar, would have been right": 1,
        "audit sample, would have been right": 1,
    }
    assert [r["cause"] for r in got["rows"]][:2] == ["right", "adds a skill people did not link"]


def test_precision_is_tabled_by_confidence_and_by_verdict_and_for_each_threshold_that_could_be_set():
    gold = {c: frozenset({"NUM.CNT.01"}) for c in "ABCDEF"}
    made = [
        prop("A", ["NUM.CNT.01"], "auto_passed", confidence=0.9),
        prop("B", ["NUM.CNT.01"], "needs_person", confidence=0.6),
        prop("C", ["GEO.SHP.01"], "needs_person", confidence=0.6),
        prop("D", ["NUM.CNT.01"], "needs_person", confidence=0.7, verdict="disagree"),
        prop("E", ["NUM.CNT.01"], "rejected", confidence=0.9, problems=["unknown skill"]),
        prop("F", [], "needs_person", confidence=0.9),
    ]
    got = mr.sweep(made, gold)
    assert got["by_confidence"] == {
        "0.6": [2, 1],
        "0.7": [1, 1],
        "0.9": [3, 2],
    }  # [proposals, right]; E is right though code flagged it
    assert got["by_verdict"] == {"agree": [5, 3], "disagree": [1, 1]}
    # eligible = no code problem, a skill, the checker agrees: A (0.9, right), B (0.6, right), C (0.6, wrong)
    assert got["if_confidence_at_least"] == {
        "0.0": {"passes": 3, "right": 2, "precision": 0.667, "share": 0.5},
        "0.6": {"passes": 3, "right": 2, "precision": 0.667, "share": 0.5},
        "0.9": {"passes": 1, "right": 1, "precision": 1.0, "share": 0.167},
    }


needs_db = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")


@needs_db
def test_a_paid_reply_kept_by_the_adapter_reads_back_as_a_stored_call(monkeypatch):
    from engine.adapters import llm_budget
    from engine.core import db

    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    said = {"skills": ["NUM.CNT.01"], "extra": 1}
    monkeypatch.setattr(llm, "_dispatch", lambda *a, **k: (said, "claude-sonnet-5-5", 30, 20, 10))
    with db.connect() as conn:
        with pytest.raises(llm.LLMSchemaError):
            llm.generate(conn, PROPOSE, {}, version=2, stage="dev_eval", about="ACT-X-1")
        got = [c for c in mr.stored(conn) if c[2] == "ACT-X-1"]
        conn.rollback()
    assert len(got) == 1 and got[0][1] == PROPOSE and got[0][3] == "refused" and got[0][4] == said
    assert "failed its schema" in got[0][5]
    assert llm_budget.trigger_for("dev_eval") == "engine:dev_eval"


@needs_db
def test_a_probe_call_is_not_part_of_a_stored_run(monkeypatch):
    from engine.core import db

    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    monkeypatch.setattr(llm, "_dispatch", lambda *a, **k: ({"skills": []}, "claude-sonnet-5-5", 30, 20, 10))
    with db.connect() as conn:
        for about in ("probe:ACT-X-2", "ACT-X-2"):
            try:
                llm.generate(conn, PROPOSE, {}, version=2, stage="dev_eval", about=about)
            except llm.LLMError:
                pass
        got = [c[2] for c in mr.stored(conn) if c[2].endswith("ACT-X-2")]
        conn.rollback()
    assert got == ["ACT-X-2"]


@needs_db
def test_a_run_rebuilt_from_its_stored_replies_scores_what_the_run_scored(monkeypatch):
    """Capture every call of a scripted dev-set run, store them as flow_run rows, read them back: the same score."""
    from engine.core import db
    from engine.w1_bank import cli_map
    from tests.test_map_ledger import RULES, _band  # noqa: F401

    said = {
        "skills": ["NUM.CNT.01"],
        "objective_code": "",
        "objective_text": "",
        "levels": {},
        "confidence": 0.9,
    }
    calls: list[tuple[str, str, dict]] = []

    def scripted(purpose, about, variables):
        near = sorted(mr._example_skills(variables))[:1]  # a skill the examples show, so it can pass
        reply = (
            {**said, "skills": near, "reason": "r"}
            if purpose == PROPOSE
            else {"verdict": "agree", "why": "w"}
        )
        calls.append((purpose, about, reply))
        return reply

    monkeypatch.setattr(cli_map, "config", lambda: {"band": "KX"})
    with db.connect() as conn:
        _band(conn)
        conn.execute("update threshold set value = 100 where key = 'map.dev_count'")
        tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
        made, gold, _ = cli_map.replay_dev(conn, scripted)
        want = cli_map.score(
            [cli_map.Scored(p.subject_code, frozenset(cli_map.skills(p)), p.status) for p in made], gold
        )
        assert calls, "the scripted run asked something"
        for i, (purpose, about, reply) in enumerate(calls):
            conn.execute(
                "insert into flow_run (tenant_id, flow, trigger, request, result, started_at)"
                " values (%s, %s, 'engine:dev_eval', %s, %s, now() + %s * interval '1 second')",
                (tenant, purpose, Json({"about": about}), Json({"reply": reply, "outcome": "accepted"}), i),
            )
        lines = cli_map.replay_report(conn, 10)
        conn.rollback()
    head = json.loads(lines[0])
    assert head["score"] == want and not any(head["left_unread"].values())
    json.loads(lines[1])  # the counts by cause print as JSON too
    assert len(lines) == 2 + len(made)


def test_the_skills_each_proposal_was_shown_as_examples_are_noted_as_it_is_replayed():
    shown: dict = {}
    ask, _ = mr.replaying([call(0, PROPOSE, "A"), call(1, VALIDATE, "A")], shown)
    ask(PROPOSE, "A", {"examples": [{"skills": ["NUM.CNT.01"]}, {"skills": ["NUM.CNT.02", "MOT.FMS.01"]}]})
    ask(VALIDATE, "A", {"examples": [{"skills": ["XXX.YYY.01"]}]})
    assert shown == {"A": frozenset({"NUM.CNT.01", "NUM.CNT.02", "MOT.FMS.01"})}, (
        "only the proposer's examples"
    )


def _split_case():
    gold = {c: frozenset({"NUM.CNT.01", "NUM.CNT.02"}) for c in "ABCD"}
    shown = {c: frozenset({"NUM.CNT.01", "NUM.CNT.02"}) for c in "ABCD"}
    made = [
        prop("A", ["NUM.CNT.01", "NUM.CNT.02"], "auto_passed", confidence=0.9),
        prop("B", ["NUM.CNT.01", "SEB.ATT.01"], "needs_person", confidence=0.6),  # one core, one extra
        prop("C", ["NUM.CNT.02"], "needs_person", confidence=0.6, verdict="disagree"),
        prop("D", ["GEO.SHP.01"], "needs_person", confidence=0.9),  # wrong and not in the examples
    ]
    return made, gold, shown


def test_each_proposed_skill_is_counted_by_its_place_in_the_list_and_by_whether_it_was_in_the_examples():
    made, gold, shown = _split_case()
    got = mr.skill_split(made, gold, shown)
    assert got["skills"] == {"proposed": 6, "in_gold": 4}
    assert got["by_rank"] == {"1": [4, 3], "2": [2, 1]}
    assert got["by_example"] == {"in the examples": [4, 4], "not in the examples": [2, 0]}


def test_an_activity_could_pass_when_every_skill_it_names_was_in_the_examples_whatever_it_said_of_itself():
    made, gold, shown = _split_case()
    table = mr.skill_split(made, gold, shown)["if_every_skill_was_in_the_examples"]
    assert table["0.0"] == {"passes": 2, "right": 2, "precision": 1.0, "share": 0.5}, "A and C"
    assert table["0.9"] == {"passes": 1, "right": 1, "precision": 1.0, "share": 0.25}, "A alone"
    with_checker = mr.skill_split(made, gold, shown)[
        "if_every_skill_was_in_the_examples_and_the_checker_agreed"
    ]
    assert with_checker["0.0"]["passes"] == 1, "C is out: the checker disagreed"


def test_a_proposal_split_into_the_skills_that_pass_and_the_ones_offered_to_a_person():
    made, gold, shown = _split_case()
    got = mr.skill_split(made, gold, shown)["split_by_the_examples"]
    assert got["0.0"] == {
        "auto_skills": 4,
        "auto_right": 4,
        "auto_precision": 1.0,
        "offered": 2,
        "offered_in_gold": 0,
    }
    assert got["0.9"]["auto_skills"] == 2 and got["0.9"]["offered"] == 4
    assert got["0.9"]["offered_in_gold"] == 2, (
        "B's and C's right skills fall below the bar and wait for a person"
    )


def test_a_share_that_passed_is_given_with_its_wilson_interval_and_none_with_no_activities():
    lo, hi = mr.wilson(9, 10)
    assert (round(lo, 3), round(hi, 3)) == (0.596, 0.982)
    assert mr.wilson(0, 0) == (0.0, 0.0)
    assert 0.72 < mr.wilson(10, 10)[0] < 0.73 and mr.wilson(10, 10)[1] == 1.0


def test_a_partial_run_is_summed_up_in_counts_with_the_interval_and_no_activity_named():
    gold = {f"ACT-{i}": frozenset({"NUM.CNT.01"}) for i in range(6)}
    made = [
        prop("ACT-0", ["NUM.CNT.01"], "auto_passed"),
        prop("ACT-1", ["NUM.CNT.01"], "auto_passed"),
        prop("ACT-2", ["NUM.CNT.09"], "auto_passed"),
        prop("ACT-3", ["NUM.CNT.01"], "needs_person", confidence=0.5, reason="confidence under the bar"),
        prop("ACT-4", [], "rejected", problems=["no skill"]),
    ]
    got = mr.partial(made, gold, 0.7, held_total=6)
    assert got["held_total"] == 6 and got["answered"] == 5 and got["unanswered"] == 1
    assert (
        got["passed"] == 3
        and got["passed_right"] == 2
        and got["held_to_a_person"] == 1
        and got["rejected"] == 1
    )
    assert got["precision_of_passed"] == pytest.approx(2 / 3, abs=0.001)
    lo, hi = got["precision_interval"]
    assert 0.2 < lo < 0.5 and 0.8 < hi < 0.95
    assert got["share_passed"] == pytest.approx(3 / 5, abs=0.001)
    assert "ACT-" not in json.dumps(got), "counts only: no activity is named"


@needs_db
def test_the_held_out_run_is_read_back_for_the_activities_that_were_answered_and_the_rest_are_counted_unanswered():
    from engine.core import db
    from engine.w1_bank import cli_map
    from tests.test_map_ledger import _band

    said = {
        "skills": ["NUM.CNT.01"],
        "objective_code": "",
        "objective_text": "",
        "levels": {},
        "confidence": 0.9,
    }
    calls: list[tuple[str, str, dict]] = []

    def scripted(purpose, about, variables):
        near = sorted(mr._example_skills(variables))[:1]  # a skill the examples show, so it can pass
        reply = (
            {**said, "skills": near, "reason": "r"}
            if purpose == PROPOSE
            else {"verdict": "agree", "why": "w"}
        )
        calls.append((purpose, about, reply))
        return reply

    with db.connect() as conn:
        _band(conn)
        conn.execute("update threshold set value = 1 where key = 'map.dev_count'")
        monkey = pytest.MonkeyPatch()
        monkey.setattr(cli_map, "config", lambda: {"band": "KX"})
        tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
        whole = cli_map.read_band(conn, tenant, "KX")
        tune, held = cli_map.gold_split(conn, whole)
        assert len(held) == 3, "three of the four mapped activities are held out"
        cli_map._made(conn, scripted, "KX", held, tune)
        first = sorted(held)[0]
        for i, (purpose, about, reply) in enumerate(c for c in calls if c[1] == first):
            conn.execute(
                "insert into flow_run (tenant_id, flow, trigger, request, result, started_at)"
                " values (%s, %s, 'engine:held_out', %s, %s, now() + %s * interval '1 second')",
                (tenant, purpose, Json({"about": about}), Json({"reply": reply, "outcome": "accepted"}), i),
            )
        lines = cli_map.replay_report(conn, 10, stage="held_out")
        conn.rollback()
        monkey.undo()
    got = json.loads(lines[0])
    assert len(lines) == 1, "one line of counts, no row for an activity"
    assert got["held_total"] == 3 and got["answered"] == 1 and got["unanswered"] == 2
    assert "ACT-KX" not in lines[0]


@needs_db
def test_the_estimate_prices_a_call_from_the_proposer_calls_already_paid_and_calls_nothing():
    from engine.core import db
    from engine.w1_bank import cli_map

    with db.connect() as conn:
        tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
        conn.execute("delete from flow_run where flow = %s", (PROPOSE,))
        assert cli_map.estimate(conn, 3) == (3, None, 0), "nothing paid for yet: three gaps, no price"
        assert "not measured" in cli_map.estimate_line(3, None, 0)
        for i in range(6):
            conn.execute(
                "insert into flow_run (tenant_id, flow, trigger, request, result, status, cost_inr)"
                " values (%s, %s, 'engine:held_out', %s, %s, 'ok', 1.32)",
                (tenant, PROPOSE, Json({"about": f"X{i}"}), Json({"outcome": "accepted"})),
            )
        n, per_call, calls = cli_map.estimate(conn, 3)
        assert (n, calls) == (3, 6) and per_call is not None and per_call > 0
        assert "about $" in cli_map.estimate_line(n, per_call, calls)
        conn.rollback()


def test_the_proposer_is_asked_in_the_stage_and_at_the_version_named_and_without_either_as_before(
    monkeypatch,
):
    from engine.w1_bank import cli_map

    seen = {}
    monkeypatch.setattr(
        cli_map, "model_ask", lambda conn, p=None, v=None, stage=None, say=None: seen.update(p=p, stage=stage)
    )
    cli_map._ask(None, None, 3, "draft")
    assert seen == {"p": 3, "stage": "draft"}
    cli_map._ask(None, None)
    assert seen == {"p": None, "stage": None}
