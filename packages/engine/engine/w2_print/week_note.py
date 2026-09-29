"""N4 — the week's declaration (goals/n4-week-declaration.yaml; workflow v1: "LLM structures, teacher confirms").

An educator says in their own words what the class did this week. The engine proposes which of that grade's skill sets
it covered: one yes/no per skill set, asked of Jev in one call (ADR 0036), each with its probability; those at or
above `week.skill_yes_above` come ticked. The educator confirms or changes the ticks, and what they confirm is kept
(`week_declaration`, append-only: the latest for a section and week stands) — the week's papers are made from it.
If Jev cannot be reached, nothing is ticked and the educator ticks the skill sets themselves.

Measured 2026-09-28 on 24 gold notes (`supabase/seed/week_note_gold.json`): at 0.5, precision 0.94, recall 0.97, the
exact set on 21 of 24, about 0.3 s a note. Jev is shown the note and the skill sets' own words, never a child.
"""

import json

from engine.adapters import jev
from engine.core import db

PURPOSE = "week_skills"
GOLD = db.REPO_ROOT / "supabase" / "seed" / "week_note_gold.json"
BAR = ("week.skill_yes_above", 0.5)


def _bar(conn):
    row = conn.execute("select value from threshold where key = %s", (BAR[0],)).fetchone()
    return float(row["value"]) if row else BAR[1]


def options(conn, band):
    """{code: its name and what the child can do} for the skill sets a class in `band` works on: those of its grade,
    and the ones for that grade and above ("G2+")."""
    grade = int(band[1:]) if band[1:].isdigit() else 0
    out = {}
    for r in conn.execute(
        "select s.code, s.name, s.learning_objective, g.band from skill_set s join rung g"
        " on g.tenant_id = s.tenant_id and g.code = s.rung_code order by s.code"
    ):
        b = r["band"]
        from_grade = b.endswith("+") and b[1:-1].isdigit() and int(b[1:-1]) <= grade
        if b == band or from_grade:
            out[r["code"]] = f"{r['name']} — {r['learning_objective']}"
    return out


def propose(conn, band, note, ask=None):
    """→ {"skill_sets": [{code, about, yes, ticked}] most likely first, "why": "" or why nothing is proposed}."""
    ask = ask or jev.decide_yes_no
    about = options(conn, band)
    if not note.strip():
        return {"skill_sets": [_row(c, a, None, False) for c, a in about.items()], "why": "no note written"}
    try:
        yes = ask(conn, PURPOSE, {"educator_note": note.strip()}, about)["yes"]
    except jev.JevError as e:
        return {"skill_sets": [_row(c, a, None, False) for c, a in about.items()], "why": str(e)}
    bar = _bar(conn)
    rows = [_row(c, about[c], p, p >= bar) for c, p in yes.items()]
    return {"skill_sets": sorted(rows, key=lambda r: -r["yes"]), "why": ""}


def _row(code, about, yes, ticked):
    return {"code": code, "about": about, "yes": yes, "ticked": ticked}


def confirm(conn, section, week, note, skill_sets, by, proposed=()):
    """What the educator confirms for their section's week, kept as said. Refuses a skill set that is not the grade's."""
    band = conn.execute("select band from child where section = %s and active limit 1", (section,)).fetchone()
    if not band:
        raise ValueError(f"no class {section!r}")
    allowed = options(conn, band["band"])
    unknown = sorted(set(skill_sets) - set(allowed))
    if unknown:
        raise ValueError(f"not skill sets of {band['band']}: {', '.join(unknown)}")
    if not by:
        raise ValueError("a declaration names the educator making it")
    return conn.execute(
        # clock_timestamp, not now(): two declarations in one transaction still have an order, and the latest stands
        "insert into week_declaration (tenant_id, section, week, note, skill_sets, proposed, by, created_at)"
        " select id, %s, %s, %s, %s, %s, %s, clock_timestamp() from tenant where slug = %s returning id, created_at",
        (section, week, note, sorted(skill_sets), json.dumps(list(proposed)), by, db.tenant_slug()),
    ).fetchone()


def current(conn, section, week):
    """The week's declaration that stands — the latest — or None."""
    return conn.execute(
        "select section, week, note, skill_sets, proposed, by, created_at from week_declaration"
        " where section = %s and week = %s order by created_at desc limit 1",
        (section, week),
    ).fetchone()


def evaluate(conn, ask=None, gold=None):
    """Jev against the gold notes: precision and recall of the ticked skill sets, and how many notes it got exactly."""
    gold = gold if gold is not None else json.loads(GOLD.read_text(encoding="utf-8"))["notes"]
    tp = fp = fn = exact = 0
    misses, failed = [], []
    asking = jev.counting(ask or jev.decide_yes_no, failed)
    for g in gold:
        before = len(failed)
        proposed = propose(conn, g["band"], g["note"], asking)
        if len(failed) > before:  # not asked is not "nothing ticked"
            continue
        got = {r["code"] for r in proposed["skill_sets"] if r["ticked"]}
        want = set(g["skill_sets"])
        tp, fp, fn = tp + len(got & want), fp + len(got - want), fn + len(want - got)
        exact += got == want
        if got != want:
            misses.append({"note": g["note"], "want": sorted(want), "got": sorted(got)})
    return {
        "n": len(gold),
        "exact": exact,
        "precision": round(tp / max(1, tp + fp), 3),
        "recall": round(tp / max(1, tp + fn), 3),
        "misses": misses,
        "unanswered": len(failed),
        "error": failed[0] if failed else "",
    }
