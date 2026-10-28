"""People taken off the staff list: `engine staff remove EMAIL [EMAIL ...] [--apply]` (goals/staffrm_remove_a_person.yaml).

Nimish found a placeholder entry on the live list, the text `your-email` with a coordinator's password and every class,
and nothing could remove it. `plan` says, for every email named, what removal would do and writes nothing; `apply` writes
it in the caller's transaction. Unlike the loader, an email is not checked for its shape: the entry that started this is
not shaped like one. Only the `app.staff` row changes. What the removed person signed stays as it was (rule 4): those
rows hold their email or name as plain text, never a key to this list.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

from engine.core import db
from engine.core.staff import save, staff


@dataclass
class Line:
    """What removing one email would do. `action` is remove or refused."""

    email: str
    action: str = "refused"
    said: str = ""


def _can_sign_in(people: Sequence[dict[str, Any]]) -> bool:
    return any(str(s["role"]).lower() == "coordinator" and s.get("password") for s in people)


def plan(conn: db.Conn, emails: Sequence[str]) -> list[Line]:
    """→ one Line per email, in the order given. Writes nothing."""
    people = staff(conn)
    by = {s["email"].lower(): s for s in people}
    asked = [e.strip().lower() for e in emails]
    times = Counter(asked)
    lines = [Line(e) for e in asked]
    for ln in lines:
        if times[ln.email] > 1:
            ln.said = "refused: named more than once in this command"
        elif ln.email not in by:
            ln.said = "refused: is not on the staff list"
        else:
            me = by[ln.email]
            ln.action, ln.said = "remove", f"would remove {me['name']} ({me['role']})"
    going = {ln.email for ln in lines if ln.action == "remove"}
    if going and not _can_sign_in([s for s in people if s["email"].lower() not in going]):
        for ln in lines:
            if ln.action == "remove":
                ln.action, ln.said = "refused", "refused: that would leave no coordinator who can sign in"
    return lines


def apply(conn: db.Conn, lines: Sequence[Line]) -> list[dict[str, Any]]:
    """Take the planned people off the list, in the caller's transaction → those removed. Everyone else is written back
    exactly as read. Refuses a plan with a refusal in it, so a half is never applied."""
    if any(ln.action != "remove" for ln in lines):
        raise ValueError("a refused email is in the plan, so nothing is removed")
    going = {ln.email for ln in lines}
    people = staff(conn)
    gone = [s for s in people if s["email"].lower() in going]
    save(conn, [s for s in people if s["email"].lower() not in going])
    return gone
