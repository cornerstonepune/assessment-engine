"""A child's own paper: the home paper chosen from the child's graph, or one a teacher asks for.

A paper is asked for as areas — a skill set, a level, how many questions each. A home paper's one area is the
engine's (`assess.focus.home`: the weakest skill, or a stretch); a custom paper's areas are the teacher's, any
skills, any levels, any count. One engine makes both.

`plan` draws the paper's questions: at random from the bank's active questions for each area, at the area's level, none the child
has seen, the ones that can show the child's own repeated mistake first. It writes nothing, and the same
child in the same week always gets the same plan, so what the Growth page shows is what `make` prints.

`make` is a person approving that plan: it prints it as a paper with its QR, exactly as a library worksheet is
handed out — a sheet_template made for this child, the child's sheet_instance, the questions recorded as seen — and
the paper names who approved it. One next paper a week: a second approval is refused (`approved` says which).
"""

import json
import random
from dataclasses import replace

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
    "secure": "four in five right — a step up",
    "stretch_ready": "ready to move up",
    "asked": "chosen by a teacher",
}
HOW = {"focus": "chosen from their own checked papers", "custom": "chosen by their teacher"}
MOST_ASKED = 40  # questions in one area of a paper a teacher asks for


def rule(conn) -> dict:
    """How far from its rung an area may be worked on, the stretch level for each strong state, and where Easy
    ends — all rows."""
    r = dict(_config(conn, "focus", {"reach": 2, "stretch": {"secure": "Hard", "stretch_ready": "Advance"}}))
    r["easy_below"] = _threshold(conn, "next_sheet.demote_below", 0.5)
    return r


def catalog(conn) -> list[dict]:
    """The bank's taught skill sets: rung, place on the ladder, the skill each is for, every skill it uses. A skill
    the school does not teach yet is never on a child's paper, whatever the child's map shows."""
    rows = conn.execute(
        "select s.code, s.rung_code, r.ladder_order,"
        " (select x from item i, unnest(i.skill_codes) x where i.skill_set_code = s.code"
        "   and i.status = 'active' group by x order by count(*) desc, x limit 1) as own,"
        " (select coalesce(array_agg(distinct x), '{}') from item i, unnest(i.skill_codes) x"
        "   where i.skill_set_code = s.code and i.status = 'active') as skills"
        " from skill_set s left join rung r on r.code = s.rung_code and r.tenant_id = s.tenant_id"
        " where exists (select 1 from topic t where t.tenant_id = s.tenant_id and t.code = s.topic_code and t.taught)"
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


def _where_it_shows(conn, area, levels) -> focus.Area:
    """A repeated mistake is worked on where it can happen: the home paper moves up from its level to the first
    the skill set defines whose questions can show the mistake. Taking the smaller digit from the larger needs an
    exchange, which Easy never asks for — an Easy paper could not show the child the mistake it is for."""
    if not area.mistake:
        return area
    defined = levels.get(area.skill_set, ())
    for level in [d for d in focus.LEVELS[focus.LEVELS.index(area.level) :] if d in defined]:
        rows = conn.execute(
            "select responses from item where status = 'active' and skill_set_code = %s and difficulty = %s",
            (area.skill_set, level),
        ).fetchall()
        if any(_can_show(r, area.mistake) for r in rows):
            return replace(area, level=level)
    return area


def _levels(conn) -> dict:
    return {
        r["code"]: tuple(r["difficulty"] or {})
        for r in conn.execute("select code, difficulty from skill_set")
    }


def _asked(conn, states, ask) -> list:
    """The areas a teacher asked for, each checked against the bank's own skill sets and levels, with the child's
    repeated mistake in that skill, if any, so the questions that can show it come first."""
    cat = {c["code"]: c for c in catalog(conn)}
    levels = _levels(conn)
    out = []
    for a in ask:
        code, level, n = a.get("skill_set"), a.get("level"), a.get("n")
        if code not in cat:
            raise ValueError(f"no skill set {code!r}")
        if level not in levels.get(code, ()):
            raise ValueError(
                f"{code} has no level {level!r}: it has {', '.join(levels.get(code, ())) or 'none'}"
            )
        if not isinstance(n, int) or not 1 <= n <= MOST_ASKED:
            raise ValueError(f"ask for 1 to {MOST_ASKED} questions in an area, not {n!r}")
        own = cat[code]["own"]
        mine = [x for x in states if x["skill_code"] == own and x["state"] in focus.LAGGING]
        weakest = min(mine, key=lambda x: focus.LAGGING.index(x["state"]), default=None)
        mistake = weakest["repeating_misconception"] if weakest else None
        out.append((focus.Area(code, own, level, 0, 0, mistake, "asked"), n))
    return out


def plan(conn, child_id: str, week: str, ask: list | None = None) -> dict:
    """The areas and the questions for a paper for this child; nothing is written. Without `ask`, the home paper
    the graph proposes; with it, the areas a teacher asked for — refused, never padded, when the bank holds too
    few questions the child has not seen."""
    states = conn.execute(
        "select skill_code, rung_code, state, n_events, n_correct, repeating_misconception"
        " from child_skill_state where child_id = %s",
        (child_id,),
    ).fetchall()
    if ask:
        chosen = _asked(conn, states, ask)
    else:
        n = int(_config(conn, "assemble.items_per_sheet", 12))
        levels = _levels(conn)
        chosen = [
            (_where_it_shows(conn, a, levels), n)
            for a in focus.home(states, catalog(conn), rule(conn), levels)
        ]
    names = {r["code"]: r["name"] for r in conn.execute("select code, name from skill_set")}
    skills = {r["code"]: r["name"] for r in conn.execute("select code, name from skill")}
    mistakes = {r["code"]: r["name"] for r in conn.execute("select code, name from misconception")}
    rng = random.Random(f"{child_id}|{week}")
    out = []
    for area, want in chosen:
        questions = _draw(conn, child_id, area, want, rng)
        if ask and len(questions) < want:
            raise ValueError(
                f"only {len(questions)} questions this child has not seen in {names.get(area.skill_set)} at"
                f" {area.level}; ask for {len(questions)} or fewer"
            )
        why = (
            WHY["asked"]
            if area.state == "asked"
            else f"Right {area.right} of {area.answered} — {WHY[area.state]}"
        )
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


def approved(conn, child_id: str, week: str) -> dict | None:
    """The next paper already approved for this child this week: its QR, who approved it and when."""
    row = conn.execute(
        "select qr_code as qr, approved_by, approved_at from sheet_instance"
        " where child_id = %s and week = %s and kind = 'focus' order by created_at limit 1",
        (child_id, week),
    ).fetchone()
    return dict(row) if row else None


def make(conn, child_id: str, week: str, actor: str, ask: list | None = None) -> dict:
    """`actor` approves the plan: it prints as this child's paper, its QR, its questions seen, and names them.
    One home paper a week; a teacher may ask for as many custom papers as the bank can fill."""
    # one approval at a time per child, so two teachers clicking together cannot both print this week's paper
    conn.execute("select id from child where id = %s for update", (child_id,))
    kind = "custom" if ask else "focus"
    had = None if ask else approved(conn, child_id, week)
    if had:
        raise ValueError(f"this week's next paper is already approved: {had['qr']} by {had['approved_by']}")
    p = plan(conn, child_id, week, ask)
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
    qr = _qr(template, child_id, week, kind)
    instance = conn.execute(
        "insert into sheet_instance (tenant_id, qr_code, sheet_template_id, child_id, week, section, kind,"
        " print_status, printed_at, approved_by, approved_at)"
        " values (%s,%s,%s,%s,%s,%s,%s,'printed',now(),%s,now()) returning id",
        (child["tenant_id"], qr, template, child_id, week, child["section"], kind, actor),
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
        key = render_sheet(sheet, outdir, week_label=f"{name or 'Practice'} · {HOW[kind]}", pw=pw)
    pdf = outdir / f"{qr}.pdf"
    conn.execute(
        "update sheet_instance set pdf_path = %s, key = %s where id = %s",
        (str(pdf), json.dumps(key), instance),
    )
    return {"qr": qr, "pdf_path": str(pdf), "pages": key["pages"], "questions": len(ids), "areas": p["areas"]}
