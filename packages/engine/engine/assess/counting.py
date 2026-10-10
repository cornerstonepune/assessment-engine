"""Questions a child answers by counting what the page draws — Grade 1's tally marks, and its start of multiplication
as equal groups added again (goals/g1-taught-till-september.yaml), and Grade 2's arrays
(goals/md2d1-multiplication-models.yaml). Pure, no I/O.

Each generator draws its numbers from a level's rule, computes the answer, and names the mistake behind each wrong
answer it predicts. `pictures` draws the tally and the groups from the same numbers, so what the child counts and
what the key says cannot part.
"""

from random import Random
from typing import Any, cast

from engine.assess import md_tags as MD
from engine.assess import words as W
from engine.assess.items import Item, Response, cells, item

# the shape a case asks for by its method: the one table that says what each shape is measured as, read backwards
SHAPE_OF = {v["method"]: shape for shape, v in MD.SHAPES.items() if "method" in v}


def one_of(value: Any, rng: Random) -> Any:
    """A rule value that may name one choice or several."""
    return rng.choice(cast(list[Any], value)) if isinstance(value, list) else value


def named(right: int, predicted: list[tuple[str, int]]) -> dict[str, Any]:
    """{mistake: the answer it gives}, in the order given, leaving out one whose answer is the right one or another's:
    a wrong answer two mistakes give names neither for certain."""
    out: dict[str, Any] = {}
    for code, wrong in predicted:
        if wrong != right and wrong not in out.values():
            out[code] = wrong
    return out


def tally(rng: Random, rung: str, signal: str, check: dict[str, Any]) -> Item:
    """READ: one tally, how many it shows. ALTOGETHER and MORE: two tallies, put together or compared. Every tally
    holds `lo` to `hi` lines, a bundle being four lines crossed by a fifth."""
    shape, lo, hi = one_of(check.get("shape", "READ"), rng), check.get("lo", 5), check.get("hi", 10)
    if shape == "READ":
        n, thing = rng.randint(lo, hi), rng.choice(W.THINGS)
        bundles, ones = divmod(n, 5)
        mis = named(
            n,
            [
                ("M_TALLY_FIVE_AS_FOUR", n - bundles),
                ("M_TALLY_CROSS_COUNTED", n + bundles),
                ("M_TALLY_BUNDLE_AS_ONE", bundles + ones),
            ]
            if bundles
            else [],
        )
        spec = {"shape": shape, "count": n, "thing": thing}
        r = Response("ans", "digits", str(n), cells=cells(n + bundles), misconceptions=mis)
        return item(
            "TALLY",
            rung,
            signal,
            "tally",
            f"How many {thing} does the tally show?",
            spec,
            [r],
            working_lines=0,
        )
    first, second = rng.sample(W.THINGS, 2)
    if shape == "MORE":  # two different tallies, the first the larger
        a, b = sorted(rng.sample(range(lo, hi + 1), 2), reverse=True)
        right, op, stem = a - b, "-", f"How many more {first} than {second} are there?"
        mis = named(right, [("M_WRONG_OP", a + b), ("M_TALLY_FIVE_AS_FOUR", (a - a // 5) - (b - b // 5))])
    else:
        a, b = rng.randint(lo, hi), rng.randint(lo, hi)
        right, op, stem = a + b, "+", f"How many {first} and {second} are there altogether?"
        mis = named(right, [("M_WRONG_OP", abs(a - b)), ("M_TALLY_FIVE_AS_FOUR", right - a // 5 - b // 5)])
    spec = {"shape": shape, "a": a, "b": b, "op": op, "things": [first, second]}
    r = Response("ans", "digits", str(right), cells=cells(a + b), misconceptions=mis)
    return item("TALLY2", rung, signal, "tally", stem, spec, [r], working_lines=0)


def equal_groups(rng: Random, rung: str, signal: str, check: dict[str, Any]) -> Item:
    """`groups` equal groups of `size`, how many in all: as the same number added again (SUM), as rings of dots
    (PICTURE), as a story (STORY), or as rows of dots (ARRAY) read in three labelled boxes, rows × in each row = in
    all, so the two numbers are never read the wrong way round. `a` is the number of groups (rows) and `b` the size of
    each, so the answer is a × b. A case names the shape by its method (G05 is an array): the shape it is printed as."""
    shape = SHAPE_OF.get(check.get("method") or "") or one_of(check.get("shape", "SUM"), rng)
    k, n = rng.randint(*check.get("groups", [2, 3])), rng.randint(*check.get("size", [2, 5]))
    if shape == "SUM":
        stem = "Add the equal groups."
        mis = named(k * n, [("M_GROUP_MISSED", (k - 1) * n)])
    else:
        mis = named(k * n, [("M_WRONG_OP", k + n), ("M_ONE_GROUP", n), ("M_GROUP_MISSED", (k - 1) * n)])
        stem = "How many dots are there in all?"
        if shape == "STORY":
            stem = rng.choice(W.templates("equal_groups"))["text"].format(a=k, b=n, n=rng.choice(W.NAMES))
    spec = {"shape": shape, "a": k, "b": n, "op": "×"}
    r = Response("ans", "digits", str(k * n), cells=cells(k * n), misconceptions=mis)
    if shape == "ARRAY":
        read = [
            Response("rows", "digits", str(k), cells=cells(k), label="rows"),
            Response("each", "digits", str(n), cells=cells(n), label="in each row"),
        ]
        stem = "How many rows? How many dots in each row? How many dots in all?"
        return item("ARRAY", rung, signal, "equal_groups", stem, spec, [*read, r], working_lines=0)
    return item("GROUPS", rung, signal, "equal_groups", stem, spec, [r], working_lines=0)
