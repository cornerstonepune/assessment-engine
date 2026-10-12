"""Step 8i: the bank brought to its levels' rules — retire what no longer fits, fill what is short.

A level's rule changed (step 8h), so some of its stored questions are now outside it: they are retired
through the same path a person's flag takes (`item_feedback`, verdict retire — the question stays, and
says why), never deleted. Then every level is topped up to its target: a level made of taxonomy cases
case by case, each case to its fair share of the target and the rest spread where numbers remain; any
other level through the generator it always used. Papers already printed point at their own questions
and never change; `engine library build` then replaces the worksheets that held a retired question.
"""

import json
import math
import random
from collections import Counter

from engine.assess import draw, taxonomy
from engine.assess import draw_case as K
from engine.core import db
from engine.w1_bank import bank, cases, inventory, labels
from engine.w1_bank.spec import read as spec

ACTOR = "engine (step 8i)"


def fill_cases(conn, code, difficulty, n, dry_run=False, after_batch=None, rng=None, quotas=None):
    """A level that lists taxonomy cases (step 8f), filled evenly from them: every question drawn is,
    as measured, one of its cases (`assess/draw.py`). Questions the bank already holds anywhere are
    not drawn again — except on a dry run, which proves the level can be made, not that it is new (a
    scenario asks the smallest levels for more than they have left). `quotas` says what each case is
    still short of, and `n` is then what the level as a whole still needs (`draw.level`). Returns
    (counts, {case: accepted}, items)."""
    _, s, check = spec(conn, code, difficulty)
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    held = (
        set()
        if dry_run
        else {
            r["item_key"] for r in conn.execute("select item_key from item where tenant_id = %s", (tenant,))
        }
    )
    matches = cases.for_level(conn, check)
    missing = sorted({*check["cases"], *check.get("methods", [])} - set(matches))
    if missing:
        raise ValueError(f"{code} {difficulty} names cases that are not rows: {', '.join(missing)}")
    known, rules, vocab = bank._known_codes(conn), labels.rules(conn), labels.vocabulary(conn)
    all_cases = cases.matches(conn)
    drawn = draw.level(rng or random.Random(), check, matches, s["rung_code"], n, seen=held, quotas=quotas)
    counts = Counter(asked=n, drawn=len(drawn), accepted=0, already_in_bank=0, unnamed_distractor_dropped=0)
    per_case, accepted = Counter(), []
    for case_code, it in drawn:
        counts["unnamed_distractor_dropped"] += bank._strip_unnamed(it, known)
        charged = labels.label_item(it, s["skill_codes"], rules, vocab)
        prov = {"skill_set_version": s["version"], "generator": f"case:{case_code}"}
        if not dry_run and not bank._insert(
            conn, tenant, it, code, difficulty, s["eval_type"], prov, charged, all_cases
        ):
            counts["already_in_bank"] += 1
            continue
        counts["accepted"] += 1
        per_case[case_code] += 1
        accepted.append(it)
    if after_batch:
        after_batch()
    return dict(counts), dict(per_case), accepted


def retire_outside(conn, actor=ACTOR):
    """Retire every active question its level's rule no longer holds, or keyed by a rule its kind has since
    corrected; returns how many, by level."""
    out = Counter()
    for r in cases.outside_their_level(conn):
        conn.execute(
            "insert into item_feedback (tenant_id, item_id, actor, verdict, note) values (%s,%s,%s,'retire',%s)",
            (r["tenant_id"], r["id"], actor, "no longer what its level holds: " + "; ".join(r["why"])),
        )
        out[(r["skill_set_code"], r["difficulty"])] += 1
    return out


def fairness_rule(conn):
    """The row that says when a choice is answered by ticking one place (`bank.choice_answer_max_share`)."""
    row = conn.execute("select value from config where key = 'bank.choice_answer_max_share'").fetchone()
    if not row:
        raise ValueError("the config row bank.choice_answer_max_share is missing (engine load)")
    return row["value"]


def _drawn_now(conn, code, difficulty, n):
    """`n` questions as the level draws them today, stored nowhere: a level of cases through its cases, any other
    through its own generator. A level the model writes is not drawn: none of those is answered by ticking."""
    _, _, check = spec(conn, code, difficulty)
    if check.get("cases"):
        return fill_cases(conn, code, difficulty, n, dry_run=True)[2]
    from engine.assess import bands

    if check.get("format") in bands.NATIVE_GENERATORS:
        return bank.fill_native(conn, code, difficulty, n, dry_run=True)[1]
    return []


def redraw_unfair(conn, actor=ACTOR):
    """Retire a group of questions answered by ticking whose right answers sit in one place, so the top-up draws it
    again — when the level, as it draws today, places them fairly: the group was made by a rule since corrected
    (REASON.EXPLAIN's claims, all true at one level and all false at another until 2026-09-29). A level whose own
    design fixes the answer draws no fairer, and waits for a person (`engine audit`). Returns how many, by level."""
    rule = fairness_rule(conn)
    out = Counter()
    for (code, difficulty, fmt, rid), _, _, _ in inventory.unfair(inventory.tick_places(conn), rule):
        out[(code, difficulty)] += 0
        now = Counter(
            r.options.index(r.answer)
            for it in _drawn_now(conn, code, difficulty, 3 * rule["min_questions"])
            if it.fmt == fmt
            for r in it.responses
            if r.rid == rid and r.kind == "tick" and r.options and r.answer in r.options
        )
        if sum(now.values()) < rule["min_questions"] or inventory.unfair({"now": now}, rule):
            continue  # too few drawn to tell, or the level itself places them unfairly
        rows = conn.execute(
            "select id, tenant_id from item where status = 'active' and source = 'generated' and skill_set_code = %s"
            " and difficulty = %s and fmt = %s and responses @> %s",
            (code, difficulty, fmt, json.dumps([{"rid": rid, "kind": "tick"}])),
        ).fetchall()
        for r in rows:
            conn.execute(
                "insert into item_feedback (tenant_id, item_id, actor, verdict, note)"
                " values (%s,%s,%s,'retire',%s)",
                (r["tenant_id"], r["id"], actor, f"its right answers sat in one place ({rid}): drawn again"),
            )
        out[(code, difficulty)] += len(rows)
    return out


def _held_per_way(conn, code, difficulty, check, matches):
    """{case: what the level holds of it in each way it is printed in} and how many questions it holds. A level that
    lists written methods holds each case's share in every one of them (ADR 0055), so a level full of an older way's
    questions is still short of a new method's (goals/md3d-division-methods.yaml)."""
    rows = conn.execute(
        "select fmt, tags from item where status = 'active' and skill_set_code = %s and difficulty = %s",
        (code, difficulty),
    ).fetchall()
    methods = [matches[m] for m in check.get("methods", [])]
    # A question that is two cases at once (no exchange, and a zero inside) counts for both: crediting
    # only the first listed made the later cases look short and the level overfilled.
    have = {
        c: [
            sum(taxonomy.matches(way, r["fmt"], r["tags"]) for r in rows)
            for way in K.ways(matches[c], methods)
        ]
        for c in check["cases"]
    }
    return have, len(rows)


def top_up(conn, code, difficulty, target, rng=None):
    """Fill one level to `target`, each case to its share in every way the level prints it. Returns how many questions
    it added."""
    _, _, check = spec(conn, code, difficulty)
    if check.get("cases"):
        matches = cases.for_level(conn, check)
        have, total = _held_per_way(conn, code, difficulty, check, matches)
        share = math.ceil(target / len(check["cases"]))
        quotas = {
            c: [max(0, k - h) for k, h in zip(draw.split(share, len(held)), held, strict=True)]
            for c, held in have.items()
        }
        want = max(0, target - total)
        if not want and not any(map(sum, quotas.values())):
            return 0
        counts, _, _ = fill_cases(conn, code, difficulty, want, rng=rng, quotas=quotas)
        return counts["accepted"]
    total = conn.execute(
        "select count(*) as n from item where status = 'active' and skill_set_code = %s and difficulty = %s",
        (code, difficulty),
    ).fetchone()["n"]
    if total >= target:
        return 0
    from engine.assess import bands

    if check.get("format") in bands.NATIVE_GENERATORS:
        counts, _ = bank.fill_native(conn, code, difficulty, target - total)
    else:
        counts, _, _ = bank.fill(conn, code, difficulty, target - total, offline=True)
    return counts["accepted"]


def refill(conn, rng=None, after_level=None):
    """Relabel, retire what no longer fits and the groups a corrected rule left answered in one place, then top every
    level up to its target. The caller commits.

    Relabelling comes first: whether a question still fits its level is read from its tags, and tags
    stored before the measurements improved would retire a question for a reading it no longer has."""
    labels.relabel(conn)
    retired = retire_outside(conn)
    redrawn = redraw_unfair(conn)
    added = Counter()
    for r in inventory.coverage(conn):
        added[(r["code"], r["difficulty"])] = top_up(conn, r["code"], r["difficulty"], r["target"], rng)
        if after_level:
            after_level(r["code"], r["difficulty"], added[(r["code"], r["difficulty"])])
    return retired, redrawn, added
