"""N5 — papers for any children of one class at once (goal m3-the-maker).

Nimish, 2026-09-30: a class practice, a class assessment or a home assessment, for the children an educator picks,
made one of three ways:

- `same`, one paper for all ("the same skill paper for multiple children"): the same questions on every child's
  copy, none that any of them has been given;
- `each`, the same skill and level with different questions ("choose the right skill and the grade level, and then
  choose the children and generate different questions"): each child's own draw, no two sharing a question;
- `own`, each child's own ("individual papers for each child"): the next step their graph shows
  (`focus_paper.home_area`), which the educator may change for any child.

Every paper is drawn and printed as a child's home paper is (`focus_paper`): a template of its own, its own code, its
questions recorded as seen, its kind, class and week on the copy, approved in the educator's name — so it lands in
Papers and in the class's pack for that week and kind. `plan` writes nothing and is exactly what `make` prints. A home
assessment is one a child a week, whoever chose it.
"""

import random
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

from engine.w2_print import focus_paper, pack

KINDS = {"practice": "class practice", "assessment": "class assessment", "focus": "home assessment"}
WAYS = ("same", "each", "own")
# how the page says it was chosen: from the child's own papers, or by the educator
HOW = {"graph": focus_paper.HOW["focus"], "educator": focus_paper.HOW["custom"]}
# a child with no next step of their own: too little checked work, or nothing left in their skill they have not seen
NO_STEP = (
    "no next step to go on yet: too few checked answers, or no question left they have not seen — choose one"
)
ROLL = "coalesce(nullif(regexp_replace(c.roll_no, '\\D', '', 'g'), '')::int, 9999), c.roll_no"


def _class(conn, section: str, children: list) -> list:
    """The picked children in roll order: every one on the roll, and every one in `section`."""
    if not children:
        raise ValueError("pick at least one child")
    rows = conn.execute(
        f"select c.id, c.roll_no, c.section from child c where c.id = any(%s::uuid[]) and c.active order by {ROLL}",
        (list(children),),
    ).fetchall()
    if len(rows) != len(set(map(str, children))):
        raise ValueError("pick children who are on the roll")
    away = [r["roll_no"] for r in rows if r["section"] != section]
    if away:
        raise ValueError(f"not in {section}: roll {', '.join(away)} — one class at a time")
    return rows


def _for_all(conn, kids, week: str, ask: list) -> dict:
    """One paper for every child: the areas asked for, filled with questions none of them has been given — refused
    whole when the bank cannot fill it."""
    whose = [str(k["id"]) for k in kids]
    rng = random.Random("|".join([week, *sorted(whose)]))
    return focus_paper.drawn(conn, whose, focus_paper._asked(conn, [], ask), rng)


def plan(conn, section, children, week, kind, way, ask=None, changed=None) -> dict:
    """Each picked child's paper, question by question, in roll order, and each child whose paper cannot be made,
    with why. Nothing is written. `changed`: {child: areas} an educator put in place of that child's own next step."""
    if kind not in KINDS:
        raise ValueError(
            f"a paper is a class practice, a class assessment or a home assessment, not {kind!r}"
        )
    if way not in WAYS:
        raise ValueError(
            f"make one paper for all, the same skill for each, or each child's own — not {way!r}"
        )
    changed = {str(k): v for k, v in (changed or {}).items() if v}
    if way != "own" and not ask:
        raise ValueError("choose a skill, its level and how many questions")
    if changed and way != "own":
        raise ValueError("a change for one child is for each child's own next step")
    kids = _class(conn, section, children)
    if set(changed) - {str(k["id"]) for k in kids}:
        raise ValueError("a change names a child who is not picked")
    shared = _for_all(conn, kids, week, ask) if way == "same" else None
    papers, refused, taken = [], [], set()
    for k in kids:
        cid = str(k["id"])
        try:
            had = focus_paper.approved(conn, cid, week) if kind == "focus" else None
            if had:
                raise ValueError(
                    f"already has this week's home assessment: {had['qr']} by {had['approved_by']}"
                )
            mine = changed.get(cid) or (ask if way == "each" else None)
            p = shared or focus_paper.plan(conn, cid, week, mine, frozenset(taken))
            if not p["n"]:
                raise ValueError(NO_STEP)
        except ValueError as e:
            refused.append({"child_id": cid, "roll_no": k["roll_no"], "why": str(e)})
            continue
        if not shared:  # no two children of the batch share a question, but for one paper for all
            taken.update(q["id"] for a in p["areas"] for q in a["questions"])
        chosen = "graph" if way == "own" and cid not in changed else "educator"
        papers.append(
            {"child_id": cid, "roll_no": k["roll_no"], "chosen": chosen, "areas": p["areas"], "n": p["n"]}
        )
    return {"section": section, "week": week, "kind": kind, "way": way, "papers": papers, "refused": refused}


def make(conn, section, children, week, kind, way, by, ask=None, changed=None) -> dict:
    """`by` approves every paper `plan` shows, and each prints with its own code. Refused whole, naming each child
    whose paper cannot be made, rather than printing some of the class."""
    if not by:
        raise ValueError("a paper is approved in a person's name")
    # one batch at a time for a child: two educators making papers together cannot both print a child's week
    conn.execute("select id from child where id = any(%s::uuid[]) order by id for update", (list(children),))
    p = plan(conn, section, children, week, kind, way, ask, changed)
    if p["refused"]:
        raise ValueError("; ".join(f"roll {r['roll_no']}: {r['why']}" for r in p["refused"]))
    with sync_playwright() as pw:
        made = [
            focus_paper.print_paper(conn, x["child_id"], week, by, kind, x, HOW[x["chosen"]], pw)
            for x in p["papers"]
        ]
    return {"qrs": [m["qr"] for m in made], "papers": len(made), "pages": sum(m["pages"] for m in made)}


def pdf(conn, qrs: list) -> bytes:
    """The papers `qrs` as printed, one after another in class and roll order, as one PDF. Refuses a paper not
    approved for print, or not rendered on this machine: a batch with a hole in it is not the batch."""
    rows = conn.execute(
        "select si.qr_code, si.print_status, si.pdf_path from sheet_instance si"
        f" left join child c on c.id = si.child_id where si.qr_code = any(%s) order by si.section, {ROLL}",
        (list(qrs),),
    ).fetchall()
    if not qrs or len(rows) != len(set(qrs)):
        raise LookupError("no such paper")
    waiting = [r["qr_code"] for r in rows if r["print_status"] in ("new", "void")]
    if waiting:
        raise ValueError(f"not approved for print: {', '.join(waiting)}")
    missing = [r["qr_code"] for r in rows if not r["pdf_path"] or not Path(r["pdf_path"]).exists()]
    if missing:
        raise FileNotFoundError(f"not rendered on this machine: {', '.join(missing)}")
    with tempfile.TemporaryDirectory() as tmp:
        return pack.merge([r["pdf_path"] for r in rows], Path(tmp) / "papers.pdf").read_bytes()
