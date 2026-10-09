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
import tempfile
from dataclasses import replace
from pathlib import Path

from engine.assess import focus
from engine.assess.pick import Sheet
from engine.assess.render import render_sheet
from engine.core import db, mistake_names, roster
from engine.w1_bank.inventory import item_from_row
from engine.w2_print.assemble import _qr
from engine.w2_print.shelf import _levels, _once, catalog, home_length, rule

WHY = {
    "patterned_error": "the same mistake more than once",
    "emerging": "fewer than half right",
    "practising": "not yet four in five right",
    "secure": "four in five right — a step up",
    "stretch_ready": "ready to move up",
    "asked": "chosen by a teacher",
}
HOW = {"focus": "chosen from their own checked papers", "custom": "chosen by their educator"}
# What the paper says it is, at the top of the page: a paper chosen from a child's graph is the one sent home
# (Nimish, 2026-09-24: "it needs to be explicitly written as home assessment").
# Nimish, 2026-09-27: "The home assessment part reads as 'home assessment.'" A paper an educator chooses instead of
# the proposed one is a different home assessment, so both say so; the week label says who chose it.
TITLE = "Home assessment"
# A paper the maker makes for the class (goal m3-the-maker) says so instead: it is sat in class, not sent home.
TITLES = {"practice": "Class practice", "assessment": "Class assessment"}
MOST_ASKED = 40
PREVIEW = (
    "PREVIEW"  # the QR a paper seen before approval carries: no sheet has it, so a stray copy never reads
)
NOTHING = "nothing to work on: the child's graph shows no area they lag in, or the bank has no unseen question for it"  # questions in one area of a paper a teacher asks for


def question_text(item):
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


def _draw(conn, whose, area, want, rng, taken=()):
    """`want` active questions for one area at its level that none of `whose` (one child, or every child of a paper
    for all) has ever been given, and none `taken` for another child's paper: questions of the area's own skill
    first, those that can show the child's repeated mistake before the rest."""
    rows = conn.execute(
        "select * from item i where i.status = 'active' and i.skill_set_code = %s and i.difficulty = %s"
        " and not exists (select 1 from item_exposure x where x.child_id = any(%s::uuid[]) and x.item_id = i.id)"
        " order by i.item_key",
        (area.skill_set, area.level, list(whose)),
    ).fetchall()
    rng.shuffle(rows)
    rows.sort(key=lambda r: (area.skill_code not in r["skill_codes"], not _can_show(r, area.mistake)))
    return [r for r in rows if str(r["id"]) not in taken][:want]


def _short(k, whose, taken, name, level, earlier=False) -> str:
    """Why an area cannot be filled, in words: how many questions are left, and for whom."""
    who = (
        "this child has not seen"
        if len(whose) == 1
        else f"none of these {len(whose)} children has been given"
    )
    if taken:
        who += " and no other paper here holds"
    if earlier:
        who += " and no line above on this paper holds"
    then = f"ask for {k} or fewer" if k else "choose another skill or level"
    return f"only {k} questions {who} in {name} at {level}; {then}"


def _states(conn, child_id):
    return conn.execute(
        "select skill_code, rung_code, state, n_events, n_correct, repeating_misconception"
        " from child_skill_state where child_id = %s",
        (child_id,),
    ).fetchall()


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
        # the child's states on this skill set's own rung (ADR 0048: a rung is one skill set), whatever skill a mistake
        # there was charged to; a state of the same skill on another rung is another skill set's
        mine = [x for x in states if x["rung_code"] == cat[code]["rung"] and x["state"] in focus.LAGGING]
        weakest = min(mine, key=lambda x: focus.LAGGING.index(x["state"]), default=None)
        mistake = weakest["repeating_misconception"] if weakest else None
        out.append((focus.Area(code, own, level, 0, 0, mistake, "asked"), n))
    return out


def home_area(conn, child_id: str, states: list | None = None) -> list:
    """[the one Area a child's home paper works on], at the level where its mistake shows — or [] when the graph shows
    none. What `plan` draws a home paper from, and what Friday's class card names for each child."""
    if states is None:
        states = _states(conn, child_id)
    band = conn.execute("select band from child where id = %s", (child_id,)).fetchone()["band"]
    levels = _levels(conn, band)
    return [_where_it_shows(conn, a, levels) for a in focus.home(states, catalog(conn), rule(conn), levels)]


def plan(conn, child_id: str, week: str, ask: list | None = None, taken=()) -> dict:
    """The areas and the questions for a paper for this child; nothing is written. Without `ask`, the home paper
    the graph proposes; with it, the areas a teacher asked for — refused, never padded, when the bank holds too
    few questions the child has not seen. `taken`: questions already on another child's paper of the same batch."""
    states = _states(conn, child_id)
    if ask:
        chosen = _asked(conn, states, ask)
    else:
        n = home_length(conn)
        chosen = [(a, n) for a in home_area(conn, child_id, states)]
    rng = random.Random(f"{child_id}|{week}")
    return {
        "child_id": child_id,
        "week": week,
        **drawn(conn, [child_id], chosen, rng, taken, strict=bool(ask)),
    }


def drawn(conn, whose, chosen, rng, taken=(), strict=True) -> dict:
    """Each chosen (area, how many) filled with questions none of `whose` has been given, as a paper shows them;
    `strict` refuses an area the bank cannot fill rather than printing it short."""
    names = _once(
        "set names", lambda: {r["code"]: r["name"] for r in conn.execute("select code, name from skill_set")}
    )
    skills = _once(
        "skill names", lambda: {r["code"]: r["name"] for r in conn.execute("select code, name from skill")}
    )
    name_of = _once("mistake names", lambda: mistake_names.names(conn))
    # what the paper may not use: other papers' questions, and its own lines' too, or two lines alike drew the same
    # questions (code review, 2026-09-30)
    out, on_it = [], set(taken)
    for i, (area, want) in enumerate(chosen):
        questions = _draw(conn, whose, area, want, rng, on_it)
        on_it.update(str(q["id"]) for q in questions)
        if strict and len(questions) < want:
            alike = any((a.skill_set, a.level) == (area.skill_set, area.level) for a, _ in chosen[:i])
            name = names.get(area.skill_set)
            raise ValueError(_short(len(questions), whose, taken, name, area.level, alike))
        why = (
            WHY["asked"]
            if area.state == "asked"
            else f"Right {area.right} of {area.answered} — {WHY[area.state]}"
        )
        if area.mistake:
            why += f": {name_of(area.mistake, skill=area.skill_code)}"
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
                        "text": question_text(q),
                        "fmt": q["fmt"],
                        "shows_mistake": _can_show(q, area.mistake),
                        "id": str(q["id"]),
                    }
                    for q in questions
                ],
            }
        )
    return {"areas": out, "n": sum(len(a["questions"]) for a in out)}


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
    p, _ = _planned(conn, child_id, week, ask)
    return {**print_paper(conn, child_id, week, actor, kind, p, HOW[kind]), "areas": p["areas"]}


def print_paper(conn, child_id: str, week: str, actor: str, kind: str, p: dict, how: str, pw=None) -> dict:
    """One child's drawn paper `p`, approved by `actor`: a template of its own, the child's copy with its code, its
    kind, class and week, its questions recorded as seen, and the page rendered, saying `how` it was chosen."""
    ids = [q["id"] for a in p["areas"] for q in a["questions"]]
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
    outdir = db.REPO_ROOT / "data" / "focus" / week
    key = _render(conn, child_id, week, actor, kind, p, ids, qr, outdir, how, pw)
    # its own page says how it was chosen and what it works on: a maker's class paper is not a home paper (2026-09-30)
    key = {**key, "how": how, "areas": [{"name": a["name"], "level": a["level"]} for a in p["areas"]]}
    pdf = outdir / f"{qr}.pdf"
    conn.execute(
        "update sheet_instance set pdf_path = %s, key = %s where id = %s",
        (str(pdf), json.dumps(key), instance),
    )
    return {"qr": qr, "pdf_path": str(pdf), "pages": key["pages"], "questions": len(ids)}


def _planned(conn, child_id, week, ask):
    p = plan(conn, child_id, week, ask)
    ids = [q["id"] for a in p["areas"] for q in a["questions"]]
    if not ids:
        raise ValueError(NOTHING)
    return p, ids


def _render(conn, child_id, week, actor, kind, p, ids, qr, outdir, how=None, pw=None):
    """The paper as it prints, into `outdir` as `<qr>.pdf`; returns its key. Approving and seeing it both come here;
    a batch passes its one Playwright (`pw`) to every paper."""
    band = conn.execute("select band from child where id = %s", (child_id,)).fetchone()["band"]
    rows = {str(r["id"]): r for r in conn.execute("select * from item where id = any(%s::uuid[])", (ids,))}
    name = roster.names(conn, [child_id], actor).get(child_id, "")
    title, label = heading(kind, [a["name"] for a in p["areas"]], name, how)
    sheet = Sheet(qr, band, "Focus", 1, week, [item_from_row(rows[i]) for i in ids], title=title)
    return render_sheet(sheet, outdir, week_label=label, pw=pw)


def heading(kind, areas, name, how=None):
    """→ (the paper's title, the line under it): what a child's paper says at its top — a home assessment, or the
    class's practice or assessment — and who chose it."""
    title = TITLES.get(kind, TITLE)
    return f"{title}: " + " · ".join(areas), f"{name or title} · {title}, {how or HOW[kind]}"


def preview(conn, child_id: str, week: str, actor: str, ask: list | None = None) -> bytes:
    """The paper `make` would print now, as PDF bytes, before anyone approves it: the same plan, the same page,
    its QR `PREVIEW`. Nothing is written — no sheet, no QR, no question marked seen."""
    p, ids = _planned(conn, child_id, week, ask)
    with tempfile.TemporaryDirectory() as tmp:
        _render(conn, child_id, week, actor, "custom" if ask else "focus", p, ids, PREVIEW, tmp)
        return (Path(tmp) / f"{PREVIEW}.pdf").read_bytes()
