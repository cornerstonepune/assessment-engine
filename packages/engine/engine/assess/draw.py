"""A level's questions, drawn evenly from the taxonomy cases it holds (step 8f). Deterministic given an RNG.

A level whose rule lists `cases` holds exactly those cases. For each, candidates are drawn and kept only
when the question as measured (`assess/tags.py`) is that case (`assess/taxonomy.py`) and inside the
level's own bounds — the case rule is the definition, the drawing only has to find members of it.

Plain sums and missing numbers are sampled from their digits here. Every other kind comes from its own
generator (`bands.NATIVE_GENERATORS`), told what the case is about — a story's shape, a planted mistake —
through the same rule keys a level can set.

The drawing keeps a few defaults a question needs to test anything: no number ending in 0, no two equal
numbers, no difference under 5. A case about exactly that — a zero, a zero answer, an answer that
shrinks — lifts the default it is about, and only that one.
"""

import math

from . import bands, tags, taxonomy, verify
from . import items as I
from . import misconceptions as M

PLAIN = ("bare_sum", "column_grid")
ZERO_KEYS = {"zero_operand", "zeros_in", "zeros_max", "exchange_zeros", "carry_into_zero", "answer_zeros"}
ROUND_KEYS = {"round_operand", "answer_power_of_ten"}
SIZE_KEYS = {"answer_digit_change", "difference_small", "unknown_digits"}
HINTS = ("structure", "shape", "planted", "round_to", "missing_count", "missing_in", "missing_place")
DIGITS = range(1, 5)
OPS = {"ADD": "+", "SUB": "-"}
POSITIONS = {"FIRST_OPERAND": "a", "SECOND_OPERAND": "b", "RESULT": "answer"}


def _alternatives(match):
    return match if isinstance(match, list) else [match]


def _fmts(alt):
    f = alt.get("fmt")
    return f if isinstance(f, list) else [f]


def _pick(rng, want, pool):
    """One value of `pool` a case condition allows, or None when none does."""
    ok = [v for v in pool if want is None or taxonomy.holds(want, v)]
    return rng.choice(ok) if ok else None


def _op(rng, alt, check):
    if alt.get("operation"):
        return OPS.get(_pick(rng, alt["operation"], ["ADD", "SUB"]))
    ops = check.get("op", ["+", "-"])
    return rng.choice(ops) if isinstance(ops, list) else ops


def _pairs(alt, check, op):
    """The (digits of the first number, digits of the second) a case and its level both allow."""
    level = check.get("digits")
    allowed = {tuple(p) for p in (level if isinstance(level[0], list) else [level])} if level else None
    out = []
    for d1 in DIGITS:
        for d2 in DIGITS:
            if (op == "-" and d2 > d1) or (allowed and (d1, d2) not in allowed):
                continue
            measured = {"operand_1_digits": d1, "operand_2_digits": d2, "digits_max": max(d1, d2), "digits_min": min(d1, d2)}
            if all(taxonomy.holds(alt[k], v) for k, v in measured.items() if k in alt):
                out.append((d1, d2))
    return out


def _number(rng, d, zero_ok):
    return rng.randint(0 if (d == 1 and zero_ok) else (1 if d == 1 else 10 ** (d - 1)), 10**d - 1)


def _usable(op, a, b, about, check):
    """The defaults every question keeps unless its case is about the very thing they rule out."""
    if op == "-" and a < b:
        return False
    zero_case, round_case, size_case = about & ZERO_KEYS, about & ROUND_KEYS, about & SIZE_KEYS
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


def _built(rng, alt, op):
    """The three cases whose numbers are a construction, not a digit pattern: add or take 10, 100 or
    1000 (347 + 100); make 100 or 1000 (68 + 32); count on across a hundred (503 − 498)."""
    if alt.get("round_operand") == "POWER_OF_TEN":
        b = rng.choice([10, 100, 1000])
        a = rng.randint(b + 11, 9999 if b == 1000 else 999)
        return a, b
    if "answer_power_of_ten" in alt:
        total = rng.choice(alt["answer_power_of_ten"] if isinstance(alt["answer_power_of_ten"], list) else [alt["answer_power_of_ten"]])
        a = rng.randint(total // 10 + 1, total - total // 10 - 1)
        return a, total - a
    if alt.get("difference_small") == "YES":
        hundred = rng.randint(1, 9) * 100
        a = hundred + rng.randint(1, 9)
        return a, hundred - rng.randint(1, 9)
    return None


def _pair(rng, alt, check, op, about, fix=None):
    """Two numbers for this case, or None. `fix` pins one number's digit count (a missing number)."""
    built = _built(rng, alt, op)
    if built:
        return built
    pairs = [p for p in _pairs(alt, check, op) if not fix or p[fix[0]] == fix[1]]
    if not pairs:
        return None
    d1, d2 = rng.choice(pairs)
    zero_ok = "zero_operand" in about
    a, b = _number(rng, d1, zero_ok), _number(rng, d2, zero_ok)
    shrink = _pick(rng, alt.get("answer_digit_change"), ["-1", "-MULTIPLE", "ZERO"]) if op == "-" else None
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


def _plain(rng, alt, check, rung, k):
    op = _op(rng, alt, check)
    got = _pair(rng, alt, check, op, taxonomy.keys(alt))
    if not got:
        return None
    a, b = got
    pres = alt.get("presentation")
    column = pres == "VERTICAL" if pres else k % 2 == 0  # half in columns, half in a line
    cand = {"format": "column_grid" if column else "bare_sum", "op": op, "a": a, "b": b, "answer": M.compute(op, a, b)}
    return verify.to_item(cand | {"stem": "", "missing": None, "misconceptions": []}, rung)


def _many(rng, alt, check, rung, k):
    """Three or more numbers (§2.8), or three with a friendly pair (§8, K07)."""
    about = taxonomy.keys(alt)
    friendly = alt.get("shape") == "FRIENDLY_PAIRS"
    n = 3 if friendly else _pick(rng, alt.get("num_operands"), range(3, 6))
    widest = _pick(rng, alt.get("digits_max"), range(1, check.get("digits_max", 4) + 1))
    if not n or not widest:
        return None
    if friendly:
        x = rng.randint(11, 89)
        xs = [x, rng.randint(11, 99), 100 - x]
    elif alt.get("operand_order") == "MIXED":
        low = _pick(rng, alt.get("digits_min"), range(1, widest)) or 1
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
    layout = "horizontal" if friendly else ("column" if (pres == "VERTICAL" if pres else k % 2 == 0) else "horizontal")
    return I.multi_add(rng, rung, "Procedural", xs=xs, layout=layout, shape="FRIENDLY_PAIRS" if friendly else None)


def _missing(rng, alt, check, rung, k):
    """A missing number (§6.1, §6.3): which number the box hides and how many digits it has."""
    if isinstance(alt.get("num_operands"), dict):
        return bands.native_item("missing_number", {"kind": "among_three", "hi": check.get("max_total", 100)}, rng, rung, "Conceptual")
    op = _op(rng, alt, check)
    ways = ["FIRST_OPERAND", "SECOND_OPERAND"] + (["RESULT"] if op == "-" else [])
    where = _pick(rng, alt.get("unknown_position"), ways)
    size = _pick(rng, alt.get("unknown_digits"), DIGITS) if "unknown_digits" in alt else None
    if not where:
        return None
    fix = (0, size) if size and where == "FIRST_OPERAND" else ((1, size) if size and where == "SECOND_OPERAND" else None)
    got = _pair(rng, alt, check, op, taxonomy.keys(alt), fix)
    if not got:
        return None
    a, b = got
    ans = M.compute(op, a, b)
    sign = "−" if op == "-" else "+"
    text = {"a": f"□ {sign} {b} = {ans}", "b": f"{a} {sign} □ = {ans}", "answer": f"{a} {sign} {b} = □"}[POSITIONS[where]]
    cand = {"format": "missing_number", "op": op, "a": a, "b": b, "answer": ans, "stem": text}
    return verify.to_item(cand | {"missing": POSITIONS[where], "misconceptions": []}, rung)


def _native(rng, alt, check, rung, k):
    fmt = rng.choice(_fmts(alt))
    hints = {key: (rng.choice(v) if isinstance(v, list) else v) for key in HINTS if (v := alt.get(key)) is not None}
    if alt.get("operation"):
        hints["op"] = OPS[_pick(rng, alt["operation"], ["ADD", "SUB"])]
    try:
        return bands.native_item(fmt, {**check, **hints}, rng, rung, "Conceptual")
    except (KeyError, ValueError, RuntimeError):
        return None  # this attempt's numbers could not make the case; the next attempt draws again


def one(rng, match, check, rung, k=0):
    """One candidate for a case, or None when this attempt's numbers are not that case. `k` counts the
    questions kept so far; where the case does not fix the layout, even is in columns, odd in a line."""
    alt = rng.choice(_alternatives(match))
    fmts = set(_fmts(alt))
    if fmts <= set(PLAIN):
        many = (
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


def _some(rng, match, check, rung, want, seen, tries):
    out, k = [], 0
    while len(out) < want and k < tries:
        it = one(rng, match, check, rung, len(seen))  # alternates the layout by questions kept, not tries
        k += 1
        if it is not None and it.item_id not in seen:
            seen.add(it.item_id)
            out.append(it)
    return out


def level(rng, check, matches, rung, n, seen=None, tries_per_item=2000):
    """Up to `n` distinct [(case, question)] for a level: the same number from each case it holds, then
    — where a case's numbers run out (7 − 7 has nine) — the rest from the cases that still have more."""
    codes = list(check["cases"])
    seen = set() if seen is None else seen
    quota = math.ceil(n / len(codes))
    out = [(code, it) for code in codes for it in _some(rng, matches[code], check, rung, quota, seen, quota * tries_per_item)]
    open_codes = list(codes)
    while len(out) < n and open_codes:
        for code in list(open_codes):
            more = _some(rng, matches[code], check, rung, 1, seen, tries_per_item)
            if not more:
                open_codes.remove(code)
            out += [(code, it) for it in more]
            if len(out) >= n:
                break
    return out[:n]
