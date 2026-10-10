"""Finding the mistake and judging a claim (taxonomy §11; rungs X1, X2). Deterministic given an RNG.

`find_mistake` shows another child's worked answer with one named mistake planted in it. The mistake is
chosen (`planted`) from every one the taxonomy's §11 lists and the predictors can compute: a column
slip in addition, subtraction or multiplication (`assess/mul_mistakes.py`: products side by side, carries left
out, a carry onto a zero lost, the second row not moved), numbers lined up from the left, a carry of 1 where the
column needs 2,
a subtraction turned round, a missing digit that works in its own column only, = read as "the answer
comes next". A column answer asks which digit of the child's answer is wrong first — a column the
engine can check — then the right answer, then why; where its mistake always puts that digit in the same column, it
asks only the answer and why (`asks_where`).

`explain_claim` asks whether a statement about a calculation is true, and why (moved from `items.py`).
"""

import functools
import random
from collections.abc import Callable
from typing import Any

from . import misconceptions as M
from . import operations as O
from . import times_kinds as TK
from . import written_methods as WM
from .items import Item, Response, cells, item, sample_add, sample_sub

NAMES = ["Ishaan", "Anaya", "Vihaan", "Saee", "Tara", "Arjun"]
COLUMNS = ["ones", "tens", "hundreds", "thousands", "ten-thousands"]
COLUMN_SLIPS = {
    "+": ["M_NOCARRY", "M_CARRY_SKIP", "M_CONCAT", "M_DROP_CARRYOUT", "M_ZERO_DROPPED"],
    "-": [
        "M_SMALL_FROM_LARGE",
        "M_NO_DECREMENT",
        "M_ZERO_LENDER",
        "M_ZERO_NOT_NINE",
        "M_EXCHANGE_WRONG_PLACE",
        "M_ZERO_DROPPED",
    ],
}
# a multiplication's: the number of digits each number has is its level's (2 × 1, 3 × 1, 2 × 2)
COLUMN_SLIPS["×"] = ["M_MUL_NO_CARRY", "M_MUL_CONCAT", "M_MUL_CARRY_ONTO_ZERO_LOST", "M_MUL_PLACEHOLDER"]
# the numbers a × slip needs when no level says: a zero for the carry to land on, a second row to leave unmoved
NEEDS = {"M_MUL_CARRY_ONTO_ZERO_LOST": (3, 1), "M_MUL_PLACEHOLDER": (2, 2)}
ACROSS_ZERO = {"M_ZERO_LENDER", "M_ZERO_NOT_NINE"}
ALIGNED = {"M_ALIGN_LEFT", "M_H2V_SHIFT"}
SHAPES = {
    "M_CARRY_ALWAYS_1": "three",
    "M_SUB_INSTEAD": "reversed",
    "M_MISSING_DIGIT_LOCAL": "digit",
    "M_EQUALS_MEANS_ANSWER": "equals",
    "M_PARTITION_TENS_AS_ONES": "partitioned",  # C06: 23 × 4 worked as 2 × 4 + 3 × 4 = 20
}
PLANTABLE = set(COLUMN_SLIPS["+"]) | set(COLUMN_SLIPS["-"]) | set(COLUMN_SLIPS["×"]) | ALIGNED | set(SHAPES)
COUNTED = 2000  # calculations a slip's columns are counted over (`_columns`)
# one calculation drawn for a slip: (the column its first wrong digit is in, (a, b, every mistake it shows))
Drawn = tuple[int, tuple[int, int, dict[str, int]]] | None


def _first_wrong_column(right: int, wrong: int) -> int:
    r, w = str(right)[::-1], str(wrong)[::-1]
    for i in range(max(len(r), len(w))):
        if (r[i : i + 1] or "0") != (w[i : i + 1] or "0"):
            return i
    return 0


def _where(right, wrong):
    width = max(len(str(right)), len(str(wrong)))
    opts = [f"{c} column" for c in COLUMNS[:width]]
    return Response(
        "where",
        "tick",
        opts[_first_wrong_column(right, wrong)],
        options=opts,
        label="The first wrong digit is in the",
    )


def _why(code):
    name = next(
        (t[code][1] for t in (*M.TABLES.values(), M.MULTI_PREDICTORS) if code in t), WM.NAMES.get(code)
    )
    return Response("why", "text", None, rubric=f"Names the mistake: {name or code}")


def _spread[T](
    rng: random.Random, draw: Callable[[], tuple[int, T] | None], what: str, tries: int = 80, enough: int = 10
) -> T:
    """One of `tries` drawn candidates, its column chosen evenly among the columns the candidates' first wrong
    digit falls in. Asked "which column is the first wrong digit in?", a child who ticks the same box every time
    must not score: drawn as they come, a carry of 2 was always in the tens and a smaller-from-larger slip in the
    ones 83 times in 100 (`engine audit`, 2026-09-23). A mistake that can only ever show in one column is not
    asked the column at all (`asks_where`)."""
    by: dict[int, list[T]] = {}
    kept = 0
    for _ in range(tries):
        got = draw()
        if got is not None:
            col, cand = got
            by.setdefault(col, []).append(cand)
            kept += 1
            if kept == enough:  # ten candidates see every column a mistake commonly shows, and stay quick
                break
    if not by:
        raise RuntimeError(f"no question shows {what}")
    return rng.choice(by[rng.choice(sorted(by))])


def _times(rng: random.Random, code: str, sizes: tuple[int, int]) -> tuple[int, int]:
    """A multiplication of these digit counts, no table fact and nothing round, a carry onto a zero where that is
    the mistake: 506 × 7."""
    d1, d2 = sizes
    if d1 < 2:
        raise O.CannotMake(f"{code} needs a number of 2 digits or more: 1 digit by 1 is a table fact")
    while True:
        a = rng.randint(10 ** (d1 - 1), 10**d1 - 1)
        if code == "M_MUL_CARRY_ONTO_ZERO_LOST" and d1 >= 3:
            a = a - (a // 10 % 10) * 10  # the tens a zero
        b = rng.randint(2 if d2 == 1 else 10 ** (d2 - 1), 10**d2 - 1)
        if a > 12 and a % 10 and b % 10:
            return a, b


def _shown(op: str, code: str, a: int, b: int, mis: dict[str, int]) -> Drawn:
    """The calculation with the column its first wrong digit is in, or None where it does not show this slip."""
    seen = "M_ALIGN_LEFT" if code in ALIGNED else code  # a sum copied out of a line is lined up from the left
    if seen not in mis:
        return None
    mis = mis | {code: mis[seen]}
    return _first_wrong_column(M.compute(op, a, b), mis[code]), (a, b, mis)


def _drawn(rng: random.Random, code: str, op: str, sizes: tuple[int, int]) -> Drawn:
    """One calculation drawn the way this slip's question draws it, its two numbers `sizes` digits long (lined up from
    the left, the second the shorter), or None where its numbers do not show the slip."""
    d1, d2 = sizes
    if op == "×":
        a, b = _times(rng, code, sizes)
    elif code in ALIGNED:
        short = d2 if d2 < d1 else rng.randint(1, max(1, d1 - 1))
        a, b = (sample_add if op == "+" else sample_sub)(rng, max(d1, 2), short, {0, 1, 2})
    elif op == "+":
        a, b = sample_add(rng, d1, d2, {1, 2, 3})
    else:
        a, b = sample_sub(rng, d1, d2, {1, 2}, across_zero=code in ACROSS_ZERO)
    return _shown(op, code, a, b, M.predict(op, a, b))


@functools.cache
def _columns(code: str, op: str, sizes: tuple[int, int]) -> frozenset[int]:
    """The columns this slip's first wrong digit falls in, over `COUNTED` calculations drawn as its questions are,
    from a seed of their own so every run counts the same; none where numbers of these sizes cannot show it."""
    rng = random.Random(0)
    return frozenset(got[0] for got in (_drawn(rng, code, op, sizes) for _ in range(COUNTED)) if got)


def asks_where(spec: dict[str, Any]) -> bool:
    """Whether a worked answer's question asks which column its first wrong digit is in: not where its mistake, on
    numbers these sizes, always puts it in the same one, where a child ticking that box every time would score.
    ADD.2D1D's Advance plants only numbers lined up from the left (always the ones), ADD.4D's only a final carry
    dropped (always the top), MUL.3D1D's only a carry lost onto a zero (always the tens). Mistakes of their own
    shape (`SHAPES`) decide their own questions."""
    code, op = spec.get("planted"), O.sign(spec.get("op"))
    if op is None or code not in set(COLUMN_SLIPS.get(op, [])) | ALIGNED:
        return True
    return len(_columns(code, op, (len(str(spec["a"])), len(str(spec["b"]))))) > 1


def _times_column(rng: random.Random, code: str, sizes: tuple[int, int]) -> tuple[int, int, dict[str, int]]:
    """A multiplication of these digit counts whose worked answer this slip gets wrong."""
    if not _columns(code, "×", sizes):
        raise O.CannotMake(f"no {sizes[0]}-digit by {sizes[1]}-digit multiplication shows {code}")
    return _spread(rng, lambda: _drawn(rng, code, "×", sizes), f"{sizes[0]} × {sizes[1]} digits with {code}")


def _column(
    rng: random.Random, code: str, op: str, sizes: tuple[int, int]
) -> tuple[int, int, dict[str, int]]:
    """A two-number calculation in columns, its numbers `sizes` digits long, whose answer this mistake gets wrong."""
    return _spread(
        rng, lambda: _drawn(rng, code, op, sizes), f"{sizes[0]} by {sizes[1]} digit {op} with {code}"
    )


def _aligned(
    rng: random.Random, code: str, op: str, sizes: tuple[int, int]
) -> tuple[int, int, dict[str, int]]:
    for _ in range(400):
        got = _drawn(rng, code, op, sizes)
        if got:
            return got[1]
    raise RuntimeError(f"no {op} question shows {code}")


def _shaped(rng: random.Random, code: str, name: str) -> tuple[str, dict[str, Any], list[Response]]:
    """(stem, spec, responses) for the mistakes that are not column slips."""
    shape = SHAPES[code]
    if (
        shape == "partitioned"
    ):  # a 2-digit number partitioned and each part multiplied with its tens taken as ones
        n, m = TK.number(rng, 2), rng.randint(3, 9)
        right, wrong = n * m, sum(WM.ones(p) * m for p in WM.parts(n))
        worked = " + ".join(f"{WM.ones(p)} × {m}" for p in WM.parts(n))
        stem = f"{name} partitioned {n} to work out {n} × {m}: {worked} = {wrong}. That is not right."
        ans = Response(
            "ans",
            "digits",
            str(right),
            cells=cells(right),
            misconceptions={code: wrong},
            label="correct answer",
        )
        return stem, dict(a=n, b=m, op="×", wrong=wrong, planted=code), [ans, _why(code)]
    if shape == "three":

        def draw():
            # 2-digit numbers carry 2 out of the ones; 3-digit ones can carry 2 out of the tens instead
            lo, hi = rng.choice([(56, 99), (156, 499)])
            xs = [rng.randint(lo, hi) for _ in range(3)]
            wrong = M.carry_always_one(xs)
            if not wrong or not all(x % 10 for x in xs):
                return None
            return _first_wrong_column(sum(xs), wrong), (xs, wrong)

        xs, wrong = _spread(rng, draw, "three numbers that need a carry of 2")
        right = sum(xs)
        stem = f"{name} added {' + '.join(map(str, xs))} in columns and wrote {wrong}. That is not right."
        spec = dict(addends=xs, op="+", layout="column", wrong=wrong, planted=code)
        return (
            stem,
            spec,
            [
                _where(right, wrong),
                Response(
                    "ans",
                    "digits",
                    str(right),
                    cells=cells(right),
                    misconceptions={code: wrong},
                    label="correct answer",
                ),
                _why(code),
            ],
        )
    if shape == "reversed":
        b, c = rng.randint(3, 19), rng.randint(3, 19)
        while b == c:
            c = rng.randint(3, 19)
        right, wrong = b + c, abs(c - b)
        text = f"□ − {b} = {c}"
        stem = f"{name} solved {text} and wrote {wrong} in the box. That is not right."
        spec = dict(a=right, b=b, op="-", text=text, wrong=wrong, planted=code)
    elif shape == "digit":
        while True:
            a, b = sample_add(rng, 2, 2, {1})
            if (a % 10) + (b % 10) >= 10 and a // 10 < 9:
                break
        c = a + b
        tens_b, tens_c = (b // 10) % 10, (c // 10) % 10
        wrong = (tens_c - tens_b) % 10
        right = (a // 10) % 10
        text = f"□{a % 10} + {b} = {c}"
        stem = f"{name} found the missing digit in {text} and wrote {wrong}. That is not right."
        spec = dict(a=a, b=b, op="+", text=text, wrong=wrong, planted=code)
    else:  # equals
        a, b = rng.randint(11, 40), rng.randint(5, 30)
        c = rng.randint(3, a + b - 3)
        right, wrong = a + b - c, a + b
        text = f"{a} + {b} = □ + {c}"
        stem = f"{name} wrote {wrong} in the box: {text}. That is not right."
        spec = dict(a=a, b=b, op="+", text=text, wrong=wrong, planted=code)
    ans = Response(
        "ans",
        "digits",
        str(right),
        cells=cells(max(right, wrong)),
        misconceptions={code: wrong},
        label="correct answer",
    )
    return stem, spec, [ans, _why(code)]


def find_mistake(
    rng: random.Random,
    rung: str,
    signal: str,
    op: str = "+",
    digits: int | tuple[int, int] = 2,
    planted: str | None = None,
) -> Item:
    """A worked answer with one named mistake; the child finds it, corrects it and says why.

    With no `planted` mistake the choice is the two column slips of its operation, as it always was."""
    op = O.require("find_mistake", op, makes=("+", "-", "×"))
    name = rng.choice(NAMES)
    code = planted or rng.choice(COLUMN_SLIPS[op][:2])
    if code not in PLANTABLE:
        raise ValueError(f"{code} is not a mistake a worked answer can show")
    if code in SHAPES:
        stem, spec, rs = _shaped(rng, code, name)
        return item("FTM", rung, "Conceptual", "find_mistake", stem, spec, rs, working_lines=2)
    d1, d2 = (
        (digits, digits) if isinstance(digits, int) else digits
    )  # the level's two numbers, one given for both
    if code in COLUMN_SLIPS["×"]:  # a slip only multiplication makes decides the operation, and its numbers
        op = "×"
        a, b, mis = _times_column(
            rng, code, digits if isinstance(digits, tuple) else NEEDS.get(code, (d1, 1))
        )
    elif op == "×":
        raise O.CannotMake(f"{code} is not a mistake a multiplication's worked answer shows")
    elif code in ALIGNED:
        a, b, mis = _aligned(rng, code, op, (max(d1, 2), d2))
    else:
        if code not in COLUMN_SLIPS[op]:
            op = "-" if op == "+" else "+"  # a slip only one operation can make decides the operation
        if code == "M_EXCHANGE_WRONG_PLACE" or code in ACROSS_ZERO:  # both need a hundreds column
            d1, d2 = max(d1, 3), max(d1, 3) if d1 == d2 else d2
        a, b, mis = _column(rng, code, op, (d1, d2))
    wrong = mis[code]
    right = M.compute(op, a, b)
    spec: dict[str, Any] = dict(a=a, b=b, op=op, wrong=wrong, planted=code)
    ans = Response(
        "ans",
        "digits",
        str(right),
        cells=cells(max(right, wrong)),
        misconceptions=mis,
        label="correct answer",
    )
    rs = ([_where(right, wrong)] if asks_where(spec) else []) + [ans, _why(code)]
    lined = " (written in a line, then copied into columns)" if code == "M_H2V_SHIFT" else ""
    stem = f"{name} worked out {a} {O.PRINTED[op]} {b}{lined} and wrote {wrong}. That is not right."
    return item(
        "FTM",
        rung,  # the rung of the skill it practises: X2 on its own, a calculation skill's rung in its Advance
        "Conceptual",
        "find_mistake",
        stem,
        spec,
        rs,
        working_lines=2,
    )


def explain_claim(rng, rung, signal, a_range=(120, 480), claim_is_true=True, claim_topic="compensation"):
    """A claim to judge and explain: tick yes/no, then say why.

    Two claim shapes, each one template the numbers slot into (ADR 0010 — the language is written
    once, not per question). `compensation`: moving 1 from one addend to the other leaves the
    total alone (the false variant moves it one way only, so the total does change).
    `regrouping`: exchanging a ten for ten ones leaves the number's value alone (the false
    variant claims it shrinks). Defaults reproduce the original true compensation claim, which
    `blueprints.py` calls with no arguments."""
    name = rng.choice(["Zoya", "Aarav", "Meera", "Kabir", "Riya", "Dev"])
    if claim_topic == "regrouping":
        a = rng.randint(*a_range)
        shown = f"{a // 10} tens and {a % 10} ones" if a < 100 else f"{a}"
        claim = (
            f"When you exchange one ten in {a} for ten ones, {a} is still worth the same."
            if claim_is_true
            else f"When you exchange one ten in {a} for ten ones, {a} becomes smaller."
        )
        rubric = (
            "Accept: the exchange only renames the parts — one ten and ten ones are the same"
            " value — so the total does not change."
        )
        spec = dict(a=a, shown=shown, name=name, topic="regrouping", claim_is_true=claim_is_true)
    else:
        a = rng.randint(*a_range)
        b = rng.choice([99, 199, 299, 49, 79] if a >= 120 else [9, 19, 29])
        claim = (
            f"{a} + {b} gives the same total as {a - 1} + {b + 1}."
            if claim_is_true
            else f"{a} + {b} gives the same total as {a - 1} + {b}."
        )
        rubric = (
            "Accept any explanation showing 1 moved from one number to the other, or that"
            " both sums equal the same total."
        )
        spec = dict(a=a, b=b, name=name, topic="compensation", claim_is_true=claim_is_true)
    rs = [
        Response(
            "tick", "tick", "yes" if claim_is_true else "no", options=["yes", "no"], label="Is this correct?"
        ),
        Response("why", "text", None, rubric=rubric),
    ]
    return item(
        "CLAIM",
        "X1",
        "Conceptual",
        "explain_claim",
        f"{name} says: “{claim}” Is {name} correct? Explain your answer.",
        spec,
        rs,
        working_lines=3,
    )
