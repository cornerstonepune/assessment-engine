"""The space a new mistake is learned in (goals/s22-learned-mistakes.yaml). Pure: numbers in, numbers out.

A rule is how a child works a column sum, column by column from the ones: what each column writes, what it carries
(adding) or borrows (taking away) into the next, whether the last carry is written, how the two numbers are lined up,
and whether the digits come out reversed. The right method is one rule; every other rule is a way of being wrong that
code can compute on any two numbers. The named mistakes people wrote by hand (`misconceptions.py`) mostly sit in this
space already — which is the test that it is the right space (tests/test_learned_rules.py).

A wrong answer no named mistake explains is searched for here (`explaining`): every rule that reproduces it exactly.
A rule that reproduces such answers on several different questions is what a child is doing — proposed to a person,
who names it (`w1_bank/learned.py`). The search is exhaustive and small (a few hundred rules), so nothing is guessed.
"""

from itertools import product
from typing import Any

# What a column writes, from its two digits and what came in from the column to its right.
WRITES = {
    "+": {
        "sum": lambda a, b, c: str((a + b + c) % 10),
        "sum_without_carry_in": lambda a, b, c: str((a + b) % 10),
        "whole_sum": lambda a, b, c: str(a + b + c),
        "difference": lambda a, b, c: str(abs(a - b)),
        "larger": lambda a, b, c: str(max(a, b)),
    },
    "-": {
        "exchange": lambda a, b, c: str((a - b - c) % 10),
        "smaller_from_larger": lambda a, b, c: str(abs(a - b)),
        "smaller_from_larger_after_borrow": lambda a, b, c: str(abs(a - c - b)),
        "zero_when_short": lambda a, b, c: str(max(a - b - c, 0)),
        "bottom_from_top_swapped": lambda a, b, c: str((b - a - c) % 10),
        # a zero that is exchanged across becomes 10 and stays 10 (should be 9)
        "zero_lends_as_ten": lambda a, b, c: str(10 - b if a == 0 and c else (a - b - c) % 10),
        "sum": lambda a, b, c: str((a + b + c) % 10),
    },
}
# What goes into the next column.
CARRIES = {
    "+": {
        "carry": lambda a, b, c: (a + b + c) // 10,
        "none": lambda a, b, c: 0,
        "always_one": lambda a, b, c: 1,
    },
    "-": {
        "borrow": lambda a, b, c: 1 if a - b - c < 0 else 0,
        "none": lambda a, b, c: 0,
        "borrow_two": lambda a, b, c: 2 if a - b - c < 0 else 0,
        # across a zero: the zero lends, and the column to its left is never reduced
        "borrow_stops_at_zero": lambda a, b, c: 0 if a == 0 and c else (1 if a - b - c < 0 else 0),
    },
}
# where a carry or an exchange lands: the next column, two columns left, or two left for the ones column only
TO = ("next", "next_but_one", "first_next_but_one")
LAST = ("write", "drop")  # the carry out of the last column
ALIGN = ("right", "left")  # ones under ones, or the shorter number pushed to the left
TURN = ("none", "reversed", "zero_dropped")  # as worked, read back reversed, or a placeholder zero left out

RIGHT = {
    "+": {"op": "+", "write": "sum", "carry": "carry", "to": "next", "last": "write", "align": "right", "turn": "none"},
    "-": {"op": "-", "write": "exchange", "carry": "borrow", "to": "next", "last": "write", "align": "right",
          "turn": "none"},
}  # fmt: skip

WORDS = {
    ("write", "sum"): "",
    ("write", "sum_without_carry_in"): "adds each column but leaves out what was carried into it",
    ("write", "whole_sum"): "writes each column's whole total, both digits",
    ("write", "difference"): "takes away in each column instead of adding",
    ("write", "larger"): "writes the larger digit of each column",
    ("write", "exchange"): "",
    (
        "write",
        "smaller_from_larger",
    ): "takes the smaller digit from the larger in each column, whichever row it is in",
    (
        "write",
        "smaller_from_larger_after_borrow",
    ): "takes the smaller from the larger after the lender is reduced",
    ("write", "zero_when_short"): "writes 0 in a column where the top digit is too small",
    ("write", "bottom_from_top_swapped"): "takes the top digit from the bottom one",
    ("write", "zero_lends_as_ten"): "a zero it exchanges across becomes 10 and stays 10",
    ("carry", "carry"): "",
    ("carry", "borrow"): "",
    ("carry", "none"): "never carries or exchanges into the next column",
    ("carry", "always_one"): "carries one into every column",
    ("carry", "borrow_two"): "reduces the next column by two when exchanging",
    ("carry", "borrow_stops_at_zero"): "exchanging across a zero, never reduces the column left of the zero",
    ("to", "next"): "",
    ("to", "next_but_one"): "puts the carry or takes the exchange two columns to the left",
    (
        "to",
        "first_next_but_one",
    ): "takes the ones column's exchange from two columns to the left, then works the rest right",
    ("last", "write"): "",
    ("last", "drop"): "leaves off the carry from the last column",
    ("align", "right"): "",
    ("align", "left"): "lines the numbers up from the left, not by their ones",
    ("turn", "none"): "",
    ("turn", "reversed"): "writes the answer's digits in reverse order",
    ("turn", "zero_dropped"): "leaves a placeholder zero out of the answer",
}
PARTS = ("write", "carry", "to", "last", "align", "turn")


def rules(op):
    """Every rule for `op`, the right method first."""
    out = [
        {"op": op, "write": w, "carry": c, "to": to, "last": last, "align": al, "turn": t}
        for w, c, to, last, al, t in product(WRITES[op], CARRIES[op], TO, LAST, ALIGN, TURN)
        if op == "+" or last == "write"  # taking away has no carry out of its last column
    ]
    return sorted(out, key=cost)


def cost(rule):
    """How far a rule is from the right method: the number of parts that differ. Simplest explanation first."""
    return sum(rule[p] != RIGHT[rule["op"]][p] for p in PARTS)


def rule_id(rule):
    return "|".join([rule["op"], *(rule[p] for p in PARTS)])


def from_id(text):
    op, *parts = text.split("|")
    return {"op": op, **dict(zip(PARTS, parts))}


def words(rule):
    """What a child working by this rule does, in the school's words."""
    return "; ".join(w for w in (WORDS[(p, rule[p])] for p in PARTS) if w) or "works the sum the right way"


def _digits(n, width):
    return [int(ch) for ch in str(n).zfill(width)][::-1]  # ones first


def answer(rule, a, b):
    """What a child working by `rule` writes for `a op b`, or None where the rule cannot be carried out (a larger
    number taken from a smaller)."""
    op = rule["op"]
    if op == "-" and a < b:
        return None
    if rule["align"] == "left" and len(str(a)) != len(str(b)):
        w = max(len(str(a)), len(str(b)))
        a, b = a * 10 ** (w - len(str(a))), b * 10 ** (w - len(str(b)))
    width = max(len(str(a)), len(str(b)))
    write, carry = WRITES[op][rule["write"]], CARRIES[op][rule["carry"]]
    out, pending, through_zero = [], {}, False
    for i, (x, y) in enumerate(zip(_digits(a, width), _digits(b, width))):
        c = pending.pop(i, 0)
        step = 2 if rule["to"] == "next_but_one" or (rule["to"] == "first_next_but_one" and i == 0) else 1
        if rule["carry"] == "borrow_stops_at_zero":
            # a zero exchanged across becomes 9 and passes the exchange on; the first column after the zeros that
            # should give it up is left as it was
            if x == 0 and c:
                out.append(str(9 - y if y <= 9 else 0))
                pending[i + step], through_zero = c, True
                continue
            if through_zero:
                c, through_zero = 0, False
        out.append(write(x, y, c))
        if moved := carry(x, y, c):
            pending[i + step] = pending.get(i + step, 0) + moved
    if op == "+" and rule["last"] == "write":  # carries past the last column are written, column by column
        i = width
        while pending:
            c = pending.pop(i, 0)
            out.append(str(c % 10))
            if c >= 10:
                pending[i + 1] = pending.get(i + 1, 0) + c // 10
            i += 1
    text = "".join(reversed(out)).lstrip("0") or "0"
    if rule["turn"] == "reversed":
        text = text[::-1]
    elif rule["turn"] == "zero_dropped":
        at = text.find("0", 1)  # never the leading digit
        if at < 0:
            return None
        text = text[:at] + text[at + 1 :]
    return int(text)


def predict(rule, a, b):
    """The wrong answer the rule gives for `a op b`, or None where it gives the right one or none at all."""
    got = answer(rule, a, b)
    right = a + b if rule["op"] == "+" else a - b
    return got if got is not None and got != right and got >= 0 else None


def explaining(op, a, b, wrote):
    """Every rule that gives exactly `wrote` for `a op b` when that is not the right answer, simplest first."""
    return [r for r in rules(op) if predict(r, a, b) == wrote] if op in WRITES else []


def works_the_sum(spec: dict[str, Any], response: dict[str, Any]) -> bool:
    """Whether `response` asks for its question's own two-number sum, worked exactly: the only answer a rule about
    working that sum can explain. An estimate beside it (right within a tolerance), a check of it (the claimed answer
    take away the second number) or a reason is not that sum, and no rule here, learned or named, explains it."""
    a, b, op, want = (
        str(spec.get("a", "")),
        str(spec.get("b", "")),
        spec.get("op"),
        str(response.get("answer", "")),
    )
    if op not in WRITES or not (a.isdigit() and b.isdigit()) or response.get("tolerance") is not None:
        return False
    return want.lstrip("-").isdigit() and int(want) == (int(a) + int(b) if op == "+" else int(a) - int(b))
