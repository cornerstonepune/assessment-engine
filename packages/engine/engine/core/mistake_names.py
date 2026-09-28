"""A named mistake's name, for the operation it was made in.

One code can name a different mistake in each operation: `M_WRONG_OP` is "subtracted instead of adding" in an
addition, "added instead of subtracting" in a subtraction, "added instead of multiplying" in a multiplication — one
`misconception` row each (the table's key is code and op). A lookup by code alone keeps whichever row came last: on
2026-09-28 a live report called "763 children, 427 girls, how many boys? — wrote 1190" added-instead-of-multiplying.
The name is the one for the question's own operation; else the operation of the skill it was charged to
(`skills.by_operation`, read backwards); a code whose rows all share one name needs neither.
"""


def names(conn):
    """→ name_of(code, op=None, skill=None): the mistake's name for that operation, or its code when it cannot be told."""
    rows = conn.execute("select code, op, name from misconception").fetchall()
    exact = {(r["code"], r["op"]): r["name"] for r in rows}
    alone = {}
    for r in rows:
        alone.setdefault(r["code"], set()).add(r["name"])
    row = conn.execute("select value from config where key = 'skills.by_operation'").fetchone()
    op_of_skill = {skill: op for op, skill in (row["value"] if row else {}).items()}

    def name_of(code, op=None, skill=None):
        op = _op(op) or op_of_skill.get(skill)
        if (code, op) in exact:
            return exact[(code, op)]
        only = alone.get(code, set())
        return next(iter(only)) if len(only) == 1 else code

    return name_of


def _op(op):
    """The operation a question's spec writes, as the vocabulary writes it: a two-step story's first."""
    if not op:
        return None
    return {"*": "×", "x": "×"}.get(op[0], op[0])
