"""A person's three answers to a drafted part of a K2 page: keep it, change it, reject it (D-073, task M1-11).

The engine's side of the screens' buttons. Only a part marked drafted can be answered: the school's own words, and a part
a person has already made theirs, are refused, so nothing the school wrote is ever changed through here. Who answered is
kept by id (D-046), on the part's mark and in the curriculum's edit history.
"""

from typing import LiteralString, cast

from engine.core import db
from engine.w1_bank.k2_gaps import PAGE_PARTS


def _column(conn: db.Conn, tenant: db.Id, code: str, part: str) -> LiteralString:
    """The part's column, once the part is a part of a page and is marked drafted."""
    if part not in PAGE_PARTS:  # a column name never comes from a caller
        raise ValueError(f"{part} is not a part of a page")
    mark = conn.execute(
        "select 1 from activity_part_source where tenant_id = %s and activity_code = %s and part = %s"
        " and source = 'drafted'",
        (tenant, code, part),
    ).fetchone()
    if not mark:
        raise ValueError(
            f"{code} {part} is not a drafted part: it is the school's words, or already a person's"
        )
    return cast(LiteralString, part)


def _made_theirs(conn: db.Conn, tenant: db.Id, staff: db.Id, code: str, part: str) -> None:
    conn.execute(
        "update activity_part_source set source = 'person', check_me = false, staff_id = %s, updated_at = now()"
        " where tenant_id = %s and activity_code = %s and part = %s",
        (staff, tenant, code, part),
    )


def _by(conn: db.Conn, staff: db.Id) -> None:
    conn.execute("select set_config('app.changed_by', %s, true)", (f"staff:{staff}",))


def keep(conn: db.Conn, tenant: db.Id, staff: db.Id, code: str, part: str) -> None:
    """The draft stays as written and becomes the person's: its doubt is cleared."""
    _column(conn, tenant, code, part)
    _made_theirs(conn, tenant, staff, code, part)


def change(conn: db.Conn, tenant: db.Id, staff: db.Id, code: str, part: str, text: str) -> None:
    """The person's own words in place of the draft's."""
    col = _column(conn, tenant, code, part)
    if not text.strip():
        raise ValueError("a part changed to nothing is a rejected draft: use reject")
    _by(conn, staff)
    conn.execute(
        f"update activity set {col} = %s where tenant_id = %s and code = %s",  # noqa: S608
        (text.strip(), tenant, code),
    )
    _made_theirs(conn, tenant, staff, code, part)


def reject(conn: db.Conn, tenant: db.Id, staff: db.Id, code: str, part: str) -> None:
    """The draft goes: the part is empty again and carries no mark."""
    col = _column(conn, tenant, code, part)
    _by(conn, staff)
    conn.execute(f"update activity set {col} = '' where tenant_id = %s and code = %s", (tenant, code))  # noqa: S608
    conn.execute(
        "delete from activity_part_source where tenant_id = %s and activity_code = %s and part = %s",
        (tenant, code, part),
    )
