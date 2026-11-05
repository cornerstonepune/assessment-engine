"""People and enrolment: `engine staff import` and `engine enrol k2` (goals/m0-05-people-enrolment.yaml).

Two loaders, one rule for both. A dry run reads, compares and prints what it would do, and writes nothing; `apply` writes
it all in one transaction, and only if no row is refused. Running either twice changes nothing the second time. Neither
prints a name, an email, a phone number or a birthday: a report says line numbers and roll numbers.

`import_staff` copies the website's sign-in list (`config` key app.staff, left exactly as it is, password hashes and all)
into `staff`, `pii.staff` and a dated grant of the person's role. `enrol_k2` reads the school's Children List (number,
name, birthday), makes the K2 campus-year-class when it is not there, and enrols each child with the number as their roll
number. A child is made new unless `match_existing` says a child already sitting at that roll number in K2 is the same
person; a child's evidence, answers and state are never read or written here.
"""

import csv
import io
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import psycopg

from engine.core import db, signer
from engine.core import staff_write as write
from engine.core.report import Report
from engine.core.staff import staff as signin_list

DEFAULT_LETTER = "A"  # the class's own section within the grade (K2-A)
ROLL = re.compile(r"^[A-Za-z0-9-]{1,8}$")
COLUMNS = ("number", "name", "birthday")
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d %b %Y", "%d %B %Y")
AGE_YEARS = (2, 10)  # a birthday outside this is a typing slip for a K2 list, refused rather than stored


def _tenant(conn: db.Conn) -> Any:
    return db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]


def year_label(on: date) -> str:
    """The school year a date is in, April to March: 2026-11-03 → '2026-27'."""
    start = on.year if on.month >= 4 else on.year - 1
    return f"{start}-{(start + 1) % 100:02d}"


def parse_birthday(text: str, today: date) -> date:
    """→ the date, day first as the school writes it. A two-digit year, a date that is not a date, and an age outside
    K2's are refused, never guessed."""
    for fmt in DATE_FORMATS:
        try:
            d = datetime.strptime(text.strip(), fmt).date()
        except ValueError:
            continue
        low, high = AGE_YEARS
        if not date(today.year - high - 1, today.month, 1) < d <= date(today.year - low, today.month, 28):
            raise ValueError("that birthday is not a K2 child's — check the year")
        return d
    raise ValueError("birthday not read — write it 25/12/2020 or 2020-12-25")


# ---------------------------------------------------------------- staff import


def import_staff(conn: db.Conn, by: str, apply: bool) -> Report:
    """Copy each entry of the sign-in list into the staff tables. An entry already there (same email) is left. A role
    held for the whole campus is granted from today; a role held for a class or a child (the list's `specialist`) needs
    that class or child, so the person is added and the role is left to be set there. `config` is read, never written.
    `by` is the signer's email; grants carry their staff id, looked up once the staff rows exist (signer.py)."""
    out = Report()
    tenant = _tenant(conn)
    entries = signin_list(conn)
    if not signer.first_import_ok(conn, by, entries):
        out.refuse(signer.REFUSED_FIRST)
        return out
    grants: list[tuple[Any, str]] = []  # written last, when the signer is surely a member of staff
    scope = {
        r["code"]: r["scope"]
        for r in conn.execute("select code, scope from role where tenant_id = %s", (tenant,)).fetchall()
    }
    campus = db.one(conn, "select id from campus where tenant_id = %s", (tenant,))["id"]
    for n, entry in enumerate(entries, start=1):
        email, role = str(entry["email"]).strip().lower(), str(entry["role"])
        if role not in scope:
            out.refuse(f"entry {n}: the role {role!r} is not a role (roles: {', '.join(sorted(scope))})")
            continue
        here = conn.execute(
            "select staff_id from pii.staff where tenant_id = %s and email = %s", (tenant, email)
        ).fetchone()
        staff_id = here["staff_id"] if here else None
        campus_wide = scope[role] == "campus"
        if staff_id is None:
            out.count("staff added")
            how = (
                f"grant {role}" if campus_wide else f"{role} is held for a {scope[role]}: set it there later"
            )
            out.lines.append(f"  entry {n}: would add a member of staff; {how}")
            if not campus_wide:
                out.count("roles left to set")
        holds = (
            staff_id is not None
            and conn.execute(
                "select 1 from staff_role_grant where staff_id = %s and role_code = %s and valid_to is null",
                (staff_id, role),
            ).fetchone()
        )
        if staff_id is not None and campus_wide and not holds:
            out.count("roles granted")
            out.lines.append(f"  entry {n}: already on the list; would grant {role}")
        elif staff_id is not None:
            out.count("already there")
        if apply and not out.refused:
            grants += write.stage(
                conn, tenant, campus, entry, staff_id, role if campus_wide and not holds else ""
            )
    if apply and not out.refused:
        write.grant_all(conn, tenant, grants, signer.resolve(conn, by))
    return out


# ---------------------------------------------------------------- the class list


@dataclass
class Row:
    line: int
    roll: str
    first: str
    last: str
    born: date


def read_list(path: Path, today: date, out: Report) -> list[Row]:
    """The rows of the Children List that are clean, each refusal said by line. A file missing a column is refused whole;
    a number or a name or a birthday twice is refused on its second line."""
    text = Path(path).read_text(encoding="utf-8-sig")
    delim = "\t" if "\t" in (text.splitlines() or [""])[0] else ","
    rows = csv.reader(io.StringIO(text), delimiter=delim)
    head = [h.strip().lower() for h in next(rows, list[str]())]
    missing = [c for c in COLUMNS if c not in head]
    if missing:
        raise ValueError(
            f"the list has no column called {', '.join(missing)} — it needs a header row: {', '.join(COLUMNS)}"
        )
    at = {c: head.index(c) for c in COLUMNS}
    kept: list[Row] = []
    seen_roll: dict[str, int] = {}
    seen_child: dict[tuple[str, date], int] = {}
    for line, raw in enumerate(rows, start=2):
        if not any(cell.strip() for cell in raw):
            continue
        cell = {c: (raw[i].strip() if i < len(raw) else "") for c, i in at.items()}
        parts = cell["name"].split()
        if not ROLL.match(cell["number"]):
            out.refuse(
                f"line {line}: the number {cell['number']!r} is not a roll number (1 to 8 letters, digits or -)"
            )
            continue
        if not parts:
            out.refuse(f"line {line}: roll {cell['number']} has no name")
            continue
        try:
            born = parse_birthday(cell["birthday"], today)
        except ValueError as e:
            out.refuse(f"line {line}: roll {cell['number']}: {e}")
            continue
        who = (" ".join(parts).lower(), born)
        if cell["number"] in seen_roll:
            out.refuse(f"line {line}: roll {cell['number']} is also on line {seen_roll[cell['number']]}")
            continue
        if who in seen_child:
            out.refuse(f"line {line}: roll {cell['number']} is the same child as line {seen_child[who]}")
            continue
        seen_roll[cell["number"]], seen_child[who] = line, line
        kept.append(Row(line, cell["number"], parts[0], " ".join(parts[1:]), born))
    return kept


def _grade(conn: db.Conn, tenant: Any, name: str) -> str:
    """The code of the grade the command is named for (`k2`), from the `grade` table: a grade is a row, not a string here."""
    row = conn.execute(
        "select code from grade where tenant_id = %s and lower(code) = lower(%s)", (tenant, name.strip())
    ).fetchone()
    if row is None:
        raise ValueError(f"no grade called {name}")
    return str(row["code"])


def _class_ids(
    conn: db.Conn, tenant: Any, grade: str, year: str, letter: str, apply: bool, out: Report
) -> Any:
    """The K2 class of that year, made when it is not there. → its id, or None on a dry run that has no class yet."""
    campus = conn.execute("select id from campus where tenant_id = %s", (tenant,)).fetchall()
    if len(campus) != 1:
        raise ValueError(f"expected one campus, found {len(campus)}")
    y = conn.execute(
        "select id from academic_year where tenant_id = %s and label = %s", (tenant, year)
    ).fetchone()
    if y is None:
        out.lines.append(f"  would add the school year {year}")
        out.count("years added")
        if not apply:
            return None
        start = int(year[:4])
        y = db.one(
            conn,
            "insert into academic_year (tenant_id, label, starts_on, ends_on) values (%s,%s,%s,%s) returning id",
            (tenant, year, date(start, 4, 1), date(start + 1, 3, 31)),
        )
    c = conn.execute(
        "select id from school_class where tenant_id = %s and academic_year_id = %s and grade_code = %s"
        " and section = %s",
        (tenant, y["id"], grade, letter),
    ).fetchone()
    if c is None:
        out.lines.append(f"  would add the class {grade}-{letter} for {year}")
        out.count("classes added")
        if not apply:
            return None
        c = db.one(
            conn,
            "insert into school_class (tenant_id, campus_id, academic_year_id, grade_code, section)"
            " values (%s,%s,%s,%s,%s) returning id",
            (tenant, campus[0]["id"], y["id"], grade, letter),
        )
    return c["id"]


def _same_person(conn: db.Conn, child_id: Any, row: Row, by: str) -> bool:
    who = conn.execute("select * from pii.read_child(%s, %s)", (child_id, by)).fetchone()
    born = conn.execute("select birthday from pii.child where child_id = %s", (child_id,)).fetchone()
    return bool(
        who
        and who["first_name"].lower() == row.first.lower()
        and who["last_name"].lower() == row.last.lower()
        and (born is None or born["birthday"] in (None, row.born))
    )


def enrol_k2(
    conn: db.Conn,
    grade_name: str,
    path: Path,
    by: str,
    apply: bool,
    match_existing: bool = False,
    since: date | None = None,
    teacher: str | None = None,
    reason: str | None = None,
    letter: str = DEFAULT_LETTER,
) -> Report:
    """`by` is the signer's email, refused before anything is read unless it is a member of staff; rows carry their id."""
    out = Report()
    who = signer.resolve(conn, by) if by.strip() or apply else ""
    today = date.today()
    since = since or today
    rows = read_list(path, today, out)
    tenant = _tenant(conn)
    grade = _grade(conn, tenant, grade_name)
    class_id = _class_ids(conn, tenant, grade, year_label(since), letter, apply and not out.refused, out)
    actor = who or "engine enrol k2 (dry run)"
    plan: list[tuple[Row, Any, str]] = []  # the row, its existing child (or None), what to do
    for r in rows:
        child = conn.execute(
            "select id from child where tenant_id = %s and section = %s and roll_no = %s",
            (tenant, grade, r.roll),
        ).fetchone()
        if child is None:
            out.count("children added")
            plan.append((r, None, "new"))
            continue
        open_here = (
            class_id
            and conn.execute(
                "select 1 from enrolment where child_id = %s and class_id = %s and roll_no = %s and to_date is null",
                (child["id"], class_id, r.roll),
            ).fetchone()
        )
        if open_here and _same_person(conn, child["id"], r, actor):
            out.count("already there")
        elif match_existing and _same_person(conn, child["id"], r, actor):
            out.count("existing children enrolled")
            plan.append((r, child["id"], "existing"))
        else:
            out.refuse(
                f"line {r.line}: roll {r.roll} is already a different child in {grade}"
                + ("" if match_existing else " (if it is the same child, run again with --match-existing)")
            )
    if teacher:
        _plan_teacher(conn, tenant, grade, teacher, class_id, since, out, reason)
    if apply and not out.refused:
        for r, child_id, what in plan:
            if what == "new":
                child_id = db.one(
                    conn,
                    "insert into child (tenant_id, roll_no, band, section) values (%s,%s,%s,%s) returning id",
                    (tenant, r.roll, grade, grade),
                )["id"]
                conn.execute(
                    "insert into pii.child (tenant_id, child_id, first_name, last_name, birthday) values (%s,%s,%s,%s,%s)",
                    (tenant, child_id, r.first, r.last, r.born),
                )
            else:  # a child already there: the list's birthday is added only where none is held
                conn.execute(
                    "update pii.child set birthday = %s where child_id = %s and birthday is null",
                    (r.born, child_id),
                )
            conn.execute("select enrol_child(%s,%s,%s,%s,%s)", (child_id, class_id, r.roll, since, who))
        if teacher:
            _grant_teacher(conn, tenant, teacher, class_id, since, who, reason)
    return out


def _teacher(conn: db.Conn, tenant: Any, email: str) -> Any:
    return conn.execute(
        "select staff_id from pii.staff where tenant_id = %s and email = %s", (tenant, email.strip().lower())
    ).fetchone()


def _plan_teacher(
    conn: db.Conn,
    tenant: Any,
    grade: str,
    email: str,
    class_id: Any,
    since: date,
    out: Report,
    reason: str | None,
) -> None:
    person = _teacher(conn, tenant, email)
    if person is None:
        out.refuse("the class educator is not on the staff tables — run `engine staff import` first")
        return
    if class_id is None:
        out.count("class educators set")
        return
    holders = conn.execute(
        "select staff_id from staff_role_grant where school_class_id = %s and role_code = 'class_teacher'"
        " and (valid_to is null or valid_to > %s)",
        (class_id, since),
    ).fetchall()
    if any(h["staff_id"] == person["staff_id"] for h in holders):
        out.count("class educator already set")
    elif holders and not reason:
        out.refuse(
            f"warning: {grade} already has a class educator. To add this one as well, run again with"
            " --override-reason 'why' — the reason is kept"
        )
    else:
        out.count("class educators set")


def _grant_teacher(
    conn: db.Conn, tenant: Any, email: str, class_id: Any, since: date, by: str, reason: str | None
) -> None:
    person = _teacher(conn, tenant, email)
    held = conn.execute(
        "select 1 from staff_role_grant where staff_id = %s and school_class_id = %s and role_code = 'class_teacher'"
        " and valid_to is null",
        (person["staff_id"], class_id),
    ).fetchone()
    if not held:
        try:
            write.grant(conn, tenant, person["staff_id"], "class_teacher", since, by, class_id, reason)
        except psycopg.errors.RaiseException as e:
            raise ValueError(str(e.diag.message_primary)) from e
