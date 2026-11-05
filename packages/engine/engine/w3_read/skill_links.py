"""A person's list of skills that come before others, and a member of staff's word that a link is right
(goals/m1-15-skill-links.yaml). N10, the skill graph.

`load` reads a CSV of pairs (before_code, after_code, reason, source, and strength if the list has it) and makes each a
PROPOSED link between two registry skills; `confirm` is one member of staff saying one link, by id, is right. Nothing
reads a proposed link (the views `skill_link_confirmed` and `skill_prerequisite_confirmed` show confirmed ones only), so
loading a list changes no paper and no child's map until a person confirms. Both go through two fixed database
functions; this file holds no SQL about the link tables and no free text reaches a shell. A link's two ends are
checked here for a message that names the line, and again by the database, which is the rule.
"""

import csv
import io
import uuid
from dataclasses import dataclass
from pathlib import Path

import psycopg

from engine.core import db, signer

REQUIRED = ("before_code", "after_code", "reason", "source")
OPTIONAL = ("strength",)


class Refused(Exception):
    """A list or a confirmation refused, in words a person can act on. Never carries an email or a name."""


@dataclass(frozen=True)
class Loaded:
    added: int
    there: int


def _rows(path: str | Path) -> list[tuple[int, dict[str, str]]]:
    """The pairs of a list, each with the line it starts on (line 1 is the header). A quoted reason may run over lines."""
    try:
        text = Path(path).read_text(encoding="utf-8-sig")
    except OSError:
        raise Refused(f"Cannot read the list at {path}.") from None
    reader = csv.DictReader(io.StringIO(text, newline=""))
    names = tuple(n.strip() for n in reader.fieldnames or ())
    missing = [n for n in REQUIRED if n not in names]
    extra = [n for n in names if n not in REQUIRED + OPTIONAL]
    if missing or extra:
        raise Refused(
            f"The list needs the columns {', '.join(REQUIRED)} (strength is optional); "
            + (f"missing {', '.join(missing)}" if missing else f"unknown {', '.join(extra)}")
            + "."
        )
    rows: list[tuple[int, dict[str, str]]] = []
    for r in reader:
        line = reader.line_num
        if None in r:
            raise Refused(f"line {line}: more values than columns (put a reason that has a comma in quotes).")
        rows.append((line, {(k or "").strip(): (v or "").strip() for k, v in r.items()}))
    if not rows:
        raise Refused("The list has no pairs in it.")
    return rows


def pairs(path: str | Path) -> list[dict[str, str]]:
    """The pairs a list holds, one dict each, or Refused if it cannot be read as a list."""
    return [row for _, row in _rows(path)]


def _line_problem(row: dict[str, str], skills: set[str], strengths: set[str]) -> str | None:
    """What is wrong with one pair, in words, or None."""
    for end in ("before_code", "after_code"):
        if row[end] not in skills:
            return f"{row[end] or '(empty)'} is not a skill in the registry"
    if row["before_code"] == row["after_code"]:
        return "a skill cannot come before itself"
    for name in ("reason", "source"):
        if not row[name]:
            return f"the {name} is empty"
    if row.get("strength") and row["strength"] not in strengths:
        return f"strength {row['strength']} is not one of {', '.join(sorted(strengths))}"
    return None


def load(conn: db.Conn, path: str | Path) -> Loaded:
    """Every pair in the list as a proposed link; a pair already there is left exactly as it is. All or nothing: the
    first pair that is wrong refuses the list, naming its line (line 1 is the header). Every line is read before any is
    written; a ring is found only by the database, as it writes, so the caller's transaction (`db.connect`) is what
    leaves nothing written when it raises."""
    rows = _rows(path)
    school = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
    skills = {
        r["code"] for r in conn.execute("select code from registry_skill where tenant_id = %s", (school,))
    }
    strengths = {
        r["code"] for r in conn.execute("select code from link_strength where tenant_id = %s", (school,))
    }
    for line, row in rows:
        problem = _line_problem(row, skills, strengths)
        if problem:
            raise Refused(f"line {line}: {problem}.")
    added = there = 0
    for line, row in rows:
        try:
            with conn.transaction():
                done = db.one(
                    conn,
                    "select public.propose_skill_link(%s, %s, %s, %s, %s, coalesce(nullif(%s, ''), 'hard')) as done",
                    (
                        school,
                        row["before_code"],
                        row["after_code"],
                        row["reason"],
                        row["source"],
                        row.get("strength", ""),
                    ),
                )["done"]
        except psycopg.errors.CheckViolation as e:
            if "come before itself" in (e.diag.message_primary or ""):
                raise Refused(
                    f"line {line}: {row['before_code']} before {row['after_code']} would make a ring "
                    "(a skill would come before itself)."
                ) from None
            raise Refused(
                f"line {line}: the database refuses it ({e.diag.constraint_name or 'a rule'})."
            ) from None
        added += done == "added"
        there += done == "there"
    return Loaded(added, there)


def confirm(conn: db.Conn, link_id: str, by: str) -> str:
    """One link confirmed by a member of staff of the school who is on the staff list and active: 'confirmed', or
    'already' when somebody confirmed it first (their word stands). Refused for an id that is no link's, and for an
    email that is not on the staff list."""
    try:
        wanted = uuid.UUID(link_id.strip())
    except ValueError:
        raise Refused("That is not a link's id (a long code of letters, digits and dashes).") from None
    try:
        staff = signer.resolve(conn, by)
    except ValueError as refused:
        raise Refused(str(refused)) from None
    word = db.one(conn, "select public.confirm_skill_link(%s, %s) as word", (wanted, staff))["word"]
    if word == "not staff":
        raise Refused("That member of staff is no longer active.")
    if word == "no link":
        raise Refused("There is no link with that id.")
    if word == "no confirming state":
        raise Refused("The school's link states hold none that means confirmed.")
    return word
