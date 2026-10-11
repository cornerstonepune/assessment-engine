"""Multiples and factors worked out from the question's own words (goals/md4c-multiples-and-factors.yaml), never from
what the code that made it stored: every list, every yes-or-no and every digit sum (the sum's box is its sentence's,
`scenarios._from_sentence`). A list is right in any order, a pair either way round, as marking marks it."""

import math
import re
from collections import Counter

# What a "Write the …" question asks for, read off its sentence, and the list it makes: each member a tuple.
LISTS = (
    (
        r"common multiples of (\d+) and (\d+) below (\d+)",
        lambda a, b, below: [(k,) for k in range(1, below) if k % a == 0 and k % b == 0],
    ),
    (r"multiples of (\d+) up to (\d+)", lambda n, top: [(k,) for k in range(n, top + 1, n)]),
    (r"all the factors of (\d+)", lambda n: [(d,) for d in range(1, n + 1) if n % d == 0]),
    (r"factor pairs of (\d+)", lambda n: [(d, n // d) for d in range(1, math.isqrt(n) + 1) if n % d == 0]),
)


def _written(text):
    """A list as written: its members, split at commas, each one's numbers in order of size (8 × 3 is 3 × 8)."""
    parts = (sorted(int(x) for x in re.findall(r"\d+", p)) for p in re.split(r"[,;]", text))
    return Counter(tuple(p) for p in parts if p)


def _divides(stem, rid):
    """Whether the number a yes-or-no asks about divides as asked: "Is 45 a multiple of 5?" (rid `yes`); "Is 340
    divisible by 2, by 5 and by 10?" (rids `by2`, `by5`, `by10`); "Is 117 divisible by 3?" (`by3`). None for another."""
    if rid == "yes" and (m := re.search(r"Is (\d+) a multiple of (\d+)\?", stem)):
        return int(m[1]) % int(m[2]) == 0
    if (by := re.fullmatch(r"by(\d+)", rid)) and (m := re.search(r"Is (\d+) divisible by", stem)):
        return int(m[1]) % int(by[1]) == 0
    return None


def checks(fmt, stem, responses, stated):
    """[whether each answer it can work out is the one stated] for a multiples question; [] for any other kind."""
    if fmt != "multiples":
        return []
    out = []
    for pattern, make in LISTS:
        if m := re.search(pattern, stem):
            out.append(_written(stated.get("list", "")) == Counter(make(*map(int, m.groups()))))
            break
    for r in responses:
        if r.kind == "tick" and (right := _divides(stem, r.rid)) is not None:
            out.append(stated.get(r.rid) == ("yes" if right else "no"))
    return out
