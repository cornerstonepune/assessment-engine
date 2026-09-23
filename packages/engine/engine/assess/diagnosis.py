"""Finding the mistake and judging a claim (taxonomy §11; rungs X1, X2). Deterministic given an RNG.

`find_mistake` shows another child's worked answer with one named mistake planted in it. The mistake is
chosen (`planted`) from every one the taxonomy's §11 lists and the predictors can compute: a column
slip in addition or subtraction, numbers lined up from the left, a carry of 1 where the column needs 2,
a subtraction turned round, a missing digit that works in its own column only, = read as "the answer
comes next". A column answer asks which digit of the child's answer is wrong first — a column the
engine can check — then the right answer, then why.

`explain_claim` asks whether a statement about a calculation is true, and why (moved from `items.py`).
"""

from . import misconceptions as M
from .items import Response, _cells, _item, sample_add, sample_sub

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
ACROSS_ZERO = {"M_ZERO_LENDER", "M_ZERO_NOT_NINE"}
ALIGNED = {"M_ALIGN_LEFT", "M_H2V_SHIFT"}
SHAPES = {
    "M_CARRY_ALWAYS_1": "three",
    "M_SUB_INSTEAD": "reversed",
    "M_MISSING_DIGIT_LOCAL": "digit",
    "M_EQUALS_MEANS_ANSWER": "equals",
}
PLANTABLE = set(COLUMN_SLIPS["+"]) | set(COLUMN_SLIPS["-"]) | ALIGNED | set(SHAPES)


def _first_wrong_column(right, wrong):
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
    name = M.ADD_PREDICTORS.get(code) or M.SUB_PREDICTORS.get(code) or M.MULTI_PREDICTORS.get(code)
    return Response("why", "text", None, rubric=f"Names the mistake: {name[1] if name else code}")


def _spread(rng, draw, what, tries=80):
    """One of `tries` drawn candidates, its column chosen evenly among the columns the candidates' first wrong
    digit falls in. Asked "which column is the first wrong digit in?", a child who ticks the same box every time
    must not score: drawn as they come, a carry of 2 was always in the tens and a smaller-from-larger slip in the
    ones 83 times in 100 (`engine audit`, 2026-09-23). A mistake that can only ever show in one column (a
    dropped final carry) still does; a level mixes it with others."""
    by = {}
    for _ in range(tries):
        got = draw()
        if got is not None:
            col, cand = got
            by.setdefault(col, []).append(cand)
    if not by:
        raise RuntimeError(f"no question shows {what}")
    return rng.choice(by[rng.choice(sorted(by))])


def _column(rng, code, op, digits):
    """A two-number calculation in columns whose answer this mistake would get wrong."""

    def draw():
        if op == "+":
            a, b = sample_add(rng, digits, digits, {1, 2, 3})
        else:
            a, b = sample_sub(rng, digits, digits, {1, 2}, across_zero=code in ACROSS_ZERO)
        mis = M.predict(op, a, b)
        if code not in mis:
            return None
        return _first_wrong_column(M.compute(op, a, b), mis[code]), (a, b, mis)

    return _spread(rng, draw, f"{digits}-digit {op} with {code}")


def _aligned(rng, code, op, digits):
    for _ in range(400):
        short = rng.randint(1, max(1, digits - 1))
        a, b = (sample_add if op == "+" else sample_sub)(rng, max(digits, 2), short, {0, 1, 2})
        mis = M.predict(op, a, b)
        if "M_ALIGN_LEFT" in mis:
            return a, b, mis | {code: mis["M_ALIGN_LEFT"]}
    raise RuntimeError(f"no {op} question shows {code}")


def _shaped(rng, code, name):
    """(stem, spec, responses) for the mistakes that are not column slips."""
    shape = SHAPES[code]
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
                    cells=_cells(right),
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
        cells=_cells(max(right, wrong)),
        misconceptions={code: wrong},
        label="correct answer",
    )
    return stem, spec, [ans, _why(code)]


def find_mistake(rng, rung, signal, op="+", digits=2, planted=None):
    """A worked answer with one named mistake; the child finds it, corrects it and says why.

    With no `planted` mistake the choice is the two column slips of its operation, as it always was."""
    name = rng.choice(NAMES)
    code = planted or rng.choice(COLUMN_SLIPS[op][:2])
    if code not in PLANTABLE:
        raise ValueError(f"{code} is not a mistake a worked answer can show")
    if code in SHAPES:
        stem, spec, rs = _shaped(rng, code, name)
        return _item("FTM", rung, "Conceptual", "find_mistake", stem, spec, rs, working_lines=2)
    if code in ALIGNED:
        a, b, mis = _aligned(rng, code, op, max(digits, 2))
    else:
        if code not in COLUMN_SLIPS[op]:
            op = "-" if op == "+" else "+"  # a slip only one operation can make decides the operation
        wide = code == "M_EXCHANGE_WRONG_PLACE" or code in ACROSS_ZERO  # both need a hundreds column
        a, b, mis = _column(rng, code, op, max(digits, 3) if wide else digits)
    wrong = mis[code]
    right = M.compute(op, a, b)
    rs = [
        _where(right, wrong),
        Response(
            "ans",
            "digits",
            str(right),
            cells=_cells(max(right, wrong)),
            misconceptions=mis,
            label="correct answer",
        ),
        _why(code),
    ]
    lined = " (written in a line, then copied into columns)" if code == "M_H2V_SHIFT" else ""
    stem = (
        f"{name} worked out {a} {'−' if op == '-' else op} {b}{lined} and wrote {wrong}. That is not right."
    )
    return _item(
        "FTM",
        rung,  # the rung of the skill it practises: X2 on its own, a calculation skill's rung in its Advance
        "Conceptual",
        "find_mistake",
        stem,
        dict(a=a, b=b, op=op, wrong=wrong, planted=code),
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
