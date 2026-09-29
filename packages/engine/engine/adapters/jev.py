"""The only module that talks to Jev, TypeSafe's decision model (ADR 0036).

Jev answers a question fixed in advance with one of up to 255 named options and a probability for each; it never
writes text and never sees an image. It is used where the engine needs a judgement code cannot compute; anything
code can compute stays code — asked whether 45 is a right answer to 81 − 46, Jev said 0.47 (2026-09-27).

One call is: the active prompt row for a purpose (its text is the instructions, `json_schema.type` the kind of
answer, `model` the model) → the options the caller names → `POST /v1/systemone` → a flow_run row either way.
Callers get the options ranked by probability; an answer that is not one of the options is refused.
"""

import json
import os
import urllib.error
import urllib.request

from engine.adapters import llm
from engine.core import db

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
MAX_OPTIONS = 255  # the service's own limit on one choice
TIMEOUT_S = 30
ATTEMPTS = 3


class JevError(RuntimeError):
    pass


def _post(body, key=None):
    key = os.environ.get("TYPESAFE_API_KEY", "") if key is None else key
    if not key:
        raise JevError("no TYPESAFE_API_KEY in the engine's environment: Jev cannot be asked")
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    last = None
    for _ in range(ATTEMPTS):  # the service answers 5xx now and then; the same request then succeeds
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                return json.load(r)
        except (urllib.error.URLError, TimeoutError) as e:
            last = e
            if isinstance(e, urllib.error.HTTPError) and e.code < 500:
                break
    raise JevError(f"Jev did not answer: {last}")


def ask(row, state, options, post=_post):
    """One decision → {"choice", "ranked": [(option, p), …] best first, "model", "tokens_in", "tokens_out"}.
    `row`: a prompt row (text, model, json_schema); `state`: what Jev is shown; `options`: {name: meaning}."""
    if len(options) > MAX_OPTIONS:
        raise JevError(f"{len(options)} options; Jev takes at most {MAX_OPTIONS} in one choice")
    kind = (row.get("json_schema") or {}).get("type", "choice")
    question = {"type": kind, "instructions": row["text"].format(**state), "criteria": options}
    reply = post({"model": row["model"], "state": state, "questions": {"decision": question}})
    answer = reply["answers"]["decision"]
    probabilities = answer.get("probabilities") or {}
    if answer.get("choice") not in options or set(probabilities) - set(options):
        raise JevError(f"Jev answered {answer.get('choice')!r}, which is not one of the options it was given")
    usage = reply.get("usage") or {}
    return {
        "choice": answer["choice"],
        "ranked": sorted(probabilities.items(), key=lambda kv: -kv[1]),
        "model": reply.get("model", row["model"]),
        "tokens_in": usage.get("input_tokens"),
        "tokens_out": usage.get("output_tokens"),
    }


def yes_no(row, state, asks, post=_post):
    """Many yes/no questions in one call → {"yes": {name: probability of yes}, "model", "tokens_in", "tokens_out"}.
    `asks`: {name: what it is about}, each put into the row's text as {subject}; the row's `json_schema.criteria`
    says what counts as yes and as no. An answer that is not a probability, or a name not asked, is refused."""
    criteria = (row.get("json_schema") or {}).get("criteria")
    questions = {
        name: {"type": "noul", "instructions": row["text"].format(**state, subject=about)}
        | ({"criteria": criteria} if criteria else {})
        for name, about in asks.items()
    }
    reply = post({"model": row["model"], "state": state, "questions": questions})
    answers = reply["answers"]
    if set(answers) != set(asks):
        raise JevError(f"Jev answered {sorted(answers)}, not the questions it was asked")
    yes = {}
    for name, a in answers.items():
        p = a.get("noul")
        if not isinstance(p, (int, float)) or not 0 <= p <= 1:
            raise JevError(f"Jev's answer to {name!r} is not a probability: {a!r}")
        yes[name] = float(p)
    usage = reply.get("usage") or {}
    return {
        "yes": yes,
        "model": reply.get("model", row["model"]),
        "tokens_in": usage.get("input_tokens"),
        "tokens_out": usage.get("output_tokens"),
    }


def counting(ask, failed):
    """`ask`, with the reason of every call Jev did not answer also kept in `failed`: an eval tells a decision Jev could
    not be asked about from one it was unsure of (with no key, both used to score as nothing chosen)."""

    def asking(*args, **kwargs):
        try:
            return ask(*args, **kwargs)
        except JevError as e:
            failed.append(str(e))
            raise

    return asking


def decide_yes_no(conn, purpose, state, asks, post=_post, version=None):
    """`yes_no` with the purpose's active prompt row (or `version`, active or not: only an eval names one), recorded
    as a flow_run with its tokens and cost."""
    return _recorded(conn, purpose, lambda row: yes_no(row, state, asks, post), version)


def decide(conn, purpose, state, options, post=_post, version=None):
    """`ask` with the purpose's active prompt row (or `version`), recorded as a flow_run with its tokens and cost."""
    return _recorded(conn, purpose, lambda row: ask(row, state, options, post), version)


def _recorded(conn, purpose, call, version=None):
    row = llm.active_prompt(conn, purpose, version=version)
    run = conn.execute(
        "insert into flow_run (tenant_id, flow, trigger) select id, %s, 'engine' from tenant where slug = %s"
        " returning id",
        (purpose, db.tenant_slug()),
    ).fetchone()["id"]
    try:
        out = call(row)
    except (JevError, KeyError) as e:
        conn.execute(
            "update flow_run set finished_at = clock_timestamp(), status = 'error', error = %s where id = %s",
            (str(e), run),
        )
        raise
    cost = llm._cost_inr(conn, row["model"], out["tokens_in"], out["tokens_out"])
    conn.execute(
        "update flow_run set finished_at = clock_timestamp(), status = 'ok', model = %s, tokens_in = %s,"
        " tokens_out = %s, cost_inr = %s where id = %s",
        (out["model"], out["tokens_in"], out["tokens_out"], cost, run),
    )
    return {**out, "prompt_id": row["id"], "flow_run_id": run}
