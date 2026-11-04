"""Who signed a people load: a staff id, never a typed name or email (CLAUDE.md rule 6, D-046).

`--by` on `engine staff import` and `engine enrol k2` is the signer's EMAIL. It is looked up through
`public.staff_of_email` (engine only: lower-cases, returns the staff id, writes the lookup to the access log), and the
id, as text, is what `staff_role_grant.granted_by` and `enrolment.recorded_by` hold, because the website can read those
two columns and must never find a person's name or email in them. A signer who matches no one (or two) is refused in
words that do not repeat what was typed. Nothing here prints an email.
"""

from typing import Any

from engine.core import db

REFUSED = (
    "--by must be the email you sign in with, of a member of staff already on the staff tables"
    " (`engine staff import` puts them there)"
)
REFUSED_FIRST = (
    "--by must be the email you sign in with: a member of staff already on the staff tables, or on the website's"
    " sign-in list (the first `engine staff import` makes them)"
)


def lookup(conn: db.Conn, email: str) -> str | None:
    """→ the staff id (text) of the email, or None when nobody has it or two do."""
    found = conn.execute("select public.staff_of_email(%s) as id", (email.strip().lower(),)).fetchone()
    return str(found["id"]) if found and found["id"] else None


def resolve(conn: db.Conn, email: str) -> str:
    """→ the signer's staff id, or a ValueError saying `--by` is not a member of staff."""
    who = lookup(conn, email) if email.strip() else None
    if who is None:
        raise ValueError(REFUSED)
    return who


def first_import_ok(conn: db.Conn, email: str, sign_in_list: list[dict[str, Any]]) -> bool:
    """`engine staff import` is how the first staff exist, so its signer may be on the website's sign-in list and not on
    the staff tables yet; the id is looked up after the run has made them. No `--by` (a dry run) is nobody to check."""
    mine = email.strip().lower()
    return (
        not mine
        or lookup(conn, mine) is not None
        or mine in {str(e["email"]).strip().lower() for e in sign_in_list}
    )
