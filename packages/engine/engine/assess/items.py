"""Item generators. Every generator is deterministic given an RNG and returns Item objects.

An Item has one or more Responses. A Response is one thing the child writes that can be
scored: a run of digit cells, a tick, or free text. Closed responses carry the correct
answer and the misconception -> wrong-answer table; open responses carry a rubric.
"""

import hashlib
import itertools
from dataclasses import asdict, dataclass, field
from typing import Any

from . import misconceptions as M
from . import operations as O


@dataclass
class Response:
    rid: str  # e.g. "a", "b", "est", "brick2"
    kind: str  # digits | tick | text
    answer: Any  # str for digits/tick; None for text
    cells: int = 0  # number of digit cells (digits)
    options: list[str] = field(default_factory=list)  # for tick
    misconceptions: dict[str, Any] = field(default_factory=dict)
    tolerance: int | None = None  # for estimates: |read - answer| <= tolerance is correct
    rubric: str | None = None  # for text
    label: str = ""  # short label printed next to the cells


@dataclass
class Item:
    item_id: str
    template: str
    rung: str
    skills: list[str]
    signal: str
    fmt: str
    scaffolded: bool
    stem: str
    spec: dict[str, Any]  # rendering payload
    responses: list[Response]
    working_lines: int = 2

    def to_dict(self):
        return asdict(self)


def _id(template, payload):
    h = hashlib.sha1(f"{template}|{payload}".encode()).hexdigest()[:8]
    return f"{template}-{h}"


def cells(n: Any) -> int:
    return len(str(n)) + 1


def item(
    template: str,
    rung: str,
    signal: str,
    fmt: str,
    stem: str,
    spec: dict[str, Any],
    responses: list[Response],
    scaffolded: bool = False,
    working_lines: int = 2,
    skills: list[str] | None = None,
) -> Item:
    return Item(
        _id(template, spec),
        template,
        rung,
        skills or [],  # a label only; `bank` measures the real one from the question (ADR 0030)
        signal,
        fmt,
        scaffolded,
        stem,
        spec,
        responses,
        working_lines,
    )


# ---------------------------------------------------------------- operand samplers


def regroup_count_add(a, b):
    w = max(len(str(a)), len(str(b)))
    da, db = M.digits(a, w), M.digits(b, w)
    c, n = 0, 0
    for x, y in zip(da, db):
        s = x + y + c
        c = 1 if s >= 10 else 0
        n += c
    return n


def regroup_count_sub(a, b):
    w = max(len(str(a)), len(str(b)))
    da, db = M.digits(a, w), M.digits(b, w)
    n, borrow = 0, 0
    for x, y in zip(da, db):
        x -= borrow
        if x < y:
            n += 1
            borrow = 1
        else:
            borrow = 0
    return n


def sample_add(rng, digits_a, digits_b, regroups, max_total=None, tries=2000):
    lo_a, hi_a = 10 ** (digits_a - 1), 10**digits_a - 1
    lo_b, hi_b = 10 ** (digits_b - 1), 10**digits_b - 1
    if digits_a == 1:
        lo_a = 1
    if digits_b == 1:
        lo_b = 1
    for _ in range(tries):
        a, b = rng.randint(lo_a, hi_a), rng.randint(lo_b, hi_b)
        if a == b or a % 10 == 0 or b % 10 == 0:
            continue
        if max_total and a + b > max_total:
            continue
        if regroup_count_add(a, b) in regroups:
            return a, b
    raise RuntimeError(f"no add sample for {digits_a},{digits_b},{regroups}")


def sample_mul(rng, digits_a, digits_b, max_product=None, tries=2000):
    """Multiplication operands — the one sampler a new operation costs, once (ADR 0010, W1 gate 3).

    No regrouping argument: a multiplication's carries follow from the operands and are not a
    dial the skill-set rule turns, the way an addition's are. x1 and x10 are excluded for the
    same reason sample_add excludes multiples of ten — they do not test the skill."""
    lo_a, hi_a = 10 ** (digits_a - 1), 10**digits_a - 1
    lo_b, hi_b = 10 ** (digits_b - 1), 10**digits_b - 1
    if digits_a == 1:
        lo_a = 2
    if digits_b == 1:
        lo_b = 2
    for _ in range(tries):
        a, b = rng.randint(lo_a, hi_a), rng.randint(lo_b, hi_b)
        if a % 10 == 0 or b % 10 == 0 or a == 1 or b == 1:
            continue
        if max_product and a * b > max_product:
            continue
        return a, b
    raise RuntimeError(f"no mul sample for {digits_a},{digits_b},max_product={max_product}")


def sample_sub(rng, digits_a, digits_b, regroups, across_zero=False, tries=4000, max_a=None):
    lo_a, hi_a = 10 ** (digits_a - 1), 10**digits_a - 1
    if max_a:
        hi_a = min(hi_a, max_a)
    lo_b, hi_b = 10 ** (digits_b - 1), 10**digits_b - 1
    if digits_b == 1:
        lo_b = 1
    for _ in range(tries):
        a, b = rng.randint(lo_a, hi_a), rng.randint(lo_b, hi_b)
        if (
            b >= a
            or a - b < (5 if digits_a >= 2 else 1)
            or b % 10 == 0
            or (a % 10 == 0 and not across_zero and digits_a <= 2)
        ):
            continue
        ds = M.digits(a, digits_a)
        has_zero = 0 in ds[1:]
        if across_zero != has_zero:
            continue
        if regroup_count_sub(a, b) in regroups:
            return a, b
    raise RuntimeError(f"no sub sample for {digits_a},{digits_b},{regroups},{across_zero}")


# ---------------------------------------------------------------- closed computation items


def bare_sum(rng, rung, signal, op, da, db, regroups, max_total=None, across_zero=False, layout="horizontal"):
    op = O.require("bare_sum", op)
    if op == "+":
        a, b = sample_add(rng, da, db, regroups, max_total)
    else:
        a, b = sample_sub(rng, da, db, regroups, across_zero, max_a=max_total)
    ans = a + b if op == "+" else a - b
    r = Response("ans", "digits", str(ans), cells=cells(max(ans, a)), misconceptions=M.predict(op, a, b))
    fmt = "column_grid" if layout == "column" else "bare_sum"
    return item(
        f"{'ADD' if op == '+' else 'SUB'}.{da}D{db}D.REG{'Z' if across_zero else ''.join(map(str, sorted(regroups)))}",
        rung,
        signal,
        fmt,
        "",
        dict(a=a, b=b, op=op, layout=layout),
        [r],
        working_lines=3 if layout == "horizontal" else 0,
    )


def missing_number(rng, rung, signal, kind, hi):
    """a + □ = c  |  □ - b = c  |  c - □ = a  ; numbers to `hi`."""
    if kind == "add_missing_addend":
        c = rng.choice([hi, hi // 2, rng.randrange(20, hi, 5)]) if hi >= 40 else rng.randint(8, hi)
        a = rng.randint(1, c - 1)
        ans = c - a
        stem = f"{a} + □ = {c}"
        mis = {"M_ADD_INSTEAD": a + c, "M_FACT_PM1": ans + 1}
    elif kind == "sub_missing_minuend":
        b = rng.randint(2, hi // 3)
        c = rng.randint(hi // 4, hi - b)
        ans = b + c
        stem = f"□ − {b} = {c}"
        mis = {"M_SUB_INSTEAD": abs(c - b), "M_FACT_PM1": ans - 1}
    elif kind == "among_three":  # 35 + □ + 18 = 80 (taxonomy §6.1)
        a, other, ans = (rng.randint(11, hi // 3) for _ in range(3))
        c = a + ans + other
        stem = f"{a} + □ + {other} = {c}"
        mis = {"M_ADD_INSTEAD": a + other + c, "M_FACT_PM1": ans + 1}
    else:  # sub_missing_subtrahend
        c = rng.randint(hi // 4, hi - 2)
        a = rng.randint(1, c - 1)
        ans = c - a
        stem = f"{c} − □ = {a}"
        mis = {"M_ADD_INSTEAD": c + a, "M_FACT_PM1": ans + 1}
    mis = {k: v for k, v in mis.items() if v != ans and v >= 0}
    r = Response("ans", "digits", str(ans), cells=cells(hi), misconceptions=mis)
    return item("MISSING.NUM", rung, signal, "missing_number", stem, dict(text=stem), [r], working_lines=1)


def balance_scale(rng, rung, signal, hi):
    """a + b = □ + c"""
    a = rng.randrange(10, hi // 2, 10 if hi >= 100 else 1)
    b = rng.randrange(10, hi // 2, 10 if hi >= 100 else 1)
    while b == a:
        b = rng.randrange(10, hi // 2, 10 if hi >= 100 else 1)
    c = rng.randrange(10, a + b - 5, 10 if hi >= 100 else 1)
    ans = a + b - c
    mis = {"M_EQUALS_MEANS_ANSWER": a + b, "M_ADD_ALL": a + b + c}
    mis = {k: v for k, v in mis.items() if v != ans}
    r = Response("ans", "digits", str(ans), cells=cells(a + b), misconceptions=mis)
    return item(
        "BALANCE",
        rung,
        "Conceptual",
        "balance_scale",
        "Write the missing number so that the scales balance.",
        dict(left=[a, b], right=[None, c]),
        [r],
        working_lines=1,
    )


def number_wall(rng, rung, signal, hi):
    base = [rng.randint(3, hi) for _ in range(3)]
    m1, m2 = base[0] + base[1], base[1] + base[2]
    top = m1 + m2
    rs = [
        Response("m1", "digits", str(m1), cells=cells(top), misconceptions=M.predict("+", base[0], base[1])),
        Response("m2", "digits", str(m2), cells=cells(top), misconceptions=M.predict("+", base[1], base[2])),
        Response("top", "digits", str(top), cells=cells(top), misconceptions=M.predict("+", m1, m2)),
    ]
    return item(
        "WALL",
        rung,
        signal,
        "number_wall",
        "The number in each brick is the sum of the two bricks below it. Complete the wall.",
        dict(base=base),
        rs,
        working_lines=0,
    )


def partition_scaffold(rng, rung, signal, regroups):
    a, b = sample_add(rng, 3, 3, regroups)
    da, db = M.digits(a, 3), M.digits(b, 3)
    hund = (da[2] + db[2]) * 100
    tens = (da[1] + db[1]) * 10
    ones = da[0] + db[0]
    rs = [
        Response("a_t", "digits", str(da[1] * 10), cells=3, label="tens of first"),
        Response("a_o", "digits", str(da[0]), cells=2, label="ones of first"),
        Response("b_h", "digits", str(db[2] * 100), cells=4),
        Response("b_t", "digits", str(db[1] * 10), cells=3),
        Response("b_o", "digits", str(db[0]), cells=2),
        Response("hund", "digits", str(hund), cells=4),
        Response("tens", "digits", str(tens), cells=4),
        Response("ones", "digits", str(ones), cells=3),
        Response("ans", "digits", str(a + b), cells=5, misconceptions=M.predict("+", a, b)),
    ]
    return item(
        "PARTITION",
        rung,
        "Conceptual",
        "partition_scaffold",
        f"Complete the calculation {a} + {b} by partitioning.",
        dict(a=a, b=b, a_h=da[2] * 100),
        rs,
        scaffolded=True,
        working_lines=0,
    )


def digit_cards(rng, rung, signal, n_cards=3, addend=None):
    cards = rng.sample(range(1, 10), n_cards)
    if addend is None:
        addend = rng.randint(100, 400)
    best = max(int("".join(map(str, p))) + addend for p in itertools.permutations(cards))
    worst = min(int("".join(map(str, p))) + addend for p in itertools.permutations(cards))
    big = int("".join(map(str, sorted(cards, reverse=True))))
    rs = [
        Response(
            "largest",
            "digits",
            str(best),
            cells=5,
            label="largest total",
            misconceptions={"M_SMALLEST_NUMBER": worst, "M_FORGOT_ADDEND": big},
        )
    ]
    return item(
        "CARDS",
        rung,
        "Stretch",
        "digit_cards",
        f"Use each of the digits {', '.join(map(str, cards))} once to make a {n_cards}-digit number. Add {addend} to your number. What is the largest total you can make? Show how you know.",
        dict(cards=cards, addend=addend),
        rs
        + [
            Response(
                "how",
                "text",
                None,
                rubric="Accept: largest digits placed in the highest places; or any argument that a bigger start gives a bigger total.",
            )
        ],
        working_lines=3,
    )


def efficient_method(rng, rung, signal, kind=None):
    """Pairs with an obvious shortcut: near-multiples of 10/100 or same-tens.

    `kind` pins the shortcut family (STRATEGY.EFFICIENT's Easy/Medium/Hard bands each test one
    by name); the default keeps the original random choice for callers that don't care."""
    kind = kind or rng.choice(["near100", "same_tens", "near1000"])
    if kind == "near100":
        a = rng.randint(150, 480)
        b = rng.choice([98, 99, 199, 299])
        op = "+"
    elif kind == "same_tens":
        t = rng.randint(2, 8) * 10
        a = t * 10 + rng.randint(1, 9) + 100 * rng.randint(1, 4)
        b = (a // 10) * 10 - rng.randint(1, 3) * 10
        op = "-"
        a, b = a, a - rng.randint(11, 19)
    else:
        a = rng.randint(2000, 4800)
        b = rng.choice([998, 999, 1999, 2998])
        op = "+"
    ans = a + b if op == "+" else a - b
    rs = [Response("ans", "digits", str(ans), cells=cells(ans), misconceptions=M.predict(op, a, b))]
    return item(
        "EFFICIENT",
        rung,
        signal,
        "efficient_method",
        f"Use the most efficient method you can to work out {a} {op} {b}. Show your method.",
        dict(a=a, b=b, op=op),
        rs
        + [
            Response(
                "method",
                "text",
                None,
                rubric="Any compensation / friendly-number / counting-on method stated. Column method is correct but not 'most efficient'.",
            )
        ],
        working_lines=3,
    )


def partial_worked(rng, rung, signal):
    """Emyr-style: a 3-digit subtraction with the regrouping started; child completes the partition and the answer."""
    a, b = sample_sub(rng, 3, 3, {1})
    da, db = M.digits(a, 3), M.digits(b, 3)
    # find the regrouping column
    if da[0] < db[0]:
        parts = (da[2] * 100, (da[1] - 1) * 10, da[0] + 10)
    else:
        parts = ((da[2] - 1) * 100, da[1] * 10 + 100, da[0])
    rs = [
        Response("p2", "digits", str(parts[1]), cells=4, label="tens after regrouping"),
        Response("p3", "digits", str(parts[2]), cells=3, label="ones after regrouping"),
        Response("ans", "digits", str(a - b), cells=4, misconceptions=M.predict("-", a, b)),
    ]
    return item(
        "PARTIAL",
        rung,
        "Conceptual",
        "partial_worked",
        "Asha did not finish her calculation. Complete it for her.",
        dict(a=a, b=b, p1=parts[0], b_parts=(db[2] * 100, db[1] * 10, db[0])),
        rs,
        scaffolded=True,
        working_lines=0,
    )


# ---------------------------------------------------------------- word problems (deterministic contexts; LLM hook later)


def multi_add(rng, rung, signal, n_addends=3, digits_each=4, xs=None, layout="column", shape=None):
    """Three or more numbers added, in columns or written in a line (taxonomy §2.8). `xs` gives the
    numbers when a caller has already chosen them — a case with mixed lengths, or friendly pairs."""
    if xs is None:
        lo, hi = 10 ** (digits_each - 1), 10**digits_each - 1
        xs = [rng.randint(lo, hi) for _ in range(n_addends)]
        while any(x % 10 == 0 for x in xs):
            xs = [rng.randint(lo, hi) for _ in range(n_addends)]
    ans = sum(xs)
    widest = max(len(str(x)) for x in xs)
    mis = {"M_DROP_CARRYOUT": ans % (10**widest), "M_FACT_PM10": ans + 10, "M_FACT_PM100": ans - 100}
    mis |= M.predict_multi(xs)
    mis = {k: v for k, v in mis.items() if v != ans and v >= 0}
    r = Response("ans", "digits", str(ans), cells=len(str(ans)) + 1, misconceptions=mis)
    spec = dict(addends=xs, op="+", layout=layout) | ({"shape": shape} if shape else {})
    column = layout == "column"
    return item(
        f"ADD.MULTI{len(xs)}",
        rung,
        signal,
        "column_grid" if column else "bare_sum",
        "Add them in the easiest order." if shape == "FRIENDLY_PAIRS" else "",
        spec,
        [r],
        working_lines=0 if column else 3,
    )
