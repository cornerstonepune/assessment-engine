"""The model adapter is the only module that talks to a text model. It must fill the prompt
row, survive the free tier's 503s and spurious 404s, fall through an ordered model list, refuse
output that does not match the row's schema, and leave a flow_run row every time."""
import io
import json
import urllib.error

import pytest

from engine.adapters import llm

SCHEMA = {"type": "object", "required": ["items"], "properties": {
    "items": {"type": "array", "items": {"type": "object", "required": ["a"],
                                          "properties": {"a": {"type": "integer"}}}}}}


class Conn:
    """Enough of a psycopg connection for the adapter: prompt row, config row, flow_run writes."""
    def __init__(self, schema=SCHEMA, fallback=("m2", "m3")):
        self.schema, self.fallback, self.runs, self._sql = schema, list(fallback), [], ""

    def execute(self, sql, params=()):
        self._sql = sql
        if "insert into flow_run" in sql or "update flow_run" in sql:
            self.runs.append((sql, params))
        return self

    def fetchone(self):
        if "from prompt" in self._sql:
            return {"id": "p1", "text": "Make {{n}} things about {{topic}}.", "model": "m1", "json_schema": self.schema}
        if "from config" in self._sql:
            return {"value": self.fallback}
        if "returning id" in self._sql:
            return {"id": "run1"}
        return None


def response(payload, tokens=42):
    body = json.dumps({"candidates": [{"content": {"parts": [{"text": json.dumps(payload)}]}}],
                       "usageMetadata": {"totalTokenCount": tokens}}).encode()
    return io.BytesIO(body)


def http_error(code, body=b""):
    return urllib.error.HTTPError("u", code, "err", {}, io.BytesIO(body))


DAILY_QUOTA_429 = json.dumps({"error": {"code": 429, "details": [
    {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
     "violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier", "quotaValue": "20"}]},
    {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "38s"}]}}).encode()

MINUTE_QUOTA_429 = json.dumps({"error": {"code": 429, "details": [
    {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
     "violations": [{"quotaId": "GenerateRequestsPerMinutePerProjectPerModel-FreeTier"}]},
    {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "7s"}]}}).encode()


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
            if isinstance(r, Exception): raise r
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
