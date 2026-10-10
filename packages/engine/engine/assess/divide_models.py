"""Division as the models a child meets first (goals/md3c-division-models.yaml): dots shared equally into rings, dots
ringed in equal groups, an array divided by its rows, one number taken away again and again to 0, and jumps back on a
number line to 0. Pure, no I/O.

Each draws its numbers from its level's rule as multiplication's models do (`times_models.py`): `groups`, how many
groups there are (rings, rows, jumps, times taken away), and `size`, how many in each. The number divided is their
product and the divisor is the one the question gives, so every question is the exact division `a ÷ b`, and its tags,
its key and the scenarios' check read it as one (ADR 0062). Each names the mistake behind every wrong answer it
predicts: multiplied, one group taken away, all of them counted, the number the question gives written for the one it
asks, the start counted as a jump. `pictures` draws each from the same numbers, so what the child sees and the key
cannot part.
"""

from random import Random
from typing import Any

from engine.assess.counting import named
from engine.assess.items import Item, Response, cells, item

# the mistakes a child makes with division's models, each a row of its own (supabase/seed/misconceptions.json)
ALL_COUNTED = "M_DIV_ALL_COUNTED"  # 12 dots shared into 3 rings, answered 12
GIVEN = "M_DIV_GROUPS_FOR_SIZE"  # answered 3, the rings: the number the question gives for the one it asks
START = "M_DIV_START_COUNTED"  # from 20 back to 0 in 4s, answered 6: the start counted as a jump
MISTAKES = (ALL_COUNTED, GIVEN, START)
METHODS = ("SHARING", "GROUPING", "ARRAY")  # the ways an equal-groups question divides


def _drawn(rng: Random, rule: dict[str, Any]) -> tuple[int, int]:
    """(groups, size) from the level's rule, each a [lo, hi] it names, or 2 to 5 where it names none."""
    groups: list[int] = rule.get("groups") or [2, 5]
    size: list[int] = rule.get("size") or [2, 5]
    return rng.randint(int(groups[0]), int(groups[-1])), rng.randint(int(size[0]), int(size[-1]))


def _done(a: int, b: int) -> list[tuple[str, int]]:
    """The two ways a division is done instead of found: the numbers multiplied, and one group taken away."""
    return [("M_WRONG_OP", a * b), ("M_DIV_SUBTRACTED", a - b)]


def equal_groups(rng: Random, rung: str, signal: str, rule: dict[str, Any]) -> Item:
    """A division as equal groups, by the case's method: dots shared equally into rings (SHARING: the rings are the
    divisor, how many in each the answer), dots ringed in groups of a size (GROUPING: the size is the divisor, how many
    groups the answer), or an array divided by its rows (ARRAY), read in three labelled boxes, in all ÷ rows = in each
    row."""
    method = rule.get("method")
    if method not in METHODS:
        raise ValueError(
            f"a division's equal groups are shared, grouped or an array ({', '.join(METHODS)}), not {method!r}"
        )
    groups, size = _drawn(rng, rule)
    a = groups * size
    b, q = (size, groups) if method == "GROUPING" else (groups, size)
    spec = {"a": a, "b": b, "op": "÷", "method": method}
    if method == "ARRAY":
        mis = named(q, [*_done(a, b), (GIVEN, b)])
        read = [
            Response("all", "digits", str(a), cells=cells(a), label="in all"),
            Response("rows", "digits", str(b), cells=cells(b), label="rows"),
            Response("ans", "digits", str(q), cells=cells(a), misconceptions=mis, label="in each row"),
        ]
        stem = "How many dots in all? How many rows? How many dots in each row?"
        return item("ARRAY.DIV", rung, signal, "equal_groups", stem, spec, read, working_lines=0)
    mis = named(q, [*_done(a, b), (ALL_COUNTED, a), (GIVEN, b)])
    if method == "SHARING":
        stem, label = (
            f"Share the {a} dots equally into the {b} rings. How many dots go in each ring?",
            "in each ring",
        )
    else:
        stem, label = f"Ring the {a} dots in groups of {b}. How many groups are there?", "groups"
    r = Response("ans", "digits", str(q), cells=cells(a), misconceptions=mis, label=label)
    return item("GROUPS.DIV", rung, signal, "equal_groups", stem, spec, [r], working_lines=0)


def repeated_subtraction(rng: Random, rung: str, signal: str, rule: dict[str, Any]) -> Item:
    """15 − 3 − 3 − 3 − 3 − 3 = 0, how many 3s: one number taken away again and again until nothing is left, printed
    whole from its numbers (`pictures`), the count of what is taken away the answer. Counting the number it starts from
    as one more, and writing the number taken away, are the mistakes it names."""
    q, b = _drawn(rng, rule)
    a = q * b
    mis = named(q, [(START, q + 1), (GIVEN, b)])
    r = Response("ans", "digits", str(q), cells=cells(a), misconceptions=mis, label=f"{b}s")
    spec = {"a": a, "b": b, "op": "÷", "method": "REPEATED_SUBTRACTION"}
    stem = f"How many {b}s are taken away to reach 0?"
    return item("TAKEN.AWAY", rung, signal, "repeated_subtraction", stem, spec, [r], working_lines=0)


def jumps_back(rng: Random, rung: str, signal: str, rule: dict[str, Any]) -> Item:
    """From 20, jumps of 4 back to 0: a line from 0 to 20 with a mark at every number and no jump drawn, for the child
    draws them; how many jumps is the answer. Writing where the first jump lands, counting the start as a jump, and
    writing the jump are the mistakes it names."""
    q, b = _drawn(rng, rule)
    a = q * b
    mis = named(q, [("M_DIV_SUBTRACTED", a - b), (START, q + 1), (GIVEN, b)])
    r = Response("ans", "digits", str(q), cells=cells(a), misconceptions=mis, label="jumps")
    spec = {"a": a, "b": b, "op": "÷", "method": "NUMBER_LINE"}
    stem = f"Start at {a}. Jump back {b} at a time to 0. How many jumps?"
    return item("NLINE.DIV", rung, signal, "number_line_jumps", stem, spec, [r], working_lines=0)
