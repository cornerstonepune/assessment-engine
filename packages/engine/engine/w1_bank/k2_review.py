"""A person's three answers to a drafted part of a K2 page: keep it, change it, reject it (D-073, task M1-11).

The engine's side of the screens' buttons. Only a part marked drafted can be answered: the school's own words, and a part
a person has already made theirs, are refused, so nothing the school wrote is ever changed through here. Who answered is
kept by id (D-046), on the part's mark and in the curriculum's edit history.
"""

from typing import LiteralString

from psycopg.types.json import Jsonb

from engine.core import db
from engine.w1_bank import map_ledger
from engine.w1_bank.k2_format import LISTS, edited, render
from engine.w1_bank.k2_gaps import column
from engine.w1_bank.map_agents import sampled
from engine.w1_bank.map_ledger import changed_by


def _column(conn: db.Conn, tenant: db.Id, code: str, part: str) -> LiteralString:
    """The part's column, once the part is a part of a page and is marked drafted."""
    col = column(part)  # a column name never comes from a caller
    mark = conn.execute(
        "select 1 from activity_part_source where tenant_id = %s and activity_code = %s and part = %s"
        " and source = 'drafted'",
        (tenant, code, part),
    ).fetchone()
    if not mark:
        raise ValueError(
            f"{code} {part} is not a drafted part: it is the school's words, or already a person's"
        )
    return col


def _made_theirs(conn: db.Conn, tenant: db.Id, staff: db.Id, code: str, part: str) -> None:
    conn.execute(
        "update activity_part_source set source = 'person', check_me = false, staff_id = %s, updated_at = now()"
        " where tenant_id = %s and activity_code = %s and part = %s",
        (staff, tenant, code, part),
    )


def keep(conn: db.Conn, tenant: db.Id, staff: db.Id, code: str, part: str) -> None:
    """The draft stays as written and becomes the person's: its doubt is cleared."""
    _column(conn, tenant, code, part)
    _made_theirs(conn, tenant, staff, code, part)


def change(conn: db.Conn, tenant: db.Id, staff: db.Id, code: str, part: str, value: object) -> None:
    """The person's own words in place of the draft's: text, or for the steps a list and for the thinking an idea with
    its slips (the text beside is written from the list, so the site reads either)."""
    col = _column(conn, tenant, code, part)
    made = edited(part, value)
    changed_by(conn, f"staff:{staff}")
    listed = LISTS.get(part)
    structured = made if not isinstance(made, str) else None
    conn.execute(
        f"update activity set {col} = %s{f', {listed} = %s' if listed else ''} where tenant_id = %s and code = %s",  # noqa: S608
        (render(part, made), *((Jsonb(structured) if structured else None,) if listed else ()), tenant, code),
    )
    _made_theirs(conn, tenant, staff, code, part)


def reject(conn: db.Conn, tenant: db.Id, staff: db.Id, code: str, part: str) -> None:
    """The draft goes: the part is empty again and carries no mark."""
    col = _column(conn, tenant, code, part)
    changed_by(conn, f"staff:{staff}")
    listed = LISTS.get(part)
    conn.execute(
        f"update activity set {col} = ''{f', {listed} = null' if listed else ''} where tenant_id = %s and code = %s",  # noqa: S608
        (tenant, code),
    )
    conn.execute(
        "delete from activity_part_source where tenant_id = %s and activity_code = %s and part = %s",
        (tenant, code, part),
    )


def review_list(conn: db.Conn, tenant: db.Id) -> list[dict]:
    """The drafted pages a person reads, in order: those tagged check_me first, then the audit share (`map.audit_share`,
    D-063) of the rest, drawn by code (the same draw every time). Each: the page's code, check_me, the proposal's reason."""
    share = map_ledger.rules(conn)["audit_share"]
    rows = conn.execute(
        "select p.subject_code as code, p.reason, bool_or(s.check_me) as check_me from curriculum_proposal p"
        " join activity_part_source s on s.tenant_id = p.tenant_id and s.proposal_id = p.id and s.source = 'drafted'"
        " where p.tenant_id = %s and p.kind = 'page_part' and p.about is null group by p.id, p.subject_code, p.reason"
        " order by p.subject_code",
        (tenant,),
    ).fetchall()
    doubtful = [dict(r) for r in rows if r["check_me"]]
    rest = [dict(r) for r in rows if not r["check_me"] and sampled("page_part", r["code"], share)]
    return [*doubtful, *rest]
