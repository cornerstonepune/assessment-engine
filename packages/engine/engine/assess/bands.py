"""A band's rule → the numbers it allows. Deterministic, no I/O.

One place samples a band. `bank._sampled` builds candidate questions from these pairs and
`spec.known_misconceptions` runs the predictors over them; before this module each did its own
sampling, and the second one would have drifted from the first.
"""

import random

from engine.assess import items as I
from engine.assess import misconceptions as M
from engine.assess import words as W

# The shapes the arithmetic sampler can render from (op, a, b) alone. A band whose check names
# a format outside this and outside NATIVE_GENERATORS cannot be made by anything.
SAMPLER_FORMATS = ["column_grid", "bare_sum", "missing_number", "word_1step"]


def makeable(check):
    """Can any generator produce a question for this band? The one authority — `engine audit`
    and a fill must agree, or a band passes the audit and then fills nothing."""
    if check.get("cases"):
        return True  # a level made of taxonomy cases; `engine audit` checks each case is a row
    fmt = check.get("format")
    if fmt:
        return fmt in NATIVE_GENERATORS or fmt in SAMPLER_FORMATS
    return bool(pairs(check, 1))


def pairs(check, n, seed=1):
    """Up to `n` (op, a, b) triples satisfying this band's checkable rule, in a stable order.

    A rule with no `op`/`digits` is a native-generator band (an explanation, a budget): it has no
    numbers to sample, so this returns nothing rather than guessing at some.
    """
    if "op" not in check or "digits" not in check:
        return []
    ops = check["op"] if isinstance(check["op"], list) else [check["op"]]
    digits_a, digits_b = check["digits"]
    regroups = set(check.get("regroups", []))
    rng = random.Random(seed)
    out = []
    for _ in range(n * 4):
        if len(out) >= n:
            break
        op = ops[len(out) % len(ops)]
        try:
            if op == "+":
                a, b = I.sample_add(rng, digits_a, digits_b, regroups, max_total=check.get("max_total"))
            elif op == "-":
                a, b = I.sample_sub(
                    rng,
                    digits_a,
                    digits_b,
                    regroups,
                    across_zero=bool(check.get("across_zero")),
                    max_a=check.get("max_total"),
                )
            elif op == "×":
                a, b = I.sample_mul(rng, digits_a, digits_b, max_product=check.get("max_total"))
            else:
                break  # no sampler for this operation yet; the model path still covers it
        except RuntimeError:
            continue
        if check.get("no_zero_top") and "0" in str(a):
            continue
        out.append((op, a, b))
    return out


def one_of(v, rng):
    """A check value that may be a single value or a list of alternatives (op, kind, …)."""
    return rng.choice(v) if isinstance(v, list) else v


# fmt -> (rng, rung, signal, check) -> Item. One entry per chunk-B generator (ADR 0010); no model
# call and no verify.problems detour either — these generators are trusted code, not untrusted
# model output, the same guarantee the arithmetic sampler gets from its round trip through check.
# fmt: off
NATIVE_GENERATORS = {
    "missing_number": lambda rng, rung, signal, c: I.missing_number(rng, rung, signal, c["kind"], c["hi"]),
    "balance_scale": lambda rng, rung, signal, c: I.balance_scale(rng, rung, signal, c["hi"]),
    "number_wall": lambda rng, rung, signal, c: I.number_wall(rng, rung, signal, c["hi"]),
    "number_line_jumps": lambda rng, rung, signal, c: I.number_line_jumps(
        rng, rung, signal, one_of(c["op"], rng), c["hi"]),
    "estimate_then_calc": lambda rng, rung, signal, c: I.estimate_then_calc(
        rng, rung, signal, one_of(c["op"], rng), *c["digits"], set(c["regroups"])),
    "multi_add": lambda rng, rung, signal, c: I.multi_add(
        rng, rung, signal, c.get("n_addends", 3), c.get("digits_each", 4)),
    "efficient_method": lambda rng, rung, signal, c: I.efficient_method(
        rng, rung, signal, kind=one_of(c.get("kind"), rng)),
    "word_1step": lambda rng, rung, signal, c: W.word_1step(
        rng, rung, signal, c["digits_max"], tuple(c.get("regroups", (0, 1)))),
    "word_2step": lambda rng, rung, signal, c: W.word_2step(rng, rung, signal, c["digits_max"]),
    "word_budget": lambda rng, rung, signal, c: W.word_budget(rng, rung, signal),
    "find_mistake": lambda rng, rung, signal, c: I.find_mistake(
        rng, rung, signal, op=one_of(c["op"], rng), digits=c["digits"][0]),
    "explain_claim": lambda rng, rung, signal, c: I.explain_claim(
        rng, rung, signal, a_range=tuple(c.get("a_range", (120, 480))),
        claim_is_true=c.get("claim_is_true", True), claim_topic=c.get("claim_topic", "compensation")),
}


# fmt: on


def native_item(fmt, check, rng, rung, signal):
    if fmt not in NATIVE_GENERATORS:
        raise ValueError(f"no native generator for format {fmt!r}")
    return NATIVE_GENERATORS[fmt](rng, rung, signal, check)


def codes(check, n=20, seed=1, rung="R0", signal="Procedural"):
    """Every named misconception reachable in this band, taken from the generators that build its
    real items: a native format through its own generator's response map, plain arithmetic through
    the predictors. One source of truth — what the bank computes for an item is what this reports,
    so the two cannot drift.
    """
    fmt = check.get("format")
    if fmt in NATIVE_GENERATORS:
        rng = random.Random(seed)
        out = set()
        for _ in range(n):
            try:
                item = native_item(fmt, check, rng, rung, signal)
            except (KeyError, ValueError, RuntimeError):
                break  # a rule this generator cannot serve claims no misconceptions, and says so
            out |= {c for r in item.responses for c in (r.misconceptions or {})}
        return sorted(out)
    return M.applicable(pairs(check, n, seed))
