"""An educator stops a kind of question at a level, or across a skill, and can start it again (goals/gen_retire_a_kind.yaml).
Nimish, 2026-10-26: "the educator also, today, does not want certain types of questions. They should be able to delete
those kinds of questions from the bank itself."

Answers already given to a question must stay readable (rule 4), so a stop deletes nothing. It is a row of
`skill_level_kind_stop`, never changed, and `drawable_item` leaves the kind out at that level: no new paper draws it, and
every past paper keeps its questions and their meaning. An approved paper not yet given that holds one goes back for
approval, never changed silently, and is named. The level's approval is withdrawn, as any edit of it does. A restart is
another row. `touches` says what a stop would touch before anything is written.
"""

from typing import Any

from engine.core import db
from engine.w1_bank import english_edit

# The papers a stop touches: of these questions, not void
_PAPERS = (
    "from sheet_instance si join sheet_template t on t.id = si.sheet_template_id"
    " where si.print_status <> 'void' and t.item_ids && %(items)s::uuid[]"
)
# Of those, the ones approved and not yet given: this week's or later, no word that it was given, nothing read from it
_NOT_GIVEN = (
    " and si.approved_by is not null and si.print_status in ('printed', 'with_teacher')"
    " and coalesce(si.week, t.week) >= to_char(now() at time zone 'Asia/Kolkata', 'IYYY-\"W\"IW')"
    " and not exists (select 1 from capture k where k.sheet_instance_id = si.id)"
    " and not exists (select 1 from flow_run f where f.flow = 'given' and f.request -> 'qrs' ? si.qr_code)"
)


def _tenant(conn: db.Conn) -> db.Id:
    return db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]


def _levels(conn: db.Conn, code: str, kind: str, level: str | None) -> list[str]:
    """The levels of `code` that ask `kind`, in the school's order: `level` alone, or every one."""
    return [
        r["difficulty"]
        for r in conn.execute(
            "select x.difficulty from skill_level_question_type x"
            " join difficulty d on d.tenant_id = x.tenant_id and d.code = x.difficulty"
            " where x.skill_code = %s and x.question_type = %s and (%s::text is null or x.difficulty = %s)"
            " order by d.ord",
            (code, kind, level, level),
        )
    ]


def _stopped(conn: db.Conn, code: str, level: str) -> set[str]:
    return {
        r["question_type"]
        for r in conn.execute(
            "select question_type from kind_stopped where skill_code = %s and difficulty = %s", (code, level)
        )
    }


def _items(conn: db.Conn, code: str, kind: str, levels: list[str]) -> list[db.Id]:
    """The questions of `kind` in the bank at these levels (retired ones too: a past paper may hold them)."""
    return [
        r["id"]
        for r in conn.execute(
            "select id from item where skill_set_code = %s and difficulty = any(%s)"
            " and question_type_of(fmt, template) = %s",
            (code, levels, kind),
        )
    ]


def _not_given(conn: db.Conn, items: list[db.Id]) -> list[str]:
    return [
        r["qr_code"]
        for r in conn.execute(
            f"select si.qr_code {_PAPERS}{_NOT_GIVEN} order by si.qr_code", {"items": items}
        )
    ]


def touches(conn: db.Conn, code: str, kind: str, level: str | None = None) -> dict[str, Any]:
    """What stopping `kind` would touch, writing nothing: {levels, questions (in use in the bank), papers (past, not
    void, holding one), withdraw (the codes of the approved papers not yet given that would go back for approval)}."""
    levels = [x for x in _levels(conn, code, kind, level) if kind not in _stopped(conn, code, x)]
    items = _items(conn, code, kind, levels)
    active = db.one(
        conn, "select count(*) as n from item where id = any(%s::uuid[]) and status = 'active'", (items,)
    )["n"]
    papers = db.one(conn, f"select count(distinct si.id) as n {_PAPERS}", {"items": items})["n"]
    return {"levels": levels, "questions": active, "papers": papers, "withdraw": _not_given(conn, items)}


def stop(conn: db.Conn, code: str, kind: str, by: str, level: str | None = None) -> dict[str, Any]:
    """`by` stops `kind` at `level`, or at every level of `code` that asks it. {stopped, why, levels, questions, papers,
    withdrawn}: refused in words, with nothing written, for no person, a kind not asked there, one already stopped,
    or a level left with no kind in use."""

    def refuse(why: str) -> dict[str, Any]:
        return {"stopped": False, "why": why, "levels": [], "questions": 0, "papers": 0, "withdrawn": []}

    if not by.strip():
        return refuse("Say who stops it.")
    conn.execute("select pg_advisory_xact_lock(hashtext(%s))", (f"kind_stop {code}",))
    if not _levels(conn, code, kind, level):
        return refuse("This skill does not ask that kind of question" + (f" at {level}." if level else "."))
    said = touches(conn, code, kind, level)
    if not said["levels"]:
        return refuse("That kind is already stopped there.")
    for x in said["levels"]:
        if not set(english_edit.level_kinds(conn, code, x)) - _stopped(conn, code, x) - {kind}:
            return refuse(
                f"A level keeps at least one kind of question in use; {x} has no other. Add one first."
            )
    tenant, withdrawn = _tenant(conn), []
    for x in said["levels"]:
        back = _not_given(conn, _items(conn, code, kind, [x]))
        conn.execute(
            "update sheet_instance set print_status = 'new', printed_at = null, approved_by = null,"
            " approved_at = null, updated_at = now() where qr_code = any(%s)",
            (back,),
        )
        _row(conn, tenant, code, x, kind, True, by, back)
        english_edit.withdraw(conn, code, x)
        withdrawn += back
    return {
        "stopped": True,
        "why": "",
        **{k: said[k] for k in ("levels", "questions", "papers")},
        "withdrawn": withdrawn,
    }


def start(conn: db.Conn, code: str, kind: str, by: str, level: str | None = None) -> dict[str, Any]:
    """`by` starts `kind` again where it was stopped: at `level`, or at every level of `code`. {started, why, levels}."""
    if not by.strip():
        return {"started": False, "why": "Say who starts it again.", "levels": []}
    conn.execute("select pg_advisory_xact_lock(hashtext(%s))", (f"kind_stop {code}",))
    levels = [x for x in _levels(conn, code, kind, level) if kind in _stopped(conn, code, x)]
    if not levels:
        return {"started": False, "why": "That kind is not stopped there.", "levels": []}
    tenant = _tenant(conn)
    for x in levels:
        _row(conn, tenant, code, x, kind, False, by, [])
        english_edit.withdraw(conn, code, x)
    return {"started": True, "why": "", "levels": levels}


def _row(conn, tenant, code, level, kind, stopped, by, withdrawn) -> None:
    conn.execute(
        "insert into skill_level_kind_stop (tenant_id, skill_code, difficulty, question_type, stopped, withdrawn,"
        " changed_by) values (%s, %s, %s, %s, %s, %s, %s)",
        (tenant, code, level, kind, stopped, withdrawn, by.strip()),
    )
