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
import threading
from datetime import date

from engine.adapters import llm
from engine.core import db
from engine.w4_close import parent_review
from engine.w4_close.parent_check import check, numbers_in  # noqa: F401 — the words held to the facts
from engine.w4_close.parent_facts import facts  # every fact the report may state, from the signed-off answers

PURPOSE = "parent_report"
FLOW = "parent_report_write"  # the run a person looks at while a report is written (`/runs/{id}`)
# One report is written at a time: each holds a connection for a minute or more, and the database's pooler allows 15.
# 2026-09-29 on live, twelve started together: three were refused "EMAXCONNSESSION ... pool_size: 15". The rest wait
# their turn, their runs saying "running"
WRITING = threading.Lock()


def draft(conn, child_id, ask=None, version=None, review_version=None):
    """→ {"facts", "draft", "problems", "prompt_id", "attempts"}: the model's words for the facts, held to them by code
    and then read against them by a second model (`parent_review`); sent back with what either found, three tries in
    all. None when there is nothing signed off to report."""
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
            # what a sentence means only a reader holds: v7-v12 each passed the check and still said "mastered" of a
            # skill only improving, and made thirty-five a three-digit number
            problems = problems or parent_review.review(conn, f, out, ask=ask, version=review_version)
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


def start(child_id, by):
    """The run the page watches while a report is written. Committed on its own connection before the writing
    starts, as a scan's is (`w3_read/inbox.start`): writing and reading a draft twice over takes longer than the
    site's thirty seconds, so the request answers first and the writing follows."""
    with db.connect() as conn:
        return str(
            conn.execute(
                "insert into flow_run (tenant_id, flow, trigger) select id, %s, %s from tenant where slug = %s"
                " returning id",
                (FLOW, f"{by}: {child_id}", db.tenant_slug()),
            ).fetchone()["id"]
        )


def write(run_id, child_id):
    """Draft, hold, read and keep one child's report on its own connection, the run marked ok or with why not."""
    with WRITING, db.connect() as conn:
        try:
            got = draft(conn, child_id)
            why = (
                "no answer of this child's has been signed off yet"
                if got is None
                else got["problems"]
                and "not kept, it still said what its facts do not: " + "; ".join(got["problems"])
            )
            if not why:
                keep(conn, child_id, got)
        except Exception as e:  # the run says why; the request that started it has already answered
            conn.rollback()
            why = f"{type(e).__name__}: {e}"
        conn.execute(
            "update flow_run set status = %s, error = %s, finished_at = now(), updated_at = now() where id = %s",
            ("error" if why else "ok", (why or None) and why[:2000], run_id),
        )
        conn.commit()


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
        "edited_by": body.get("edited_by"),
        "stale": now != body["facts"],
    }


def _current(conn, child_id, note_id):
    """Only the child's newest report, still true of their answers, is edited or approved. The page hides both buttons
    otherwise, but a page left open is not refreshed when answers are signed off or the facts' rules change."""
    now = latest(conn, child_id)
    if not now or now["id"] != str(note_id):
        raise LookupError("a newer report has replaced this one; read that one")
    if now["stale"]:
        raise LookupError("this report is out of date: what it rests on has changed since; write it again")


def edit(conn, child_id, note_id, words, by):
    """An educator's own words for a report not yet approved, held to the same facts as the model's were, kept as a
    new version beside the one it replaces; the newest is the report. Nimish, 2026-09-29: "an option for the educator
    to also edit the draft ... and then that can become the report"."""
    if not by:
        raise ValueError(["an edit names the educator making it"])
    _current(conn, child_id, note_id)
    row = conn.execute(
        "select body, week, prompt_version, approved_by from parent_note where id::text = %s and child_id = %s",
        (note_id, child_id),
    ).fetchone()
    if not row or row["approved_by"]:
        raise LookupError("no report waiting for approval with that id")
    f = json.loads(row["body"])["facts"]
    problems = check(f, words)
    if problems:
        raise ValueError(problems)
    return conn.execute(
        # the clock's own time, not the transaction's: the edit is newer than the draft it replaces even when both
        # are written in one transaction, and the newest is the report
        "insert into parent_note (tenant_id, child_id, week, body, prompt_version, created_at)"
        " select t.id, %s, %s, %s, %s, clock_timestamp() from tenant t where t.slug = %s returning id",
        (
            child_id,
            row["week"],
            json.dumps({"facts": f, "draft": words, "edited_by": by}),
            row["prompt_version"],
            db.tenant_slug(),
        ),
    ).fetchone()


def approve(conn, child_id, note_id, by):
    """An educator approves the report, by name, once; what they approved is what a parent sees."""
    if not by:
        raise ValueError("an approval names the educator giving it")
    _current(conn, child_id, note_id)
    row = conn.execute(
        "update parent_note set approved_by = %s where id::text = %s and child_id = %s and approved_by is null"
        " returning id",
        (by, note_id, child_id),
    ).fetchone()
    if not row:
        raise LookupError("no report waiting for approval with that id")
    return row


def evaluate(conn, version, ask=None, limit=None, review_version=None):
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
            got = draft(conn, k["child_id"], ask=ask, version=version, review_version=review_version)
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
