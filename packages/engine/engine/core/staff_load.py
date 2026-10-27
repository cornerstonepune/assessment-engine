"""A table of staff put on the list in one go: `engine staff load PATH [--apply]` (goals/staffload_a_table_of_staff.yaml).

Nimish, 27 Oct 2026: "I will give you a table of teachers and subjects and grades and you then do the needful."
The table has names and emails in it (rule 6), so it stays outside the repository and is read by path, as the class
list is. `plan` says, for every row, what it would do and writes nothing; `apply` writes the plan in one transaction.
Roles, classes and subjects are checked against the rows that hold them, exactly as `engine staff add` and the Staff
page check them, and a password is made here only for a person new to the list.
"""

import csv
import io
import os
import re
import secrets
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from engine.core import db
from engine.core.staff import classes, roles, save, staff, staff_hash

COLUMNS = ("name", "email", "role", "subjects", "classes")
# no 0 O 1 l I i o: a password read aloud or copied by hand is not mistaken for another
ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"
PASSWORD_LENGTH = 14
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class Line:
    """What one row of the table would do. `action` is add, update, same or refused."""

    row: int
    email: str
    name: str = ""
    role: str = ""
    classes: list[str] = field(default_factory=list[str])
    subjects: list[str] = field(default_factory=list[str])
    action: str = "refused"
    said: str = ""
    reads: list[str] = field(default_factory=list[str])
    change_role: bool = False


def read_table(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    """→ the rows, each by column, and one-line notes (columns ignored). A tab in the header line means a table copied
    from a spreadsheet; otherwise commas. A needed column that is not there is refused in words."""
    text = Path(path).read_text(encoding="utf-8-sig")
    first = text.splitlines()[0] if text.strip() else ""
    delimiter = "\t" if "\t" in first else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    header = next(reader, None) or list[str]()
    head = [h.strip().lower() for h in header]
    for needed in COLUMNS:
        if needed not in head:
            raise ValueError(
                f"the file has no column called {needed} — it needs a header row with {', '.join(COLUMNS)}"
            )
    notes = [f"ignored column: {h}" for h in head if h and h not in COLUMNS]
    rows: list[dict[str, str]] = []
    for cells in reader:
        if not any(c.strip() for c in cells):
            continue
        by = {h: (cells[i].strip() if i < len(cells) else "") for i, h in enumerate(head)}
        rows.append({c: by[c] for c in COLUMNS})
    return rows, notes


def _pieces(cell: str) -> list[str]:
    """Several values in one cell: commas, semicolons or spaces. A subject's own name may hold spaces, so the cell is
    cut at commas and semicolons first and a piece is cut at its spaces only where it is not a whole name (`_subjects`)."""
    return [p.strip() for p in re.split(r"[,;\n]", cell) if p.strip()]


def _subjects(cell: str, known: list[dict[str, Any]]) -> tuple[list[str], list[str], list[str]]:
    """→ (codes, which the dry run says it read as which code, unknown). A subject is its code, its name or its label,
    in any case."""
    by: dict[str, set[str]] = {}
    for s in known:
        for word in (s["code"], s["name"], s["label"]):
            if word:
                by.setdefault(word.casefold(), set()).add(s["code"])
    codes: list[str] = []
    reads: list[str] = []
    unknown: list[str] = []
    for piece in _pieces(cell):
        words = [piece] if piece.casefold() in by else piece.split()
        for w in words:
            found = by.get(w.casefold())
            if not found:
                unknown.append(w)
            elif len(found) > 1:
                unknown.append(f"{w} (it names {', '.join(sorted(found))})")
            else:
                [code] = found
                codes.append(code)
                if w != code:
                    reads.append(f"read {w!r} as {code}")
    return sorted(set(codes)), reads, unknown


def _said(codes: list[str], sections: list[str]) -> str:
    return f"classes {', '.join(sections) or 'none'}, subjects {', '.join(codes) or 'none'}"


def _refusal(
    conn: db.Conn, line: Line, held: set[str], times: int, sections: list[str], unknown: list[str]
) -> None:
    """Raise ValueError saying why a row cannot be applied; sets the row's classes when they are fine."""
    if not _EMAIL.match(line.email):
        raise ValueError(f"{line.email or 'a blank email'} is not shaped like an email")
    if times > 1:
        raise ValueError(f"{line.email} is in the file more than once")
    if not line.name:
        raise ValueError("no name")
    if line.role not in held:
        raise ValueError(f"no one holds the role {line.role!r} (it is one of {', '.join(sorted(held))})")
    line.classes = classes(conn, sections)
    if unknown:
        raise ValueError(f"no subject is called {', '.join(repr(u) for u in unknown)}")


def _decide(line: Line, me: dict[str, Any] | None, change_roles: bool = False) -> None:
    """Set what a fine row does against the person already on the list, if any. A person's role is changed only when
    the caller says so (`--change-roles`): who sees every class is not a thing a table should change by surprise."""
    if me is None:
        line.action, line.said = (
            "add",
            f"add — {line.name} ({line.role}), {_said(line.subjects, line.classes)}",
        )
        return
    was = str(me["role"]).lower()
    if was != line.role and not change_roles:
        line.said = (
            f"refused: already on the list as {me['role']}, and this tool changes only classes and subjects"
            " (add --change-roles to change the role as well)"
        )
    elif was == line.role and (me.get("classes", []), me.get("subjects", [])) == (
        line.classes,
        line.subjects,
    ):
        line.action, line.said = "same", "no change"
    else:
        line.action = "update"
        line.change_role = was != line.role
        role = f"role {was} to {line.role}, " if line.change_role else ""
        line.said = (
            f"update {role}classes and subjects from {_said(me.get('subjects', []), me.get('classes', []))}"
            f" to {_said(line.subjects, line.classes)}"
        )


def plan(conn: db.Conn, rows: Sequence[dict[str, str]], change_roles: bool = False) -> list[Line]:
    """→ one Line per row. Writes nothing."""
    people = {s["email"].lower(): s for s in staff(conn)}
    known = conn.execute(
        "select code, name, coalesce(label, '') as label from subject where tenant_id ="
        " (select id from tenant where slug = %s)",
        (db.tenant_slug(),),
    ).fetchall()
    held = roles(conn)
    times: dict[str, int] = {}
    for r in rows:
        e = r["email"].strip().lower()
        times[e] = times.get(e, 0) + 1
    lines: list[Line] = []
    for n, r in enumerate(rows, start=2):  # row 1 is the header
        email = r["email"].strip().lower()
        line = Line(n, email, r["name"].strip(), r["role"].strip().lower())
        lines.append(line)
        line.subjects, line.reads, unknown = _subjects(r["subjects"], known)
        try:
            _refusal(
                conn, line, held, times[email], [c for c in re.split(r"[,;\s]+", r["classes"]) if c], unknown
            )
        except ValueError as e:
            line.said = f"refused: {e}"
            continue
        _decide(line, people.get(email), change_roles)
    return lines


def new_password() -> str:
    """A one-time password from `secrets`, never a model: 14 characters of an alphabet with no look-alikes."""
    return "".join(secrets.choice(ALPHABET) for _ in range(PASSWORD_LENGTH))


def apply(conn: db.Conn, lines: Sequence[Line], cost: int) -> dict[str, str]:
    """Write the plan in the caller's transaction → `{email: one-time password}` for each person added. A person
    already on the list keeps everything but their classes and subjects (and their role, where the plan says so); a person
    not in the table is not read."""
    todo = {ln.email: ln for ln in lines if ln.action in ("add", "update")}
    given: dict[str, str] = {}
    out: list[dict[str, Any]] = []
    for s in staff(conn):
        ln = todo.pop(s["email"].lower(), None)
        out.append(
            {
                **s,
                "classes": ln.classes,
                "subjects": ln.subjects,
                **({"role": ln.role} if ln.change_role else {}),
            }
            if ln
            else s
        )
    for ln in todo.values():
        given[ln.email] = new_password()
        out.append(
            {
                "email": ln.email,
                "name": ln.name,
                "role": ln.role,
                "password": staff_hash(given[ln.email], secrets.token_hex(16), cost),
                "classes": ln.classes,
                "subjects": ln.subjects,
            }
        )
    if given or any(ln.action == "update" for ln in lines):
        save(conn, out)
    return given


def outside_repository(path: Path, what: str) -> Path:
    """→ the path, or a refusal if it lies inside the repository: a name, an email or a password must never be one
    `git add` away from a commit (rule 6)."""
    full = Path(path).expanduser().resolve()
    if full.is_relative_to(db.REPO_ROOT.resolve()):
        raise ValueError(
            f"{what} must be outside the repository (it holds names, emails or passwords): {path}"
        )
    return full


def write_private(path: Path, text: str) -> None:
    """Create a file only its owner can read (mode 600), refusing to overwrite one that is there."""
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise ValueError(f"{path} already exists — it is never overwritten; name a new file") from None
    with os.fdopen(fd, "w") as f:
        f.write(text)
