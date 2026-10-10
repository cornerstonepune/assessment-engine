"""A level's questions, drawn evenly from the taxonomy cases it holds (step 8f). Deterministic given an RNG.

A level whose rule lists `cases` holds exactly those cases. For each, candidates are drawn and kept only
when the question as measured (`assess/tags.py`) is that case (`assess/taxonomy.py`) and inside the
level's own bounds — the case rule is the definition, the drawing only has to find members of it.

Plain sums and missing numbers are sampled from their digits here. Every other kind comes from its own
generator (`bands.NATIVE_GENERATORS`), told what the case is about — a story's shape, a planted mistake, the method
it is printed by — through the same rule keys a level can set. What a case allows (its kinds, its operation, the
digits of its numbers) is read in `assess/draw_case.py`.

The drawing keeps a few defaults a question needs to test anything: no number ending in 0, no two equal
numbers, no difference under 5, nothing multiplied by 1. A case about exactly that — a zero, a zero answer, an
answer that shrinks, a round number, × 1 — lifts the default it is about, and only that one.

A multiplication's numbers, and the defaults it keeps, are `assess/draw_times.py`'s. A case that names its method
is printed that way: in a line, in columns, or in a written method of its own kind (`assess/written_methods.py`); a
level that lists `methods` prints each case's calculations in every one of them, in fair shares (ADR 0055).
"""

import math
import random
from typing import Any

from . import bands, tags, taxonomy, verify
from . import draw_case as K
from . import draw_sums as S
from . import draw_times as T
from . import items as I
from . import misconceptions as M
from . import operations as O
from . import times_kinds as TK
from . import written_methods as WM

PLAIN = ("bare_sum", "column_grid")
STRAIGHT = (*PLAIN, *WM.KINDS.values())  # every kind a straight calculation is printed in
ZERO_KEYS = {"zero_operand", "zeros_in", "zeros_max", "exchange_zeros", "carry_into_zero", "answer_zeros"}
ROUND_KEYS = {"round_operand", "answer_power_of_ten"}
SIZE_KEYS = {"answer_digit_change", "difference_small", "unknown_digits", "equal_operands"}
HINTS = (
    "structure",
    "shape",
    "planted",
    "round_to",
    "missing_count",
    "missing_in",
    "missing_place",
    "strategy",
    "method",
)
POSITIONS = {"FIRST_OPERAND": "a", "SECOND_OPERAND": "b", "RESULT": "answer"}


def _number(rng: random.Random, d: int, zero_ok: bool) -> int:
    return rng.randint(0 if (d == 1 and zero_ok) else (1 if d == 1 else 10 ** (d - 1)), 10**d - 1)


def _usable(
    op: str, a: int, b: int, about: set[str], check: dict[str, Any], alt: dict[str, Any] | None = None
) -> bool:
    """The defaults every question keeps unless its case is about the very thing they rule out."""
    zero_case, round_case, size_case = about & ZERO_KEYS, about & ROUND_KEYS, about & SIZE_KEYS
    if op == "×":
        lifts = {name for name, on in (("zero", zero_case), ("round", round_case), ("size", size_case)) if on}
        return T.usable(a, b, about, check, alt or {}, lifts)
    if op == "-" and a < b:
        return False
    if not zero_case and 0 in (a, b):
        return False
    if not (zero_case or round_case) and any(x >= 10 and x % 10 == 0 for x in (a, b)):
        return False
    if a == b and not (size_case or a < 10):
        return False
    if op == "-" and a == b and not size_case:
        return False
    if op == "-" and a >= 10 and a - b < 5 and not size_case:
        return False
    top = a + b if op == "+" else a
    return not (check.get("max_total") and top > check["max_total"])


def _pair(rng, alt, check, op, about, fix=None) -> tuple[int, int] | None:
    """Two numbers for this case, or None. `fix` pins one number's digit count (a missing number)."""
    built = S.built(rng, alt)
    if built:
        return built
    pairs = [p for p in K.pairs(alt, check, op) if not fix or p[fix[0]] == fix[1]]
    if not pairs:
        return None
    d1, d2 = rng.choice(pairs)
    zero_ok = "zero_operand" in about
    if op == "×":
        got = T.numbers(rng, alt, about, d1, d2)
        return got if got and _usable(op, *got, about, check, alt) else None
    a, b = _number(rng, d1, zero_ok), _number(rng, d2, zero_ok)
    shrink = K.pick(rng, alt.get("answer_digit_change"), ["-1", "-MULTIPLE", "ZERO"]) if op == "-" else None
    if shrink and "answer_digit_change" in alt:
        # An answer that loses digits is rare among random pairs (105 − 97): choose the answer, then b.
        size = {"-1": d1 - 1, "-MULTIPLE": rng.randint(1, d1 - 2) if d1 > 2 else 0, "ZERO": 0}[shrink]
        answer = 0 if shrink == "ZERO" else (_number(rng, size, False) if size else None)
        if answer is None:
            return None
        if shrink == "ZERO":
            b = a
        else:
            a = answer + b  # the answer and the number taken away first; the top number follows
            if len(str(a)) != d1:
                return None
    return (a, b) if _usable(op, a, b, about, check) else None


def _plain(rng: random.Random, alt: dict[str, Any], check: dict[str, Any], rung: str, k: int):
    op = K.op(rng, alt, check)
    got = op and _pair(rng, alt, check, op, taxonomy.keys(alt))
    return _set_out(alt, check, rung, k, op, *got) if op and got else None


def _set_out(
    alt: dict[str, Any], check: dict[str, Any], rung: str, k: int, op: str, a: int, b: int
) -> I.Item:
    method = alt.get("method") if isinstance(alt.get("method"), str) else None
    if method in WM.KINDS:
        return WM.make(method, a, b, rung)  # a written method, a box for every step (ADR 0055)
    pres = (
        alt.get("presentation")
        or K.LAYOUT.get(method or "")
        or {"column": "VERTICAL", "horizontal": "HORIZONTAL"}.get(check.get("layout") or "")
    )
    column = pres == "VERTICAL" if pres else k % 2 == 0  # half in columns, half in a line
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
        xs = [_number(rng, d, False) for d in lengths]
    else:
        xs = [_number(rng, widest, False) for _ in range(n)]
    if not (about & ZERO_KEYS) and any(x % 10 == 0 for x in xs):
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
    ways = ["FIRST_OPERAND", "SECOND_OPERAND"] + (["RESULT"] if op == "-" else [])
    where = K.pick(rng, alt.get("unknown_position"), ways)
    size = K.pick(rng, alt.get("unknown_digits"), K.DIGITS) if "unknown_digits" in alt else None
    if not where:
        return None
    fix = (
        (0, size)
        if size and where == "FIRST_OPERAND"
        else ((1, size) if size and where == "SECOND_OPERAND" else None)
    )
    got = _pair(rng, alt, check, op, taxonomy.keys(alt), fix)
    if not got:
        return None
    a, b = got
    ans = M.compute(op, a, b)
    sign = O.PRINTED[op]
    text = {"a": f"□ {sign} {b} = {ans}", "b": f"{a} {sign} □ = {ans}", "answer": f"{a} {sign} {b} = □"}[
        POSITIONS[where]
    ]
    cand = {"format": "missing_number", "op": op, "a": a, "b": b, "answer": ans, "stem": text}
    return verify.to_item(cand | {"missing": POSITIONS[where], "misconceptions": []}, rung)


def _one_value(rng, v):
    """A hint the generator can use: one of a list, or a number inside a range (two or more boxes)."""
    if isinstance(v, list):
        return rng.choice(v)
    if isinstance(v, dict):
        return rng.randint(v.get("gte", 1), v.get("lte", v.get("gte", 1) + 1))
    return v


def _native(
    rng: random.Random, alt: dict[str, Any], check: dict[str, Any], rung: str, k: int
) -> I.Item | None:
    fmt = rng.choice([f for f in K.fmts(alt) if bands.makes(f, alt)] or K.fmts(alt))
    hints: dict[str, Any] = {key: _one_value(rng, v) for key in HINTS if (v := alt.get(key)) is not None}
    if alt.get("context") == "TABLE_OR_CHART":
        hints["table"] = True
    if alt.get("operation"):
        hints["op"] = K.op(rng, alt, check)
        if hints["op"] is None:
            return None  # the case allows neither operation this drawer writes
    # The numbers' size, from the case as its level narrowed it (`within`), where the level's rule does not
    # already say: a story or a number line left to its generator's own default wrote 2-digit numbers on a
    # 1-digit level, and every one was refused by the case it was drawn for.
    if "digits" not in check and any(
        k in alt for k in ("operand_1_digits", "operand_2_digits", "digits_max")
    ):
        pairs = K.pairs(alt, check, hints.get("op") or "+")
        if not pairs:
            return None
        d1, d2 = rng.choice(pairs)
        hints["digits"] = [d1, d2]
        if "hi" not in check:
            hints["hi"] = 10**d1 - 1 + (10**d2 - 1 if hints.get("op", "+") == "+" else 0)
    try:
        return bands.native_item(fmt, {**check, **hints}, rng, rung, "Conceptual")
    except O.CannotMake:
        raise  # the case asks this kind for an operation it does not make: no draw can give it, say so
    except RuntimeError:
        return None  # numbers that did not fit, drawn again; a rule the kind cannot read is raised, not drawn past


def one(rng, match, check, rung, k=0):
    """One candidate for a case, or None when this attempt's numbers are not that case. `k` counts the
    questions kept so far; where the case does not fix the layout, even is in columns, odd in a line."""
    alt = rng.choice(K.alternatives(match))
    fmts = set(K.fmts(alt))
    # a straight calculation: in a line or in columns, or in the one written method it names (`_set_out`)
    if fmts <= set(STRAIGHT) and (fmts & set(PLAIN) or isinstance(alt.get("method"), str)):
        many = alt.get("operation") != "MUL" and (  # a × case reads `carry_max` of one multiplication
            ("num_operands" in alt and any(taxonomy.holds(alt["num_operands"], n) for n in (3, 4, 5)))
            or "carry_max" in alt
            or alt.get("shape") == "FRIENDLY_PAIRS"
        )
        it = (_many if many else _plain)(rng, alt, check, rung, k)
    elif fmts == {"missing_number"}:
        it = _missing(rng, alt, check, rung, k)
    else:
        it = _native(rng, alt, check, rung, k)
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
    return out if len(out) == want else out + _rest(match, check, rung, want - len(out), seen)


def _rest(match: Any, check: dict[str, Any], rung: str, want: int, seen: set[str]) -> list[I.Item]:
    """What a × case still holds when its draws run dry, read from every pair it can be (`draw_times.every`): dry is
    then a fact, not 2000 misses in a row. A range too large to list, and other kinds', keep the misses."""
    out: list[I.Item] = []
    for alt in [
        x for x in K.alternatives(match) if x.get("operation") == "MUL" and set(K.fmts(x)) <= set(STRAIGHT)
    ]:
        about = taxonomy.keys(alt)
        ranges = [T.every(alt, about, d1, d2) for d1, d2 in K.pairs(alt, check, "×")]
        pairs = [] if None in ranges else [p for r in ranges if r for p in r]
        for a, b, k in [(a, b, k) for a, b in pairs if _usable("×", a, b, about, check, alt) for k in (0, 1)]:
            it = _set_out(
                alt, check, rung, k, "×", a, b
            )  # both layouts: a level that does not fix one prints either
            if it.item_id not in seen and taxonomy.matches(match, it.fmt, tags.derive(it)):
                seen.add(it.item_id)
                out.append(it)
                if len(out) == want:
                    return out
    return out


def _shared(
    rng: random.Random,
    ways: list[Any],
    check: dict[str, Any],
    rung: str,
    want: int,
    seen: set[str],
    tries: int,
) -> list[I.Item]:
    """A case's share dealt over the ways its level prints it, the first ones one more where it does not divide, and
    taken a way at a time, so a share cut short keeps every method."""
    base, extra = divmod(want, len(ways))
    got = [
        _some(rng, w, check, rung, base + (i < extra), seen, (base + 1) * tries) for i, w in enumerate(ways)
    ]
    return [its[i] for i in range(max(map(len, got), default=0)) for its in got if i < len(its)]


def level(
    rng: random.Random,
    check: dict[str, Any],
    matches: dict[str, Any],
    rung: str,
    n: int,
    seen: set[str] | None = None,
    tries_per_item: int = 2000,
    quotas: dict[str, int] | None = None,
) -> list[tuple[str, I.Item]]:
    """Up to `n` distinct [(case, question)] for a level: the same number from each case it holds, then —
    where a case's numbers run out (7 − 7 has nine) — the rest from the cases that still have more.

    With `quotas` (what each case is still short of) every case is drawn its own shortfall as far as its
    numbers go, and `n` is only what the level as a whole still needs: a case that has run out stays
    short for good, and letting that spill onto the others made every refill add more of them.

    A level that lists `methods` prints each case's share in every written method it can be printed in, in fair
    shares (`draw_case.ways`, assumption A1); `matches` then holds the methods' cases too."""
    codes = list(check["cases"])
    seen = set() if seen is None else seen
    even = quotas is None
    quotas = dict.fromkeys(codes, math.ceil(n / len(codes))) if even else quotas
    ways = {c: K.ways(matches[c], [matches[m] for m in check.get("methods", [])]) for c in codes}
    drawn = {
        code: _shared(rng, ways[code], check, rung, quotas.get(code, 0), seen, tries_per_item)
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
