"""A child's next paper, chosen from the child's own graph (goal s11-focus-paper).

`plan` reads the child's graph, picks the areas the child lags in (`assess.focus`) and draws the paper's
questions: at random from the bank's active questions for each area, at the area's level, none the child
has seen, the ones that can show the child's own repeated mistake first. It writes nothing, and the same
child in the same week always gets the same plan, so what the Growth page shows is what `make` prints.

`make` prints that plan as a paper with its QR, exactly as a library worksheet is handed out: a
sheet_template made for this child, the child's sheet_instance, the questions recorded as seen.
"""

import json
import random

from playwright.sync_api import sync_playwright

from engine.assess import focus
from engine.assess.pick import Sheet
from engine.assess.render import render_sheet
from engine.core import db, roster
from engine.w1_bank.inventory import item_from_row
from engine.w2_print.assemble import _config, _qr, _threshold

WHY = {
    "patterned_error": "the same mistake more than once",
    "emerging": "fewer than half right",
    "practising": "not yet four in five right",
}


def rule(conn) -> dict:
    """How many areas, how far from its rung an area may be worked on, and where Easy ends — all rows."""
    r = dict(_config(conn, "focus", {"most": 3, "reach": 2}))
    r["easy_below"] = _threshold(conn, "next_sheet.demote_below", 0.5)
    return r


def catalog(conn) -> list[dict]:
    """The bank's skill sets: rung, place on the ladder, the skill each is for, every skill it uses."""
    rows = conn.execute(
        "select s.code, s.rung_code, r.ladder_order,"
        " (select x from item i, unnest(i.skill_codes) x where i.skill_set_code = s.code"
        "   and i.status = 'active' group by x order by count(*) desc, x limit 1) as own,"
        " (select coalesce(array_agg(distinct x), '{}') from item i, unnest(i.skill_codes) x"
        "   where i.skill_set_code = s.code and i.status = 'active') as skills"
        " from skill_set s left join rung r on r.code = s.rung_code and r.tenant_id = s.tenant_id"
    ).fetchall()
    return [
        {
            "code": r["code"],
            "rung": r["rung_code"],
            "order": r["ladder_order"],
            "own": r["own"],
            "skills": set(r["skills"]),
        }
        for r in rows
    ]


def _shares(n, k):
    """n questions over k areas, the weakest first taking any remainder: 12 over 3 → 4, 4, 4; over 5 → 3, 3, 2, 2, 2."""
    return [n // k + (1 if i < n % k else 0) for i in range(k)]


def _words(item):
    """The question as a line of text: its stem, or for a bare sum its numbers (the page prints it in full)."""
    sp = item["spec"]
    if item["fmt"] == "missing_digit" and "c" in sp:
        return f"{sp['a']} {sp['op'].replace('-', '−')} {sp['b']} = {sp['c']}"
    if item["stem"]:
        return item["stem"]
    if sp.get("text"):
        return sp["text"]
    nums = sp.get("addends") or [sp.get("a"), sp.get("b")]
    how = " (in columns)" if sp.get("layout") == "column" else ""
    return f" {sp.get('op', '+').replace('-', '−')} ".join(str(n) for n in nums) + " = ?" + how


def _can_show(item, mistake):
    return bool(mistake) and any(mistake in (r.get("misconceptions") or {}) for r in item["responses"])


def _draw(conn, child_id, area, want, rng):
    """`want` active questions for one area at its level that the child has never been given: questions of
    the area's own skill first, those that can show the child's repeated mistake before the rest."""
    rows = conn.execute(
        "select * from item i where i.status = 'active' and i.skill_set_code = %s and i.difficulty = %s"
        " and not exists (select 1 from item_exposure x where x.child_id = %s and x.item_id = i.id)"
        " order by i.item_key",
        (area.skill_set, area.level, child_id),
    ).fetchall()
    rng.shuffle(rows)
    rows.sort(key=lambda r: (area.skill_code not in r["skill_codes"], not _can_show(r, area.mistake)))
    return rows[:want]


def plan(conn, child_id: str, week: str) -> dict:
    """The areas and the questions for this child's next paper; nothing is written."""
    states = conn.execute(
        "select skill_code, rung_code, state, n_events, n_correct, repeating_misconception"
        " from child_skill_state where child_id = %s",
        (child_id,),
    ).fetchall()
    chosen = focus.areas(states, catalog(conn), rule(conn))
    names = {r["code"]: r["name"] for r in conn.execute("select code, name from skill_set")}
    skills = {r["code"]: r["name"] for r in conn.execute("select code, name from skill")}
    mistakes = {r["code"]: r["name"] for r in conn.execute("select code, name from misconception")}
    n = int(_config(conn, "assemble.items_per_sheet", 12))
    rng = random.Random(f"{child_id}|{week}")
    out = []
    for area, want in zip(chosen, _shares(n, len(chosen)) if chosen else []):
        questions = _draw(conn, child_id, area, want, rng)
        why = f"Right {area.right} of {area.answered} — {WHY[area.state]}"
        if area.mistake:
            why += f": {mistakes.get(area.mistake, area.mistake)}"
        out.append(
            {
                "skill_set": area.skill_set,
                "name": names.get(area.skill_set, area.skill_set),
                "skill": skills.get(area.skill_code, area.skill_code),
                "level": area.level,
                "right": area.right,
                "answered": area.answered,
                "mistake": area.mistake,
                "why": why + ".",
                "questions": [
                    {
                        "item_key": q["item_key"],
                        "text": _words(q),
                        "fmt": q["fmt"],
                        "shows_mistake": _can_show(q, area.mistake),
                        "id": str(q["id"]),
                    }
                    for q in questions
                ],
            }
        )
    return {"child_id": child_id, "week": week, "areas": out, "n": sum(len(a["questions"]) for a in out)}


def make(conn, child_id: str, week: str, actor: str) -> dict:
    """Print the plan as this child's paper: a sheet made for the child, its QR, its questions seen."""
    p = plan(conn, child_id, week)
    ids = [q["id"] for a in p["areas"] for q in a["questions"]]
    if not ids:
        raise ValueError(
            "nothing to work on: the child's graph shows no area they lag in, or the bank has no unseen question for it"
        )
    child = conn.execute("select tenant_id, band, section from child where id = %s", (child_id,)).fetchone()
    template = conn.execute(
        "insert into sheet_template (tenant_id, band, week, item_ids, source, child_id)"
        " values (%s,%s,%s,%s::uuid[],'focus',%s) returning id",
        (child["tenant_id"], child["band"], week, ids, child_id),
    ).fetchone()["id"]
    qr = _qr(template, child_id, week, "focus")
    instance = conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, section, kind)"
        " values (%s,%s,%s,%s,%s,%s,'focus') returning id",
        (child["tenant_id"], qr, template, child_id, week, child["section"]),
    ).fetchone()["id"]
    conn.execute(
        "insert into item_exposure (tenant_id, child_id, item_id, week)"
        " select %s, %s, id, %s from unnest(%s::uuid[]) as id order by id on conflict do nothing",
        (child["tenant_id"], child_id, week, ids),
    )
    rows = {str(r["id"]): r for r in conn.execute("select * from item where id = any(%s::uuid[])", (ids,))}
    title = "Practice on: " + " · ".join(a["name"] for a in p["areas"])
    sheet = Sheet(qr, child["band"], "Focus", 1, week, [item_from_row(rows[i]) for i in ids], title=title)
    name = roster.names(conn, [child_id], actor).get(child_id, "")
    outdir = db.REPO_ROOT / "data" / "focus" / week
    with sync_playwright() as pw:
        key = render_sheet(
            sheet, outdir, week_label=f"{name or 'Practice'} · chosen from their own checked papers", pw=pw
        )
    pdf = outdir / f"{qr}.pdf"
    conn.execute(
        "update sheet_instance set pdf_path = %s, key = %s where id = %s",
        (str(pdf), json.dumps(key), instance),
    )
    return {"qr": qr, "pdf_path": str(pdf), "pages": key["pages"], "questions": len(ids), "areas": p["areas"]}
