"""N11 — Friday's class card (goals/w4a-class-card.yaml), computed from each child's graph alone; no model.

For every skill set the section's children have checked evidence on: the children in the graph's own groups — ready to
move up, secure, practising, emerging, reteach (grouped by the named mistake each repeats), not enough evidence yet.
For every child: the area their home paper will work on, exactly as W2 makes it (`focus_paper.home_area`). A child
with no checked evidence is named as such, never dropped. The card is kept as the week's `class_card` rows (Ring B,
rebuilt whenever it is built); the educator confirms it once, by name, and what they confirmed is kept as they saw it.
"""

import json

from engine.core import db
from engine.w2_print import focus_paper

GROUPS = {
    "stretch_ready": "move_up",
    "secure": "secure",
    "practising": "practising",
    "emerging": "emerging",
    "not_enough_yet": "not_enough_yet",
}
ORDER = ("move_up", "secure", "practising", "emerging", "reteach", "not_enough_yet")


WEAKEST_FIRST = ("patterned_error", "emerging", "practising", "secure", "stretch_ready", "not_enough_yet")


def _weakest(states):
    """{(rung, child): the child's weakest state on that rung} — a child sits once in a skill set's groups, where they
    are weakest; "not enough yet" only when nothing on the rung has enough evidence."""
    out = {}
    for s in sorted(states, key=lambda s: WEAKEST_FIRST.index(s["state"])):
        out.setdefault((s["rung_code"], str(s["child_id"])), s)
    return out


def _children(conn, section):
    return conn.execute(
        "select id, roll_no, band from child where section = %s and active order by roll_no", (section,)
    ).fetchall()


def build(conn, section):
    """→ {"section", "skills": [{skill_set, name, rung, groups}], "children": [{child_id, roll_no, home, why}]}."""
    kids = _children(conn, section)
    if not kids:
        raise ValueError(f"no class {section!r}")
    ids = [k["id"] for k in kids]
    states = conn.execute(
        "select child_id, skill_code, rung_code, state, n_events, n_correct, repeating_misconception"
        " from child_skill_state where child_id = any(%s)",
        (ids,),
    ).fetchall()
    sets = {
        r["rung_code"]: r
        for r in conn.execute(
            "select code, name, rung_code from skill_set where status is distinct from 'retired'"
        )
    }
    mistakes = {r["code"]: r["name"] for r in conn.execute("select code, name from misconception")}

    by_rung = {}
    for (rung, who), s in _weakest(states).items():
        g = by_rung.setdefault(rung, {k: [] for k in ORDER if k != "reteach"} | {"reteach": {}})
        if s["state"] == "patterned_error":
            code = s["repeating_misconception"]
            g["reteach"].setdefault(code, {"name": mistakes.get(code, code), "children": []})[
                "children"
            ].append(who)
        else:
            g[GROUPS[s["state"]]].append(who)
    skills = [
        {
            "skill_set": sets[r]["code"] if r in sets else None,
            "name": sets[r]["name"] if r in sets else r,
            "rung": r,
            "groups": by_rung[r],
        }
        for r in sorted(by_rung, key=lambda r: (sets[r]["code"] if r in sets else "~", r))
    ]

    seen = {str(s["child_id"]) for s in states}
    children = []
    for k in kids:
        who = str(k["id"])
        if who not in seen:
            children.append(
                {"child_id": who, "roll_no": k["roll_no"], "home": None, "why": "no checked paper yet"}
            )
            continue
        mine = [s for s in states if str(s["child_id"]) == who]
        area = next(iter(focus_paper.home_area(conn, k["id"], mine)), None)
        children.append(
            {
                "child_id": who,
                "roll_no": k["roll_no"],
                "home": area
                and {
                    "skill_set": area.skill_set,
                    "level": area.level,
                    "mistake": area.mistake,
                    "mistake_name": mistakes.get(area.mistake) if area.mistake else None,
                    "state": area.state,
                    "right": area.right,
                    "answered": area.answered,
                },
                "why": "" if area else "nothing lags and nothing to stretch into in the bank",
            }
        )
    return {"section": section, "skills": skills, "children": children}


def store(conn, section, week, card):
    """The week's card as `class_card` rows, one per rung: what was there for this section and week is replaced."""
    conn.execute("delete from class_card where section = %s and week = %s", (section, week))
    for s in card["skills"]:
        g = s["groups"]
        conn.execute(
            "insert into class_card (tenant_id, section, week, rung_code, secure, reteach, move_up, groups)"
            " select id, %s, %s, %s, %s::uuid[], %s, %s::uuid[], %s from tenant where slug = %s",
            (
                section,
                week,
                s["rung"],
                g["secure"],
                json.dumps({c: r["children"] for c, r in g["reteach"].items()}),
                g["move_up"],
                json.dumps(g),
                db.tenant_slug(),
            ),
        )
    return len(card["skills"])


def confirm(conn, section, week, by, card):
    """The educator confirms the week's card, by name; kept as they saw it (append-only; the latest stands)."""
    if not by:
        raise ValueError("a confirmation names the educator making it")
    return conn.execute(
        "insert into class_card_confirmation (tenant_id, section, week, by, card, created_at)"
        " select id, %s, %s, %s, %s, clock_timestamp() from tenant where slug = %s returning id, created_at",
        (section, week, by, json.dumps(card), db.tenant_slug()),
    ).fetchone()


def confirmed(conn, section, week):
    return conn.execute(
        "select by, card, created_at from class_card_confirmation where section = %s and week = %s"
        " order by created_at desc limit 1",
        (section, week),
    ).fetchone()
