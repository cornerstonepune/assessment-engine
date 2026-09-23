"""W1 — what the bank holds: each level's coverage against a class's need, an independent recheck of
every stored question, the wrong answers no named mistake explains, a staff member's flag, and a
sample sheet a person can hold. `bank.py` makes questions; this looks at the ones already made."""

import random

from engine.assess import misconceptions as M
from engine.assess import verify
from engine.assess.items import Item, Response
from engine.assess.layout import WORKING_LINES
from engine.assess.pick import Sheet, _sheet_id
from engine.assess.render import render_sheet
from engine.w1_bank import cases


def _class_need(conn):
    """How many questions one class needs from one unit in one week: every child's sheet plus the
    spares, drawn without replacement (`assemble.for_week`). All three numbers are config rows."""

    def cfg(key, default):
        row = conn.execute("select value from config where key = %s", (key,)).fetchone()
        return int(default if row is None else row["value"])

    return (cfg("bank.class_size", 16) + cfg("assemble.spares_per_difficulty", 2)) * cfg(
        "assemble.items_per_sheet", 12
    )


def coverage(conn):
    """Active item counts for every skill_set x difficulty — the 16x4 unit grid W1 gate 2 fills.
    Every combination appears, zero cells included, so a short unit is a number, not a guess.

    `target` is what a class needs in one week — `(class_size + spares) x items_per_sheet`, every
    term a config row (ADR 0016) — unless the band's own row sets `min_items`, which it does when its
    whole number range holds fewer questions than that ("adds within 10" has about 40 pairs in
    total). Both are rows, so the gate stays checkable without a code exception, and a school with a
    different class register moves it by changing one number."""
    need = _class_need(conn)
    # every level a skill in use defines — a skill may have fewer than four (1-digit − 1-digit has no Hard)
    return conn.execute(
        "select s.code, d.difficulty, coalesce(i.n, 0) as n,"
        " coalesce((s.difficulty -> d.difficulty ->> 'min_items')::int, " + str(need) + ") as target"
        " from skill_set s"
        " cross join (values ('Easy',1),('Medium',2),('Hard',3),('Advance',4)) as d(difficulty, ord)"
        " left join ("
        "   select skill_set_code, difficulty, count(*) as n from item"
        "   where status = 'active' group by skill_set_code, difficulty"
        " ) i on i.skill_set_code = s.code and i.difficulty = d.difficulty"
        " where s.status <> 'retired' and s.difficulty ? d.difficulty"
        " order by s.code, d.ord"
    ).fetchall()


def recheck(conn):
    """Rebuild every active generated item from its own stored spec and compare.

    The rebuild runs the same `verify.to_item` that made the row, so the audit cannot drift from
    generation: if the two ever disagree the item is named, and the count must stay zero. Claims
    with no predictor behind them (the model's own, for an operation we cannot compute) are the
    one thing not re-derived — there is nothing to re-derive them from.
    """
    bad = [r["item_key"] for r in cases.outside_their_level(conn)]

    rows = conn.execute(
        "select item_key, fmt, stem, spec, responses, rung_code, skill_codes, generator from item"
        " where status = 'active' and source = 'generated' and fmt = any(%s)",
        (list(verify.FORMATS),),
    ).fetchall()
    for r in rows:
        sp = r["spec"]
        if not {"a", "b", "op"} <= sp.keys():
            continue  # an older row that kept only its printed text
        if set(sp) - {"a", "b", "op", "layout", "missing", "text"}:
            continue  # made by a generator with more than numbers (a story's table): not `to_item`'s to rebuild
        stored = next(x for x in r["responses"] if x["rid"] == "ans")
        rebuilt = verify.to_item(
            {
                "format": r["fmt"],
                "op": sp["op"],
                "a": sp["a"],
                "b": sp["b"],
                "answer": M.compute(sp["op"], sp["a"], sp["b"]),
                "stem": r["stem"],
                "missing": sp.get("missing"),
                "misconceptions": [],
            },
            r["rung_code"],
            skills=list(r["skill_codes"]),
        )
        want = rebuilt.responses[0]
        table = M.TABLES.get(sp["op"], {})
        claims_disagree = any(
            code in table and want.misconceptions.get(code) != value
            for code, value in stored["misconceptions"].items()
        )
        # A person's rewording keeps the numbers and so the rebuilt key; its own key names the wording.
        renamed = rebuilt.item_id != r["item_key"] and r["generator"] != "correction"
        if want.answer != stored["answer"] or renamed or claims_disagree:
            bad.append(r["item_key"])
    return bad


def unclassified(conn, limit=50):
    """The wrong answers no named mistake explains, commonest first (ADR 0012).

    `assess/mark.py` already tags these `unclassified`; nothing has ever gathered them up. For
    arithmetic they are a long tail. For every other kind of question they are the *only* way the
    mistake vocabulary can grow — a person names a recurring cluster once, and from then on it is
    predicted like any other. Empty until W3 reads real papers, which is the point: the
    instrument exists before the data, not after someone wishes they had it."""
    return conn.execute(
        # The legacy reader stores its whole JSON reply in raw_read; what a person needs to see
        # is the number the child wrote, so pull child_answer out when it is there.
        "select i.skill_set_code, i.difficulty, i.rung_code, i.item_key, i.stem, i.spec,"
        # Two shapes reach raw_read: the sheet marker writes the digits a child wrote ("8113"),
        # the legacy reader writes its whole JSON reply. Show the answer either way.
        "       case when left(btrim(r.raw_read), 1) = '{'"
        "            then coalesce(nullif(r.raw_read::jsonb->>'child_answer', ''), r.raw_read)"
        "            else r.raw_read end as wrote,"
        "       count(distinct r.capture_id) as children"
        " from item_result r"
        " join item i on i.id = r.item_id"
        " join capture c on c.id = r.capture_id"
        " where r.status = 'wrong' and cardinality(r.misconception_codes) = 0"
        "   and r.raw_read is not null and r.state <> 'rejected'"
        # a superseded capture is the same paper read twice; counting it twice would invent
        # a pattern out of one child (the double-import fault, STATE.md N3)
        "   and c.superseded_by is null"
        " group by 1,2,3,4,5,6,7 order by count(distinct r.capture_id) desc, i.item_key limit %s",
        (limit,),
    ).fetchall()


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
    return Item(
        r["item_key"],
        r["template"],
        r["rung_code"],
        list(r["skill_codes"]),
        r["signal"],
        r["fmt"],
        False,
        r["stem"],
        r["spec"],
        [Response(**x) for x in r["responses"]],
        working_lines=WORKING_LINES[r["fmt"]],
    )


def sheet(conn, code, difficulty, n, outdir, seed=1, pw=None):
    rows = conn.execute(
        "select i.*, r.band from item i join rung r on r.tenant_id = i.tenant_id and r.code = i.rung_code"
        " where i.status = 'active' and i.skill_set_code = %s and i.difficulty = %s",
        (code, difficulty),
    ).fetchall()
    if len(rows) < n:
        raise ValueError(f"only {len(rows)} active items for {code} {difficulty}; asked for {n}")
    chosen = random.Random(seed).sample(rows, n)
    name = conn.execute("select name from skill_set where code = %s", (code,)).fetchone()["name"]
    sh = Sheet(
        _sheet_id(code, difficulty, seed, "bank"),
        chosen[0]["band"],
        difficulty,
        seed,
        "bank",
        [item_from_row(r) for r in chosen],
        title=name,
    )
    return render_sheet(sh, outdir, week_label=f"{code} · {difficulty}", pw=pw)
