"""A band's rule → the numbers it allows. Deterministic, no I/O.

One place samples a band. `bank._sampled` builds candidate questions from these pairs and
`spec.known_misconceptions` runs the predictors over them; before this module each did its own
sampling, and the second one would have drifted from the first.
"""

import random

from engine.assess import diagnosis as D
from engine.assess import equality as EQ
from engine.assess import items as I
from engine.assess import misconceptions as M
from engine.assess import missing_digits as MD
from engine.assess import reasoning as RS
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
        rng, rung, signal, one_of(c["op"], rng), *c["digits"], set(c["regroups"]), round_to=c.get("round_to", 10),
        judged=c.get("shape") == "JUDGED", tolerance=c.get("tolerance")),
    "multi_add": lambda rng, rung, signal, c: I.multi_add(
        rng, rung, signal, c.get("n_addends", 3), c.get("digits_each", 4)),
    "efficient_method": lambda rng, rung, signal, c: I.efficient_method(
        rng, rung, signal, kind=one_of(c.get("kind"), rng)),
    "word_1step": lambda rng, rung, signal, c: W.word_1step(
        rng, rung, signal, c.get("digits_max", 2), tuple(c.get("regroups", (0, 1))), structure=c.get("structure"),
        op=c.get("op"), table=c.get("table", False), digits=c.get("digits"), max_total=c.get("max_total")),
    "word_2step": lambda rng, rung, signal, c: W.word_2step(rng, rung, signal, c["digits_max"], structure=c.get("structure")),
    "word_budget": lambda rng, rung, signal, c: W.word_budget(
        rng, rung, signal, c.get("n_costs", 3), tuple(c.get("budget_range", (5000, 12000))),
        c.get("one_cost_is_a_product", False)),
    "find_mistake": lambda rng, rung, signal, c: D.find_mistake(
        rng, rung, signal, op=one_of(c.get("op", "+"), rng), digits=c.get("digits", [2])[0],
        planted=one_of(c["planted"], rng) if c.get("planted") else None),
    "explain_claim": lambda rng, rung, signal, c: D.explain_claim(
        rng, rung, signal, a_range=tuple(c.get("a_range", (120, 480))),
        claim_is_true=c.get("claim_is_true", True), claim_topic=c.get("claim_topic", "compensation")),
    "missing_digit": lambda rng, rung, signal, c: MD.missing_digit(
        rng, rung, signal, {**c, "op": one_of(c.get("op", "+"), rng), "width": one_of(c.get("width", 2), rng)}),
    "equation": lambda rng, rung, signal, c: EQ.equation(rng, rung, signal, one_of(c["shape"], rng), c.get("hi", 50)),
    "fact_family": lambda rng, rung, signal, c: EQ.fact_family(rng, rung, signal, one_of(c["shape"], rng), c.get("hi", 20)),
    "inverse_check": lambda rng, rung, signal, c: EQ.inverse_check(
        rng, rung, signal, one_of(c.get("op", "+"), rng), c.get("digits_max", 3)),
    "choose_estimate": lambda rng, rung, signal, c: RS.choose_estimate(
        rng, rung, signal, one_of(c.get("op", "+"), rng), c.get("digits_max", 3)),
    "possible_answer": lambda rng, rung, signal, c: RS.possible_answer(
        rng, rung, signal, one_of(c.get("op", "+"), rng), c.get("digits_max", 3)),
    "odd_even": lambda rng, rung, signal, c: RS.odd_even(rng, rung, signal, one_of(c.get("op", "+"), rng), c.get("digits_max", 3)),
    "break_apart": lambda rng, rung, signal, c: RS.break_apart(
        rng, rung, signal, one_of(c.get("op", "+"), rng), c.get("digits_max", 3)),
}

# The rule keys each generator reads — and so the only keys a level of that kind may set (`engine audit`,
# "every key a level's rule sets is one its generator reads"). A key nothing reads is a promise the
# printed questions do not keep: ADDSUB.2D.NOREG's `order: shorter_first` printed longer-first sums.
READS = {
    "missing_number": {"kind", "hi"},
    "balance_scale": {"hi"},
    "number_wall": {"hi"},
    "number_line_jumps": {"op", "hi"},
    "estimate_then_calc": {"op", "digits", "regroups", "round_to", "shape", "tolerance"},
    "multi_add": {"n_addends", "digits_each"},
    "efficient_method": {"kind"},
    "word_1step": {"digits_max", "regroups", "structure", "op", "table", "digits", "max_total"},
    "word_2step": {"digits_max", "structure"},
    "word_budget": {"n_costs", "budget_range", "one_cost_is_a_product"},
    "find_mistake": {"op", "digits", "planted"},
    "explain_claim": {"a_range", "claim_is_true", "claim_topic"},
    "missing_digit": {"op", "width", "missing_count", "missing_in", "missing_place", "shape", "regroups"},
    "equation": {"shape", "hi"},
    "fact_family": {"shape", "hi"},
    "inverse_check": {"op", "digits_max"},
    "choose_estimate": {"op", "digits_max"},
    "possible_answer": {"op", "digits_max"},
    "odd_even": {"op", "digits_max"},
    "break_apart": {"op", "digits_max"},
}
SAMPLER_READS = {"op", "digits", "regroups", "max_total", "no_zero_top", "across_zero", "min_answer"}
# `within` — a skill's operation and digit shape — is read with every case: drawn inside it (`cases.for_level`)
# and measured against it (`verify.dimension_problems`)
CASE_LEVEL_READS = {"cases", "within", "max_total", "digits", "digits_max", "op", "layout"}
ALWAYS = {"format", "min_items"}


def unread_keys(check, kinds=()):
    """The keys a level's rule sets that nothing reads. `kinds` are the kinds of question a case level's
    cases draw (their generators read the level's rule too)."""
    if check.get("cases"):
        reads = CASE_LEVEL_READS.union(*(READS.get(k, set()) for k in kinds))
    elif check.get("format") in NATIVE_GENERATORS:
        reads = READS[check["format"]]
    else:
        reads = SAMPLER_READS
    return sorted(set(check) - reads - ALWAYS)


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
