"""ADR 0032 — a notebook per child, rebuilt by code from every check a person makes, and read before
every read of that child.

Ring B: `child_reading_profile` is a pure function of `item_result` and `read_correction`, truncatable
at any time; nothing in it is a model's guess (rule 1). What it holds: how often the reader was right
for this child, by kind of question and by confidence; the child's own confidence floor; the kinds
routed to a person whatever the confidence; the digits the reader confuses in this child's hand; and
confirmed handwriting samples for the second reader. `apply` is the other half — the next read of the
child, changed by it (`correction_must_change_a_later_read`).
"""

import json
import re
from collections import Counter

FLOORS = (70, 80, 90)
NO_FLOOR = 95  # no level at which this child's readings were 95% right: every reading goes to a person
MIN_CHECKS = 10  # checks before a child's floor is her own rather than the default
MIN_STOOD = 6  # readings of one kind the reader stood behind before its overturn rate counts
CONFUSED = 2  # a digit read for another this many times is doubted from then on
SAMPLES = 8
KIND_WORDS = {
    "legacy_bare": "sum",
    "legacy_missing": "missing-number",
    "legacy_word": "word-problem",
    "legacy_text": "written",
}


def _norm(s):
    return re.sub(r"[\s,]", "", s or "").casefold()


def doubted(why):
    """A reading the reader did NOT stand behind. ADR 0029's hold ("read as a wrong answer; a person
    checks every…") is policy, not doubt: the reader read a value and stands behind it."""
    return bool(why) and not why.startswith("read as")


def build(rows, route_above=0.25):
    """The notebook, from every answer of one child a person has settled (`checked_rows`, oldest first)."""
    notes = {
        "checked": len(rows),
        "right": 0,
        "by_kind": {},
        "by_confidence": {},
        "gave_up": {"n": 0, "guess_right": 0},
        "floor": FLOORS[0],
        "route": [],
        "confusions": {},
        "samples": [],
    }
    at = {
        level: [0, 0] for level in FLOORS
    }  # readings the reader stood behind at or above each level: n, right
    conf, confusions = Counter(), Counter()
    for r in rows:
        truth = _norm(r["human_read"])
        right = _norm(r["model_read"]) == truth
        k = notes["by_kind"].setdefault(
            r["fmt"], {"checked": 0, "right": 0, "stood_behind": 0, "overturned": 0}
        )
        k["checked"] += 1
        if doubted(r.get("why") or ""):
            notes["gave_up"]["n"] += 1
            notes["gave_up"]["guess_right"] += bool(truth) and _norm(r.get("guess")) == truth
            continue
        notes["right"] += right
        k["right"] += right
        k["stood_behind"] += 1
        k["overturned"] += not right
        if r["answer_state"] != "written":
            continue
        c = float(r.get("confidence") or 0)
        bucket = "90+" if c >= 90 else "80-89" if c >= 80 else "70-79" if c >= 70 else "<70"
        conf[(bucket, "n")] += 1
        conf[(bucket, "right")] += right
        for level in FLOORS:
            if c >= level:
                at[level][0] += 1
                at[level][1] += right
        if not right:
            m, h = r["model_read"] or "", r["human_read"] or ""
            if m.isdigit() and h.isdigit() and len(m) == len(h):
                diff = [i for i in range(len(m)) if m[i] != h[i]]
                if len(diff) == 1:
                    confusions[f"{m[diff[0]]}>{h[diff[0]]}"] += 1
    notes["by_confidence"] = {
        b: {"n": conf[(b, "n")], "right": conf[(b, "right")]} for b in ("90+", "80-89", "70-79", "<70")
    }
    if at[FLOORS[0]][0] >= MIN_CHECKS:
        notes["floor"] = next(
            (lv for lv in FLOORS if at[lv][0] >= MIN_CHECKS and at[lv][1] / at[lv][0] >= 0.95), NO_FLOOR
        )
    notes["route"] = sorted(
        fmt
        for fmt, k in notes["by_kind"].items()
        if k["stood_behind"] >= MIN_STOOD and k["overturned"] / k["stood_behind"] > route_above
    )
    notes["confusions"] = dict(confusions)
    # The last few distinct things this child wrote, with the crop each was read from — what the child
    # wrote by a person's word, so a reading the reader got wrong is the most useful sample of all.
    seen, samples = set(), []
    for r in reversed(rows):
        text = (r["human_read"] or "").strip()
        if not text or not r.get("box") or text in seen:
            continue
        seen.add(text)
        samples.append({"capture_id": str(r["capture_id"]), "page": r["page"], "box": r["box"], "text": text})
        if len(samples) == SAMPLES:
            break
    notes["samples"] = samples[::-1]
    return notes


def apply(readings, notes, fmt_of):
    """The next read of this child, with the notebook open: a reading of a routed kind, or holding a
    digit this child has had confused twice, is flagged with the reading offered as the guess. A
    doubt the reader already had, and a blank, are left exactly as they are; nothing is overwritten."""
    if not notes:
        return readings
    route = set(notes.get("route") or [])
    confused = {
        k.split(">")[0]: k.split(">")[1] for k, n in (notes.get("confusions") or {}).items() if n >= CONFUSED
    }
    out = {}
    for slot, r in readings.items():
        text = r.get("child_answer") or ""
        if r.get("answer_state") != "written" or (r.get("why") or "") or not text:
            out[slot] = r
            continue
        fmt = fmt_of(slot)
        why = ""
        if fmt in route:
            k = notes["by_kind"][fmt]
            why = f"this child's {KIND_WORDS.get(fmt, fmt)} answers were read wrong {k['overturned']} times in {k['stood_behind']}; a person checks them"
        elif d := next((d for d in text if d in confused), None):
            why = f"this child's {d} has been read for a {confused[d]} before"
        out[slot] = (
            {**r, "child_answer": "", "answer_state": "illegible", "why": why, "guess": text} if why else r
        )
    return out


# ---------------------------------------------------------------- the rows, and the table


def checked_rows(conn, child_id=None):
    """Every answer a person has settled, oldest first: typed (the latest reading a person gave) or
    signed off without a change (the reader's reading, confirmed). A judgement is not a reading, so
    an answer settled by Right/Wrong alone is not here."""
    return conn.execute(
        "with latest as (select distinct on (rc.item_result_id) rc.item_result_id, rc.human_read, rc.judged"
        "               from read_correction rc order by rc.item_result_id, rc.created_at desc)"
        " select si.child_id, i.fmt, c.id as capture_id, c.path, c.pages as file_pages,"
        "        coalesce((i.spec ->> 'page')::int, 1) as page, i.item_key, t.batch_id as paper, r.id as item_result_id,"
        "        coalesce(r.raw_read::jsonb ->> 'child_answer', '') as model_read,"
        "        coalesce(l.human_read, r.raw_read::jsonb ->> 'child_answer', '') as human_read,"
        "        coalesce((r.raw_read::jsonb ->> 'confidence')::float, 0) as confidence,"
        "        coalesce(r.raw_read::jsonb ->> 'why', '') as why,"
        "        coalesce(r.raw_read::jsonb ->> 'answer_state', '') as answer_state,"
        "        coalesce(r.raw_read::jsonb ->> 'guess', '') as guess,"
        "        r.raw_read::jsonb -> 'box' as box, (l.item_result_id is not null) as corrected"
        " from item_result r join item i on i.id = r.item_id join capture c on c.id = r.capture_id"
        " join sheet_instance si on si.id = c.sheet_instance_id join sheet_template t on t.id = si.sheet_template_id"
        " left join latest l on l.item_result_id = r.id"
        " where c.superseded_by is null and l.judged is null and (l.item_result_id is not null or r.state = 'confirmed')"
        "   and (%s::uuid is null or si.child_id = %s::uuid)"
        " order by c.created_at, i.item_key",
        (child_id, child_id),
    ).fetchall()


def signed_off(conn):
    """The answers people confirmed without changing, in the shape `read_eval.gold_sheets` reads."""
    return [r for r in checked_rows(conn) if not r["corrected"] and r["answer_state"] in ("written", "blank")]


def rebuild(conn, child_ids=None):
    """Every checked child's notebook, written; returns how many. The caller commits."""
    row = conn.execute("select value from threshold where key = 'read.route_above_overturn'").fetchone()
    route_above = float(row["value"]) if row else 0.25
    by_child = {}
    for r in checked_rows(conn):
        by_child.setdefault(str(r["child_id"]), []).append(r)
    wanted = {str(c) for c in child_ids} if child_ids else set(by_child)
    for child, rows in by_child.items():
        if child not in wanted:
            continue
        conn.execute(
            "insert into child_reading_profile (tenant_id, child_id, notes)"
            " select tenant_id, id, %s from child where id = %s"
            " on conflict (tenant_id, child_id) do update set notes = excluded.notes, updated_at = now()",
            (json.dumps(build(rows, route_above)), child),
        )
    return len(wanted & set(by_child))


def for_child(conn, child_id):
    row = conn.execute("select notes from child_reading_profile where child_id = %s", (child_id,)).fetchone()
    return (json.loads(row["notes"]) if isinstance(row["notes"], str) else row["notes"]) if row else {}


def lines(conn, child_ids=None, actor="engine-cli"):
    """One line per notebook, for a person: the child by name (read through pii, logged), and what it holds."""
    rows = conn.execute(
        "select p.first_name, c.section, cp.notes from child_reading_profile cp join child c on c.id = cp.child_id,"
        " lateral pii.read_child(c.id, %s) p where (%s::uuid[] is null or cp.child_id = any(%s::uuid[]))"
        " order by c.section, p.first_name",
        (actor, child_ids, child_ids),
    ).fetchall()
    out = []
    for r in rows:
        n = json.loads(r["notes"]) if isinstance(r["notes"], str) else r["notes"]
        stood = sum(k["stood_behind"] for k in n["by_kind"].values())
        bits = [
            f"{n['checked']} checked",
            f"reader right {n['right']} of {stood} it stood behind",
            f"floor {n['floor']}",
        ]
        if n["route"]:
            bits.append("routes: " + ", ".join(KIND_WORDS.get(f, f) for f in n["route"]))
        if n["confusions"]:
            bits.append(
                "confuses "
                + ", ".join(
                    f"{k} ×{v}" for k, v in sorted(n["confusions"].items(), key=lambda kv: -kv[1])[:3]
                )
            )
        bits.append(f"{len(n['samples'])} samples")
        out.append(f"{r['first_name']} ({r['section']}): " + " · ".join(bits))
    return out
