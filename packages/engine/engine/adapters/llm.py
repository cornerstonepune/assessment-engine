"""The only module that talks to a text model.

One call is: the active prompt row for a purpose → placeholders filled → Gemini generateContent
asking for JSON → retry on the free tier's transient codes → the next model in the config list →
the reply checked against the row's json_schema → a flow_run row either way. Callers never see a
model id, an HTTP code, or an unvalidated reply.
"""
import base64
import json
import ssl
import time
import urllib.error
import urllib.request

import certifi
import jsonschema

from engine import db

WAITS = (5, 10, 20, 40, 60)  # seconds between attempts on one model; a fill is a background job, patience is free
RETRIES = len(WAITS)
TRANSIENT = (404, 429, 503)  # 404 is returned spuriously by this API under load (STATE.md)
TIMEOUT_S = 180
RATE_LIMIT_WAIT_S = 60  # a 429 without Retry-After: the free tier's limits are per minute
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


class LLMError(RuntimeError):
    pass


def generate(conn, purpose, variables, images=()):
    row = conn.execute(
        "select id, text, model, json_schema from prompt where purpose = %s and active", (purpose,)
    ).fetchone()
    if not row:
        raise LLMError(f"no active prompt for {purpose!r}")
    cfg = conn.execute("select value from config where key = 'llm.fallback_models'").fetchone()
    models = [row["model"]] + list(cfg["value"] if cfg else [])
    run = conn.execute(
        "insert into flow_run (tenant_id, flow, trigger) select id, %s, %s from tenant where slug = %s"
        " returning id", (purpose, "engine", db.tenant_slug()),
    ).fetchone()["id"]

    parts = [{"text": _fill(row["text"], variables)}]
    parts += [{"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(img).decode()}}
              for img in images]
    body = json.dumps({"contents": [{"parts": parts}],
                       "generationConfig": {"response_mime_type": "application/json"}}).encode()
    try:
        raw = _call(models, body, db.env("GEMINI_API_KEY"))
        out = json.loads(raw["candidates"][0]["content"]["parts"][0]["text"])
        try:
            jsonschema.validate(out, row["json_schema"])
        except jsonschema.ValidationError as e:
            raise LLMError(f"{purpose} output failed its schema: {e.message}") from e
    except LLMError as e:
        conn.execute("update flow_run set finished_at = clock_timestamp(), status = %s, error = %s where id = %s",
                     ("error", str(e), run))
        raise
    tokens = raw["usageMetadata"]["totalTokenCount"] if "usageMetadata" in raw else None
    # clock_timestamp(), not now(): now() is the transaction's start, which would make every run 0 s
    conn.execute("update flow_run set finished_at = clock_timestamp(), status = %s, tokens = %s where id = %s",
                 ("ok", tokens, run))
    return out


def _quota(body):
    """Google's 429 says which limit was hit. Returns (daily_limit_hit, seconds_to_wait_or_None).
    The free tier's binding limit is requests per day per model (20 at the time of writing)."""
    try:
        details = json.loads(body)["error"].get("details", [])
    except (ValueError, KeyError, TypeError):
        return False, None
    daily = any("PerDay" in v.get("quotaId", "")
                for d in details for v in d.get("violations", []))
    retry = next((d["retryDelay"] for d in details if "retryDelay" in d), "")
    seconds = int(retry.rstrip("s")) if retry.rstrip("s").isdigit() else None
    return daily, seconds


def _fill(text, variables):
    for k, v in variables.items():
        text = text.replace("{{" + k + "}}", v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, indent=2))
    return text


def _call(models, body, key):
    ctx = ssl.create_default_context(cafile=certifi.where())
    errors = {}  # model -> its last error, so the message shows one line per model
    for model in models:
        for wait in WAITS:
            req = urllib.request.Request(ENDPOINT.format(model=model), data=body,
                                         headers={"Content-Type": "application/json", "x-goog-api-key": key})
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
