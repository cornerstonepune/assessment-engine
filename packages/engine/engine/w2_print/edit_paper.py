"""W2/N7 — an educator reviews a child's paper, removes a question or adds one from the bank, and approves it
(goals/paper_review_add_remove.yaml). Nimish, 2026-10-27: "they should see a page where they can look at the actual
questions, and that should have an add/remove button".

A paper's code, the boxes the reader looks for and its answer key belong to what was printed with that code, so an edit
never changes a paper in place. It makes the paper again from the questions now chosen, exactly as a paper is first
made (`focus_paper.print_paper`): a template, a new code, the page and its key rendered. The earlier copy is set void,
and a copy of it already in a child's hands still reads and marks as itself. Each edit is a `paper_edit` row, never
changed (rule 4). An approved paper edited waits for approval again; a printed one is refused.

Printed means the paper left the screen: its print was opened (`printed`, a `flow_run` this module writes when the
print PDF is fetched), it was said given (`given.py`), or a copy of it was uploaded. A page printed from the browser's
own menu is not seen; the new code is what keeps that copy right.
"""

from engine.core import db, settings
from engine.w2_print import focus_paper, given, shelf

PRINTED = "printed"
LIMITS = ("assessment.min_questions", "assessment.max_questions")
MOST_OFFERED = 60  # questions listed in the last dropdown; the bank holds about fifty a skill and level
_PAPER = (
    "select si.id, si.tenant_id, si.qr_code as qr, si.child_id, si.section, si.week, si.kind, si.print_status,"
    " si.approved_by, si.approved_at, si.key, t.item_ids, t.source from sheet_instance si"
    " join sheet_template t on t.id = si.sheet_template_id where si.qr_code = %s"
)
_QUESTIONS = (
    "select i.id, i.item_key, i.fmt, i.stem, i.spec, i.difficulty as level, i.skill_set_code as skill_set,"
    " s.name as skill, tp.code as topic, tp.name as topic_name, k.code as kind, k.words as kind_words"
    " from unnest(%s::uuid[]) with ordinality as x(id, n) join item i on i.id = x.id"
    " left join skill s on s.tenant_id = i.tenant_id and s.code = i.skill_set_code"
    " left join topic tp on tp.tenant_id = s.tenant_id and tp.code = s.topic_code"
    " left join question_type k on k.tenant_id = i.tenant_id and k.code = question_type_of(i.fmt, i.template)"
    " order by x.n"
)


def _paper(conn, qr: str, lock: bool = False) -> dict:
    row = conn.execute(_PAPER + (" for update of si" if lock else ""), (qr,)).fetchone()
    if row is None:
        raise LookupError(f"{qr} is not a paper of this school")
    return row


def printed_why(conn, p: dict) -> str:
    """Why the paper counts as printed, in the educator's words; "" while it has not left the screen."""
    if conn.execute("select 1 from capture where sheet_instance_id = %s", (p["id"],)).fetchone():
        return "Answers from it are already uploaded."
    for flow, words in ((given.GIVEN, "It was given out."), (PRINTED, "Its print was opened.")):
        if conn.execute(
            "select 1 from flow_run where flow = %s and request -> 'qrs' ? %s", (flow, p["qr"])
        ).fetchone():
            return words
    return ""


def state(conn, p: dict) -> tuple[str, str]:
    """(replaced, printed, waiting or approved; why it is printed)."""
    if p["print_status"] == "void":
        return "replaced", ""
    why = printed_why(conn, p)
    if why:
        return "printed", why
    return ("waiting" if p["approved_by"] is None else "approved"), ""


def limits(conn) -> tuple[int, int]:
    """The fewest and most questions a paper may hold: the `assessment.*_questions` threshold rows."""
    low, high = (settings.threshold(conn, k, float("nan")) for k in LIMITS)
    if low != low or high != high:  # NaN: a row is missing, and no number is made up for it
        raise LookupError(f"the threshold rows {' and '.join(LIMITS)} are needed")
    return int(low), int(high)


def questions(conn, ids: list) -> list[dict]:
    """The questions, in order, each with its text, skill, topic, level and kind."""
    rows = conn.execute(_QUESTIONS, (list(ids),)).fetchall()
    return [{**r, "id": str(r["id"]), "text": focus_paper.question_text(r)} for r in rows]


def covers(qs: list[dict]) -> list[dict]:
    """Each skill and level the questions test, in the order they first come, with how many."""
    out: dict = {}
    for q in qs:
        k = (q["skill_set"], q["level"])
        out.setdefault(k, {"skill_set": k[0], "name": q["skill"] or k[0], "level": k[1], "n": 0})["n"] += 1
    return list(out.values())


def newer(conn, qr: str) -> str | None:
    """The code an edit replaced this paper with, following every later edit; None for a paper never edited."""
    now = None
    while row := conn.execute(
        "select qr_after from paper_edit where qr_before = %s", (now or qr,)
    ).fetchone():
        now = row["qr_after"]
    return now


def review(conn, qr: str) -> dict:
    """The paper as its review page shows it: its questions in order, what it covers, its state, the limits, and
    whether it can be changed (`why_not`)."""
    p = _paper(conn, qr)
    st, why = state(conn, p)
    qs = questions(conn, p["item_ids"])
    low, high = limits(conn)
    why_not = {
        "replaced": "This paper was changed; the newer one is the one to use.",
        "printed": f"This paper is already printed. Make a new one to change it. {why}",
    }.get(st) or (
        "" if p["source"] == "focus" and p["child_id"] else "A library worksheet is not changed here."
    )
    return {
        **{k: p[k] for k in ("qr", "section", "week", "kind", "approved_by", "approved_at")},
        "child_id": str(p["child_id"]) if p["child_id"] else None,
        "state": st,
        "why_not": why_not.strip(),
        "newer": newer(conn, qr) if st == "replaced" else None,
        "questions": qs,
        "covers": covers(qs),
        "min": low,
        "max": high,
        "pages": (p["key"] or {}).get("pages", 0),
    }


def _refuse_if_fixed(conn, p: dict) -> bool:
    """Refuses a paper an edit may not change; True when the edit withdraws an approval."""
    st, why = state(conn, p)
    if st == "printed":
        raise PermissionError(f"This paper is already printed. Make a new one to change it. {why}".strip())
    if st == "replaced":
        raise PermissionError(f"This paper was changed since: use {newer(conn, p['qr'])}.")
    if p["source"] != "focus" or not p["child_id"]:
        raise PermissionError("A library worksheet is not changed here.")
    return st == "approved"


def _edit(conn, qr: str, by: str, ids: list, removed=(), added=(), at=None) -> dict:
    """The paper made again with `ids`, the earlier copy void, the edit kept. Refused, nothing written, past a limit."""
    if not by.strip():
        raise ValueError("an edit is made in a person's name")
    p = _paper(conn, qr, lock=True)
    withdrew = _refuse_if_fixed(conn, p)
    low, high = limits(conn)
    if len(ids) < low:
        raise ValueError(
            f"A paper keeps at least {low} question{'s' * (low != 1)}: this would leave {len(ids)}."
        )
    if len(ids) > high:
        raise ValueError(f"A paper holds at most {high} questions, and this one has {len(p['item_ids'])}.")
    qs = questions(conn, ids)
    key = p["key"] or {}
    made = focus_paper.print_paper(
        conn, str(p["child_id"]), p["week"], by, p["kind"], {"areas": covers(qs)},
        key.get("how") or focus_paper.HOW["custom"], ids=ids, waiting=True,
    )  # fmt: skip
    conn.execute(
        "update sheet_instance set print_status = 'void', updated_at = now() where id = %s", (p["id"],)
    )
    conn.execute(
        "insert into paper_edit (tenant_id, child_id, qr_before, qr_after, removed, added, at_position,"
        " withdrew_approval, changed_by) values (%s,%s,%s,%s,%s::uuid[],%s::uuid[],%s,%s,%s)",
        (p["tenant_id"], p["child_id"], qr, made["qr"], list(removed), list(added), at, withdrew, by.strip()),
    )
    before = {(c["skill_set"], c["level"]): c for c in covers(questions(conn, p["item_ids"]))}
    after = {(c["skill_set"], c["level"]) for c in covers(qs)}
    gone = [f"{c['name']} · {c['level']}" for k, c in before.items() if k not in after]
    return {"qr": made["qr"], "was": qr, "n": len(ids), "withdrew_approval": withdrew, "uncovered": gone}


def remove(conn, qr: str, item_id: str, by: str) -> dict:
    """`by` takes one question off the paper."""
    ids = [str(i) for i in _paper(conn, qr)["item_ids"]]
    if item_id not in ids:
        raise LookupError("That question is not on this paper.")
    return _edit(conn, qr, by, [i for i in ids if i != item_id], removed=[item_id])


def add(conn, qr: str, item_id: str, by: str, at: int | None = None) -> dict:
    """`by` puts a question from the bank on the paper: at position `at` (1 the first), or at the end. Only a question
    a paper may draw now (`drawable_item`: active, its level confirmed, its kind approved and not stopped)."""
    ids = [str(i) for i in _paper(conn, qr)["item_ids"]]
    if item_id in ids:
        raise ValueError("That question is already on this paper.")
    if not conn.execute("select 1 from drawable_item where id = %s", (item_id,)).fetchone():
        raise LookupError("That question is no longer used: it was retired, or its kind was stopped.")
    where = len(ids) if at is None else min(max(at, 1), len(ids) + 1) - 1
    return _edit(conn, qr, by, [*ids[:where], item_id, *ids[where:]], added=[item_id], at=where + 1)


def approve(conn, qr: str, by: str) -> dict:
    """`by` approves a paper waiting for approval: it may now be printed, and the child is given its questions."""
    if not by.strip():
        raise ValueError("an approval must name a person")
    p = _paper(conn, qr, lock=True)
    st, why = state(conn, p)
    if st != "waiting":
        raise PermissionError(
            {"approved": f"Already approved by {p['approved_by']}."}.get(
                st, why or "This paper was changed since."
            )
        )
    conn.execute(
        "update sheet_instance set print_status = 'printed', printed_at = now(), approved_by = %s,"
        " approved_at = now(), updated_at = now() where id = %s",
        (by.strip(), p["id"]),
    )
    if p["child_id"]:
        shelf.seen_by(conn, p["tenant_id"], p["child_id"], p["week"], p["item_ids"])
    return {"qr": qr, "approved_by": by.strip()}


def print_opened(conn, qrs: list[str], by: str) -> None:
    """The print PDF of these approved papers was fetched: from now on they are printed, and an edit is refused."""
    tenant = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
    given._keep(conn, tenant, PRINTED, by or "the website", "print opened", {"qrs": list(qrs), "by": by})


def bank(conn, qr: str, topic=None, skill=None, level=None, kind=None) -> dict:
    """The add dropdowns, each narrowing the next, every option a row: topics, the topic's skills, the skill's levels
    (the `difficulty` rows, in order), the kinds at that level, and its questions not on the paper, each with how many
    days ago the child was given it inside `exposure.days` (`days`, None if not). Only what a paper may draw now."""
    p = _paper(conn, qr)
    out: dict = {"topics": conn.execute(
        "select distinct t.code, t.name, t.ord from drawable_item d join skill s on s.tenant_id = d.tenant_id"
        " and s.code = d.skill_set_code join topic t on t.tenant_id = s.tenant_id and t.code = s.topic_code"
        " order by t.ord, t.code"
    ).fetchall(), "skills": [], "levels": [], "kinds": [], "questions": []}  # fmt: skip
    if topic:
        out["skills"] = conn.execute(
            "select distinct s.code, s.name, s.ladder_order from drawable_item d join skill s on s.tenant_id ="
            " d.tenant_id and s.code = d.skill_set_code where s.topic_code = %s order by s.ladder_order, s.code",
            (topic,),
        ).fetchall()
    if skill:
        out["levels"] = conn.execute(
            "select f.code from difficulty f where exists (select 1 from drawable_item d where d.tenant_id ="
            " f.tenant_id and d.skill_set_code = %s and d.difficulty = f.code) order by f.ord",
            (skill,),
        ).fetchall()
    if skill and level:
        out["kinds"] = conn.execute(
            "select k.code, k.words from question_type k where exists (select 1 from drawable_item d where"
            " d.tenant_id = k.tenant_id and d.skill_set_code = %s and d.difficulty = %s and d.question_type = k.code)"
            " order by k.words",
            (skill, level),
        ).fetchall()
        rows = conn.execute(
            "select d.id from drawable_item d where d.skill_set_code = %s and d.difficulty = %s"
            " and (%s::text is null or d.question_type = %s) and not d.id = any(%s::uuid[]) order by d.item_key"
            " limit %s",
            (skill, level, kind, kind, p["item_ids"], MOST_OFFERED),
        ).fetchall()
        days = _given_days(conn, p["child_id"], [r["id"] for r in rows])
        out["questions"] = [
            {**q, "days": days.get(q["id"])} for q in questions(conn, [r["id"] for r in rows])
        ]
    return out


def _given_days(conn, child_id, ids: list) -> dict[str, int]:
    """{question: days since the child was last given it}, for those inside the `exposure.days` window."""
    if not child_id or not ids:
        return {}
    window = settings.exposure_days(conn)
    return {
        str(r["item_id"]): r["days"]
        for r in conn.execute(
            "select item_id, (current_date - max(created_at)::date) as days from item_exposure"
            " where child_id = %s and item_id = any(%s::uuid[]) group by item_id"
            " having max(created_at) > now() - make_interval(days => %s)",
            (child_id, ids, window),
        )
    }
