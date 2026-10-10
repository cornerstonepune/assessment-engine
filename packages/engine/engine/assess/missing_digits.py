"""Missing digits (taxonomy §6.2, §6.4): the Olympiad-style reasoning across a carry or an exchange.

A calculation in columns with some digits hidden — in either number, in the answer, or in both — and
every question checked by brute force to have exactly one answer. Two shapes beside the boxes:
`SAME_LETTER` (A5 + 2A = 88: one letter, one digit, wherever it stands) and `INEQUALITY` (3□ + 27 < 70:
how many digits could go in the box). Deterministic given an RNG.

Every box names a wrong answer a child could write: the digit that works in its own column when the
carry or the exchange from the column to its right is forgotten (M_MISSING_DIGIT_LOCAL), or, where no
regroup reaches it, a fact one out. A multiplication by one digit (goals/md2b-times-advance.yaml) hides digits of
the larger number or of the answer. A box names the other digit its column allows alone where there is exactly one
(2□ × 4 = 92: 8 × 4 ends in 2 as 3 × 4 does; 48 × 2 = □6: the carry forgotten), else a times-table row out, as a +
or − box names a fact one out: the digit from the row before (M_MUL_ROW_OUT). The larger number's lead digit never
has a column-alone digit: its column is the whole rest of the answer, which only the right digit makes.
"""

import itertools
import random
from typing import Any

from . import misconceptions as M
from . import operations as O
from .items import Item, Response, item, sample_add, sample_sub
from .times_kinds import number

ROWS = ("FIRST", "SECOND", "RESULT")
PLACES = ["ONES", "TENS", "HUNDREDS", "THOUSANDS"]


def _calc(op: str, a: int, b: int) -> int:
    return O.compute(op, a, b)


def _numbers(rng: random.Random, op: str, width: int, regroups: Any) -> tuple[int, int]:
    if op == "×":  # a number that is no table fact and not round, times one digit
        if width < 2:
            raise O.CannotMake(
                "a × missing digit needs a number of 2 digits or more: 1 digit is a table fact"
            )
        return number(rng, width), rng.randint(2, 9)
    if op == "+":
        return sample_add(rng, width, width, set(regroups))
    # a zero in the top number's lender column half the time, where there is one (§6.4: 4□2 − 185)
    return sample_sub(rng, width, width, set(regroups), across_zero=width >= 3 and rng.random() < 0.5)


def _carry_into(op: str, a: int, b: int, col: int) -> int:
    """The carry (addition) or the exchange (subtraction) arriving at column `col` from its right."""
    w = max(len(str(a)), len(str(b)))
    da, db = M.digits(a, w), M.digits(b, w)
    carry = 0
    for i in range(col):
        if op == "+":
            carry = 1 if da[i] + db[i] + carry >= 10 else 0
        else:
            carry = 1 if da[i] - carry < db[i] else 0
    return carry


def _local(op: str, row: str, col: int, a: int, b: int, c: int) -> int:
    """The digit a child writes in this box by working its column alone, without the regroup from the right."""
    w = max(len(str(a)), len(str(b)), len(str(c)))
    da, db, dc = M.digits(a, w), M.digits(b, w), M.digits(c, w)
    if row == "RESULT":
        return (da[col] + db[col]) % 10 if op == "+" else (da[col] - db[col]) % 10
    if op == "+":
        other = db[col] if row == "FIRST" else da[col]
        return (dc[col] - other) % 10
    return (dc[col] + db[col]) % 10 if row == "FIRST" else (da[col] - dc[col]) % 10


def _masked(numbers: dict[str, int], hidden: list[tuple[str, int]]) -> dict[str, str]:
    """Each row's digits with the hidden places boxed, left to right."""
    out = {}
    for row, n in numbers.items():
        s = list(str(n))
        for r, col in hidden:
            if r == row:
                s[len(s) - 1 - col] = "□"
        out[row] = "".join(s)
    return out


def _solutions(op: str, masks: dict[str, str]) -> list[tuple[int, ...]]:
    """Every digit filling that makes the boxed calculation true (a leading box is never 0)."""
    slots = [(row, i) for row in ROWS for i, ch in enumerate(masks[row]) if ch == "□"]
    found = []
    for fill in itertools.product(range(10), repeat=len(slots)):
        s = {row: list(masks[row]) for row in ROWS}
        for (row, i), d in zip(slots, fill):
            s[row][i] = str(d)
        if any(s[row][0] == "0" and len(s[row]) > 1 for row in ROWS):
            continue
        a, b, c = (int("".join(s[row])) for row in ROWS)
        if _calc(op, a, b) == c:
            found.append(fill)
    return found


def _choose(
    rng: random.Random,
    numbers: dict[str, int],
    missing_count: int,
    missing_in: str | None,
    missing_place: str | None,
) -> list[tuple[str, int]] | None:
    rows = missing_in.split("+") if missing_in else None
    pair = (
        ["FIRST", "RESULT"] if "SECOND" not in numbers else ["FIRST", "SECOND"]
    )  # × hides no digit of its 1
    if rows is None:
        more = ["RESULT"] if missing_count > 2 and "RESULT" not in pair else []
        rows = rng.sample(pair, 1) if missing_count == 1 else pair + more
    if len(rows) > missing_count:
        return None
    hidden: list[tuple[str, int]] = []
    for row in rows:
        width = len(str(numbers[row]))
        col = PLACES.index(missing_place) if missing_place and missing_count == 1 else rng.randrange(width)
        if col >= width or (row, col) in hidden:
            return None
        hidden.append((row, col))
    room = sum(len(str(numbers[row])) for row in set(rows))
    for _ in range(200):  # bounded: more boxes than these rows have digits is no question, not a hang
        if len(hidden) >= min(missing_count, room):
            break
        row = rng.choice(rows)
        col = rng.randrange(len(str(numbers[row])))
        if (row, col) not in hidden:
            hidden.append((row, col))
    return hidden if len(hidden) == missing_count else None


def _times_named(row: str, col: int, a: int, b: int, c: int) -> dict[str, int]:
    """The wrong digit a child writes in a × box, by its mistake (see the module); empty where neither names one."""
    da, dc = str(a)[::-1], str(c)[::-1]
    if row == "RESULT":
        if col >= len(da):
            return {}  # the answer's lead digits are the last carry: no column of their own
        carry = O.times_columns(a, b)[col]["carry_in"]
        alone, right = {int(da[col]) * b % 10}, int(dc[col])
        row_out = (int(da[col]) * (b - 1) + carry) % 10
    else:
        lead = col == len(da) - 1
        alone = set() if lead else {x for x in range(10) if x * b % 10 == int(dc[col])}
        right = int(da[col])
        row_out = right - 1 if right - 1 >= (1 if lead else 0) else right + 1
    others = alone - {right}
    if len(others) == 1:
        return {"M_MISSING_DIGIT_LOCAL": next(iter(others))}
    return {"M_MUL_ROW_OUT": row_out} if row_out != right and row_out <= 9 else {}


def _boxes(op: str, a: int, b: int, c: int, hidden: list[tuple[str, int]]) -> list[Response]:
    rs: list[Response] = []
    for k, (row, col) in enumerate(sorted(hidden, key=lambda h: (ROWS.index(h[0]), -h[1])), 1):
        right = M.digits({"FIRST": a, "SECOND": b, "RESULT": c}[row], 4)[col]
        if op == "×":
            mis = _times_named(row, col, a, b, c)
        else:
            local = _local(op, row, col, a, b, c)
            carried = local != right and _carry_into(op, a, b, col)
            mis = {"M_MISSING_DIGIT_LOCAL": local} if carried else {"M_FACT_PM1": (right + 1) % 10}
        rs.append(Response(f"d{k}", "digits", str(right), cells=1, label=f"box {k}", misconceptions=mis))
    # a + or − box always names one; a × answer's last carry names none
    if not any(r.misconceptions for r in rs):
        raise RuntimeError("no box names a digit a child could write")
    return rs


def missing_digit(rng: random.Random, rung: str, signal: str, rule: dict[str, Any]) -> Item:
    """One missing-digit question for a level's `rule` (op, width, missing_count, missing_in,
    missing_place, shape, regroups). Raises RuntimeError when this draw's numbers cannot make it."""
    op = O.require("missing_digit", rule.get("op", "+"), makes=("+", "-", "×"))
    a, b = _numbers(rng, op, rule.get("width", 2), rule.get("regroups", (0, 1, 2)))
    c = _calc(op, a, b)
    if op == "×" and rule.get("shape"):
        raise O.CannotMake(f"a multiplication's missing digits have no {rule['shape']} shape")
    if rule.get("shape") == "SAME_LETTER":
        return _same_letter(rng, rung, signal, op, (a, b, c))
    if rule.get("shape") == "INEQUALITY":
        return _inequality(rng, rung, signal, op, (a, b))
    solved = {"a": a, "b": b}
    numbers = {"FIRST": a, "RESULT": c} if op == "×" else {"FIRST": a, "SECOND": b, "RESULT": c}
    hidden = _choose(
        rng, numbers, int(rule.get("missing_count", 1)), rule.get("missing_in"), rule.get("missing_place")
    )
    if not hidden:
        raise RuntimeError("this shape does not fit these numbers")
    masks = _masked(numbers, hidden) | ({"SECOND": str(b)} if op == "×" else {})
    if len(_solutions(op, masks)) != 1:
        raise RuntimeError("more than one filling works; not a fair question")
    spec = dict(a=masks["FIRST"], b=masks["SECOND"], c=masks["RESULT"], op=op, solved=solved)
    return item(
        "MISSING.DIGIT",
        rung,
        signal,
        "missing_digit",
        "Write the missing digits.",
        spec,
        _boxes(op, a, b, c, hidden),
        working_lines=2,
    )


def _same_letter(rng: random.Random, rung: str, signal: str, op: str, numbers: tuple[int, int, int]) -> Item:
    """A5 + 2A = 88: the tens of the first number and the ones of the second are one digit."""
    a, b, c = numbers
    solved = {"a": a, "b": b}
    sa, sb = str(a), str(b)
    if len(sa) != 2 or len(sb) != 2 or sa[0] != sb[1]:
        raise RuntimeError("the same letter needs the same digit in both places")
    ma, mb = "A" + sa[1], sb[0] + "A"
    fits = [d for d in range(1, 10) if _calc(op, int(f"{d}{sa[1]}"), int(f"{sb[0]}{d}")) == c]
    if fits != [int(sa[0])]:
        raise RuntimeError("the letter is not one digit only")
    sign = "−" if op == "-" else "+"
    spec = dict(a=ma, b=mb, c=str(c), op=op, solved=solved, shape="SAME_LETTER")
    rs = [
        Response(
            "A", "digits", sa[0], cells=1, label="A =", misconceptions={"M_FACT_PM1": (int(sa[0]) + 1) % 10}
        )
    ]
    stem = f"{ma} {sign} {mb} = {c}. The letter A stands for the same digit both times. What is A?"
    return item("MISSING.LETTER", rung, signal, "missing_digit", stem, spec, rs, working_lines=2)


def _inequality(rng: random.Random, rung: str, signal: str, op: str, numbers: tuple[int, int]) -> Item:
    """3□ + 27 < 70 (addition) or 7□ − 25 > 50 (subtraction): how many digits could go in the box?"""
    a, b = numbers
    solved = {"a": a, "b": b}
    sa = str(a)
    head = sa[:-1]
    rel = "<" if op == "+" else ">"
    target = (_calc(op, a, b) // 10 + rng.randint(0, 1)) * 10
    fits = [
        d
        for d in range(10)
        if (
            _calc(op, int(f"{head}{d}"), b) < target
            if op == "+"
            else _calc(op, int(f"{head}{d}"), b) > target
        )
    ]
    if not 2 <= len(fits) <= 8:
        raise RuntimeError("too few or too many digits fit to be worth asking")
    sign = "−" if op == "-" else "+"
    masked = head + "□"
    spec = dict(
        a=masked, b=str(b), c=str(target), op=op, relation=rel, solved=solved, shape="INEQUALITY", fits=fits
    )
    rs = [
        Response(
            "count",
            "digits",
            str(len(fits)),
            cells=2,
            label="how many digits",
            misconceptions={"M_FACT_PM1": len(fits) + 1},
        )
    ]
    stem = f"{masked} {sign} {b} {rel} {target}. How many different digits could go in the box?"
    return item("MISSING.INEQ", rung, signal, "missing_digit", stem, spec, rs, working_lines=2)


def one(rng: random.Random, rung: str, signal: str, rule: dict[str, Any], tries: int = 300) -> Item:
    """A missing-digit question for this rule, drawing again until one is fair — the old generator's
    promise to the week's blueprints, which ask for one and expect it."""
    for _ in range(tries):
        try:
            return missing_digit(rng, rung, signal, rule)
        except RuntimeError:
            continue
    raise RuntimeError(f"no fair missing-digit question for {rule}")
