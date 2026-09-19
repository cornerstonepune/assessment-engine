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
from .ladder import RUNGS


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


def _cells(n):
    return len(str(n)) + 1


def _item(template, rung, signal, fmt, stem, spec, responses, scaffolded=False, working_lines=2, skills=None):
    return Item(
        _id(template, spec),
        template,
        rung,
        skills or RUNGS[rung]["skills"],
        signal,
        fmt,
        scaffolded,
        stem,
        spec,
        responses,
        working_lines,
    )


# ---------------------------------------------------------------- operand samplers


def _regroup_count_add(a, b):
    w = max(len(str(a)), len(str(b)))
    da, db = M.digits(a, w), M.digits(b, w)
    c, n = 0, 0
    for x, y in zip(da, db):
        s = x + y + c
        c = 1 if s >= 10 else 0
        n += c
    return n


def _regroup_count_sub(a, b):
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
        if _regroup_count_add(a, b) in regroups:
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
        if _regroup_count_sub(a, b) in regroups:
            return a, b
    raise RuntimeError(f"no sub sample for {digits_a},{digits_b},{regroups},{across_zero}")


# ---------------------------------------------------------------- closed computation items


def bare_sum(rng, rung, signal, op, da, db, regroups, max_total=None, across_zero=False, layout="horizontal"):
    if op == "+":
        a, b = sample_add(rng, da, db, regroups, max_total)
    else:
        a, b = sample_sub(rng, da, db, regroups, across_zero, max_a=max_total)
    ans = a + b if op == "+" else a - b
    r = Response("ans", "digits", str(ans), cells=_cells(max(ans, a)), misconceptions=M.predict(op, a, b))
    fmt = "column_grid" if layout == "column" else "bare_sum"
    return _item(
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
    else:  # sub_missing_subtrahend
        c = rng.randint(hi // 4, hi - 2)
        a = rng.randint(1, c - 1)
        ans = c - a
        stem = f"{c} − □ = {a}"
        mis = {"M_ADD_INSTEAD": c + a, "M_FACT_PM1": ans + 1}
    mis = {k: v for k, v in mis.items() if v != ans and v >= 0}
    r = Response("ans", "digits", str(ans), cells=_cells(hi), misconceptions=mis)
    return _item("MISSING.NUM", rung, signal, "missing_number", stem, dict(text=stem), [r], working_lines=1)


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
    r = Response("ans", "digits", str(ans), cells=_cells(a + b), misconceptions=mis)
    return _item(
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
        Response("m1", "digits", str(m1), cells=_cells(top), misconceptions=M.predict("+", base[0], base[1])),
        Response("m2", "digits", str(m2), cells=_cells(top), misconceptions=M.predict("+", base[1], base[2])),
        Response("top", "digits", str(top), cells=_cells(top), misconceptions=M.predict("+", m1, m2)),
    ]
    return _item(
        "WALL",
        rung,
        signal,
        "number_wall",
        "The number in each brick is the sum of the two bricks below it. Complete the wall.",
        dict(base=base),
        rs,
        working_lines=0,
    )


def _bridge_jump(rng, op, hi, tries=200):
    """A jump that crosses exactly one ten, for a small range: the first hop lands on the ten,
    the second finishes. That bridge is the strategy R2 ("within 20, crossing ten") teaches.
    Returns (a, b, land1)."""
    if hi < 12:
        raise RuntimeError(f"no bridging jump below hi=12; got {hi}")
    for _ in range(tries):
        if op == "+":
            a = rng.randint(3, min(hi - 3, 18))
            if a % 10 == 0:
                continue
            to_ten = 10 - (a % 10)
            hi_b = min(9, hi - a)
            if hi_b <= to_ten:
                continue
            return a, rng.randint(to_ten + 1, hi_b), a + to_ten
        a = rng.randint(11, hi)
        ones = a % 10
        if ones in (0, 9):
            continue  # ones == 9 leaves no b that both crosses the ten and stays single-digit
        b = rng.randint(ones + 1, 9)
        if a - b < 1:
            continue
        return a, b, a - ones
    raise RuntimeError(f"no bridging jump within hi={hi}")


def number_line_jumps(rng, rung, signal, op, hi):
    """a ± b shown as two jumps. Landing boxes + answer are responses.

    Above hi=54 the jump splits into tens then ones. Below it there is no room for an 11-39
    second jump, so the jump bridges the next ten instead — the same picture at the scale a
    "within 20" rung actually works at."""
    if hi < 54:
        a, b, land1 = _bridge_jump(rng, op, hi)
        ans = a + b if op == "+" else a - b
        first = abs(land1 - a)
        rs = [
            Response(
                "land1",
                "digits",
                str(land1),
                cells=_cells(hi),
                label=f"after {op}{first}",
                misconceptions={"M_FACT_PM1": land1 + (1 if op == "+" else -1)},
            ),
            Response("ans", "digits", str(ans), cells=_cells(hi), misconceptions=M.predict(op, a, b)),
        ]
        # `tens`/`ones` are the renderer's names for the two jump sizes, whatever their place value.
        return _item(
            "NLINE.BRIDGE",
            rung,
            signal,
            "number_line_jumps",
            f"Complete {a} {op} {b}. Use the number line to help you.",
            dict(a=a, b=b, op=op, tens=first, ones=b - first),
            rs,
            scaffolded=True,
            working_lines=0,
        )
    if op == "+":
        a = rng.randint(hi // 4, hi - 40)
        b = rng.randint(11, 39)
        while b % 10 == 0:
            b = rng.randint(11, 39)
        tens, ones = (b // 10) * 10, b % 10
        land1 = a + tens
        ans = a + b
    else:
        a = rng.randint(hi // 2, hi - 1)
        b = rng.randint(11, 39)
        while b % 10 == 0 or b >= a:
            b = rng.randint(11, 39)
        tens, ones = (b // 10) * 10, b % 10
        land1 = a - tens
        ans = a - b
    rs = [
        Response(
            "land1",
            "digits",
            str(land1),
            cells=_cells(hi),
            misconceptions={"M_FACT_PM10": land1 + (10 if op == "+" else -10)},
            label=f"after {op}{tens}",
        ),
        Response("ans", "digits", str(ans), cells=_cells(hi), misconceptions=M.predict(op, a, b)),
    ]
    return _item(
        "NLINE",
        rung,
        signal,
        "number_line_jumps",
        f"Complete {a} {op} {b}. Use the number line to help you.",
        dict(a=a, b=b, op=op, tens=tens, ones=ones),
        rs,
        scaffolded=True,
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
    return _item(
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


def sort_into_table(rng, rung, signal, op, n=4):
    """n two-digit calculations; child ticks 'needs regrouping' or 'no regrouping'. Tests recognition."""
    items, rs = [], []
    want = [1, 0] * (n // 2)
    rng.shuffle(want)
    for i, w in enumerate(want):
        if op == "+":
            a, b = sample_add(rng, 2, 2, {w})
        else:
            a, b = sample_sub(rng, 2, 2, {w})
        items.append(f"{a} {op} {b}")
        rs.append(
            Response(
                f"s{i}",
                "tick",
                "regroup" if w else "none",
                options=["regroup", "none"],
                label=f"{a} {op} {b}",
                misconceptions={},
            )
        )
    word = "Change a ten for 10 ones" if op == "-" else "Make a new ten"
    return _item(
        "SORT",
        rung,
        "Conceptual",
        "sort_into_table",
        "For each calculation, tick the box that describes it. Do not work out the answer.",
        dict(items=items, col_a=word, col_b="No regrouping needed"),
        rs,
        working_lines=0,
    )


def estimate_then_calc(rng, rung, signal, op, digits_a, digits_b, regroups):
    if op == "+":
        a, b = sample_add(rng, digits_a, digits_b, regroups)
    else:
        a, b = sample_sub(rng, digits_a, digits_b, regroups)
    ra, rb = round(a, -1), round(b, -1)
    est = ra + rb if op == "+" else ra - rb
    ans = a + b if op == "+" else a - b
    rs = [
        Response("est", "digits", str(est), cells=_cells(max(est, ans)), tolerance=10, label="estimate"),
        Response(
            "ans",
            "digits",
            str(ans),
            cells=_cells(max(est, ans)),
            misconceptions=M.predict(op, a, b),
            label="exact",
        ),
    ]
    return _item(
        "ESTIMATE",
        rung,
        signal,
        "estimate_then_calc",
        f"Estimate first, then work out {a} {op} {b}.",
        dict(a=a, b=b, op=op, ra=ra, rb=rb),
        rs,
        scaffolded=True,
        working_lines=2,
    )


def missing_digit(rng, rung, signal, op, width):
    """Column calculation with 1–2 hidden digits; brute-force guarantees a unique solution."""
    for _ in range(300):
        if op == "+":
            a, b = sample_add(rng, width, width, {1, 2})
            c = a + b
        else:
            a, b = sample_sub(rng, width, width, {1, 2})
            c = a - b
        sa, sb, sc = str(a), str(b).zfill(width), str(c)
        # hide one digit in a and one in b (never leading), keep c visible
        pa = rng.randint(1, len(sa) - 1)
        pb = rng.randint(1, len(sb) - 1)
        # count solutions
        sols = []
        for x in range(10):
            for y in range(10):
                aa = int(sa[:pa] + str(x) + sa[pa + 1 :])
                bb = int(sb[:pb] + str(y) + sb[pb + 1 :])
                if (aa + bb if op == "+" else aa - bb) == c:
                    sols.append((x, y))
        if len(sols) == 1:
            rs = [
                Response("da", "digits", sa[pa], cells=1, label="top"),
                Response("db", "digits", sb[pb], cells=1, label="bottom"),
            ]
            return _item(
                "MISSING.DIGIT",
                rung,
                signal,
                "missing_digit",
                "Write the missing digits.",
                dict(a=sa[:pa] + "□" + sa[pa + 1 :], b=sb[:pb] + "□" + sb[pb + 1 :], c=sc, op=op),
                rs,
                working_lines=2,
            )
    raise RuntimeError("no unique missing-digit item")


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
    return _item(
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
    rs = [Response("ans", "digits", str(ans), cells=_cells(ans), misconceptions=M.predict(op, a, b))]
    return _item(
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
    return _item(
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
    return _item(
        "CLAIM",
        "X1",
        "Conceptual",
        "explain_claim",
        f"{name} says: “{claim}” Is {name} correct? Explain your answer.",
        spec,
        rs,
        working_lines=3,
    )


def find_mistake(rng, rung, signal, op="+", digits=2):
    """A worked column calculation with one planted misconception; child ticks the wrong step and writes the correct answer."""
    if op == "+":
        a, b = sample_add(rng, digits, digits, {1})
        mis = M.predict("+", a, b)
        code = rng.choice([c for c in ("M_NOCARRY", "M_CARRY_SKIP") if c in mis])
    else:
        a, b = sample_sub(rng, digits, digits, {1})
        mis = M.predict("-", a, b)
        code = rng.choice([c for c in ("M_SMALL_FROM_LARGE", "M_NO_DECREMENT") if c in mis])
    wrong = mis[code]
    ans = a + b if op == "+" else a - b
    name = rng.choice(["Ishaan", "Anaya", "Vihaan", "Saee"])
    opts = ["ones column", "tens column", "both"]
    correct_opt = (
        "ones column"
        if code in ("M_NOCARRY",)
        else ("tens column" if code == "M_CARRY_SKIP" else "ones column")
    )
    rs = [
        Response("where", "tick", correct_opt, options=opts, label="Where is the mistake?"),
        Response(
            "ans",
            "digits",
            str(ans),
            cells=_cells(max(ans, wrong)),
            misconceptions=mis,
            label="correct answer",
        ),
        Response(
            "why",
            "text",
            None,
            rubric=f"Names the mistake: {M.ADD_PREDICTORS.get(code, M.SUB_PREDICTORS.get(code))[1]}",
        ),
    ]
    return _item(
        "FTM",
        "X2",
        "Conceptual",
        "find_mistake",
        f"{name} worked out {a} {op} {b} and wrote {wrong}. That is not right.",
        dict(a=a, b=b, op=op, wrong=wrong, planted=code),
        rs,
        working_lines=2,
    )


# ---------------------------------------------------------------- word problems (deterministic contexts; LLM hook later)


def missing_part_20(rng, rung, signal):
    c = rng.randint(8, 20)
    a = rng.randint(1, c - 1)
    ans = c - a
    r = Response(
        "ans", "digits", str(ans), cells=2, misconceptions={"M_ADD_INSTEAD": a + c, "M_FACT_PM1": ans + 1}
    )
    return _item(
        "PPW20",
        rung,
        "Conceptual",
        "missing_number",
        f"{a} + □ = {c}",
        dict(text=f"{a} + □ = {c}"),
        [r],
        working_lines=1,
    )


def multi_add(rng, rung, signal, n_addends=3, digits_each=4):
    lo, hi = 10 ** (digits_each - 1), 10**digits_each - 1
    xs = [rng.randint(lo, hi) for _ in range(n_addends)]
    while any(x % 10 == 0 for x in xs):
        xs = [rng.randint(lo, hi) for _ in range(n_addends)]
    ans = sum(xs)
    mis = {"M_DROP_CARRYOUT": ans % (10**digits_each), "M_FACT_PM10": ans + 10, "M_FACT_PM100": ans - 100}
    mis |= M.predict_multi(xs)
    mis = {k: v for k, v in mis.items() if v != ans}
    r = Response("ans", "digits", str(ans), cells=len(str(ans)) + 1, misconceptions=mis)
    return _item(
        f"ADD.MULTI{n_addends}",
        rung,
        signal,
        "column_grid",
        "",
        dict(addends=xs, op="+", layout="column"),
        [r],
        working_lines=0,
    )
