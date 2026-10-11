"""Who signs in to the website: the staff list, `config.app.staff`, the database's alone (goals/ui4a-staff-and-search.yaml).

Each person is an email, a name, a role and a password hash the website checks. The seed's list is empty, so no
one's email is in the public repository; a person is put on the list by `engine staff add`, run by Nimish on his own
machine, and their password is typed there and nowhere else.
"""

import hashlib
import json
from typing import Any

from engine.core import db


def staff_hash(password: str, salt: str) -> str:
    """`scrypt$salt$hash` exactly as `apps/web/lib/auth.ts` checks it: node's `scryptSync` defaults
    (N=16384, r=8, p=1), 64 bytes, and the hex salt used as TEXT, not decoded — node takes a string
    salt as its UTF-8 bytes, and decoding it here would make every password look wrong."""
    digest = hashlib.scrypt(password.encode(), salt=salt.encode(), n=16384, r=8, p=1, dklen=64)
    return f"scrypt${salt}${digest.hex()}"


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


def add(conn: db.Conn, email: str, name: str, role: str, password: str) -> dict[str, Any]:
    """→ the person as put on the list. Refuses an email already on it and a role no decision names, changing nothing."""
    email = email.strip().lower()
    people = staff(conn)
    if any(s["email"].lower() == email for s in people):
        raise ValueError(f"{email} is already on the staff list — nothing changed")
    if role not in roles(conn):
        raise ValueError(f"no one holds the role {role!r}: it is one of {', '.join(sorted(roles(conn)))}")
    person = {"email": email, "name": name.strip(), "role": role, "password": password}
    save(conn, [*people, person])
    return person
