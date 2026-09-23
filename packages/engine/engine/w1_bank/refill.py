"""Step 8i: the bank brought to its levels' rules — retire what no longer fits, fill what is short.

A level's rule changed (step 8h), so some of its stored questions are now outside it: they are retired
through the same path a person's flag takes (`item_feedback`, verdict retire — the question stays, and
says why), never deleted. Then every level is topped up to its target: a level made of taxonomy cases
case by case, each case to its fair share of the target and the rest spread where numbers remain; any
other level through the generator it always used. Papers already printed point at their own questions
and never change; `engine library build` then replaces the worksheets that held a retired question.
"""

import math
import random
from collections import Counter

from engine.assess import draw, taxonomy
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
    matches = cases.matches(conn, check["cases"])
    missing = sorted(set(check["cases"]) - set(matches))
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


def _held_per_case(conn, code, difficulty, check, matches):
    rows = conn.execute(
        "select fmt, tags from item where status = 'active' and skill_set_code = %s and difficulty = %s",
        (code, difficulty),
    ).fetchall()
    # A question that is two cases at once (no exchange, and a zero inside) counts for both: crediting
    # only the first listed made the later cases look short and the level overfilled.
    have = Counter(
        c for r in rows for c in check["cases"] if taxonomy.matches(matches[c], r["fmt"], r["tags"])
    )
    return have, len(rows)


def top_up(conn, code, difficulty, target, rng=None):
    """Fill one level to `target`. Returns how many questions it added."""
    _, _, check = spec(conn, code, difficulty)
    if check.get("cases"):
        matches = cases.matches(conn, check["cases"])
        have, total = _held_per_case(conn, code, difficulty, check, matches)
        share = math.ceil(target / len(check["cases"]))
        quotas = {c: max(0, share - have[c]) for c in check["cases"]}
        want = max(0, target - total)
        if not want and not any(quotas.values()):
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
    """Relabel, retire what no longer fits, then top every level up to its target. The caller commits.

    Relabelling comes first: whether a question still fits its level is read from its tags, and tags
    stored before the measurements improved would retire a question for a reading it no longer has."""
    labels.relabel(conn)
    retired = retire_outside(conn)
    added = Counter()
    for r in inventory.coverage(conn):
        added[(r["code"], r["difficulty"])] = top_up(conn, r["code"], r["difficulty"], r["target"], rng)
        if after_level:
            after_level(r["code"], r["difficulty"], added[(r["code"], r["difficulty"])])
    return retired, added
