"""N12 — the parent report (goals/w4c-parent-report.yaml): the end of the loop, one page a parent reads.

Code works out every fact from the child's signed-off answers (`facts`): what they can do and on how many answers,
what is nearly secure, what has improved from their earlier answers to their recent ones, each named mistake with
their own example and what the school does about it, what comes next. A model writes the words (`parent_report`
prompt) — given the facts and never the child's name: it writes [child], and the website puts the name in (rule 6).
Code then holds the words to the facts (`check`): every skill and mistake answered once, no number the facts do not
hold, none of the words the school does not use, no code, no name. A draft that fails is sent back once with what it
broke; one that fails twice is never kept. A kept draft waits for an educator to approve it before any parent sees it.
"""

import json
from datetime import date

from engine.adapters import llm
from engine.core import db, mistake_names
from engine.w4_close import report
from engine.w4_close.parent_check import check, numbers_in  # noqa: F401 — the words held to the facts

PURPOSE = "parent_report"
NEARLY = 0.8  # four in five right, waiting only on a second paper to be called secure
IMPROVED_BY = (
    0.25  # the recent half of a skill set's answers right this much more often than the earlier half
)

SIGNED = """
select e.placed_rung as rung, e.correct, e.observed_at, coalesce(ir.working_shown, 'none') as working
from evidence_placed e
left join item_result ir on ir.id = e.item_result_id
left join capture c on c.id = ir.capture_id
where e.child_id = %s and e.confirmed_by is not null and (c.id is null or c.superseded_by is null)
order by e.observed_at, e.id
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


def _states(conn, child_id, state):
    """{rung: (right, answered)} over the child's skills in one state of the graph's."""
    return {
        r["rung_code"]: (r["right"], r["answered"])
        for r in conn.execute(
            "select rung_code, sum(n_correct)::int as right, sum(n_events)::int as answered from child_skill_state"
            " where child_id = %s and state = %s group by rung_code",
            (child_id, state),
        )
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
    stretch = {sets[r]["code"] for r in _states(conn, child_id, "stretch_ready") if r in sets}
    # one entry per skill set: a rung holds several of the registry's skills, and each can be strong or practising
    # on its own — the first eval listed ADD.2D2D twice, and held the words to a count they rightly would not repeat
    strong = {}
    for s in rep["strong"]:
        if s["skill_set"] in by_code:
            got = strong.setdefault(s["skill_set"], [0, 0])
            got[0], got[1] = got[0] + s["right"], got[1] + s["answered"]
    can_do = [
        _skill(by_code[code], right=right, answered=n, ready_to_move_up=code in stretch)
        for code, (right, n) in strong.items()
    ]
    nearly = [
        _skill(sets[r], right=right, answered=n)
        for r, (right, n) in _states(conn, child_id, "practising").items()
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
        "answers": len(rows),
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
            if rep["next"]["state"] in ("secure", "stretch_ready") or nxt["code"] in strong
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


def draft(conn, child_id, ask=None, version=None):
    """→ {"facts", "draft", "problems", "prompt_id", "attempts"}: the model's words for the facts, held to them; sent
    back with what they broke, twice at most. None when there is nothing signed off to report."""
    ask = ask or llm.generate
    f = facts(conn, child_id)
    if f is None:
        return None
    fix = ""
    for attempt in (
        1,
        2,
        3,
    ):  # every try held to the facts in full; a third lets a stubborn slip be put right
        meta = {}
        try:
            # what comes next is the engine's decision, and code says it on the page: v5 was told "secure already" and
            # still wrote "more practice, as [child] is still practising" twice — a model not given it cannot say it
            told = {k: v for k, v in f.items() if k != "next"}
            out = ask(
                conn, PURPOSE, {"grade": f["grade"], "facts": told, "fix": fix}, meta=meta, version=version
            )
            problems = check(f, out)
        except llm.LLMError as e:
            # 2026-09-28, the first eval on live: a draft over its schema's length ended the whole run. A draft that
            # breaks its schema has broken a rule like any other, and is sent back with what it broke.
            if "failed its schema" not in str(e):
                raise
            out, problems = None, [str(e)]
        if not problems:
            break
        fix = "Your last answer broke these rules. Fix every one:\n- " + "\n- ".join(problems) + "\n"
    return {
        "facts": f,
        "draft": out,
        "problems": problems,
        "prompt_id": meta.get("prompt_id"),
        "attempts": attempt,
    }


def keep(conn, child_id, got):
    """A draft that holds to its facts, kept for an educator to approve; the week is today's."""
    if got["problems"]:
        raise ValueError("a draft that breaks its facts is never kept: " + "; ".join(got["problems"]))
    y, w, _ = date.today().isocalendar()
    return conn.execute(
        "insert into parent_note (tenant_id, child_id, week, body, prompt_version)"
        " select t.id, %s, %s, %s, (select version from prompt where id = %s) from tenant t where t.slug = %s"
        " returning id, created_at",
        (
            child_id,
            f"{y}-W{w:02d}",
            json.dumps({"facts": got["facts"], "draft": got["draft"]}),
            got["prompt_id"],
            db.tenant_slug(),
        ),
    ).fetchone()


def latest(conn, child_id):
    """The child's newest kept report, and whether their signed-off answers have changed since it was written."""
    row = conn.execute(
        "select id, week, body, prompt_version, approved_by, created_at, updated_at from parent_note"
        " where child_id = %s and body like '{\"facts\"%%' order by created_at desc limit 1",
        (child_id,),
    ).fetchone()
    if not row:
        return None
    body = json.loads(row["body"])
    now = json.loads(json.dumps(facts(conn, child_id), default=str))
    return {
        "id": str(row["id"]),
        "week": row["week"],
        "facts": body["facts"],
        "draft": body["draft"],
        "prompt_version": row["prompt_version"],
        "approved_by": row["approved_by"],
        "approved_at": row["approved_by"] and row["updated_at"].isoformat(),
        "written_at": row["created_at"].isoformat(),
        "stale": now != body["facts"],
    }


def approve(conn, child_id, note_id, by):
    """An educator approves the report, by name, once; what they approved is what a parent sees."""
    if not by:
        raise ValueError("an approval names the educator giving it")
    row = conn.execute(
        "update parent_note set approved_by = %s where id::text = %s and child_id = %s and approved_by is null"
        " returning id",
        (by, note_id, child_id),
    ).fetchone()
    if not row:
        raise LookupError("no report waiting for approval with that id")
    return row


def evaluate(conn, version, ask=None, limit=None):
    """Rule 7: the version drafts a report for every child with signed-off answers, and code holds each to its facts.
    The bar is every one (rule 12). → {"n", "passed", "first_try", "failures", "sample"}."""
    kids = conn.execute(
        "select distinct child_id from evidence_event where confirmed_by is not null order by child_id"
    ).fetchall()[:limit]
    out = {
        "version": version,
        "n": 0,
        "passed": 0,
        "first_try": 0,
        "failures": [],
        "sample": None,
        "drafts": [],
    }
    for k in kids:
        try:
            got = draft(conn, k["child_id"], ask=ask, version=version)
        except llm.LLMError as e:  # one child's failure is counted, never the end of the others'
            got = {"problems": [str(e)]}
        if got is None:
            continue
        out["n"] += 1
        if got["problems"]:
            out["failures"].append({"child": str(k["child_id"])[:8], "problems": got["problems"]})
            continue
        out["passed"] += 1
        out["first_try"] += got["attempts"] == 1
        out["sample"] = out["sample"] or got["draft"]
        # every draft, to be read by a person: code holds the words to the facts, not to sense (v3: 10 of 10 held, and
        # one still said "leave four questions blank")
        out["drafts"].append({"child": str(k["child_id"])[:8], "draft": got["draft"]})
    return out
