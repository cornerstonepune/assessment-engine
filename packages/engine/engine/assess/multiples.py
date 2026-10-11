"""Multiples, factors and divisibility (goals/md4c-multiples-and-factors.yaml; the taxonomy's F cases).

Seven shapes: the multiples of a number up to a limit (F01), whether a number is a multiple of another (F02), divisible
by 2, by 5 and by 10 (F06), all the factors of a number (F03), its factor pairs (F04), the common multiples of two
numbers below a limit (F05), and divisible by 3 from the sum of the digits (F07). F08, a product odd or even, is
`reasoning.parity_of_product`'s.

A list is one answer (kind `list`): its numbers in any order, a pair either way round. It is printed as groups of boxes,
two more than it holds, so the count is not given away (`spec["spaces"]`, each `spec["width"]` boxes, `spec["per"]`
numbers a group); the reader reads each group and joins them; `judge` names what a written list shows against its key,
one answer, so one factor left out is one mistake. A yes-or-no is right one way as often as the other in each place it
is asked. Deterministic given an RNG; pure: no I/O. `bands.NATIVE_GENERATORS["multiples"]` hands a case's shape here."""

import math
import re
from collections import Counter
from collections.abc import Callable
from random import Random
from typing import Any

from . import misconceptions as M
from .counting import one_of
from .items import Item, Response, cells, item

UNFIT = "these numbers do not make this question; draw again"
SPACES = "You may not need every space."
YES_NO = ["yes", "no"]
Member = tuple[int, ...]
Shape = tuple[str, dict[str, Any], list[Response]]  # the question, its numbers, its answers


def members(text: str, per: int = 1) -> Counter[Member]:
    """A list as written: its numbers, `per` to a member in the order written, a pair sorted (3 × 8 is 8 × 3)."""
    nums = [int(x) for x in re.findall(r"\d+", text)]
    if per == 1:
        return Counter((n,) for n in nums)
    return Counter(tuple(sorted(nums[i : i + per])) for i in range(0, len(nums) - per + 1, per))


def _listed(found: list[Member], per: int) -> str:
    sep = " × "
    return ", ".join(sep.join(map(str, m)) if per > 1 else str(m[0]) for m in found)


def _list(found: list[Member], wrong: dict[str, list[Member]], per: int) -> Response:
    """A list answer, keyed by what each named mistake writes for it."""
    named = {code: _listed(w, per) for code, w in wrong.items() if Counter(w) != Counter(found)}
    return Response("list", "list", _listed(found, per), cells=0, misconceptions=named)


def _tick(rid: str, label: str, right: bool, wrong: str) -> Response:
    answer = "yes" if right else "no"
    other = "no" if right else "yes"
    return Response(rid, "tick", answer, options=list(YES_NO), label=label, misconceptions={wrong: other})


def _room(found: list[Member], per: int) -> dict[str, int]:
    """Two groups more than the list holds, each with room for its widest number."""
    return {"spaces": len(found) + 2, "width": max(len(str(x)) for m in found for x in m), "per": per}


def multiples(rng: Random) -> Shape:
    """The multiples of 6 up to 60 (F01): from the number itself to the limit, which is a multiple or not. Going past it,
    a step counted wrong and a multiple left out are each named."""
    n = rng.randint(2, 10)
    k = rng.randint(5, min(10, 100 // n))
    over = rng.randint(1, n - 1) if rng.random() < 1 / 3 else 0
    limit = n * k + (over if n * k + over <= 100 else 0)
    found = [(m,) for m in range(n, limit + 1, n)]
    mid = len(found) // 2
    wrong = {
        "M_OUT_OF_RANGE": [*found, (found[-1][0] + n,)],
        "M_MULTIPLE_MISSED": found[:mid] + found[mid + 1 :],
        "M_NOT_A_MULTIPLE": found[:mid] + [(found[mid][0] + 1,)] + found[mid + 1 :],
    }
    stem = f"Write the multiples of {n} up to {limit}. {SPACES}"
    return stem, {"n": n, "limit": limit, **_room(found, 1)}, [_list(found, wrong, 1)]


def is_a_multiple(rng: Random) -> Shape:
    """Is 45 a multiple of 5? (F02) Yes as often as no; a no that ends in the other number's last digit (is 34 a
    multiple of 4?) is asked as often as it can be, its yes the last-digit rule used where it does not work."""
    of = rng.randint(2, 10)
    if rng.random() < 0.5:
        number = of * rng.randint(math.ceil(10 / of), 99 // of)
    else:
        lure = [x for x in range(10, 100) if x % of and x % 10 == of % 10] if of not in (2, 5, 10) else []
        others = [x for x in range(10, 100) if x % of]
        number = rng.choice(lure if lure and rng.random() < 0.5 else others)
    right = number % of == 0
    lured = not right and number % 10 == of % 10 and of not in (2, 5, 10)
    wrong = "M_LAST_DIGIT_RULE_MISAPPLIED" if lured else "M_REVERSES_CLAIM_TRUTH"
    stem = f"Is {number} a multiple of {of}?"
    return stem, {"number": number, "of": of}, [_tick("yes", "a multiple?", right, wrong)]


# a 3-digit number's last digit: 0 (all three yes), 5, even, odd and not 5 — each tick yes or no about as often
LAST = (("0", 0.4), ("5", 0.2), ("2468", 0.2), ("1379", 0.2))


def divisible_by_2_5_10(rng: Random) -> Shape:
    """Is 340 divisible by 2, by 5 and by 10? (F06) Three ticks. A wrong tick its first digit would give is the first
    digit read for the last; a yes to 10 for a number ending in 5 takes 5 for 10."""
    digits = rng.choices([d for d, _ in LAST], weights=[w for _, w in LAST])[0]
    number = rng.randint(10, 99) * 10 + int(rng.choice(digits))
    first = int(str(number)[0])
    rs: list[Response] = []
    for by in (2, 5, 10):
        right = number % by == 0
        wrong = "no" if right else "yes"
        reads = "yes" if first % by == 0 else "no"
        code = (
            "M_FIVE_AS_TEN"
            if by == 10 and number % 10 == 5
            else "M_FIRST_DIGIT_FOR_LAST"
            if reads == wrong
            else "M_REVERSES_CLAIM_TRUTH"
        )
        rs.append(_tick(f"by{by}", f"by {by}", right, code))
    stem = f"Is {number} divisible by 2, by 5 and by 10? Tick yes or no for each."
    return stem, {"number": number}, rs


def _divisors(n: int) -> list[int]:
    return [d for d in range(1, n + 1) if n % d == 0]


def _in_the_tables(n: int) -> bool:
    """A factor pair of `n` other than 1 × n is a fact of the tables to 12 × 12, so its factors are found from a fact
    the child knows: 28 (4 × 7), never 57 (3 × 19 only)."""
    return any(n // d <= 12 for d in _divisors(n) if 1 < d and d * d <= n)


def factors(rng: Random) -> Shape:
    """All the factors of 12 (F03), a number up to 60 with four to eight, one of its factor pairs a fact of the tables.
    A multiple written for a factor, a number that does not divide and a factor left out (the number itself, most
    often) are named."""
    number = rng.choice([n for n in range(6, 61) if 4 <= len(_divisors(n)) <= 8 and _in_the_tables(n)])
    found = [(d,) for d in _divisors(number)]
    stray = next(x for x in range(2, number) if number % x)
    wrong = {
        "M_FACTOR_MISSED": found[:-1],
        "M_MULTIPLE_FOR_FACTOR": [*found, (2 * number,)],
        "M_NOT_A_FACTOR": sorted([*found, (stray,)]),
    }
    stem = f"Write all the factors of {number}. {SPACES}"
    return stem, {"number": number, **_room(found, 1)}, [_list(found, wrong, 1)]


def factor_pairs(rng: Random) -> Shape:
    """The factor pairs of 24 (F04), a number up to 100 with three to five pairs, each either way round (up to 60 there
    are 17 such numbers, too few for a level to hold 24 different questions). A pair written twice, turned round, and a
    pair left out are named."""
    pairs = [n for n in range(12, 101) if 3 <= math.ceil(len(_divisors(n)) / 2) <= 5 and _in_the_tables(n)]
    number = rng.choice(pairs)
    found = [(d, number // d) for d in _divisors(number) if d * d <= number]
    turned = next((m[1], m[0]) for m in reversed(found) if m[0] != m[1])
    wrong = {"M_FACTOR_PAIR_TWICE": [*found, turned], "M_FACTOR_MISSED": found[:-1]}
    stem = f"Write the factor pairs of {number}. {SPACES}"
    return stem, {"number": number, **_room(found, 2)}, [_list(found, wrong, 2)]


def common_multiples(rng: Random) -> Shape:
    """The common multiples of 3 and 4 below 30 (F05): two to four of them, the limit the next ten past the last where
    one fits before the next common multiple. A multiple of one only, a common multiple left out and one past the limit
    are named."""
    a, b = sorted(rng.sample(range(2, 11), 2))
    lcm = a * b // math.gcd(a, b)
    if lcm == b:
        raise RuntimeError(UNFIT)  # every multiple of b is common: one number's multiples, not two's
    c = rng.randint(2, 4)
    tens = (lcm * c // 10 + 1) * 10
    limit = tens if tens <= lcm * (c + 1) else lcm * c + 1
    if limit > 100:
        raise RuntimeError(UNFIT)
    found = [(lcm * i,) for i in range(1, c + 1)]
    one = next(x for x in range(a, limit) if (x % a == 0) != (x % b == 0))
    wrong = {
        "M_MULTIPLE_OF_ONE_ONLY": sorted([*found, (one,)]),
        "M_COMMON_MULTIPLE_MISSED": found[:1],
        "M_OUT_OF_RANGE": [*found, (lcm * (c + 1),)],
    }
    stem = f"Write the common multiples of {a} and {b} below {limit}. {SPACES}"
    return stem, {"a": a, "b": b, "limit": limit, **_room(found, 1)}, [_list(found, wrong, 1)]


def divisible_by_3(rng: Random) -> Shape:
    """Is 117 divisible by 3? Add its digits first (F07): the sum in a box, a fact one out its slip, then yes or no, one
    as often as the other; a wrong tick its last digit would give is the last-digit rule used where it does not work."""
    right = rng.random() < 0.5
    number = rng.choice([n for n in range(100, 1000) if (n % 3 == 0) == right])
    ds = [int(d) for d in str(number)]
    total = sum(ds)
    slips = {
        c: v for c, v in M.predict("+", ds[0] + ds[1], ds[2]).items() if c == "M_FACT_PM1" and v != total
    }
    label = f"{' + '.join(map(str, ds))} = □"
    box = Response("sum", "digits", str(total), cells=cells(total), label=label, misconceptions=slips)
    by_last = number % 10 % 3 == 0
    code = "M_LAST_DIGIT_RULE_MISAPPLIED" if by_last != right else "M_REVERSES_CLAIM_TRUTH"
    stem = f"Is {number} divisible by 3? Add its digits first."
    return stem, {"number": number}, [box, _tick("by3", "divisible by 3?", right, code)]


SHAPES: dict[str, Callable[[Random], Shape]] = {
    "MULTIPLES": multiples,
    "IS_A_MULTIPLE": is_a_multiple,
    "DIVISIBLE_BY_2_5_10": divisible_by_2_5_10,
    "FACTORS": factors,
    "FACTOR_PAIRS": factor_pairs,
    "COMMON_MULTIPLES": common_multiples,
    "DIVISIBLE_BY_3": divisible_by_3,
}


def make(rng: Random, rung: str, signal: str, shape: str) -> Item:
    """One question of the given shape. Raises RuntimeError when this draw's numbers do not make it."""
    if shape not in SHAPES:
        raise ValueError(f"no multiples shape {shape!r}")
    stem, numbers, rs = SHAPES[shape](rng)
    spec = {"shape": shape, "ops": ["×"], **numbers}
    return item(f"MULT.{shape}", rung, signal, "multiples", stem, spec, rs, working_lines=1)


def from_rule(rng: Random, rung: str, signal: str, rule: dict[str, Any]) -> Item:
    """A case's question: one of its shapes (`bands.NATIVE_GENERATORS`)."""
    return make(rng, rung, signal, one_of(rule["shape"], rng))


def _extra(spec: dict[str, Any], member: Member, key: Counter[Member]) -> str | None:
    """What one number written beyond the key shows, by the question's own numbers."""
    shape, x = spec.get("shape"), member[0]
    if member in key:
        return "M_FACTOR_PAIR_TWICE" if shape == "FACTOR_PAIRS" else None
    if shape == "MULTIPLES":
        return "M_OUT_OF_RANGE" if x % spec["n"] == 0 else "M_NOT_A_MULTIPLE"
    if shape in ("FACTORS", "FACTOR_PAIRS"):
        n = spec["number"]
        return "M_MULTIPLE_FOR_FACTOR" if len(member) == 1 and x > n and x % n == 0 else "M_NOT_A_FACTOR"
    if shape == "COMMON_MULTIPLES":
        a, b = spec["a"], spec["b"]
        both, one = x % a == 0 and x % b == 0, x % a == 0 or x % b == 0
        return "M_OUT_OF_RANGE" if both else "M_MULTIPLE_OF_ONE_ONLY" if one else "M_NOT_A_MULTIPLE"
    return None


MISSED = {
    "MULTIPLES": "M_MULTIPLE_MISSED",
    "FACTORS": "M_FACTOR_MISSED",
    "FACTOR_PAIRS": "M_FACTOR_MISSED",
    "COMMON_MULTIPLES": "M_COMMON_MULTIPLE_MISSED",
}


def judge(spec: dict[str, Any], key: str, wrote: str) -> tuple[bool, list[str]]:
    """A written list against its key, as one answer: (right, the mistakes it shows) — any order, a pair either way
    round; a member left out and each number beyond the key named for what it is."""
    per = int(spec.get("per", 1))
    want, got = members(key, per), members(wrote, per)
    if want == got:
        return True, []
    codes: set[str] = {MISSED[spec["shape"]]} if want - got and spec.get("shape") in MISSED else set()
    codes |= {c for m in (got - want) if (c := _extra(spec, m, want))}
    return False, sorted(codes)
