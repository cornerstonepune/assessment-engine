"""The written methods of division, a calculation printed as its method's steps, each a box (ADR 0063).

Partitioning the number divided (72 ÷ 4 is 40 ÷ 4 and 32 ÷ 4, then added: the most tens of lots of the divisor, then
the rest), chunking (for each place of the quotient, largest first, the lots of the divisor it is worth taken away:
96 ÷ 4 is 20 lots, 16 left, then 4 lots, 0 left) and long division (516 ÷ 4: divide, multiply, take away, bring down,
a box for every product and every number left). Short division is the division layout, each exchange written small
(`division.exchanges`). Every step is a `Response` with its own key, so the reader reads it and marking marks it by
itself; the quotient is `ans`, and the remainder `rem` where there is one (ADR 0056). Pure, no I/O.

What a step or total can be worked wrong as, each from the numbers: a part's or a lot's quotient with its zero left out
(40 ÷ 4 written 1, 20 lots written 2: `M_DIV_QUOTIENT_ZERO_DROPPED`), carried into the total it makes; one group short,
leaving too much to take away (`M_DIV_REMAINDER_TOO_BIG`); a digit not brought down (`M_DIV_BRING_DOWN_MISSED`); a part
names its own small division's slips, a product its multiplication's and a number left its take-away's, which count
against multiplication and subtraction (`skills.by_method`, assumption A11). A product or a take-away never names the
wrong operation: on a division that name is the division's own, multiplied instead of dividing.
"""

from random import Random
from typing import Any

from . import div_mistakes as DM
from . import misconceptions as M
from . import operations as O
from .counting import named
from .items import Item, Response, cells, item
from .times_kinds import number

# the method, as printed: the kind of question that prints it
KINDS = {"PARTITION_DIVIDEND": "partitioning", "CHUNKING": "chunking", "LONG_DIVISION": "long_division"}
STEMS = {
    "PARTITION_DIVIDEND": "Divide each part, then add.",
    "LONG_DIVISION": "Divide, multiply, take away, bring down.",
}
ZERO, SHORT, NOT_DOWN = "M_DIV_QUOTIENT_ZERO_DROPPED", "M_DIV_REMAINDER_TOO_BIG", "M_DIV_BRING_DOWN_MISSED"


def parts(a: int, b: int) -> list[int]:
    """72 ÷ 4 → [40, 32]: the most tens of lots of the divisor, then the rest."""
    first = a // (10 * b) * 10 * b
    return [first, a - first]


def takes(a: int, b: int) -> list[tuple[int, int, int]]:
    """96 ÷ 4 → [(20, 80, 16), (4, 16, 0)]: for each place of the quotient, largest first, the lots of the divisor it is
    worth, what they take away and what is left. A place worth nothing takes nothing."""
    q, left = str(a // b), a
    out: list[tuple[int, int, int]] = []
    for i, d in enumerate(q):
        lots = int(d) * 10 ** (len(q) - 1 - i)
        if lots:
            left -= lots * b
            out.append((lots, lots * b, left))
    return out


def cycles(a: int, b: int) -> list[tuple[int, int, int, int | None]]:
    """516 ÷ 4 → [(5, 4, 11, 1), (11, 8, 36, 6), (36, 36, 0, None)]: each number divided in turn, its quotient digit times
    the divisor, what is left with the next digit brought down (the last: the remainder), and that digit. The first is
    the number's leading digits, as few as reach the divisor."""
    s = str(a)
    k = next((i for i in range(1, len(s) + 1) if int(s[:i]) >= b), len(s))
    partial = int(s[:k])
    out: list[tuple[int, int, int, int | None]] = []
    for nxt in [*(int(d) for d in s[k:]), None]:
        product = partial // b * b
        after = (partial - product) * 10 + nxt if nxt is not None else partial - product
        out.append((partial, product, after, nxt))
        partial = after
    return out


def _dropped(n: int) -> int:
    """20 → 2, 100 → 1: a quotient with its zeros left out."""
    return int(str(n).replace("0", "") or 0)


def _slips(op: str, x: int, y: int) -> list[tuple[str, int]]:
    """A small multiplication's or take-away's own slips, never the wrong operation, whose name on a division is the
    division's (multiplied instead of dividing)."""
    return [(c, v) for c, v in M.predict(op, x, y).items() if c != "M_WRONG_OP"]


def _box(rid: str, n: int, mis: dict[str, Any], label: str) -> Response:
    return Response(rid, "digits", str(n), cells=cells(n), misconceptions=mis, label=label)


def _total(a: int, b: int, own: list[tuple[str, int]]) -> list[Response]:
    """The quotient's box, named by the division's own mistakes and then the method's not already named; the
    remainder's after "r" where there is one."""
    q, r = O.divide(a, b)
    mine = DM.in_box(a, b, 0)
    mis = named(q, [*mine.items(), *((c, v) for c, v in own if c not in mine)])
    out = [_box("ans", q, mis, f"{a} ÷ {b} =")]
    return [*out, _box("rem", r, DM.in_box(a, b, 1), "r")] if r else out


def _partitioning(a: int, b: int) -> list[Response]:
    out: list[Response] = []
    for k, p in enumerate(parts(a, b), start=1):
        q, r = divmod(p, b)
        out.append(_box(f"s{k}", q, DM.in_box(p, b, 0), f"{p} ÷ {b} ="))
        if r:
            out.append(_box(f"s{k}r", r, DM.in_box(p, b, 1), "r"))
    first, rest = parts(a, b)
    return out + _total(a, b, [(ZERO, _dropped(first // b) + rest // b)])


def _chunking(a: int, b: int) -> list[Response]:
    out: list[Response] = []
    for lots, chunk, left in takes(a, b):
        place = 10 ** (len(str(lots)) - 1)
        short = [(SHORT, lots - place)] if lots > place else []
        zero = [(ZERO, _dropped(lots))] if place > 1 else []
        out += [
            _box(f"s{len(out) + 1}", lots, named(lots, [*zero, *short]), f"lots of {b}"),
            _box(f"s{len(out) + 2}", chunk, named(chunk, _slips("×", lots, b)), "take away"),
            _box(f"s{len(out) + 3}", left, named(left, _slips("-", left + chunk, chunk)), "left"),
        ]
    return out + _total(a, b, [(ZERO, sum(_dropped(lots) for lots, _, _ in takes(a, b)))])


def _long(a: int, b: int) -> list[Response]:
    out: list[Response] = []
    for partial, product, after, nxt in cycles(a, b):
        q = partial // b
        short = [(SHORT, (q - 1) * b)] if q else []
        # the digit left where it was is long division's own act, so it is named first: 5 − 4 written 1 for 516 ÷ 4 is
        # more likely the 1 not brought down than 5 − 4 = 0 with the 1 brought down
        down = [(c, v * 10 + nxt) for c, v in _slips("-", partial, product)] if nxt is not None else []
        left = [(NOT_DOWN, partial - product), *down] if nxt is not None else _slips("-", partial, product)
        out += [
            _box(f"s{len(out) + 1}", product, named(product, [*_slips("×", q, b), *short]), "multiply"),
            _box(
                f"s{len(out) + 2}",
                after,
                named(after, left),
                "take away, bring down" if nxt is not None else "left over",
            ),
        ]
    return out + _total(a, b, [])


WORK = {"PARTITION_DIVIDEND": _partitioning, "CHUNKING": _chunking, "LONG_DIVISION": _long}


def prints(method: str, a: int, b: int) -> bool:
    """Whether `method` can set out `a ÷ b`: every written division here divides by one digit, never by 0 or 1 (÷ 1 is
    a fact, and a 2-digit divisor's long division is D13's, placed in no grade), a number at least as big; partitioning
    needs tens of lots and a rest besides (35 ÷ 4 has no ten lots, 80 ÷ 4 no rest)."""
    if method not in WORK or not 2 <= b <= 9 or a < b:
        return False
    return method != "PARTITION_DIVIDEND" or all(parts(a, b))


def stem(method: str, a: int, b: int) -> str:
    """What the child is asked to do, in the school's words: chunking takes the hundreds of lots first, then the tens,
    then the rest, as the quotient's places say."""
    if method != "CHUNKING":
        return STEMS[method]
    first = "hundreds, then in tens" if a // b >= 100 else "tens"
    return f"Take away {b}s in {first}, then the {b}s left. Add up the {b}s."


def make(method: str, a: int, b: int, rung: str) -> Item:
    """`a ÷ b` printed in `method`, a box for every step and then the quotient, and its remainder where it has one."""
    if method not in WORK:
        raise O.CannotMake(f"no written division {method!r}: {', '.join(WORK)}")
    if not prints(method, a, b):
        raise O.CannotMake(
            f"{a} ÷ {b} in {method}: a written division divides a number at least as big by 2 to 9, and partitioning "
            "needs tens of lots of the divisor and a rest"
        )
    spec: dict[str, Any] = {"a": a, "b": b, "op": "÷", "method": method}
    return item(
        method,
        rung,
        "Procedural",
        KINDS[method],
        stem(method, a, b),
        spec,
        WORK[method](a, b),
        working_lines=0,
    )


# a method drawn on its own, from a level's rule (`bands.NATIVE_GENERATORS`): the digits of the number divided and of
# the divisor, drawn again until the method can set them out
DIGITS = {"PARTITION_DIVIDEND": (2, 1), "CHUNKING": (2, 1), "LONG_DIVISION": (3, 1)}


def drawn(method: str, rng: Random, rung: str, rule: dict[str, Any]) -> Item:
    d1, _ = rule.get("digits") or DIGITS[method]
    for _ in range(200):
        a, b = number(rng, int(d1)), rng.randint(2, 9)
        if prints(method, a, b):
            return make(method, a, b, rung)
    raise RuntimeError(f"no {d1}-digit number {method} can set out")


def partitioning(rng: Random, rung: str, signal: str, rule: dict[str, Any]) -> Item:
    return drawn("PARTITION_DIVIDEND", rng, rung, rule)


def chunking(rng: Random, rung: str, signal: str, rule: dict[str, Any]) -> Item:
    return drawn("CHUNKING", rng, rung, rule)


def long_division(rng: Random, rung: str, signal: str, rule: dict[str, Any]) -> Item:
    return drawn("LONG_DIVISION", rng, rung, rule)
