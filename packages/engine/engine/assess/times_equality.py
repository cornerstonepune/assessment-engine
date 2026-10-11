"""× and ÷ written as equations (goals/md4b2-equality.yaml; the multiplication & division taxonomy, section 10).

What × and ÷ keep — a product turned round, × 1 and ÷ 1, a number ÷ itself and 0 ÷ a number, three numbers grouped
either way, a factor doubled or partitioned, a balance against − or against ÷ — the missing sign, a comparison made
without working, and true or false about ÷ 0, about a division turned round and about a product turned round.

Each sentence is printed with its own box or its own tick: a response's `label` is its sentence, and `spec["text"]` is
every sentence as the child reads them. A true-or-false, a sign or a comparison is asked beside its other — a true claim
beside a false one, a × sentence beside a ÷ one — in either order, so a child who ticks one place every time is right
half the time, never every time (9 ÷ 0 = 0 asked alone is false on every paper). Each wrong answer is what a named mistake
writes, never the right answer. Deterministic given an RNG; pure: no I/O. `equality.from_rule` hands a × or ÷ case's
shape here."""

import math
from collections.abc import Callable
from random import Random

from . import misconceptions as M
from .items import Item, Response, cells, item

UNFIT = "these numbers do not make this question; draw again"
TRUE_FALSE = ["true", "false"]
SIGNS = ["×", "÷"]
COMPARE = ["<", "=", ">"]
# the outer two numbers of three grouped either way, making a ten or two (2 × 7 × 5: 2 × 5 first)
TENS = [(2, 5), (5, 2), (4, 5), (5, 4), (2, 10), (10, 2)]

Sentence = tuple[
    str, str, dict[str, str]
]  # a tick's sentence, its answer, and what a named mistake ticks instead
Shape = tuple[list[Response], list[str], str]  # the responses, the operations carried out, the instruction


def _box(rid: str, sentence: str, answer: int, wrong: dict[str, int]) -> Response:
    """A box in its own sentence, keyed by the mistakes whose answer is another number; room for the widest of them."""
    named = {code: v for code, v in wrong.items() if v != answer and v >= 0}
    return Response(
        rid,
        "digits",
        str(answer),
        cells=cells(max([answer, *named.values()])),
        label=sentence,
        misconceptions=named,
    )


def _either(rng: Random, options: list[str], first: Sentence, second: Sentence) -> list[Response]:
    """Two ticks, each its own sentence, in either order one as often as the other; each named by where it is printed."""
    pair = [first, second] if rng.random() < 0.5 else [second, first]
    return [
        Response(f"s{i + 1}", "tick", answer, options=list(options), label=text, misconceptions=wrong)
        for i, (text, answer, wrong) in enumerate(pair)
    ]


def order(rng: Random) -> Shape:
    """6 × 8 = 8 × □ (Y01). Writing the product is = read as "the answer comes next"."""
    a, b = rng.sample(range(2, 11), 2)
    return (
        [_box("ans", f"{a} × {b} = {b} × □", a, {"M_EQUALS_MEANS_ANSWER": a * b})],
        ["×"],
        "Write the missing number.",
    )


def by_one(rng: Random) -> Shape:
    """37 × 1 = □ and 37 ÷ 1 = □ (Y05): both leave the number. × 1 taken as adding one is named."""
    n = rng.randint(11, 99)
    rs = [_box("times", f"{n} × 1 = □", n, {"M_ONE_ADDED": n + 1}), _box("divided", f"{n} ÷ 1 = □", n, {})]
    return rs, ["×", "÷"], "Work these out."


def by_itself_and_of_zero(rng: Random) -> Shape:
    """9 ÷ 9 = □ and 0 ÷ 9 = □ (Y06): a number ÷ itself taken as nothing left, and 0 ÷ a number as the number. The rule
    is the same for any number, so any up to 50 is asked: a bank refilled week after week does not run out."""
    n = rng.randint(2, 50)
    rs = [
        _box("itself", f"{n} ÷ {n} = □", 1, {"M_DIV_SELF_AS_ZERO": 0}),
        _box("zero", f"0 ÷ {n} = □", 0, {"M_DIV_ZERO_DIVIDED": n}),
    ]
    return rs, ["÷"], "Work these out."


def true_false_order(rng: Random) -> Shape:
    """7 × 6 = 6 × 7 beside 9 − 4 = 4 − 9 (Y16): a product turned round is the same, a difference is not. True for the
    difference turns a subtraction round; false for the product judges a true claim false."""
    a, b = rng.sample(range(2, 11), 2)
    c, d = sorted(rng.sample(range(2, 20), 2), reverse=True)
    rs = _either(
        rng,
        TRUE_FALSE,
        (f"{a} × {b} = {b} × {a}", "true", {"M_REVERSES_CLAIM_TRUTH": "false"}),
        (f"{c} − {d} = {d} − {c}", "false", {"M_SUB_INSTEAD": "true"}),
    )
    return rs, ["×", "-"], "True or false? Tick one for each."


def true_false_divide_by_zero(rng: Random) -> Shape:
    """9 ÷ 0 = 0 beside 0 ÷ 9 = 0 (Y07): nothing shared is nothing each, but no number of 0s makes 9. True for the first
    reads ÷ 0 as 0; false for the second takes 0 ÷ a number to be the number. Any number up to 99 keeps the rule."""
    n = rng.randint(2, 99)
    rs = _either(
        rng,
        TRUE_FALSE,
        (f"{n} ÷ 0 = 0", "false", {"M_DIV_BY_ZERO_AS_ZERO": "true"}),
        (f"0 ÷ {n} = 0", "true", {"M_DIV_ZERO_DIVIDED": "false"}),
    )
    return rs, ["÷"], "True or false? Tick one for each."


def true_false_division_order(rng: Random) -> Shape:
    """12 ÷ 3 = 3 ÷ 12 beside 12 × 3 = 3 × 12 (Y08): a division cannot be turned round, a product can. True for the
    division divides the bigger by the smaller whichever comes first; false for the product judges a true claim false."""
    b, k = rng.randint(2, 9), rng.randint(2, 9)
    a = b * k
    rs = _either(
        rng,
        TRUE_FALSE,
        (f"{a} ÷ {b} = {b} ÷ {a}", "false", {"M_DIV_BIGGER_BY_SMALLER": "true"}),
        (f"{a} × {b} = {b} × {a}", "true", {"M_REVERSES_CLAIM_TRUTH": "false"}),
    )
    return rs, ["÷", "×"], "True or false? Tick one for each."


def grouped_either_way(rng: Random) -> Shape:
    """(2 × 7) × 5 = 2 × (7 × 5) = □ (Y02): three numbers grouped either way make one number. The outer two make a ten
    or two, as the example's 2 and 5 do, so the product stays within Grade 3's numbers. Adding every number is named
    where that is no bracket's value too: 2 + 7 + 5 is 2 × 7, so 7 is never the middle of 2 and 5."""
    a, c = rng.choice(TENS)
    middle = [b for b in range(2, 10) if b not in (a, c) and a + b + c not in (a * b, b * c)]
    b = rng.choice(middle)
    s = f"({a} × {b}) × {c} = {a} × ({b} × {c}) = □"
    return (
        [_box("ans", s, a * b * c, {"M_ADD_ALL": a + b + c})],
        ["×"],
        "Group the numbers either way to find the missing number.",
    )


def double_a_factor(rng: Random) -> Shape:
    """12 × 5 = 60, so 12 × 10 = □ (Y15): one factor doubled doubles the product. Its wrong answers are the slips of
    the multiplication asked (`misconceptions.predict`)."""
    a, b = rng.randint(11, 25), rng.randint(2, 5)
    s = f"{a} × {b} = {a * b}, so {a} × {2 * b} = □"
    return (
        [_box("ans", s, 2 * a * b, M.predict("×", a, 2 * b))],
        ["×"],
        "Use the first fact to find the answer.",
    )


def partition_a_factor(rng: Random) -> Shape:
    """7 × 12 = 7 × 10 + 7 × □ (Y03): the teen number partitioned into ten and its ones. Writing the product is = read
    as "the answer comes next"."""
    a, ones = rng.randint(3, 9), rng.randint(1, 9)
    s = f"{a} × {10 + ones} = {a} × 10 + {a} × □"
    return (
        [_box("ans", s, ones, {"M_EQUALS_MEANS_ANSWER": a * (10 + ones)})],
        ["×", "+"],
        "Write the missing number.",
    )


BALANCE = "Write the number that makes both sides equal."


def _balance(left: str, product: int, others: list[int], right: str, answer: int) -> list[Response]:
    """A product balanced against another operation, its box last: the product written is = read as "the answer comes
    next", every number added is named too; a draw whose two mistakes write one number is drawn again."""
    wrong = {"M_EQUALS_MEANS_ANSWER": product, "M_ADD_ALL": sum(others)}
    if len(set(wrong.values()) | {answer}) < 3:
        raise RuntimeError(UNFIT)
    return [_box("ans", f"{left} = {right}", answer, wrong)]


def balance_times_and_minus(rng: Random) -> Shape:
    """3 × 8 = 30 − □ (Y11): the product taken from the next ten above it."""
    a, b = rng.randint(2, 9), rng.randint(2, 9)
    p = a * b
    m = (p // 10 + 1) * 10
    return _balance(f"{a} × {b}", p, [a, b, m], f"{m} − □", m - p), ["×", "-"], BALANCE


def balance_times_and_divide(rng: Random) -> Shape:
    """6 × 4 = 48 ÷ □ (Y12): a table fact balanced against a number up to 100 divided."""
    a, b = rng.randint(2, 9), rng.randint(2, 9)
    p = a * b
    k = rng.choice([k for k in range(2, 6) if p * k <= 100] or [0])
    if not k:
        raise RuntimeError(UNFIT)
    return _balance(f"{a} × {b}", p, [a, b, p * k], f"{p * k} ÷ □", k), ["×", "÷"], BALANCE


def missing_sign(rng: Random) -> Shape:
    """6 □ 3 = 18 and 18 □ 3 = 6 (Y13): one × and one ÷ from one fact, either first. The other sign is named."""
    a, b = rng.randint(2, 9), rng.randint(2, 9)
    rs = _either(
        rng,
        SIGNS,
        (f"{a} □ {b} = {a * b}", "×", {"M_WRONG_OP": "÷"}),
        (f"{a * b} □ {b} = {a}", "÷", {"M_WRONG_OP": "×"}),
    )
    return rs, ["×", "÷"], "Write × or ÷ in each box to make it true."


def compare(rng: Random) -> Shape:
    """25 × 4 ○ 25 × 5 and 48 ÷ 6 ○ 48 ÷ 8 (Y14), without working either out: one number the same on both sides. The ×
    one turned round is named; the ÷ one answered as if a bigger divisor gave a bigger answer is the new mistake."""
    a = rng.randint(11, 30)
    b, c = rng.sample(range(2, 10), 2)
    d, e = rng.sample(range(2, 10), 2)
    lcm = d * e // math.gcd(d, e)
    if lcm > 50:
        raise RuntimeError(UNFIT)
    n = rng.choice(range(lcm, 101, lcm))
    less = {True: "<", False: ">"}
    rs = _either(
        rng,
        COMPARE,
        (f"{a} × {b} ○ {a} × {c}", less[b < c], {"M_COMPARE_REVERSED": less[b > c]}),
        (f"{n} ÷ {d} ○ {n} ÷ {e}", less[d > e], {"M_DIV_BIGGER_DIVISOR": less[d < e]}),
    )
    return rs, ["×", "÷"], "Write <, = or > without working either side out."


SHAPES: dict[str, Callable[[Random], Shape]] = {
    "ORDER": order,
    "BY_ONE": by_one,
    "BY_ITSELF_AND_OF_ZERO": by_itself_and_of_zero,
    "TRUE_FALSE_ORDER": true_false_order,
    "TRUE_FALSE_DIVIDE_BY_ZERO": true_false_divide_by_zero,
    "TRUE_FALSE_DIVISION_ORDER": true_false_division_order,
    "GROUPED_EITHER_WAY": grouped_either_way,
    "DOUBLE_A_FACTOR": double_a_factor,
    "PARTITION_A_FACTOR": partition_a_factor,
    "BALANCE_TIMES_AND_MINUS": balance_times_and_minus,
    "BALANCE_TIMES_AND_DIVIDE": balance_times_and_divide,
    "MISSING_SIGN": missing_sign,
    "COMPARE": compare,
}


def equation(rng: Random, rung: str, signal: str, shape: str) -> Item:
    """One × or ÷ equation of the given shape. Raises RuntimeError when this draw's numbers do not make it."""
    if shape not in SHAPES:
        raise ValueError(f"no × or ÷ equation shape {shape!r}")
    rs, ops, stem = SHAPES[shape](rng)
    sentences = [r.label for r in rs]
    spec = {"text": " and ".join(sentences), "sentences": sentences, "shape": shape, "ops": ops}
    return item(f"EQ.{shape}", rung, signal, "equation", stem, spec, rs, working_lines=1)
