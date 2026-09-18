"""W1 — the question bank. A prompt generates, code verifies, rows land active (ADR 0005).

`fill` is N2 as engine code. `recheck` is the independent audit of everything already in the
bank. `flag` is any staff member's after-the-fact veto. `sheet` renders a handful so a person can
hold the output. Nothing here commits: the caller owns the transaction.
"""
import json
import random
from collections import Counter

from engine import db
from engine.adapters import llm
from engine.assess import items as I
from engine.assess import misconceptions as M
from engine.assess import tags, verify
from engine.assess.items import Item, Response
from engine.assess.pick import Sheet, _sheet_id
from engine.assess.render import render_sheet

BATCH = 20  # the free tier timed out on 40 (STATE.md)
SAMPLER_FORMATS = ["column_grid", "bare_sum", "missing_number", "word_1step"]


def _sampled(check, formats, n, seed):
    """Candidates from the deterministic samplers instead of the model — the documented fallback
    for when the model is unavailable (ADR 0005), and the oracle the prompt is graded against.

    Produces the same shape `verify.problems` reads, so both paths meet the same gate.
    """
    rng = random.Random(seed)
    usable = [f for f in formats if f in SAMPLER_FORMATS] or SAMPLER_FORMATS
    da, dbi = check["digits"]
    out = []
    for i in range(n * 4):
        if len(out) >= n:
            break
        try:
            if check["op"] == "+":
                a, b = I.sample_add(rng, da, dbi, set(check["regroups"]), max_total=check.get("max_total"))
            elif check["op"] == "-":
                a, b = I.sample_sub(rng, da, dbi, set(check["regroups"]),
                                    across_zero=bool(check.get("across_zero")),
                                    max_a=check.get("max_total"))
            else:
                break  # no sampler for this operation yet; the model path still covers it
        except RuntimeError:
            continue
        if check.get("no_zero_top") and "0" in str(a):
            continue
        fmt = usable[len(out) % len(usable)]
        ans = M.compute(check["op"], a, b)
        c = {"format": fmt, "op": check["op"], "a": a, "b": b, "answer": ans, "stem": "",
             "missing": None, "misconceptions": [{"code": k, "wrong_answer": v}
                                                 for k, v in M.predict(check["op"], a, b).items()]}
        if fmt == "missing_number":
            c["missing"] = "b"
            c["stem"] = f"{a} {'−' if check['op'] == '-' else '+'} □ = {ans}"
        elif fmt == "word_1step":
            op_ctx = [t for o, t in I.CONTEXTS_1STEP if o == check["op"]]
            n1, n2 = rng.sample(I.NAMES, 2)
            c["stem"] = rng.choice(op_ctx).format(a=a, b=b, n=n1, n2=n2)
        out.append(c)
    return out


def spec(conn, code, difficulty):
    """The prompt's input, built only from rows: skill set, rung, school philosophy, misconceptions."""
    s = conn.execute(
        "select s.*, r.band, r.skill_codes from skill_set s"
        " join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code where s.code = %s", (code,)
    ).fetchone()
    if not s:
        raise ValueError(f"no skill set {code!r}")
    band = s["difficulty"].get(difficulty)
    if not band:
        raise ValueError(f"{code} has no difficulty {difficulty!r}; it has {', '.join(s['difficulty'])}")
    school = conn.execute("select value from config where key = 'assessment.philosophy'").fetchone()
    mis = conn.execute(
        "select distinct on (code) code, description from misconception where code = any(%s) order by code",
        (list(s["misconception_codes"]),),
    ).fetchall()
    prompt_input = {
        "topic": s["name"],
        "skill": f"{s['rung_code']} — {', '.join(s['skill_codes'])}",
        "learning_objective": s["learning_objective"],
        "difficulty": f"{difficulty}: {band['words']}",
        "philosophy": list(school["value"] if school else []) + list(s["philosophy"]),
        "formats": list(s["formats"]),
        "misconceptions": [{"code": m["code"], "description": m["description"]} for m in mis],
    }
    return prompt_input, s, band["check"]


def fill(conn, code, difficulty, n, dry_run=False, after_batch=None, on_reject=None, offline=False):
    """`after_batch` is called once per model call — the CLI passes conn.commit so a long fill
    keeps what it has and its flow_run rows are visible while it runs. `on_reject(candidate,
    problems)` lets the CLI show why items fall; tests pass neither. `offline` swaps the model for
    the deterministic samplers, which write no sentence a model would have written but never fail
    on a quota."""
    prompt_input, s, check = spec(conn, code, difficulty)
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    counts = Counter(asked=0, returned=0, accepted=0, rejected=0, duplicate=0, already_in_bank=0)
    reasons, seen, accepted = Counter(), set(), []
    while counts["accepted"] < n and counts["asked"] < 3 * n:
        ask = min(BATCH, n - counts["accepted"])
        if offline:
            out = {"items": _sampled(check, list(s["formats"]), ask, seed=counts["asked"])}
        else:
            out = llm.generate(conn, "item_generate", {"spec": prompt_input, "n": ask})
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
            if not dry_run and not _insert(conn, tenant, it, code, difficulty):
                counts["already_in_bank"] += 1
                continue
            counts["accepted"] += 1
            accepted.append(it)
        if after_batch:
            after_batch()
    return dict(counts), dict(reasons), accepted


def _insert(conn, tenant, it, code, difficulty):
    d = it.to_dict()
    row = conn.execute(
        "insert into item (tenant_id, item_key, template, rung_code, skill_codes, signal, fmt, stem,"
        " spec, responses, tags, source, status, skill_set_code, difficulty)"
        " values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'generated','active',%s,%s)"
        " on conflict (tenant_id, item_key) do nothing returning id",
        (tenant, it.item_id, it.template, it.rung, it.skills, it.signal, it.fmt, it.stem,
         json.dumps(d["spec"]), json.dumps(d["responses"]), json.dumps(tags.derive(it)), code, difficulty),
    ).fetchone()
    return row is not None


def recheck(conn):
    """Rebuild every active generated item from its own stored spec and compare.

    The rebuild runs the same `verify.to_item` that made the row, so the audit cannot drift from
    generation: if the two ever disagree the item is named, and the count must stay zero. Claims
    with no predictor behind them (the model's own, for an operation we cannot compute) are the
    one thing not re-derived — there is nothing to re-derive them from.
    """
    bad = []
    rows = conn.execute(
        "select item_key, fmt, stem, spec, responses, rung_code, skill_codes from item"
        " where status = 'active' and source = 'generated' and fmt = any(%s)",
        (list(verify.FORMATS),),
    ).fetchall()
    for r in rows:
        sp = r["spec"]
        if not {"a", "b", "op"} <= sp.keys():
            continue  # an older row that kept only its printed text
        stored = next(x for x in r["responses"] if x["rid"] == "ans")
        rebuilt = verify.to_item(
            {"format": r["fmt"], "op": sp["op"], "a": sp["a"], "b": sp["b"],
             "answer": M.compute(sp["op"], sp["a"], sp["b"]), "stem": r["stem"],
             "missing": sp.get("missing"), "misconceptions": []},
            r["rung_code"], skills=list(r["skill_codes"]),
        )
        want = rebuilt.responses[0]
        table = M.TABLES.get(sp["op"], {})
        claims_disagree = any(
            code in table and want.misconceptions.get(code) != value
            for code, value in stored["misconceptions"].items()
        )
        if want.answer != stored["answer"] or rebuilt.item_id != r["item_key"] or claims_disagree:
            bad.append(r["item_key"])
    return bad


def flag(conn, item_key, actor, note, verdict="retire"):
    row = conn.execute("select id, tenant_id from item where item_key = %s", (item_key,)).fetchone()
    if not row:
        raise ValueError(f"no item {item_key!r}")
    conn.execute(
        "insert into item_feedback (tenant_id, item_id, actor, verdict, note) values (%s,%s,%s,%s,%s)",
        (row["tenant_id"], row["id"], actor, verdict, note),
    )
    return conn.execute("select status from item where id = %s", (row["id"],)).fetchone()["status"]


def item_from_row(r):
    """A stored row back into the Item the renderer and marker already understand."""
    return Item(r["item_key"], r["template"], r["rung_code"], list(r["skill_codes"]), r["signal"], r["fmt"],
                False, r["stem"], r["spec"], [Response(**x) for x in r["responses"]],
                working_lines=verify.FORMATS[r["fmt"]][1])


def sheet(conn, code, difficulty, n, outdir, seed=1):
    rows = conn.execute(
        "select i.*, r.band from item i join rung r on r.tenant_id = i.tenant_id and r.code = i.rung_code"
        " where i.status = 'active' and i.skill_set_code = %s and i.difficulty = %s", (code, difficulty)
    ).fetchall()
    if len(rows) < n:
        raise ValueError(f"only {len(rows)} active items for {code} {difficulty}; asked for {n}")
    chosen = random.Random(seed).sample(rows, n)
    sh = Sheet(_sheet_id(code, difficulty, seed, "bank"), chosen[0]["band"], difficulty, seed, "bank",
               [item_from_row(r) for r in chosen])
    return render_sheet(sh, outdir, week_label=f"{code} · {difficulty}")
