"""M1-11: the drafting run has a hard stop in code (goals/m1-11-k2-complete-v1.yaml).

Nimish, 4 Nov: up to 25 US dollars of model credits for the whole drafting run. Every model call already leaves a
`flow_run` row with its tokens and its cost from `llm.prices`; the campaign row (`llm.campaigns`) names the purposes the
run spends on, the cap and a safety margin, and the adapter refuses a call, before making it, once the running total
reaches cap minus margin. A spend it cannot see (a call that answered with no cost recorded, a call left running)
stops the run too, because a total that is missing a call is not a total.
"""

import json
import os

import pytest

from engine.adapters import llm, llm_budget
from engine.core import db

pytestmark = pytest.mark.skipif(not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)")

DRAFT = "k2_page_draft"
DRAFTED = {k: "x" for k in ("objective", "steps", "thinking", "level_0", "level_1", "level_2", "level_3")}
DRAFTED |= {"flags": [], "confidence": 0.9, "reason": "r"}
VARS = {"activity": "a", "have": "h", "examples": "e", "want": "w"}
RATE = 88  # INR per US dollar, as llm.prices says


@pytest.fixture
def conn(monkeypatch):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    with db.connect() as c:
        c.tenant = c.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
        c.execute(
            "update config set value = %s where tenant_id = %s and key = 'llm.campaigns'",
            (json.dumps({"m1-11": CAMPAIGN}), c.tenant),
        )
        yield c
        c.rollback()


CAMPAIGN = {
    "stale_minutes": 10,
    "purposes": [DRAFT, "k2_page_validate", "k2_materials_split"],
    "cap_usd": 25,
    "margin_usd": 2,
    "inr_per_usd": RATE,
}
LIMIT_INR = (25 - 2) * RATE  # 2024


def spend(conn, inr, flow=DRAFT, status="ok", started="now()"):
    conn.execute(
        f"insert into flow_run (tenant_id, flow, trigger, status, cost_inr, started_at) values (%s,%s,'test',%s,%s,{started})",  # noqa: S608
        (conn.tenant, flow, status, inr),
    )


def answering(monkeypatch, calls):
    def dispatch(models, text, images, schema, effort=None, structured=False):
        calls.append(models[0])
        return DRAFTED, "claude-sonnet-5-5", 3000, 2000, 1000

    monkeypatch.setattr(llm, "_dispatch", dispatch)


def runs(conn, flow=DRAFT):
    return conn.execute("select count(*) as n from flow_run where flow = %s", (flow,)).fetchone()["n"]


def test_a_call_is_refused_before_it_is_made_once_the_total_reaches_the_cap_less_the_margin(
    conn, monkeypatch
):
    calls: list = []
    answering(monkeypatch, calls)
    spend(conn, LIMIT_INR / 2, "k2_page_validate")
    spend(conn, LIMIT_INR / 2)  # the total over the campaign's purposes is now exactly the limit
    before = runs(conn)
    with pytest.raises(llm.LLMError, match="m1-11"):
        llm.generate(conn, DRAFT, VARS, version=1)
    assert calls == [], "no call was made"
    assert runs(conn) == before, "a refusal leaves no flow_run row, because no call was made"


def test_the_refusal_says_the_spend_in_dollars_and_the_cap(conn, monkeypatch):
    answering(monkeypatch, [])
    spend(conn, LIMIT_INR + 1)
    with pytest.raises(llm.LLMError, match=r"\$23\.0\d.*\$25"):
        llm.generate(conn, DRAFT, VARS, version=1)


def test_a_call_under_the_limit_goes_through_and_is_recorded_with_its_cost(conn, monkeypatch):
    calls: list = []
    answering(monkeypatch, calls)
    spend(conn, LIMIT_INR - 10)
    meta: dict = {}
    assert llm.generate(conn, DRAFT, VARS, version=1, meta=meta) == DRAFTED
    assert calls == ["claude-sonnet-5-5"] and meta["cost_inr"] > 0
    row = conn.execute(
        "select tokens_in, tokens_out, cost_inr from flow_run where id = %s", (meta["flow_run_id"],)
    ).fetchone()
    assert (row["tokens_in"], row["tokens_out"]) == (2000, 1000) and float(row["cost_inr"]) == float(
        meta["cost_inr"]
    )


def test_the_call_that_crosses_the_limit_is_the_last_one(conn, monkeypatch):
    calls: list = []
    answering(monkeypatch, calls)
    spend(conn, LIMIT_INR - 0.5)
    llm.generate(
        conn, DRAFT, VARS, version=1
    )  # under the limit when asked: allowed, and it takes the total over
    with pytest.raises(llm.LLMError, match="m1-11"):
        llm.generate(conn, DRAFT, VARS, version=1)
    assert len(calls) == 1


def test_a_purpose_outside_the_campaign_is_not_stopped_by_it(conn, monkeypatch):
    spend(conn, LIMIT_INR * 2)
    calls: list = []
    monkeypatch.setattr(
        llm, "_dispatch", lambda *a, **k: (calls.append(1) or {"verdict": "agree", "why": "w"}, "m", 1, 1, 1)
    )
    assert llm.generate(
        conn,
        "curriculum_map_validate",
        {"activity": "a", "kind": "k", "proposal": "p", "skills": "s"},
        version=1,
    )
    assert calls == [1]


def test_a_call_that_answered_with_no_cost_recorded_stops_the_run_because_the_total_is_unknown(
    conn, monkeypatch
):
    calls: list = []
    answering(monkeypatch, calls)
    spend(conn, None)
    with pytest.raises(llm.LLMError, match="no cost"):
        llm.generate(conn, DRAFT, VARS, version=1)
    assert calls == []


def test_a_call_left_running_for_ten_minutes_stops_the_run_but_one_in_flight_does_not(conn, monkeypatch):
    calls: list = []
    answering(monkeypatch, calls)
    spend(conn, None, status="running", started="now()")  # another worker's call, in flight
    assert llm.generate(conn, DRAFT, VARS, version=1)
    spend(conn, None, status="running", started="now() - interval '11 minutes'")  # one that never came back
    with pytest.raises(llm.LLMError, match="left running"):
        llm.generate(conn, DRAFT, VARS, version=1)


def test_a_reply_that_breaks_its_schema_was_still_paid_for_and_its_cost_counts(conn, monkeypatch):
    monkeypatch.setattr(
        llm, "_dispatch", lambda *a, **k: ({"nope": 1}, "claude-sonnet-5-5", 3000, 2000, 1000)
    )
    with pytest.raises(llm.LLMSchemaError):
        llm.generate(conn, DRAFT, VARS, version=1)
    row = conn.execute(
        "select status, cost_inr from flow_run where flow = %s order by started_at desc limit 1", (DRAFT,)
    ).fetchone()
    assert row["status"] == "error" and float(row["cost_inr"]) > 0, "an error row that cost money says so"


def _last_run(conn):
    return conn.execute(
        "select status, error, request, result from flow_run where flow = %s order by started_at desc limit 1",
        (DRAFT,),
    ).fetchone()


def test_a_refused_reply_is_kept_with_its_text_its_prompt_version_and_the_reason(conn, monkeypatch):
    """M1-11c: a paid reply that broke its schema was lost; now the row says what it said and why it was refused."""
    said = {"nope": 1, "confidence_note": "fairly sure"}
    monkeypatch.setattr(llm, "_dispatch", lambda *a, **k: (said, "claude-sonnet-5-5", 3000, 2000, 1000))
    with pytest.raises(llm.LLMSchemaError):
        llm.generate(conn, DRAFT, VARS, version=1)
    row = _last_run(conn)
    assert row["result"]["reply"] == said and row["result"]["outcome"] == "refused"
    assert row["result"]["reason"] == row["error"] and "failed its schema" in row["error"]
    assert row["request"]["purpose"] == DRAFT and row["request"]["version"] == 1


def test_an_accepted_reply_is_kept_too_with_its_prompt_version(conn, monkeypatch):
    calls: list = []
    answering(monkeypatch, calls)
    out = llm.generate(conn, DRAFT, VARS, version=1)
    row = _last_run(conn)
    assert row["status"] == "ok" and row["result"] == {"reply": out, "outcome": "accepted"}
    assert row["request"]["version"] == 1


def test_the_seeded_campaign_is_twenty_five_dollars_less_a_margin_over_exactly_the_three_prompts():
    seeded = next(
        c
        for c in json.loads((db.REPO_ROOT / "supabase" / "seed" / "config.json").read_text())["config"]
        if c["key"] == "llm.campaigns"
    )["value"]["m1-11"]
    assert seeded["cap_usd"] == 25 and 0 < seeded["margin_usd"] < seeded["cap_usd"]
    assert seeded["stale_minutes"] == 10
    assert set(seeded["purposes"]) == {
        "curriculum_map_propose",
        "curriculum_map_validate",
        DRAFT,
        "k2_page_validate",
        "k2_page_check",
        "k2_page_check_b",
        "k2_materials_split",
    }, "the mapping evals spend from the same 25 dollars"
    assert seeded["inr_per_usd"] == RATE


def test_the_campaigns_money_does_not_use_up_the_days_budget_of_every_other_prompt(conn, monkeypatch):
    """The daily budget row (₹150) is for everything else; a drafting run of ₹2,000 is the campaign's own money."""
    spend(conn, 1000)
    calls: list = []
    monkeypatch.setattr(
        llm, "_dispatch", lambda *a, **k: (calls.append(1) or {"verdict": "agree", "why": "w"}, "m", 1, 1, 1)
    )
    assert llm.generate(
        conn,
        "curriculum_map_validate",
        {"activity": "a", "kind": "k", "proposal": "p", "skills": "s"},
        version=1,
    )
    assert calls == [1], "the day's total for other prompts is still under its ₹150"


STAGED = {**CAMPAIGN, "stages": {"dev_eval": 4, "held_out": 7, "draft": None}, "stage_margin_usd": 0.25}


def staged(conn, camp=None):
    conn.execute(
        "update config set value = %s where tenant_id = %s and key = 'llm.campaigns'",
        (json.dumps({"m1-11": camp or STAGED}), conn.tenant),
    )


def spend_in(conn, inr, stage):
    conn.execute(
        "insert into flow_run (tenant_id, flow, trigger, status, cost_inr) values (%s,%s,%s,'ok',%s)",
        (conn.tenant, DRAFT, f"engine:{stage}", inr),
    )


def test_a_stage_stops_at_its_own_cap_less_its_margin_while_the_other_stages_go_on(conn, monkeypatch):
    staged(conn)
    calls: list = []
    answering(monkeypatch, calls)
    spend_in(conn, (4 - 0.25) * RATE, "dev_eval")  # $3.75: the dev stage is at its limit
    with pytest.raises(llm.LLMError, match=r"stage dev_eval.*\$3\.75"):
        llm.generate(conn, DRAFT, VARS, version=1, stage="dev_eval")
    assert calls == []
    assert llm.generate(conn, DRAFT, VARS, version=1, stage="held_out") == DRAFTED
    assert llm.generate(conn, DRAFT, VARS, version=1, stage="draft") == DRAFTED, (
        "a stage with no cap has the campaign's"
    )


def test_every_stage_counts_toward_the_whole_campaigns_cap(conn, monkeypatch):
    staged(conn)
    answering(monkeypatch, [])
    spend_in(conn, LIMIT_INR, "draft")
    with pytest.raises(llm.LLMError, match="campaign m1-11 stopped"):
        llm.generate(conn, DRAFT, VARS, version=1, stage="held_out")


def test_a_stage_the_campaign_does_not_name_is_refused_so_a_typo_cannot_spend_unwatched(conn, monkeypatch):
    staged(conn)
    answering(monkeypatch, [])
    with pytest.raises(llm.LLMError, match="no stage called dev_evl"):
        llm.generate(conn, DRAFT, VARS, version=1, stage="dev_evl")


def test_the_seeded_stages_are_four_dollars_for_the_dev_eval_and_seven_for_the_held_out_score():
    seeded = next(
        c
        for c in json.loads((db.REPO_ROOT / "supabase" / "seed" / "config.json").read_text())["config"]
        if c["key"] == "llm.campaigns"
    )["value"]["m1-11"]
    assert seeded["stages"] == {"dev_eval": 4, "held_out": 7, "draft": None}
    assert 4 + 7 + 2 < seeded["cap_usd"], "the drafting stage keeps the rest"


def test_a_refusal_for_money_is_its_own_error_so_a_run_can_end_cleanly_and_keep_what_is_good(
    conn, monkeypatch
):
    answering(monkeypatch, [])
    spend(conn, LIMIT_INR + 1)
    with pytest.raises(llm.LLMBudgetError):
        llm.generate(conn, DRAFT, VARS, version=1)
    assert issubclass(llm.LLMBudgetError, llm.LLMError), "callers that only know LLMError still stop"


def test_the_status_says_the_spend_so_far_the_limit_and_the_stages_own(conn, monkeypatch):
    staged(conn)
    spend_in(conn, 0.5 * RATE, "dev_eval")
    spend_in(conn, 1.0 * RATE, "held_out")
    got = llm_budget.status(conn, db.tenant_slug(), DRAFT, "dev_eval")
    assert got == {
        "campaign": "m1-11",
        "spent_usd": pytest.approx(1.5),
        "limit_usd": 23,
        "stage": "dev_eval",
        "stage_spent_usd": pytest.approx(0.5),
        "stage_limit_usd": 3.75,
    }
    assert llm_budget.status(conn, db.tenant_slug(), "item_generate", None) is None, "no campaign, no status"
    line = llm_budget.line(got)
    assert line == "spent $1.50 of $23.00; stage dev_eval $0.50 of $3.75"


def test_how_long_a_call_may_stay_running_is_the_campaigns_own_row_not_a_number_in_code(conn, monkeypatch):
    answering(monkeypatch, [])
    spend(conn, None, status="running", started="now() - interval '11 minutes'")

    def stale(minutes):
        conn.execute(
            "update config set value = %s where tenant_id = %s and key = 'llm.campaigns'",
            (json.dumps({"m1-11": {**CAMPAIGN, "stale_minutes": minutes}}), conn.tenant),
        )

    stale(20)
    assert llm.generate(conn, DRAFT, VARS, version=1), "11 minutes is not stale when the row says 20"
    stale(5)
    with pytest.raises(llm.LLMBudgetError, match="left running"):
        llm.generate(conn, DRAFT, VARS, version=1)


def test_the_writer_and_the_readers_of_a_stage_share_one_form_of_the_trigger():
    assert (
        llm_budget.trigger_for(None) == "engine" and llm_budget.trigger_for("dev_eval") == "engine:dev_eval"
    )


ORDERED = {**STAGED, "order": ["dev_eval", "held_out", "draft"]}


def test_a_stage_may_not_start_until_the_stage_before_it_has_made_a_call(conn, monkeypatch):
    """The order of the run is the engine's, not the workflow's: the dev eval, then the held-out score, then the drafting."""
    staged(conn, ORDERED)
    answering(monkeypatch, [])
    with pytest.raises(llm.LLMBudgetError, match=r"stage held_out comes after dev_eval"):
        llm.generate(conn, DRAFT, VARS, version=1, stage="held_out")
    with pytest.raises(llm.LLMBudgetError, match=r"stage draft comes after held_out"):
        llm.generate(conn, DRAFT, VARS, version=1, stage="draft")
    assert llm.generate(conn, DRAFT, VARS, version=1, stage="dev_eval") == DRAFTED, (
        "the first stage has no one before it"
    )
    assert llm.generate(conn, DRAFT, VARS, version=1, stage="held_out") == DRAFTED
    assert llm.generate(conn, DRAFT, VARS, version=1, stage="draft") == DRAFTED, "held_out has run now"


def test_a_failed_or_refused_call_does_not_count_as_a_stage_having_run(conn, monkeypatch):
    staged(conn, ORDERED)
    answering(monkeypatch, [])
    conn.execute(
        "insert into flow_run (tenant_id, flow, trigger, status, cost_inr) values (%s,%s,'engine:dev_eval','error',NULL)",
        (conn.tenant, DRAFT),
    )
    with pytest.raises(llm.LLMBudgetError, match="comes after dev_eval"):
        llm.generate(conn, DRAFT, VARS, version=1, stage="held_out")


def test_the_seeded_campaign_names_the_order_of_its_stages():
    seeded = next(
        c
        for c in json.loads((db.REPO_ROOT / "supabase" / "seed" / "config.json").read_text())["config"]
        if c["key"] == "llm.campaigns"
    )["value"]["m1-11"]
    assert seeded["order"] == ["dev_eval", "held_out", "draft"]
    assert set(seeded["order"]) == set(seeded["stages"])
