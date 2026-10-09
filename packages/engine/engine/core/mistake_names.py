"""A named mistake's name, for the operation it was made in.

One code can name a different mistake in each operation: `M_WRONG_OP` is "subtracted instead of adding" in an
addition, "added instead of subtracting" in a subtraction, "added instead of multiplying" in a multiplication — one
`misconception` row each (the table's key is code and op). A lookup by code alone keeps whichever row came last: on
2026-09-28 a live report called "763 children, 427 girls, how many boys? — wrote 1190" added-instead-of-multiplying.
The name is the one for the question's own operation; else the operation of the skill it was charged to
(`skills.by_operation`, read backwards); a code whose rows all share one name needs neither.
"""

from collections.abc import Callable
from typing import Literal, overload

from engine.assess import operations as O
from engine.core import db

Field = Literal["name", "repair_hint", "description"]
FIELDS: tuple[Field, ...] = ("name", "repair_hint", "description")
NameOf = Callable[..., str]
HintOf = Callable[..., str | None]


@overload
def names(conn: db.Conn, field: Literal["name"] = "name") -> NameOf: ...
@overload
def names(conn: db.Conn, field: Literal["repair_hint", "description"]) -> HintOf: ...
def names(conn: db.Conn, field: Field = "name") -> HintOf:
    """→ name_of(code, op=None, skill=None): the mistake's name (or its `repair_hint`, what the school does about it)
    for that operation; the code when a name cannot be told, None when a hint cannot."""
    if field not in FIELDS:
        raise ValueError(f"a mistake has no {field!r} to look up")
    rows = conn.execute(f"select code, op, {field} as name from misconception").fetchall()
    exact = {(r["code"], r["op"]): r["name"] for r in rows}
    alone: dict[str, set[str]] = {}
    for r in rows:
        alone.setdefault(r["code"], set()).add(r["name"])
    row = conn.execute("select value from config where key = 'skills.by_operation'").fetchone()
    by_operation: dict[str, str] = row["value"] if row else {}
    op_of_skill = {skill: op for op, skill in by_operation.items()}

    def name_of(code: str, op: str | None = None, skill: str | None = None) -> str | None:
        op = _op(op) or (op_of_skill.get(skill) if skill else None)
        if (code, op) in exact:
            return exact[(code, op)]
        only = alone.get(code, set())
        return next(iter(only)) if len(only) == 1 else (code if field == "name" else None)

    return name_of


def _op(op: str | None) -> str | None:
    """The operation a question's spec writes, as the vocabulary writes it: a two-step story's first."""
    if not op:
        return None
    return O.sign(op[0]) or op[0]
