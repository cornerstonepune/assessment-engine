"""A level's questions, drawn evenly from the taxonomy cases it holds (step 8f). Deterministic given an RNG.

A level whose rule lists `cases` holds exactly those cases. For each, candidates are drawn and kept only
when the question as measured (`assess/tags.py`) is that case (`assess/taxonomy.py`) and inside the
level's own bounds — the case rule is the definition, the drawing only has to find members of it.

Plain sums and missing numbers are sampled from their digits (`assess/draw_pair.py`). Every other kind comes from its
own generator, told what the case is about (`assess/draw_native.py`). What a case allows (its kinds, its operation,
the digits of its numbers) is read in `assess/draw_case.py`.

The drawing keeps a few defaults a question needs to test anything: no number ending in 0, no two equal
numbers, no difference under 5, nothing multiplied by 1. A case about exactly that — a zero, a zero answer, an
answer that shrinks, a round number, × 1 — lifts the default it is about, and only that one.

A multiplication's numbers, and the defaults it keeps, are `assess/draw_times.py`'s; a division's are
`assess/draw_divide.py`'s, a quotient's box and a remainder's its own (`verify.division`). A case that names its method
is printed that way: in a line, in columns, in the division layout, or in a written method of its own kind
(`assess/written.py`); a level that lists `methods` prints each case's calculations in every one of them, in fair
shares (ADR 0055, 0063).
"""

import itertools
import math
import random
from collections.abc import Iterator
from typing import Any, cast

from . import bands, tags, taxonomy, verify
from . import divide_kinds as DK
from . import draw_case as K
from . import draw_divide as DD
from . import draw_native as N
from . import draw_pair as P
from . import draw_times as T
from . import facts_kinds as FK
from . import items as I
from . import misconceptions as M
from . import operations as O
from . import reasoning as RS
from . import times_kinds as TK
from . import written as WR

PLAIN = ("bare_sum", "column_grid")
# every kind a straight calculation is printed in
STRAIGHT = tuple(dict.fromkeys((*PLAIN, *WR.KINDS.values())))
SUMS_LISTED = 100_000  # pairs of a sum's digits: 3 by 2 is 81,000; 3 by 3 (810,000) is only ever drawn
POSITIONS = {
    "FIRST_OPERAND": "a",
    "SECOND_OPERAND": "b",
    "RESULT": "answer",
    "MULTIPLE": "both",
    "REMAINDER": "remainder",
}


def _plain(rng: random.Random, alt: dict[str, Any], check: dict[str, Any], rung: str, k: int):
    op = K.op(rng, alt, check)
    got = op and P.pair(rng, alt, check, op, taxonomy.keys(alt))
    return _set_out(alt, check, rung, k, op, *got) if op and got else None


def _set_out(
    alt: dict[str, Any], check: dict[str, Any], rung: str, k: int, op: str, a: int, b: int
) -> I.Item:
    method = alt.get("method") if isinstance(alt.get("method"), str) else None
    if method in WR.KINDS:
        return WR.make(method, a, b, rung)  # a written method, a box for every step (ADR 0055, 0063)
    pres = (
        alt.get("presentation")
        or K.LAYOUT.get(method or "")
        or {"column": "VERTICAL", "horizontal": "HORIZONTAL"}.get(check.get("layout") or "")
    )
    column = pres == "VERTICAL" if pres else k % 2 == 0  # half in columns, half in a line
    if op == "÷":  # in a line or the division layout, or asked in words (a shape: "How many 6s make 42?")
        shape = alt.get("shape") if isinstance(alt.get("shape"), str) else None
        return verify.division(a, b, rung, "column" if column else "horizontal", shape)
    if op == "×" and alt.get("operand_order") == "SHORTER_FIRST":
        column = False  # the 1-digit number written first is a line's: in columns it goes below the longer
    elif op == "×" and column and len(str(a)) < len(str(b)):
        a, b = b, a  # set out as the school writes it: the longer number on top, the 1-digit number below it
    cand = {
        "format": "column_grid" if column else "bare_sum",
        "op": op,
        "a": a,
        "b": b,
        "answer": M.compute(op, a, b),
    }
    return verify.to_item(cand | {"stem": "", "missing": None, "misconceptions": []}, rung)


def _many(rng, alt, check, rung, k):
    """Three or more numbers (§2.8), or three with a friendly pair (§8, K07)."""
    about = taxonomy.keys(alt)
    friendly = alt.get("shape") == "FRIENDLY_PAIRS"
    n = 3 if friendly else K.pick(rng, alt.get("num_operands"), range(3, 6))
    # a level's `digits_max` is the width of its widest number (ADDSUB.4D.ADV adds 4-digit numbers)
    widest = K.pick(
        rng, alt.get("digits_max"), [check["digits_max"]] if "digits_max" in check else range(1, 5)
    )
    if not n or not widest:
        return None
    if friendly:
        x = rng.randint(11, 89)
        xs = [x, rng.randint(11, 99), 100 - x]
    elif alt.get("operand_order") == "MIXED":
        low = K.pick(rng, alt.get("digits_min"), range(1, widest)) or 1
        lengths = [widest, low] + [rng.randint(low, widest) for _ in range(n - 2)]
        rng.shuffle(lengths)
        xs = [P.number(rng, d, False) for d in lengths]
    else:
        xs = [P.number(rng, widest, False) for _ in range(n)]
    if not (about & P.ZERO_KEYS) and any(x % 10 == 0 for x in xs):
        return None
    if check.get("max_total") and sum(xs) > check["max_total"]:
        return None
    pres = alt.get("presentation")
    layout = (
        "horizontal"
        if friendly
        else ("column" if (pres == "VERTICAL" if pres else k % 2 == 0) else "horizontal")
    )
    return I.multi_add(
        rng, rung, "Procedural", xs=xs, layout=layout, shape="FRIENDLY_PAIRS" if friendly else None
    )


def _missing(
    rng: random.Random, alt: dict[str, Any], check: dict[str, Any], rung: str, k: int
) -> I.Item | None:
    """A missing number (§6.1, §6.3): which number the box hides and how many digits it has."""
    if alt.get("shape") == "MISSING_ROW":
        return TK.missing_row(rng, rung)  # a long multiplication's second row (34 × 26 = 204 + □)
    if isinstance(alt.get("num_operands"), dict):
        return bands.native_item(
            "missing_number",
            {"kind": "among_three", "hi": check.get("max_total", 100)},
            rng,
            rung,
            "Conceptual",
        )
    op = K.op(rng, alt, check)
    if op is None:
        return None
    first = alt.get("answer_first") == "YES"  # □ = 63 ÷ 9: the answer's box written first
    ways = (
        ["RESULT"]
        if first
        else ["FIRST_OPERAND", "SECOND_OPERAND"]
        + (["RESULT"] if op == "-" else ["MULTIPLE"] if op == "×" else ["REMAINDER"] if op == "÷" else [])
    )
    where = K.pick(rng, alt.get("unknown_position"), ways)
    size = K.pick(rng, alt.get("unknown_digits"), K.DIGITS) if "unknown_digits" in alt else None
    if not where:
        return None
    fix = (
        (0, size)
        if size and where == "FIRST_OPERAND"
        else ((1, size) if size and where == "SECOND_OPERAND" else None)
    )
    got = P.pair(rng, alt, check, op, taxonomy.keys(alt), fix)
    if not got:
        return None
    a, b = (got[0], got[0]) if where == "MULTIPLE" else got  # □ × □ = 49: one number in both boxes
    hide = POSITIONS[where]
    if op == "×" and hide in ("a", "b") and FK.factor_missing(alt):
        try:
            a, b = FK.boxed_factor(a, b, hide)  # 45 × □ = 4500: the box hides 10, 100 or 1000
        except RuntimeError:
            return None
    rem = O.divide(a, b)[1] if op == "÷" else 0
    if (hide == "remainder" and not rem) or (rem and hide not in ("b", "remainder")):
        return None  # a remainder's box needs one; with one, the divisor's box or the remainder's is asked (Q12, Q13)
    ans = a // b if rem else M.compute(op, a, b)
    sign, left = O.PRINTED[op], f" r {rem}" if rem else ""
    text = {
        "a": f"□ {sign} {b} = {ans}",
        "b": f"{a} {sign} □ = {ans}{left}",
        "answer": f"□ = {a} {sign} {b}" if first else f"{a} {sign} {b} = □",
        "both": f"□ {sign} □ = {ans}",
        "remainder": f"{a} {sign} {b} = {ans} r □",
    }[hide]
    cand = {"format": "missing_number", "op": op, "a": a, "b": b, "answer": ans, "stem": text}
    return verify.to_item(cand | {"missing": hide, "misconceptions": [], "answer_first": first}, rung)


def _paired(rng: random.Random, alt: dict[str, Any], check: dict[str, Any], rung: str, build: FK.Build):
    """A kind built on its case's own two numbers (`facts_kinds`, `divide_kinds`, a product judged in `reasoning`), drawn
    as a straight question's are: a table fact on a tables level, a round number on the tens level, 2 digits by 1 where
    the case's example is (48 × 6)."""
    op = K.op(rng, alt, check)
    got = op and P.pair(rng, alt, check, op, taxonomy.keys(alt))
    if not got:
        return None
    try:
        return build(rng, *got, rung, alt)
    except RuntimeError:
        return None  # numbers this kind cannot use (7 × 7 has no fact family of four): drawn again


def _straight(alt: dict[str, Any]) -> bool:
    """A straight calculation: in a line or in columns, or in the one written method it names (`_set_out`)."""
    fmts = set(K.fmts(alt))
    return fmts <= set(STRAIGHT) and bool(fmts & set(PLAIN) or isinstance(alt.get("method"), str))


def _of_many(alt: dict[str, Any]) -> bool:
    """A straight case of three or more numbers, or a friendly pair (`_many`); a × case reads `carry_max` of one."""
    return alt.get("operation") != "MUL" and (
        ("num_operands" in alt and any(taxonomy.holds(alt["num_operands"], n) for n in (3, 4, 5)))
        or "carry_max" in alt
        or alt.get("shape") == "FRIENDLY_PAIRS"
    )


def one(rng: random.Random, match: Any, check: dict[str, Any], rung: str, k: int = 0) -> I.Item | None:
    """One candidate for a case, or None when this attempt's numbers are not that case. `k` counts the
    questions kept so far; where the case does not fix the layout, even is in columns, odd in a line."""
    alt = rng.choice(K.alternatives(match))
    fmts = set(K.fmts(alt))
    if _straight(alt):
        it = (_many if _of_many(alt) else _plain)(rng, alt, check, rung, k)
    elif fmts == {"missing_number"}:
        it = _missing(rng, alt, check, rung, k)
    elif len(fmts) == 1 and (
        build := FK.builder(alt, f := next(iter(fmts))) or DK.builder(alt, f) or RS.builder(alt, f)
    ):
        it = _paired(rng, alt, check, rung, build)
    else:
        it = N.native(rng, alt, check, rung, k)
    return it if it is not None and taxonomy.matches(match, it.fmt, tags.derive(it)) else None


def _some(
    rng: random.Random, match: Any, check: dict[str, Any], rung: str, want: int, seen: set[str], tries: int
) -> list[I.Item]:
    out: list[I.Item] = []
    k = 0
    while len(out) < want and k < tries:
        it = one(rng, match, check, rung, len(seen))  # alternates the layout by questions kept, not tries
        k += 1
        if it is not None and it.item_id not in seen:
            seen.add(it.item_id)
            out.append(it)
    return out if len(out) == want else out + _rest(rng, match, check, rung, want - len(out), seen)


def _every(alt: dict[str, Any], check: dict[str, Any], op: str) -> list[tuple[int, int]] | None:
    """Every pair a straight case of two numbers can be (`draw_times.every`, `draw_divide.every`, and every pair of a
    sum's digits); None past what can be listed."""
    if op == "÷":  # its defaults kept in the listing; the method it is printed in still has its own say
        return [(a, b) for a, b in DD.every(alt, K.pairs(alt, check, op)) if P.sets_out(alt, a, b)]
    about = taxonomy.keys(alt)
    zero_ok = "zero_operand" in about
    ranges = [
        T.every(alt, about, d1, d2) if op == "×" else _sums(T.span(d1, zero_ok), T.span(d2, zero_ok))
        for d1, d2 in K.pairs(alt, check, op)
    ]
    if None in ranges:
        return None
    return [(a, b) for r in ranges if r for a, b in r if P.usable(op, a, b, about, check, alt)]


def _sums(xs: range, ys: range) -> list[tuple[int, int]] | None:
    """Every pair of a sum's or a difference's digits, or None past what can be listed."""
    return [(a, b) for a in xs for b in ys] if len(xs) * len(ys) <= SUMS_LISTED else None


def _ops(alt: dict[str, Any], check: dict[str, Any]) -> list[str]:
    """Every operation a case can be drawn in (`draw_case.op` picks one): its own, or its level's."""
    named = alt.get("operation")
    if named is None:
        ops: Any = check.get("op", ["+", "-"])
        return list(cast(list[str], ops)) if isinstance(ops, list) else [ops]
    return [K.OPS[k] for k in K.OPS if taxonomy.holds(named, k)]


Listing = list[tuple[dict[str, Any], str, int, int, int]]


def _listing(match: Any, check: dict[str, Any]) -> tuple[Listing, bool]:
    """Every (conditions, operation, a, b, layout) the straight calculations of two numbers in a case can be printed
    with, both layouts where the level fixes neither, and whether that is the whole case: not where it has another
    kind, or a range too large to list."""
    rows: Listing = []
    whole = True
    for alt in K.alternatives(match):
        listable = _straight(alt) and not _of_many(alt)
        pairs = {op: _every(alt, check, op) for op in _ops(alt, check)} if listable else {}
        whole = whole and bool(pairs) and None not in pairs.values()
        rows += [(alt, op, a, b, k) for op, got in pairs.items() for a, b in got or [] for k in (0, 1)]
    return rows, whole


def _new(match: Any, check: dict[str, Any], rung: str, rows: Listing, seen: set[str]) -> Iterator[I.Item]:
    """The questions `rows` print that are the case, as measured, and not yet in `seen`; each one added to it."""
    for alt, op, a, b, k in rows:
        it = _set_out(alt, check, rung, k, op, a, b)
        if it.item_id not in seen and taxonomy.matches(match, it.fmt, tags.derive(it)):
            seen.add(it.item_id)
            yield it


def listed(match: Any, check: dict[str, Any], rung: str) -> list[I.Item] | None:
    """Every different question a case can be on its level, or None where that cannot be listed (`_listing`): what a
    level that falls short is measured against."""
    rows, whole = _listing(match, check)
    return list(_new(match, check, rung, rows, set())) if whole else None


def _rest(
    rng: random.Random, match: Any, check: dict[str, Any], rung: str, want: int, seen: set[str]
) -> list[I.Item]:
    """What a straight case of two numbers still holds when its draws run dry, read from every pair it can be, in a
    random order: dry is then a fact, not 2000 misses in a row, and the last questions found are as varied as the
    first (ADD.2D1D Hard's three cases hold 180 questions for its 175, and the last few turned up about once in 1,600
    draws, so a build now and then ended a few short: CI, 2026-10-21). A range too large to list, and other kinds',
    keep the misses."""
    rows, _ = _listing(match, check)
    rng.shuffle(rows)
    return list(itertools.islice(_new(match, check, rung, rows, seen), want))


def split(want: int, ways: int) -> list[int]:
    """A share dealt over `ways`, the first ones one more where it does not divide: 10 over 4 is 3, 3, 2, 2."""
    return [want // ways + (i < want % ways) for i in range(ways)]


def _shared(
    rng: random.Random,
    ways: list[Any],
    check: dict[str, Any],
    rung: str,
    want: int | list[int],
    seen: set[str],
    tries: int,
) -> list[I.Item]:
    """A case's share dealt over the ways its level prints it (`split`), or what each way is short of, and taken a way
    at a time, so a share cut short keeps every method."""
    shares = want if isinstance(want, list) else split(want, len(ways))
    got = [_some(rng, w, check, rung, k, seen, max(1, k) * tries) for w, k in zip(ways, shares, strict=True)]
    return [its[i] for i in range(max(map(len, got), default=0)) for its in got if i < len(its)]


def level(
    rng: random.Random,
    check: dict[str, Any],
    matches: dict[str, Any],
    rung: str,
    n: int,
    seen: set[str] | None = None,
    tries_per_item: int = 2000,
    quotas: dict[str, int | list[int]] | None = None,
) -> list[tuple[str, I.Item]]:
    """Up to `n` distinct [(case, question)] for a level: the same number from each case it holds, then —
    where a case's numbers run out (7 − 7 has nine) — the rest from the cases that still have more.

    With `quotas` (what each case is still short of, or each way it is printed in) every case is drawn its own
    shortfall as far as its numbers go, and `n` is only what the level as a whole still needs: a case that has run out
    stays short for good, and letting that spill onto the others made every refill add more of them.

    A level that lists `methods` prints each case's share in every written method it can be printed in, in fair
    shares (`draw_case.ways`, assumption A1); `matches` then holds the methods' cases too."""
    codes = list(check["cases"])
    seen = set() if seen is None else seen
    even = quotas is None
    shares: dict[str, int | list[int]] = dict.fromkeys(codes, math.ceil(n / len(codes))) if even else quotas
    ways = {c: K.ways(matches[c], [matches[m] for m in check.get("methods", [])]) for c in codes}
    drawn = {
        code: _shared(rng, ways[code], check, rung, shares.get(code, 0), seen, tries_per_item)
        for code in codes
    }
    # dealt a case at a time, so cutting an even draw to `n` takes one from each case in turn: nine cases asked for
    # forty drew five each, and cutting the forty-five in case order left the ninth case out altogether
    out = [
        (c, its[i])
        for i in range(max(map(len, drawn.values()), default=0))
        for c, its in drawn.items()
        if i < len(its)
    ]
    open_codes = list(codes)
    while len(out) < n and open_codes:
        for code in list(open_codes):
            either = [a for w in ways[code] for a in K.alternatives(w)]
            more = _some(rng, either, check, rung, 1, seen, tries_per_item)
            if not more:
                open_codes.remove(code)
            out += [(code, it) for it in more]
            if len(out) >= n:
                break
    return out[:n] if even else out
