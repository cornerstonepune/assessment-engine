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
from engine.assess import misconceptions as M
from engine.assess import tags, verify
from engine.assess.items import Item, Response
from engine.assess.pick import Sheet, _sheet_id
from engine.assess.render import render_sheet

BATCH = 20  # the free tier timed out on 40 (STATE.md)


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


def fill(conn, code, difficulty, n, dry_run=False):
    prompt_input, s, check = spec(conn, code, difficulty)
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    counts = Counter(asked=0, returned=0, accepted=0, rejected=0, duplicate=0, already_in_bank=0)
    reasons, seen, accepted = Counter(), set(), []
    while counts["accepted"] < n and counts["asked"] < 3 * n:
        ask = min(BATCH, n - counts["accepted"])
        out = llm.generate(conn, "item_generate", {"spec": prompt_input, "n": ask})
        counts["asked"] += ask
        for c in out["items"]:
            counts["returned"] += 1
            key = (c.get("op"), c.get("a"), c.get("b"), c.get("format"))
            if key in seen:
                counts["duplicate"] += 1
                continue
            seen.add(key)
            probs = verify.problems(c, check)
            if probs:
                counts["rejected"] += 1
                reasons.update(p.split(" ")[0] for p in probs)
                continue
            it = verify.to_item(c, s["rung_code"], skills=list(s["skill_codes"]))
            if not dry_run and not _insert(conn, tenant, it, code, difficulty):
                counts["already_in_bank"] += 1
                continue
            counts["accepted"] += 1
            accepted.append(it)
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
    """Recompute every active generated item's answer and predictor table from its spec.
    Returns the item_keys that disagree — the number that must stay zero."""
    bad = []
    rows = conn.execute(
        "select item_key, fmt, spec, responses from item where status = 'active' and source = 'generated'"
        " and fmt = any(%s)", (list(verify.FORMATS),)
    ).fetchall()
    for r in rows:
        sp = r["spec"]
        ans = next(x for x in r["responses"] if x["rid"] == "ans")
        if not {"a", "b", "op"} <= sp.keys():
            continue  # a deterministic-generator missing_number carries only its text
        correct = M.compute(sp["op"], sp["a"], sp["b"])
        expect = {"a": sp["a"], "b": sp["b"], "answer": correct}[sp.get("missing", "answer")]
        truth = M.predict(sp["op"], sp["a"], sp["b"])
        claimed = ans["misconceptions"]
        wrong_key = ans["answer"] != str(expect)
        wrong_claim = any(v == expect for v in claimed.values()) or any(
            code in truth and truth[code] != v for code, v in claimed.items())
        if wrong_key or wrong_claim:
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


def _item_from_row(r):
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
               [_item_from_row(r) for r in chosen])
    return render_sheet(sh, outdir, week_label=f"{code} · {difficulty}")
