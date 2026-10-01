"""What a parent report may say, computed from the child's signed-off answers (goals/w4c-parent-report.yaml).

`facts` is every number and name the report rests on: what the child can do and on how many answers, what is nearly
secure and why not yet, what improved from their earlier answers to their recent ones, each named mistake with their
own example, what comes next. Code computes all of it; `parent_report` gives it to the model that writes the words,
and holds the words to it. Each answer counts once, however many skills its question tests
(goals/p0-one-answer-counts-once.yaml).
"""

from engine.core import mistake_names
from engine.w4_close import report

NEARLY = 0.8  # four in five right, waiting only on a second paper to be called secure
IMPROVED_BY = (
    0.25  # the recent half of a skill set's answers right this much more often than the earlier half
)

# One row per signed-off answer (`answer_placed`), never per skill: a right answer is evidence for each skill its
# question tests, and counting those rows told a parent one right answer was three (goals/p0-one-answer-counts-once.yaml).
SIGNED = """
select a.answer as id, a.skill_codes, a.placed_rung as rung, a.correct, a.observed_at, ir.capture_id as paper,
       coalesce(ir.working_shown, 'none') as working
from answer_placed a
left join item_result ir on ir.id = a.item_result_id
left join capture c on c.id = ir.capture_id
where a.child_id = %s and a.confirmed_by is not null and (c.id is null or c.superseded_by is null)
order by a.observed_at, a.answer
"""


def _sets(conn):
    return {
        r["rung_code"]: r
        for r in conn.execute(
            "select code, name, learning_objective, rung_code from skill_set where status is distinct from 'retired'"
        )
    }


def _improving(rows, sets):
    """Skill sets whose recent answers are right clearly more often than their earlier ones, over two days or more."""
    out = []
    for rung in dict.fromkeys(r["rung"] for r in rows):
        mine = [r for r in rows if r["rung"] == rung and r["correct"] is not None]
        if len(mine) < 6 or len({r["observed_at"].date() for r in mine}) < 2 or rung not in sets:
            continue
        half = len(mine) // 2
        early, late = mine[:half], mine[half:]
        a, b = sum(r["correct"] for r in early), sum(r["correct"] for r in late)
        if b / len(late) - a / len(early) >= IMPROVED_BY:
            out.append(
                _skill(sets[rung], earlier=f"{a} of {len(early)} right", recent=f"{b} of {len(late)} right")
            )
    return out


def _skill(s, **more):
    return {"id": s["code"], "skill": s["name"], "can": s["learning_objective"], **more}


def _every(conn, child_id, states):
    """The rungs on which every skill of the child's is in one of `states`. A set is secure, or ready to move up, only
    when every skill of it the child answered is: Advika's report (2026-10-01) called word problems secure at 17 of 27
    right, ready for the next step, and moved her on, because one skill of the set was."""
    return {
        r["rung_code"]
        for r in conn.execute(
            "select rung_code from child_skill_state where child_id = %s"
            " group by rung_code having bool_and(state = any(%s))",
            (child_id, list(states)),
        )
    }


def _any(conn, child_id, states):
    """The rungs on which some skill of the child's is in one of `states`."""
    return {
        r["rung_code"]
        for r in conn.execute(
            "select distinct rung_code from child_skill_state where child_id = %s and state = any(%s)",
            (child_id, list(states)),
        )
    }


def _per_set(rows):
    """{rung: (right, answered)} over the child's answers, each once however many skills its question tests. A blank
    is not an answer here, as the graph does not count it either (`n_events`)."""
    out = {}
    for r in rows:
        if r["correct"] is not None:
            right, n = out.get(r["rung"], (0, 0))
            out[r["rung"]] = (right + r["correct"], n + 1)
    return out


def _not_yet(conn, child_id, rows):
    """{rung: why it is not secure yet}, as the graph decides it: a skill is secure only once it holds on
    `state.min_observers` papers. v7 on live wrote "nearly secure ... got 14 of 14 right" with no reason, which reads to
    a parent as a contradiction. Counted over the skills of the set still practising, as the nearly counts are."""
    row = conn.execute("select value from threshold where key = 'state.min_observers'").fetchone()
    need = row["value"] if row else 2
    practising = {
        (r["rung_code"], r["skill_code"])
        for r in conn.execute(
            "select rung_code, skill_code from child_skill_state where child_id = %s and state = 'practising'",
            (child_id,),
        )
    }
    papers = {}
    for r in rows:
        if any((r["rung"], k) in practising for k in r["skill_codes"]):
            papers.setdefault(r["rung"], set()).add(r["paper"] or r["id"])
    out = {rung: len(p) for rung, p in papers.items()}
    return {
        rung: "answered on one paper so far: secure once it holds on another"
        if n == 1
        else "answered on fewer papers than secure needs: secure once it holds on another"
        if n < need
        else "not yet right often enough to be secure"
        for rung, n in out.items()
    }


def _mistake(f, what):
    ex = f["example"]
    return {
        "id": f["mistake"],
        "mistake": f["name"],
        # the vocabulary's own example is another child's sum: the part before it is what happens on the page
        "what_happens": (what(f["mistake"], skill=f["skill_code"]) or "").split(":")[0],
        "what_we_do": f["hint"],
        "times": f["times"],
        "example": ex and {"question": ex["question"], "wrote": ex["wrote"], "right": ex["right"]},
    }


def facts(conn, child_id):
    """Everything the report may say, computed; None when an educator has signed off nothing of the child's yet."""
    rows = conn.execute(SIGNED, (child_id,)).fetchall()
    if not rows:
        return None
    band = conn.execute("select band from child where id = %s", (child_id,)).fetchone()["band"]
    sets, rep = _sets(conn), report.build(conn, child_id)
    by_code = {s["code"]: s for s in sets.values()}
    stretch = {sets[r]["code"] for r in _every(conn, child_id, ("stretch_ready",)) if r in sets}
    per_set = _per_set(rows)
    # one entry per skill set: a rung holds several of the registry's skills, and each can be strong or practising
    # on its own — the first eval listed ADD.2D2D twice, and held the words to a count they rightly would not repeat.
    # Its count is its answers, once each: adding up its skills' counts counted an answer once per skill.
    secure = _every(conn, child_id, report.STRONG)
    strong = list(
        dict.fromkeys(
            s["skill_set"]
            for s in rep["strong"]
            if s["skill_set"] in by_code and by_code[s["skill_set"]]["rung_code"] in secure
        )
    )
    can_do = [
        _skill(by_code[code], right=right, answered=n, ready_to_move_up=code in stretch)
        for code in strong
        for right, n in [per_set.get(by_code[code]["rung_code"], (0, 0))]
    ]
    why = _not_yet(conn, child_id, rows)
    nearly = [
        _skill(sets[r], right=right, answered=n, not_yet=why.get(r, "not yet secure"))
        # "nearly ... secure once it holds on another paper" promises one more paper is all it needs: never of a set
        # with a skill still making its mistake, or only emerging
        for r in sorted(
            _any(conn, child_id, ("practising",)) - _any(conn, child_id, ("patterned_error", "emerging"))
        )
        for right, n in [per_set.get(r, (0, 0))]
        if r in sets and sets[r]["code"] not in strong and n >= 3 and right / n >= NEARLY
    ]
    said = {x["id"] for x in can_do + nearly}
    nxt = rep["next"] and by_code.get(rep["next"]["skill_set"])
    wrong = [r for r in rows if r["correct"] is False]
    what = mistake_names.names(conn, "description")
    return {
        "grade": f"Grade {band[1:]}",
        "from": rows[0]["observed_at"].date().isoformat(),
        "to": rows[-1]["observed_at"].date().isoformat(),
        # a question left blank is not an answer: the header said "112 answers" with the blank ones in the count
        "answers": sum(r["correct"] is not None for r in rows),
        "can_do": can_do,
        "nearly": nearly,
        "improving": [i for i in _improving(rows, sets) if i["id"] not in said],
        "working_on": [_mistake(f, what) for f in rep["faulty"][:3]],
        "wrong_answers_no_named_mistake_explains": sum(u["times"] for u in rep["unexplained"]),
        # why, as the graph says it: secure there already, so harder questions of it; or more practice of it. v3's first
        # eval said "can do X" and then "will practise X next" to the same parent — the facts had not said which
        "next": nxt
        and _skill(
            nxt,
            level=rep["next"]["level"],
            # as the report shows it: a skill set it lists as "can do" is secure (v4 said "can do" and "more practice")
            why="secure already: next, harder questions of it"
            if nxt["rung_code"] in secure and (rep["next"]["state"] in report.STRONG or nxt["code"] in strong)
            else "still practising it: more questions of it",
        ),
        "days": (rows[-1]["observed_at"].date() - rows[0]["observed_at"].date()).days + 1,
        # what the child did on the papers — v3 read a bare "left_blank: 4" as a task ("leave four questions blank")
        "on_the_papers": {
            "wrong_answers": len(wrong),
            "wrong_answers_with_working_shown": sum(r["working"] != "none" for r in wrong),
            "questions_the_child_left_blank": sum(r["correct"] is None for r in rows),
        },
    }
