"""What a K2 activity page lacks, counted by code (goals/m1-11-k2-complete-v1.yaml, task M1-11).

A page has eight parts. This counts the ones left empty, in the sheet and in the database, and finds the one kind of
disagreement a rule can see: a name and an objective that give different number ranges ("Number names 11-20" whose
objective says "numbers from 6-10"). A flagged row goes to a person; nothing here changes a word. Every other kind of
disagreement needs a reader's judgement and is a model's question later, never decided here.
"""

import re
from typing import LiteralString, cast

PARTS = ("objective", "steps", "thinking", "materials", "level_0", "level_1", "level_2", "level_3")
PAGE_PARTS = tuple(p for p in PARTS if p != "materials")  # the ones an agent drafts as text
RANGE = re.compile(r"(\d+)\s*(?:-|–|—|to)\s*(\d+)")


def column(part: str) -> LiteralString:
    """A page part's column name: only a part of a page ever reaches SQL as a name, never a caller's string."""
    if part not in PAGE_PARTS:
        raise ValueError(f"{part} is not a part of a page")
    return cast(LiteralString, part)


def empty_parts(row: dict, parts: tuple[str, ...] = PAGE_PARTS) -> list[str]:
    """The parts of this one row that are empty (a cell of spaces is empty)."""
    return [p for p in parts if not (row.get(p) or "").strip()]


def empties(rows: list[dict]) -> dict[str, int]:
    """Each part, with how many of the rows leave it empty (a cell of spaces is empty)."""
    return {p: sum(1 for r in rows if not (r.get(p) or "").strip()) for p in PARTS}


def _ranges(text: str) -> list[tuple[int, int]]:
    out = []
    for a, b in RANGE.findall(text or ""):
        lo, hi = sorted((int(a), int(b)))
        out.append((lo, hi))
    return out


def inconsistencies(rows: list[dict]) -> list[tuple[str, str]]:
    """Rows whose name and objective both give number ranges and no range of one overlaps a range of the other."""
    out = []
    for r in rows:
        named, stated = _ranges(r.get("name", "")), _ranges(r.get("objective", ""))
        if not named or not stated:
            continue
        if not any(a1 <= b2 and a2 <= b1 for a1, b1 in named for a2, b2 in stated):
            out.append(
                (
                    r.get("code", ""),
                    f"name says {named[0][0]}-{named[0][1]}, objective says {stated[0][0]}-{stated[0][1]}",
                )
            )
    return out


def _block(title: str, rows: list[dict]) -> list[str]:
    n = len(rows)
    lines = [f"{title}: {n} activities"]
    lines += [f"  {part:<10} empty {k} of {n}" for part, k in empties(rows).items()]
    found = inconsistencies(rows)
    lines.append(f"  inconsistent, name and objective disagree (to a person, nothing changed): {len(found)}")
    lines += [f"    {code}: {why}" for code, why in found[:10]]
    if len(found) > 10:
        lines.append(f"    … and {len(found) - 10} more")
    return lines


def report(sheet_rows: list[dict], db_rows: list[dict]) -> str:
    """The gaps in the sheet's rows and, where the database has rows, in the database's."""
    out = _block("gaps in the sheet", sheet_rows)
    if db_rows:
        out += _block("gaps in the database now", db_rows)
    return "\n".join(out)
