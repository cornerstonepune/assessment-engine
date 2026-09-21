"""Every question in the bank on a numbered worksheet (ADR 0026).

Nimish, 2026-09-21: "these questions should already be converted into the worksheets … at least 10
worksheets each … mapped to worksheet IDs". A worksheet is twelve questions of one skill at one
level — a `sheet_template` row with source 'library' and a code such as R5-H07. Each level gets
max(10, ⌈N ÷ 12⌉) worksheets, so every active question is on one; where a level holds too few
questions for ten (the Grade 1 levels, ADR 0011), the deal goes round again and every question is
used an equal number of times. Each worksheet holds the level's kinds in fair shares and prints
them grouped, in the skill's own order of kinds.

A worksheet is never edited once made — a child's printed paper points at it. When a question on it
leaves the bank (removed, or reworded into a new question) the worksheet is retired, and `build`
deals a new one, with a new code, from what that left uncovered. A small level whose worksheets
share questions cannot always be patched evenly; then every worksheet of that level is retired and
the level is dealt afresh.
"""

import hashlib
import math
from collections import Counter
from pathlib import Path

from engine import db
from engine.assess.pick import Sheet
from engine.assess.render import render_sheet
from engine.bank import item_from_row

MIN_PER_LEVEL = 10
LEVEL_LETTER = {"Easy": "E", "Medium": "M", "Hard": "H", "Advance": "A"}
PDF_DIR = db.REPO_ROOT / "data" / "worksheets"


def per_sheet(conn):
    row = conn.execute("select value from config where key = 'assemble.items_per_sheet'").fetchone()
    return int(row["value"]) if row else 12


def worksheets_needed(n_questions, n, minimum=MIN_PER_LEVEL):
    """How many worksheets a level of `n_questions` gets — none if it cannot fill one."""
    return 0 if n_questions < n else max(minimum, math.ceil(n_questions / n))


def _kind_rank(kind_order):
    rank = {k: i for i, k in enumerate(kind_order)}
    return lambda q: rank.get(q["fmt"], len(rank))


def _shares(sizes, n, count):
    """{kind: [how many of that kind on each worksheet]} — every worksheet `n`, every kind its share
    of the `n × count` places in proportion to how many questions of it the level holds."""
    total, held = n * count, sum(sizes.values())
    exact = {k: total * v / held for k, v in sizes.items()}
    places = {k: math.floor(x) for k, x in exact.items()}
    for k in sorted(exact, key=lambda k: (places[k] - exact[k], k))[: total - sum(places.values())]:
        places[k] += 1
    share = {k: [places[k] // count] * count for k in sizes}
    # What is left over after the even part is dealt round the worksheets in turn, one kind after
    # another, so each worksheet gets the same number of extras and no kind two on one worksheet.
    turn = 0
    for k in sizes:
        for _ in range(places[k] % count):
            share[k][turn % count] += 1
            turn += 1
    return share


def _fill(questions, wants, key):
    """Each worksheet's questions of one kind: dealt in laps, a fresh order each lap, so every
    question is used the same number of times give or take one; a question already on the worksheet
    being filled waits for the next worksheet rather than being skipped for good."""
    if max(wants, default=0) > len(questions):
        raise ValueError(f"a worksheet needs {max(wants)} of a kind that has {len(questions)} questions")
    lap = 0
    stream = iter(sorted(questions, key=lambda q: key(lap, q)))
    waiting, out = [], []
    for want in wants:
        chosen, ids = [], set()
        for q in list(waiting):
            if len(chosen) < want and q["id"] not in ids:
                chosen.append(q)
                ids.add(q["id"])
                waiting.remove(q)
        while len(chosen) < want:
            q = next(stream, None)
            if q is None:
                lap += 1
                stream = iter(sorted(questions, key=lambda q: key(lap, q)))
            elif q["id"] in ids:
                waiting.append(q)
            else:
                chosen.append(q)
                ids.add(q["id"])
        out.append(chosen)
    return out


def deal(questions, n, kind_order, count):
    """Deal questions onto `count` worksheets of `n`. Pure, and the same deal for the same questions.

    First each worksheet's share of each kind is fixed, so every worksheet holds the level's kinds
    in fair shares; then each kind's questions are dealt into those places in laps. Each worksheet
    comes back grouped by kind, in `kind_order`, as it will print.
    """
    kind = _kind_rank(kind_order)
    by_kind = {}
    for q in sorted(questions, key=lambda q: (kind(q), q["fmt"], q["item_key"])):
        by_kind.setdefault(q["fmt"], []).append(q)
    share = _shares({k: len(v) for k, v in by_kind.items()}, n, count)
    sheets = [[] for _ in range(count)]
    for k, qs in by_kind.items():
        salt = lambda lap, q: hashlib.sha1(f"{lap}|{q['item_key']}".encode()).hexdigest()  # noqa: E731
        for i, part in enumerate(_fill(qs, share[k], salt)):
            sheets[i] += part
    return [sorted(s, key=lambda q: (kind(q), q["item_key"])) for s in sheets]


def _levels(conn, only=None):
    """Every skill at every level — or just `only`, a (skill set, level) pair."""
    code, difficulty = only or (None, None)
    return conn.execute(
        "select s.code, s.rung_code, s.formats, r.band, d.key as difficulty from skill_set s"
        " join rung r on r.tenant_id = s.tenant_id and r.code = s.rung_code, jsonb_object_keys(s.difficulty) d(key)"
        " where (%s::text is null or s.code = %s) and (%s::text is null or d.key = %s)"
        " order by r.ladder_order nulls last, s.code, d.key",
        (code, code, difficulty, difficulty),
    ).fetchall()


def _plan_level(conn, lv, n):
    """(worksheets to retire, question lists to make) for one skill at one level."""
    questions = conn.execute(
        "select id, item_key, fmt from item where status = 'active' and source = 'generated'"
        " and skill_set_code = %s and difficulty = %s order by item_key",
        (lv["code"], lv["difficulty"]),
    ).fetchall()
    sheets = conn.execute(
        "select id, code, item_ids from sheet_template where source = 'library' and retired_at is null"
        " and skill_set_code = %s and difficulty = %s order by variant",
        (lv["code"], lv["difficulty"]),
    ).fetchall()
    active = {q["id"] for q in questions}
    keep = [s for s in sheets if set(s["item_ids"]) <= active]
    retire = [s for s in sheets if s not in keep]
    want = worksheets_needed(len(questions), n)
    if not want:
        return retire, []
    kinds = list(lv["formats"])
    if not keep:
        return retire, deal(questions, n, kinds, want)
    used = Counter(i for s in keep for i in s["item_ids"])
    uncovered = [q for q in questions if q["id"] not in used]
    count = max(want - len(keep), math.ceil(len(uncovered) / n))
    if not count:
        return retire, []
    # What a retired worksheet or a new question left uncovered goes first; the rest of the new
    # worksheets is filled with the questions used least so far.
    fill = sorted((q for q in questions if q["id"] in used), key=lambda q: (used[q["id"]], q["item_key"]))
    new = deal(uncovered + fill[: max(0, count * n - len(uncovered))], n, kinds, count)
    # The smallest change is taken only if it keeps every rule. A small level whose worksheets share
    # questions cannot always be patched evenly — then the level is dealt afresh, its worksheets all
    # retired (never edited) and a whole new set made.
    after = used + Counter(q["id"] for s in new for q in s)
    alike = {frozenset(s["item_ids"]) for s in keep} | {frozenset(q["id"] for q in s) for s in new}
    if max(after[i] for i in active) - min(after[i] for i in active) <= 1 and len(alike) == len(keep) + len(
        new
    ):
        return retire, new
    return sheets, deal(questions, n, kinds, want)


def build(conn, dry_run=False, only=None):
    """Make every level ready — or just `only`, a (skill set, level) pair: retire worksheets holding
    a question no longer in the bank and deal new ones until every active question is on one and
    every level has its worksheets. Running it again changes nothing."""
    n = per_sheet(conn)
    tenant = conn.execute("select id from tenant where slug = %s", (db.tenant_slug(),)).fetchone()["id"]
    made = retired = 0
    for lv in _levels(conn, only):
        retire, make = _plan_level(conn, lv, n)
        made, retired = made + len(make), retired + len(retire)
        if dry_run:
            continue
        for s in retire:
            conn.execute("update sheet_template set retired_at = now() where id = %s", (s["id"],))
        last = conn.execute(
            "select coalesce(max(variant), 0) as v from sheet_template where source = 'library'"
            " and skill_set_code = %s and difficulty = %s",
            (lv["code"], lv["difficulty"]),
        ).fetchone()["v"]
        for k, qs in enumerate(make, last + 1):
            conn.execute(
                "insert into sheet_template (tenant_id, band, variant, item_ids, skill_set_code, difficulty,"
                " source, code) values (%s, %s, %s, %s, %s, %s, 'library', %s)",
                (tenant, lv["band"], k, [q["id"] for q in qs], lv["code"], lv["difficulty"],
                 f"{lv['rung_code']}-{LEVEL_LETTER[lv['difficulty']]}{k:02d}"),
            )  # fmt: skip
    return {"made": made, "retired": retired}


def check(conn):
    """(levels checked, {level: [problems]}): every rule a worksheet and a level must hold, read back
    from the rows independently of `build`. A level with no entry is ready."""
    n = per_sheet(conn)
    found = {}
    levels = _levels(conn)
    for lv in levels:
        where = (lv["code"], lv["difficulty"])
        questions = {
            r["id"]: r
            for r in conn.execute(
                "select id, fmt from item where status = 'active' and source = 'generated'"
                " and skill_set_code = %s and difficulty = %s",
                where,
            ).fetchall()
        }
        sheets = conn.execute(
            "select code, item_ids from sheet_template where source = 'library' and retired_at is null"
            " and skill_set_code = %s and difficulty = %s",
            where,
        ).fetchall()
        problems = []
        need = worksheets_needed(len(questions), n)
        if len(sheets) < need:
            problems.append(f"{len(sheets)} worksheets, needs {need}")
        used = Counter(i for s in sheets for i in s["item_ids"])
        if missing := [i for i in questions if i not in used]:
            problems.append(f"{len(missing)} questions on no worksheet")
        elif used and max(used[i] for i in questions) - min(used[i] for i in questions) > 1:
            problems.append(f"questions used unevenly ({min(used.values())}–{max(used.values())} times)")
        if len({frozenset(s["item_ids"]) for s in sheets}) != len(sheets):
            problems.append("two worksheets hold the same questions")
        share = Counter(q["fmt"] for q in questions.values())
        for s in sheets:
            ids = s["item_ids"]
            if len(ids) != n or len(set(ids)) != n:
                problems.append(f"{s['code']} holds {len(set(ids))} different questions, not {n}")
            if stray := [i for i in ids if i not in questions]:
                problems.append(f"{s['code']} holds {len(stray)} questions not active at this level")
                continue
            got = Counter(questions[i]["fmt"] for i in ids)
            for fmt, total in share.items():
                fair = n * total / len(questions)
                if not math.floor(fair) - 1 <= got[fmt] <= math.ceil(fair) + 1:
                    problems.append(f"{s['code']} holds {got[fmt]} {fmt}, fair share {fair:.1f}")
        if problems:
            found[f"{lv['code']} {lv['difficulty']}"] = problems
    return len(levels), found


def pdf(conn, code):
    """The worksheet as it prints — rendered the first time it is asked for, then served from disk.
    Its code stands where a child's paper has its QR."""
    path = PDF_DIR / f"{code}.pdf"
    if path.exists():
        return path
    t = conn.execute(
        "select t.id, t.band, t.difficulty, t.variant, t.item_ids, s.name from sheet_template t"
        " join skill_set s on s.tenant_id = t.tenant_id and s.code = t.skill_set_code"
        " where t.source = 'library' and t.code = %s",
        (code,),
    ).fetchone()
    if not t:
        raise LookupError(f"no worksheet {code}")
    rows = {
        r["id"]: r for r in conn.execute("select * from item where id = any(%s)", (t["item_ids"],)).fetchall()
    }
    sheet = Sheet(code, t["band"], t["difficulty"], t["variant"], "library",
                  [item_from_row(rows[i]) for i in t["item_ids"]], title=t["name"])  # fmt: skip
    render_sheet(sheet, PDF_DIR, week_label=f"Worksheet {code}")
    return Path(path)
