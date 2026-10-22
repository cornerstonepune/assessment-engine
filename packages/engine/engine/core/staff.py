"""Who signs in to the website: the staff list, `config.app.staff`, the database's alone (goals/ui4a-staff-and-search.yaml).

Each person is an email, a name, a role, and the classes they teach (ADR 0073, D1: the grade follows from the class;
the coordinator's classes are every class). The seed's list is empty, so no one's email is in the public repository.
A person signs in with their school Google account (goals/a1-sign-in-with-google.yaml): a school email new to the list
joins it as `app.sign_in` says, and `engine staff add`, run by Nimish on his own machine, puts someone on it first with
another role (the coordinator).
"""

import json
from collections.abc import Sequence
from typing import Any

from engine.core import db


def staff(conn: db.Conn) -> list[dict[str, Any]]:
    row = conn.execute("select value from config where key = 'app.staff'").fetchone()
    people: list[dict[str, Any]] = row["value"] if row else []
    return people


def roles(conn: db.Conn) -> set[str]:
    """The roles a person may hold: those the school's decisions name (`people.decides`), and any someone on the list
    already holds. A row, not a list in code."""
    row = conn.execute("select value from config where key = 'people.decides'").fetchone()
    decides: dict[str, list[str]] = row["value"] if row else {}
    named = {r for who in decides.values() for r in who}
    return named | {str(s["role"]) for s in staff(conn)}


def save(conn: db.Conn, people: list[dict[str, Any]]) -> None:
    conn.execute("update config set value = %s where key = 'app.staff'", (json.dumps(people),))


def classes(conn: db.Conn, wanted: Sequence[str]) -> list[str]:
    """The classes named, each once and in order, every one a class a child still in school is in; a typed class that
    is no class refuses them all, so a slip never narrows someone to a class that is not there."""
    named = sorted({c.strip() for c in wanted if c.strip()})
    there = {r["section"] for r in conn.execute("select distinct section from child where active").fetchall()}
    missing = [c for c in named if c not in there]
    if missing:
        raise ValueError(f"no child is in class {', '.join(missing)} — nothing changed")
    return named


def add(conn: db.Conn, email: str, name: str, role: str, teaches: Sequence[str] = ()) -> dict[str, Any]:
    """→ the person as put on the list. Refuses an email already on it, a role no decision names, and a class no child
    is in, changing nothing."""
    email = email.strip().lower()
    people = staff(conn)
    if any(s["email"].lower() == email for s in people):
        raise ValueError(f"{email} is already on the staff list — nothing changed")
    if role not in roles(conn):
        raise ValueError(f"no one holds the role {role!r}: it is one of {', '.join(sorted(roles(conn)))}")
    person = {
        "email": email,
        "name": name.strip(),
        "role": role,
        "classes": classes(conn, teaches),
    }
    save(conn, [*people, person])
    return person


def set_classes(conn: db.Conn, email: str, teaches: Sequence[str]) -> dict[str, Any]:
    """→ the person with the classes they now teach. Refuses someone not on the list and a class no child is in."""
    people = staff(conn)
    me = next((s for s in people if s["email"].lower() == email.strip().lower()), None)
    if me is None:
        raise ValueError(
            f"{email} is not on the staff list — nothing changed (engine staff add puts them on)"
        )
    me["classes"] = classes(conn, teaches)
    save(conn, people)
    return me
