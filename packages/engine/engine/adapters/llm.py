"""The only module that talks to a text model.

One call is: the active prompt row for a purpose → placeholders filled → the row's model, then
each model in the config fallback list → the reply checked against the row's json_schema → a
flow_run row either way. A `claude-*` model goes through the Anthropic SDK; anything else is
Gemini's generateContent with retry on the free tier's transient codes. Callers never see a
model id, an HTTP code, or an unvalidated reply.
"""

import base64
import json
import ssl
import time
import urllib.error
import urllib.request

import anthropic
import certifi
import jsonschema

from engine import db

WAITS = (
    5,
    10,
    20,
    40,
    60,
)  # seconds between attempts on one model; a fill is a background job, patience is free
RETRIES = len(WAITS)
TRANSIENT = (404, 429, 503)  # 404 is returned spuriously by this API under load (STATE.md)
TIMEOUT_S = 180
MAX_TOKENS = 16000  # a thinking model needs room to think and then still answer
RATE_LIMIT_WAIT_S = 60  # a 429 without Retry-After: the free tier's limits are per minute
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMError(RuntimeError):
    pass


def active_prompt(conn, purpose, subject=None):
    """The prompt row that answers `purpose`: a row scoped to `subject` wins over the shared row
    (subject is null), so a second subject carries its own master prompt (ADR 0009)."""
    row = conn.execute(
        "select id, text, model, json_schema from prompt"
        " where purpose = %s and active and (subject = %s or subject is null)"
        " order by (subject is not null) desc limit 1",
        (purpose, subject),
    ).fetchone()
    if not row:
        raise LLMError(f"no active prompt for {purpose!r}" + (f" (subject {subject!r})" if subject else ""))
    return row


def generate(conn, purpose, variables, images=(), subject=None, meta=None):
    """Refuses before spending anything once the tenant's spend today reaches the
    `llm.daily_budget_inr` threshold row — no flow_run is written for a refusal, because no call
    was made. `meta`, if a dict is passed, is filled with prompt_id, model and flow_run_id so a
    caller can write provenance without a second lookup (gate 4: every item says what made it)."""
    budget = conn.execute("select value from threshold where key = 'llm.daily_budget_inr'").fetchone()
    if budget:
        spent = conn.execute(
            "select coalesce(sum(f.cost_inr), 0) as n from flow_run f join tenant t on t.id = f.tenant_id"
            " where t.slug = %s and f.started_at::date = current_date",
            (db.tenant_slug(),),
        ).fetchone()["n"]
        if spent >= budget["value"]:
            raise LLMError(
                f"today's spend ₹{spent} has reached the ₹{budget['value']} "
                "daily budget (threshold llm.daily_budget_inr)"
            )

    row = active_prompt(conn, purpose, subject)
    cfg = conn.execute("select value from config where key = 'llm.fallback_models'").fetchone()
    models = [row["model"]] + list(cfg["value"] if cfg else [])
    run = conn.execute(
        "insert into flow_run (tenant_id, flow, trigger) select id, %s, %s from tenant where slug = %s"
        " returning id",
        (purpose, "engine", db.tenant_slug()),
    ).fetchone()["id"]

    text = _fill(row["text"], variables)
    try:
        out, model, tokens, tokens_in, tokens_out = _dispatch(models, text, images, row["json_schema"])
        try:
            jsonschema.validate(out, row["json_schema"])
        except jsonschema.ValidationError as e:
            raise LLMError(f"{purpose} output failed its schema: {e.message}") from e
    except LLMError as e:
        conn.execute(
            "update flow_run set finished_at = clock_timestamp(), status = %s, error = %s where id = %s",
            ("error", str(e), run),
        )
        raise
    cost = _cost_inr(conn, model, tokens_in, tokens_out)
    # clock_timestamp(), not now(): now() is the transaction's start, which would make every run 0 s
    conn.execute(
        "update flow_run set finished_at = clock_timestamp(), status = %s, model = %s,"
        " tokens = %s, tokens_in = %s, tokens_out = %s, cost_inr = %s where id = %s",
        ("ok", model, tokens, tokens_in, tokens_out, cost, run),
    )
    if meta is not None:
        meta.update(prompt_id=row["id"], model=model, flow_run_id=run, cost_inr=cost)
    return out


def _cost_inr(conn, model, tokens_in, tokens_out):
    """None when the vendor didn't say — never guessed at, never silently zero for a real spend."""
    if tokens_in is None or tokens_out is None:
        return None
    prices = conn.execute("select value from config where key = 'llm.prices'").fetchone()
    rate = (prices["value"] if prices else {}).get(model, {})
    return round((tokens_in * rate.get("in", 0) + tokens_out * rate.get("out", 0)) / 1_000_000, 4)


def _dispatch(models, text, images, schema):
    """Walk the model list in order, each vendor by its own transport. A model that cannot serve
    — quota gone, no key, no credit, transient errors exhausted — hands on to the next, and the
    final error names every model's reason, so a malformed request still reads as one. Returns
    (output, model that answered, total tokens, input tokens or None, output tokens or None)."""
    errors = []
    # Both vendors see the schema in the prompt: asked only for "JSON", a model may return a bare
    # list where an object was wanted, and the validation after this would refuse the whole page.
    text = f"{text}\n\nThe JSON schema to match exactly:\n{json.dumps(schema)}"
    for model in models:
        try:
            if model.startswith("claude-"):
                out, tin, tout = _call_anthropic(model, text, images, schema)
                return out, model, tin + tout, tin, tout
            parts = [{"text": text}]
            parts += [
                {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(img).decode()}}
                for img in images
            ]
            body = json.dumps(
                {
                    "contents": [{"parts": parts}],
                    "generationConfig": {"response_mime_type": "application/json"},
                }
            ).encode()
            raw = _call([model], body, db.env("GEMINI_API_KEY"))
            usage = raw.get("usageMetadata", {})
            tokens = usage.get("totalTokenCount")
            out = json.loads(raw["candidates"][0]["content"]["parts"][0]["text"])
            return out, model, tokens, usage.get("promptTokenCount"), usage.get("candidatesTokenCount")
        except LLMError as e:
            errors.append(str(e).split("; ", 1)[-1])  # _call's own summary line is repeated here
        except RuntimeError as e:  # a missing key for this vendor: skip it, say so
            errors.append(f"{model}: {e}")
    raise LLMError(f"all models unavailable: {', '.join(models)}; " + " | ".join(errors))


def _call_anthropic(model, text, images, schema):
    """One Messages call → (output, input tokens, output tokens). The reply is validated by the
    caller; the SDK already retries 429s and 5xx."""
    key = db.env("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=key, max_retries=3, timeout=TIMEOUT_S)
    content = [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": base64.standard_b64encode(img).decode(),
            },
        }
        for img in images
    ]
    content.append({"type": "text", "text": text})
    try:
        r = client.messages.create(
            model=model, max_tokens=MAX_TOKENS, messages=[{"role": "user", "content": content}]
        )
    except anthropic.RateLimitError as e:
        raise LLMError(f"{model} rate limited: {e.message}") from e
    except anthropic.APIStatusError as e:
        kind = "returned HTTP" if e.status_code < 500 and e.status_code != 429 else "server error HTTP"
        raise LLMError(f"{model} {kind} {e.status_code}: {e.message}") from e
    except anthropic.APIConnectionError as e:
        raise LLMError(f"{model} connection error: {e}") from e
    if r.stop_reason == "refusal":
        raise LLMError(f"{model} refused the request")
    reply = next((b.text for b in r.content if b.type == "text"), "")
    if not reply:
        # A thinking model can spend the whole budget before it writes anything: claude-sonnet-5
        # returned one thinking block and no text at 8000. Say that, rather than "did not return
        # JSON: ''", which sent one session hunting for a malformed request.
        raise LLMError(
            f"{model} returned no text (stop_reason {r.stop_reason}, "
            f"{r.usage.output_tokens} output tokens, blocks "
            f"{[b.type for b in r.content] or 'none'})"
        )
    reply = reply.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        out = json.loads(reply)
    except ValueError as e:
        raise LLMError(f"{model} did not return JSON: {reply[:120]!r}") from e
    return out, r.usage.input_tokens, r.usage.output_tokens


def _quota(body):
    """Google's 429 says which limit was hit. Returns (daily_limit_hit, seconds_to_wait_or_None).
    The free tier's binding limit is requests per day per model (20 at the time of writing)."""
    try:
        details = json.loads(body)["error"].get("details", [])
    except (ValueError, KeyError, TypeError):
        return False, None
    daily = any("PerDay" in v.get("quotaId", "") for d in details for v in d.get("violations", []))
    retry = next((d["retryDelay"] for d in details if "retryDelay" in d), "")
    seconds = int(retry.rstrip("s")) if retry.rstrip("s").isdigit() else None
    return daily, seconds


def _fill(text, variables):
    for k, v in variables.items():
        text = text.replace(
            "{{" + k + "}}", v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, indent=2)
        )
    return text


def _call(models, body, key):
    ctx = ssl.create_default_context(cafile=certifi.where())
    errors = {}  # model -> its last error, so the message shows one line per model
    for model in models:
        for wait in WAITS:
            req = urllib.request.Request(
                ENDPOINT.format(model=model),
                data=body,
                headers={"Content-Type": "application/json", "x-goog-api-key": key},
            )
            try:
                with urllib.request.urlopen(req, context=ctx, timeout=TIMEOUT_S) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                reply = e.read().decode(errors="replace")
                detail = " ".join(reply.split())[:160]
                if e.code not in TRANSIENT:
                    raise LLMError(f"{model} returned HTTP {e.code}: {detail}") from e
                errors[model] = f"{model} HTTP {e.code}: {detail}"
                if e.code == 429:
                    daily, retry_s = _quota(reply)
                    if daily:
                        errors[model] = f"{model} daily free-tier quota used up"
                        break  # no wait brings it back today; the next model might serve
                    wait = retry_s or max(wait, RATE_LIMIT_WAIT_S)
            except (TimeoutError, urllib.error.URLError) as e:
                errors[model] = f"{model} {type(e).__name__}"
            time.sleep(wait)
    raise LLMError(f"all models unavailable: {', '.join(models)}; " + " | ".join(errors.values()))
