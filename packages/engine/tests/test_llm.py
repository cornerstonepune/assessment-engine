"""The model adapter is the only module that talks to a text model. It must fill the prompt
row, survive the free tier's 503s and spurious 404s, fall through an ordered model list, refuse
output that does not match the row's schema, leave a flow_run row every time, and refuse to spend
past the daily budget row before it ever makes a call."""

import io
import json
import os
import urllib.error

import pytest

from engine import db
from engine.adapters import llm

SCHEMA = {
    "type": "object",
    "required": ["items"],
    "properties": {
        "items": {
            "type": "array",
            "items": {"type": "object", "required": ["a"], "properties": {"a": {"type": "integer"}}},
        }
    },
}


class Conn:
    """Enough of a psycopg connection for the adapter: prompt row(s), config, threshold, flow_run
    writes. `prompts` maps (purpose, subject) -> row, for the subject-selection tests; omitted,
    every purpose gets the one fixed row regardless of subject, matching the old fake exactly."""

    def __init__(self, schema=SCHEMA, fallback=("m2", "m3"), prompts=None, prices=None, budget=None, spent=0):
        self.schema, self.fallback, self.prompts, self.prices = schema, list(fallback), prompts, prices
        self.budget, self.spent, self.runs, self._sql, self._params = budget, spent, [], "", ()

    def execute(self, sql, params=()):
        self._sql, self._params = sql, params
        if "insert into flow_run" in sql or "update flow_run" in sql:
            self.runs.append((sql, params))
        return self

    def fetchone(self):
        if "from prompt" in self._sql:
            if self.prompts is None:
                return {
                    "id": "p1",
                    "text": "Make {{n}} things about {{topic}}.",
                    "model": "m1",
                    "json_schema": self.schema,
                }
            purpose, subject = self._params
            return self.prompts.get((purpose, subject)) or self.prompts.get((purpose, None))
        if "from threshold" in self._sql:
            return {"value": self.budget} if self.budget is not None else None
        if "sum(f.cost_inr)" in self._sql:
            return {"n": self.spent}
        if "from config" in self._sql and "llm.fallback_models" in self._sql:
            return {"value": self.fallback}
        if "from config" in self._sql and "llm.prices" in self._sql:
            return {"value": self.prices} if self.prices is not None else None
        if "returning id" in self._sql:
            return {"id": "run1"}
        return None


def response(payload, tokens=42):
    body = json.dumps(
        {
            "candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}],
            "usageMetadata": {
                "totalTokenCount": tokens,
                "promptTokenCount": tokens // 2,
                "candidatesTokenCount": tokens - tokens // 2,
            },
        }
    ).encode()
    return io.BytesIO(body)


def http_error(code, body=b""):
    return urllib.error.HTTPError("u", code, "err", {}, io.BytesIO(body))


DAILY_QUOTA_429 = json.dumps(
    {
        "error": {
            "code": 429,
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                    "violations": [
                        {"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier", "quotaValue": "20"}
                    ],
                },
                {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "38s"},
            ],
        }
    }
).encode()

MINUTE_QUOTA_429 = json.dumps(
    {
        "error": {
            "code": 429,
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.QuotaFailure",
                    "violations": [{"quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}],
                },
                {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "7s"},
            ],
        }
    }
).encode()


def test_a_model_whose_daily_quota_is_gone_is_skipped_without_waiting(calls, monkeypatch):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    log = calls([http_error(429, DAILY_QUOTA_429), response({"items": []})])
    llm.generate(Conn(), "item_generate", {})
    assert [u.split("/")[-1].split(":")[0] for u, _ in log] == ["m1", "m2"]


def test_a_per_minute_limit_waits_the_seconds_google_asks_for(calls, monkeypatch):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    waited = []
    calls([http_error(429, MINUTE_QUOTA_429), response({"items": []})])
    monkeypatch.setattr(llm.time, "sleep", waited.append)
    llm.generate(Conn(), "item_generate", {})
    assert waited == [7]


@pytest.fixture
def calls(monkeypatch):
    log = []

    def fake(script):
        it = iter(script)

        def urlopen(req, context=None, timeout=None):
            log.append((req.full_url, json.loads(req.data)))
            r = next(it)
            if isinstance(r, Exception):
                raise r
            return r

        monkeypatch.setattr(llm.urllib.request, "urlopen", urlopen)
        monkeypatch.setattr(llm.time, "sleep", lambda s: None)
        return log

    return fake


def test_fills_placeholders_and_returns_the_parsed_json(calls, monkeypatch):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    log = calls([response({"items": [{"a": 1}]})])
    out = llm.generate(Conn(), "item_generate", {"n": 3, "topic": "subtraction"})
    assert out == {"items": [{"a": 1}]}
    assert log[0][1]["contents"][0]["parts"][0]["text"].startswith("Make 3 things about subtraction.")
    assert "/m1:" in log[0][0]


@pytest.mark.parametrize("code", [503, 429, 404])
def test_retries_the_same_model_on_a_transient_error(calls, monkeypatch, code):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    log = calls([http_error(code, b'{"error": {"message": "busy"}}'), response({"items": []})])
    assert llm.generate(Conn(), "item_generate", {}) == {"items": []}
    assert [u.split("/")[-1].split(":")[0] for u, _ in log] == ["m1", "m1"]
    # the retry must send the same request, never the previous error's text
    assert log[0][1] == log[1][1] and "contents" in log[1][1]


def test_falls_through_the_ordered_model_list_when_retries_are_exhausted(calls, monkeypatch):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    log = calls([http_error(503)] * llm.RETRIES + [response({"items": []})])
    llm.generate(Conn(), "item_generate", {})
    assert log[-1][0].split("/")[-1].startswith("m2:")


def test_gives_up_with_a_clear_error_when_every_model_fails(calls, monkeypatch):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    calls([http_error(503)] * (llm.RETRIES * 3))
    with pytest.raises(llm.LLMError, match="m1, m2, m3"):
        llm.generate(Conn(), "item_generate", {})


def test_output_that_breaks_the_schema_is_refused(calls, monkeypatch):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    calls([response({"items": [{"a": "one"}]})])
    with pytest.raises(llm.LLMError, match="schema"):
        llm.generate(Conn(), "item_generate", {})


def test_a_non_transient_http_error_is_not_retried_on_that_model(calls, monkeypatch):
    """A 400 is not retried on the model that gave it, but the next model is still tried — a
    vendor's 400 can mean "no credit" or "bad key", which another vendor may not share."""
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    log = calls([http_error(400), http_error(400), http_error(400)])
    with pytest.raises(llm.LLMError, match="400"):
        llm.generate(Conn(), "item_generate", {})
    assert [u.split("/")[-1].split(":")[0] for u, _ in log] == ["m1", "m2", "m3"]


def test_every_call_leaves_a_flow_run_row_with_tokens_and_status(calls, monkeypatch):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    calls([response({"items": []}, tokens=1234)])
    conn = Conn()
    llm.generate(conn, "item_generate", {})
    assert any("insert into flow_run" in sql and "item_generate" in params for sql, params in conn.runs)
    assert any("update flow_run" in sql and 1234 in params and "ok" in params for sql, params in conn.runs)


def test_a_failure_is_recorded_on_the_flow_run_row_too(calls, monkeypatch):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    calls([http_error(400), http_error(400), http_error(400)])
    conn = Conn()
    with pytest.raises(llm.LLMError):
        llm.generate(conn, "item_generate", {})
    assert any("update flow_run" in sql and "error" in params for sql, params in conn.runs)


def test_cost_is_computed_from_the_prices_row_and_the_model_that_answered(calls, monkeypatch):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    calls([http_error(503)] * llm.RETRIES + [response({"items": []})])  # falls through to m2
    conn = Conn(prices={"m1": {"in": 1000, "out": 1000}, "m2": {"in": 10, "out": 20}})
    llm.generate(conn, "item_generate", {})
    update = next(params for sql, params in conn.runs if "update flow_run" in sql)
    assert "m2" in update  # the model that actually answered, not the row's own m1
    assert any(isinstance(p, float) and p > 0 for p in update)  # cost_inr, priced off m2's rate


def test_a_model_missing_from_the_prices_row_costs_nothing_tracked_rather_than_guessed(calls, monkeypatch):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    calls([response({"items": []})])
    conn = Conn(prices={"some-other-model": {"in": 999, "out": 999}})
    llm.generate(conn, "item_generate", {})
    update = next(params for sql, params in conn.runs if "update flow_run" in sql)
    assert 0.0 in update  # m1 isn't priced, so cost_inr is 0, not fabricated


# ---- the daily budget: refused before anything is spent, silent otherwise


def test_refuses_once_todays_spend_reaches_the_budget_row(monkeypatch):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    conn = Conn(budget=100, spent=100)
    with pytest.raises(llm.LLMError, match="budget"):
        llm.generate(conn, "item_generate", {})
    assert conn.runs == []  # refused before a flow_run row is ever written


def test_generation_proceeds_normally_when_under_budget(calls, monkeypatch):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    calls([response({"items": []})])
    conn = Conn(budget=100, spent=10)
    assert llm.generate(conn, "item_generate", {}) == {"items": []}


# ---- subject-scoped prompts (ADR 0009): a subject's own row wins; else the shared row answers


def test_a_subject_specific_prompt_row_wins_over_the_shared_one(calls, monkeypatch):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    log = calls([response({"items": []})])
    conn = Conn(
        prompts={
            ("item_generate", None): {
                "id": "generic",
                "text": "generic {{n}}",
                "model": "m1",
                "json_schema": SCHEMA,
            },
            ("item_generate", "NUM"): {
                "id": "num",
                "text": "num {{n}}",
                "model": "m1",
                "json_schema": SCHEMA,
            },
        }
    )
    llm.generate(conn, "item_generate", {"n": 1}, subject="NUM")
    assert log[0][1]["contents"][0]["parts"][0]["text"].startswith("num 1")


def test_falls_back_to_the_shared_prompt_when_no_row_names_that_subject(calls, monkeypatch):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    log = calls([response({"items": []})])
    conn = Conn(
        prompts={
            ("item_generate", None): {
                "id": "generic",
                "text": "generic {{n}}",
                "model": "m1",
                "json_schema": SCHEMA,
            }
        }
    )
    llm.generate(conn, "item_generate", {"n": 1}, subject="SCI")
    assert log[0][1]["contents"][0]["parts"][0]["text"].startswith("generic 1")


def test_no_prompt_for_that_purpose_names_the_subject_in_the_error(monkeypatch):
    monkeypatch.setattr(llm.db, "env", lambda name: "k")
    conn = Conn(prompts={})
    with pytest.raises(llm.LLMError, match="'SCI'"):
        llm.generate(conn, "nonexistent", {}, subject="SCI")


# ---- against the real database: the SQL itself, not the fake's dict lookup

pytestmark_db = pytest.mark.skipif(
    not os.getenv("DATABASE_URL"), reason="needs DATABASE_URL (see .env.example)"
)


@pytest.fixture
def real_conn():
    with db.connect() as c:
        yield c
        c.rollback()


@pytestmark_db
def test_the_subject_selection_sql_prefers_the_subject_row_and_falls_back_correctly(real_conn, monkeypatch):
    tenant = real_conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    for subject, text in ((None, "generic {{n}}"), ("NUM", "num {{n}}")):
        real_conn.execute(
            "insert into prompt (tenant_id, purpose, version, text, model, json_schema, active, subject)"
            " values (%s,'test_purpose_llm',1,%s,'m1',%s,true,%s)",
            (tenant, text, json.dumps(SCHEMA), subject),
        )
    seen = []
    monkeypatch.setattr(
        llm,
        "_dispatch",
        lambda models, text, images, schema: (seen.append(text) or {"items": []}, "m1", 5, 3, 2),
    )

    llm.generate(real_conn, "test_purpose_llm", {"n": 1}, subject="NUM")
    llm.generate(real_conn, "test_purpose_llm", {"n": 2}, subject="SCI")  # no SCI row: falls back
    llm.generate(real_conn, "test_purpose_llm", {"n": 3})  # no subject: the generic row

    assert seen[0].startswith("num 1")
    assert seen[1].startswith("generic 2")
    assert seen[2].startswith("generic 3")
