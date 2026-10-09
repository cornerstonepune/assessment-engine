"""N12 — a child's report in the shape of Aseem's (goals/w4b-report.yaml), computed from the child's confirmed evidence;
no model. Strong concepts: the skill sets the graph calls secure or ready to move up. Faulty concepts: each named mistake
the child made, how often, with the child's own example — the question as printed, what they wrote, the right answer.
Wrong answers no named mistake explains are counted per skill, never spread. Next: the area their home paper works on
(W2's own choice). Only what a person signed off counts, from readings nobody has superseded.

`against` reads the reports back against Aseem's transcribed findings (`gold_finding`): every faulty concept he named
that the papers hold must be in the report, and nothing he called strong may be faulty in it.
"""

from engine.core import mistake_names
from engine.w2_print import focus_paper

STRONG = ("secure", "stretch_ready")

WRONG = """
select coalesce(e.item_result_id, e.id) as answer, e.skill_code, e.misconception_codes, e.observed_at, i.item_key, i.fmt, i.stem, i.spec, i.responses,
       result_response(i.responses, r.rid) as response,
       coalesce((select rc.human_read from read_correction rc where rc.item_result_id = r.id and rc.judged is null
                  order by rc.created_at desc limit 1), r.raw_read::jsonb ->> 'child_answer') as wrote
from evidence_placed e
left join item_result r on r.id = e.item_result_id
left join capture c on c.id = r.capture_id
left join item i on i.id = r.item_id
where e.child_id = %s and e.confirmed_by is not null and e.correct = false
  and (c.id is null or c.superseded_by is null)
  and (%s::timestamptz is null or e.observed_at >= %s::timestamptz)
order by e.observed_at desc
"""


def _example(row):
    if not row["item_key"]:
        return None
    right = (row["response"] or {}).get("answer")  # the answer this one was for, not its question's first
    return {
        "item_key": row["item_key"],
        "question": focus_paper.question_text(row),
        "wrote": row["wrote"],
        "right": right,
    }


def build(conn, child_id, since=None):
    """→ {"child_id", "strong", "faulty", "unexplained", "next"} for one child, over evidence from `since` on."""
    skills = {r["code"]: r["name"] for r in conn.execute("select code, name from skill")}
    name_of, hint_of = mistake_names.names(conn), mistake_names.names(conn, "repair_hint")
    sets = {r["rung_code"]: r for r in conn.execute("select code, name, rung_code from skill_set")}
    states = conn.execute(
        "select skill_code, rung_code, state, n_events, n_correct, repeating_misconception"
        " from child_skill_state where child_id = %s",
        (child_id,),
    ).fetchall()
    strong = sorted(
        (
            {
                "skill_set": sets[s["rung_code"]]["code"] if s["rung_code"] in sets else None,
                "name": sets[s["rung_code"]]["name"]
                if s["rung_code"] in sets
                else skills.get(s["skill_code"]),
                "skill_code": s["skill_code"],
                "right": s["n_correct"],
                "answered": s["n_events"],
            }
            for s in states
            if s["state"] in STRONG
        ),
        key=lambda r: (r["skill_set"] or "~", r["skill_code"]),
    )

    faulty, unexplained, counted = {}, {}, set()
    for row in conn.execute(WRONG, (child_id, since, since)):
        codes = row["misconception_codes"] or []
        if not codes:
            unexplained[row["skill_code"]] = unexplained.get(row["skill_code"], 0) + 1
        for code in codes:
            # a wrong answer to a question of two skills is a row per skill, and one slip, not two
            if (code, row["answer"]) in counted:
                continue
            counted.add((code, row["answer"]))
            op = (row["spec"] or {}).get("op")
            f = faulty.setdefault(
                code,
                {
                    "mistake": code,
                    "name": name_of(code, op=op, skill=row["skill_code"]),
                    "hint": hint_of(code, op=op, skill=row["skill_code"]),
                    "skill_code": row["skill_code"],
                    "skill": skills.get(row["skill_code"], row["skill_code"]),
                    "times": 0,
                    "example": None,
                },
            )
            f["times"] += 1
            f["example"] = f["example"] or _example(row)  # the latest, rows come newest first

    area = next(iter(focus_paper.home_area(conn, child_id, states)), None) if states else None
    return {
        "child_id": str(child_id),
        "strong": strong,
        "faulty": sorted(faulty.values(), key=lambda f: (-f["times"], f["mistake"])),
        "unexplained": [
            {"skill_code": k, "skill": skills.get(k, k), "times": n} for k, n in sorted(unexplained.items())
        ],
        "next": area
        and {"skill_set": area.skill_set, "level": area.level, "mistake": area.mistake, "state": area.state},
    }


def against(findings, reports):
    """Aseem's findings (`gold.check` rows) against the reports ({child_id: report}) → the findings with `in_report`
    and why not. A finding the papers do not hold, or not yet confirmed, is counted apart, never dropped."""
    out = []
    for g in findings:
        r = reports.get(str(g["child_id"]))
        if g["outcome"] != "in the graph" or r is None:
            out.append({**g, "in_report": None, "why": g["outcome"]})
            continue
        faulty_codes = {f["mistake"] for f in r["faulty"]}
        faulty_skills = {f["skill_code"] for f in r["faulty"]} | {u["skill_code"] for u in r["unexplained"]}
        if g["verdict"] == "strong":
            ok, why = g["skill_code"] not in faulty_skills, "called faulty in the report"
        elif g["misconception_code"]:
            ok, why = g["misconception_code"] in faulty_codes, "the mistake is not in the report"
        else:
            ok, why = g["skill_code"] in faulty_skills, "the skill is not faulty in the report"
        out.append({**g, "in_report": ok, "why": "" if ok else why})
    return out
