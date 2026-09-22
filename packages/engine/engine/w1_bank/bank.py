"""W1 — the question bank. A prompt generates, code verifies, rows land active (ADR 0005).

`fill` is N2 as engine code. `recheck` is the independent audit of everything already in the
bank. `flag` is any staff member's after-the-fact veto. `sheet` renders a handful so a person can
hold the output. Nothing here commits: the caller owns the transaction.
"""

import json
import random
from collections import Counter

from engine.adapters import llm
from engine.assess import bands, tags, verify
from engine.assess import misconceptions as M
from engine.assess import words as W
from engine.core import db
from engine.w1_bank import labels
from engine.w1_bank.spec import read as spec

BATCH = 20  # the free tier timed out on 40 (STATE.md)
SAMPLER_FORMATS = bands.SAMPLER_FORMATS


def _sampled(check, formats, n, seed):
    """Candidates from the deterministic samplers instead of the model — the documented fallback
    for when the model is unavailable (ADR 0005), and the oracle the prompt is graded against.

    Produces the same shape `verify.problems` reads, so both paths meet the same gate.
    """
    rng = random.Random(seed)
    usable = [f for f in formats if f in SAMPLER_FORMATS]
    if not usable:
        raise ValueError(
            f"no sampler format among {formats!r} — this skill set needs a native generator, not --offline"
        )
    if "op" not in check or "digits" not in check:
        raise ValueError(
            f"this band's rule has no op/digits ({sorted(check)}) — it is a native-generator band;"
            f" fill it with --native, not --offline"
        )
    out = []
    for op, a, b in bands.pairs(check, n, seed):
        fmt = usable[len(out) % len(usable)]
        ans = M.compute(op, a, b)
        c = {
            "format": fmt,
            "op": op,
            "a": a,
            "b": b,
            "answer": ans,
            "stem": "",
            "missing": None,
            "misconceptions": [{"code": k, "wrong_answer": v} for k, v in M.predict(op, a, b).items()],
        }
        if fmt == "missing_number":
            c["missing"] = "b"
            c["stem"] = f"{a} {'−' if op == '-' else '+'} □ = {ans}"
        elif fmt == "word_1step":
            op_ctx = [t for t in W.templates("word_1step", op=op) if not t.get("table")]
            if not op_ctx:
                raise ValueError(
                    f"no word-problem story written for {op!r}; add one to engine/assess/word_templates.json"
                    f" or drop word_1step from this skill set's formats"
                )
            n1, n2 = rng.sample(W.NAMES, 2)
            tpl = rng.choice(op_ctx)
            c["stem"] = tpl["text"].format(a=a, b=b, n=n1, n2=n2)
            c["structure"] = tpl["structure"]
        out.append(c)
    return out


def fill(conn, code, difficulty, n, dry_run=False, after_batch=None, on_reject=None, offline=False):
    """`after_batch` is called once per model call — the CLI passes conn.commit so a long fill
    keeps what it has and its flow_run rows are visible while it runs. `on_reject(candidate,
    problems)` lets the CLI show why items fall; tests pass neither. `offline` swaps the model for
    the deterministic samplers, which write no sentence a model would have written but never fail
    on a quota."""
    prompt_input, s, check = spec(conn, code, difficulty)
    if check.get("cases"):
        raise ValueError(f"{code} {difficulty} is made of taxonomy cases — fill it with `engine bank refill`")
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    counts = Counter(
        asked=0,
        returned=0,
        accepted=0,
        rejected=0,
        duplicate=0,
        already_in_bank=0,
        unnamed_distractor_dropped=0,
    )
    known = _known_codes(conn)
    rules, vocab = labels.rules(conn), labels.vocabulary(conn)
    reasons, seen, accepted, meta = Counter(), set(), [], {}
    # A band may pin itself to one format (`check.format`); otherwise it draws on everything the
    # skill set declares. Pinning is what stops two bands of one skill set — same digits, same
    # regroups — competing for a single pool of (a, b) pairs and starving whichever fills second.
    band_formats = [check["format"]] if check.get("format") in SAMPLER_FORMATS else list(s["formats"])
    # A random base, not counts["asked"]: a fixed seed restarts the same sequence on every fresh
    # call, so a second fill meant to top a unit up would only rediscover its own earlier items.
    seed_base = random.randrange(10**9)
    while counts["accepted"] < n and counts["asked"] < 3 * n:
        ask = min(BATCH, n - counts["accepted"])
        if offline:
            out = {"items": _sampled(check, band_formats, ask, seed=seed_base + counts["asked"])}
        else:
            out = llm.generate(conn, "item_generate", {"spec": prompt_input, "n": ask}, meta=meta)
        counts["asked"] += ask
        if not out["items"]:
            break
        for c in out["items"]:
            counts["returned"] += 1
            c = verify.normalise(c)
            key = (c.get("op"), c.get("a"), c.get("b"), c.get("format"))
            if key in seen:
                counts["duplicate"] += 1
                continue
            seen.add(key)
            probs = verify.problems(c, check)
            if probs:
                counts["rejected"] += 1
                reasons.update(p.split(" ")[0] for p in probs)
                if on_reject:
                    on_reject(c, probs)
                continue
            it = verify.to_item(c, s["rung_code"], skills=list(s["skill_codes"]))
            # The band as declared, against the item as measured. Redundant for the sampler,
            # which drew from this very rule; the model path is exactly where it earns its keep.
            dims = verify.dimension_problems(tags.derive(it), check)
            if dims:
                counts["rejected"] += 1
                reasons.update(p.split(" ")[1] for p in dims)
                if on_reject:
                    on_reject(c, dims)
                continue
            counts["unnamed_distractor_dropped"] += _strip_unnamed(it, known)
            charged = labels.label_item(it, s["skill_codes"], rules, vocab)
            prov = {
                "skill_set_version": s["version"],
                "generator": f"sampled:{c['op']}" if offline else "model:item_generate",
                **({} if offline else {"prompt_id": meta.get("prompt_id"), "model": meta.get("model")}),
            }
            if not dry_run and not _insert(conn, tenant, it, code, difficulty, s["eval_type"], prov, charged):
                counts["already_in_bank"] += 1
                continue
            counts["accepted"] += 1
            accepted.append(it)
        if after_batch:
            after_batch()
    return dict(counts), dict(reasons), accepted


def _known_codes(conn):
    return {r["code"] for r in conn.execute("select distinct code from misconception").fetchall()}


def _strip_unnamed(it, known):
    """Drop distractors whose code is not in the vocabulary, and say how many were dropped.

    A model may claim a mistake under a name of its own (`M_MULT_CONCAT` for our `M_MUL_CONCAT`).
    Kept on the item it would be unmarkable — `engine audit` checks exactly this — so it is dropped
    here, where a connection knows the vocabulary, rather than trusted into the row.
    """
    dropped = 0
    for r in it.responses:
        unknown = {c for c in (r.misconceptions or {}) if c not in known}
        if unknown:
            r.misconceptions = {c: v for c, v in r.misconceptions.items() if c not in unknown}
            dropped += len(unknown)
    return dropped


def _insert(conn, tenant, it, code, difficulty, eval_type="computable", prov=None, mistake_skills=None):
    """`eval_type` is stamped from the skill set (ADR 0012) so marking never re-derives how a
    question should be judged from its shape. `prov` carries the provenance every item must be
    able to answer with — which version of the rule, which generator, which prompt and model
    (BUILD-ORDER gate 4, amended; external proposal §15)."""
    d = it.to_dict()
    prov = prov or {}
    row = conn.execute(
        "insert into item (tenant_id, item_key, template, rung_code, skill_codes, signal, fmt, stem,"
        " spec, responses, tags, source, status, skill_set_code, difficulty, eval_type,"
        " skill_set_version, generator, prompt_id, model, mistake_skills)"
        " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'generated','active',%s,%s,%s,%s,%s,%s,%s,%s)"
        " on conflict (tenant_id, item_key) do nothing returning id",
        (
            tenant,
            it.item_id,
            it.template,
            it.rung,
            it.skills,
            it.signal,
            it.fmt,
            it.stem,
            json.dumps(d["spec"]),
            json.dumps(d["responses"]),
            json.dumps(tags.derive(it)),
            code,
            difficulty,
            eval_type,
            prov.get("skill_set_version"),
            prov.get("generator"),
            prov.get("prompt_id"),
            prov.get("model"),
            json.dumps(mistake_skills or {}),
        ),
    ).fetchone()
    return row is not None


def fill_native(conn, code, difficulty, n, dry_run=False, after_batch=None):
    """Chunk B of W1 gate 2: a skill set whose format has no place in the model-candidate
    pipeline (mental strategies, word problems, budgets, estimation, efficient method) filled
    straight from its own generator in `assess/items.py`, keyed by `check['format']`."""
    prompt_input, s, check = spec(conn, code, difficulty)
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    fmt = check.get("format") or s["formats"][0]
    counts = Counter(asked=0, accepted=0, already_in_bank=0, duplicate=0, unnamed_distractor_dropped=0)
    known = _known_codes(conn)
    rules, vocab = labels.rules(conn), labels.vocabulary(conn)
    # The same in-batch guard `fill` has. Without it this path's only defence against two identical
    # questions is the insert's own conflict clause, so a dry run — a scenario, an eval — could hand
    # back a set with a repeat in it, and a caller that does not store would never know.
    seen = set()
    accepted = []
    tries = 0
    # Real (OS-seeded) randomness, not a seed derived from (code, difficulty, tries): a fixed
    # seed would make every fresh call retrace the same sequence from its first attempt, so a
    # second call meant to top up an already-filled unit would just rediscover what the first
    # call already inserted, never reaching new content.
    rng = random.Random()
    while counts["accepted"] < n and tries < n * 8:
        tries += 1
        counts["asked"] += 1
        try:
            it = bands.native_item(fmt, check, rng, s["rung_code"], "Conceptual")
        except RuntimeError:
            continue  # this draw's numbers could not make the question; the loop draws again
        if it.item_id in seen:
            counts["duplicate"] += 1
            continue
        seen.add(it.item_id)
        counts["unnamed_distractor_dropped"] += _strip_unnamed(it, known)
        charged = labels.label_item(it, s["skill_codes"], rules, vocab)
        prov = {"skill_set_version": s["version"], "generator": f"native:{fmt}"}
        if not dry_run and not _insert(conn, tenant, it, code, difficulty, s["eval_type"], prov, charged):
            counts["already_in_bank"] += 1
            continue
        counts["accepted"] += 1
        accepted.append(it)
        if after_batch and counts["accepted"] % 20 == 0:
            after_batch()
    if after_batch:
        after_batch()
    return dict(counts), accepted
