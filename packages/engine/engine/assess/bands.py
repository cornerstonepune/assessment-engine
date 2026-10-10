"""A band's rule → the numbers it allows. Deterministic, no I/O.

One place samples a band. `bank._sampled` builds candidate questions from these pairs and
`spec.known_misconceptions` runs the predictors over them; before this module each did its own
sampling, and the second one would have drifted from the first.
"""

import random
from collections.abc import Callable, Iterable
from typing import Any, cast

from engine.assess import counting as C
from engine.assess import diagnosis as D
from engine.assess import divide_models as DMOD
from engine.assess import equality as EQ
from engine.assess import estimate as E
from engine.assess import items as I
from engine.assess import misconceptions as M
from engine.assess import missing_digits as MD
from engine.assess import number_line as NL
from engine.assess import operations as O
from engine.assess import reasoning as RS
from engine.assess import times_kinds as TK
from engine.assess import times_models as TM
from engine.assess import words as W
from engine.assess import written_methods as WM
from engine.assess.counting import one_of

# The shapes the arithmetic sampler can render from (op, a, b) alone. A band whose check names
# a format outside this and outside NATIVE_GENERATORS cannot be made by anything.
SAMPLER_FORMATS = ["column_grid", "bare_sum", "missing_number", "word_1step"]


def makeable(check: dict[str, Any]) -> bool:
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


def makes(fmt: str, case: dict[str, Any]) -> bool:
    """Whether this kind can make a case of this story shape: a story kind only the shapes its template rows hold.
    W25 (a number to leave out) lists the one-step kind, which reads such a story, but no one-step template has that
    shape; its two-step templates are one calculation with a number the story does not need."""
    shape: Any = case.get("structure")
    if fmt not in ("word_1step", "word_2step") or not shape:
        return True
    shapes = cast(list[str], shape) if isinstance(shape, list) else [str(shape)]
    return any(W.templates(fmt, structure=s) for s in shapes)


def _regroups(c: dict[str, Any]) -> set[int]:
    """The regroup counts a + or − estimate draws from: its level's rule's own, or, on a level made of cases, which
    names none, every count its numbers' sizes allow, the case's match keeping what it asks for (R01 and R02 drew
    nothing: the rule was read and missing). A × estimate rounds and never regroups."""
    if TK.digits(c) is not None:
        return set()
    return set(c["regroups"]) if "regroups" in c else set(range(max(TK.sizes(c)) + 1))


def _estimate(rng: random.Random, rung: str, signal: str, c: dict[str, Any]) -> I.Item:
    """An estimate for its level's rule, the operation asked before the rule's numbers are sized: a ÷ estimate drawn
    here read a × rule's digits and crashed (KeyError 'digits'); it is built on its case's own numbers
    (`divide_kinds`), and this one refuses it in a sentence."""
    op = O.require("estimate_then_calc", one_of(c["op"], rng), makes=("+", "-", "×"))
    return E.estimate_then_calc(
        rng,
        rung,
        signal,
        op,
        *TK.sizes(c),
        _regroups(c),
        round_to=c.get("round_to", 10),
        judged=c.get("shape") == "JUDGED",
        tolerance=c.get("tolerance"),
        shape=c.get("shape"),
    )


def _widths(c: dict[str, Any]) -> tuple[int, int]:
    """A worked answer's two numbers' digits: a × level's longer and shorter, else the level's own two (one named, both
    that long). A + or − mistake was found in two numbers of the first's length, so a 2 by 1 level held none."""
    named: list[int] = c.get("digits", [2])
    return TK.digits(c) or (int(named[0]), int(named[-1]))


def _groups(rng: random.Random, rung: str, signal: str, c: dict[str, Any]) -> I.Item:
    """Equal groups multiply (`counting`) or divide (`divide_models`), as the case asks; any other operation is refused
    in a sentence, never drawn as a multiplication its case then turns away."""
    if O.require("equal_groups", one_of(c.get("op") or "×", rng), makes=("×", "÷")) == "÷":
        return DMOD.equal_groups(rng, rung, signal, c)
    return C.equal_groups(rng, rung, signal, c)


# fmt -> (rng, rung, signal, check) -> Item. One entry per chunk-B generator (ADR 0010); no model
# call and no verify.problems detour either — these generators are trusted code, not untrusted
# model output, the same guarantee the arithmetic sampler gets from its round trip through check.
# fmt: off
NATIVE_GENERATORS: dict[str, Callable[..., I.Item]] = {
    "missing_number": lambda rng, rung, signal, c: I.missing_number(rng, rung, signal, c["kind"], c["hi"]),
    "balance_scale": lambda rng, rung, signal, c: I.balance_scale(rng, rung, signal, c["hi"]),
    "number_wall": lambda rng, rung, signal, c: I.number_wall(rng, rung, signal, c["hi"]),
    "number_line_jumps": NL.number_line,
    "estimate_then_calc": lambda rng, rung, signal, c: _estimate(rng, rung, signal, c),
    "multi_add": lambda rng, rung, signal, c: I.multi_add(
        rng, rung, signal, c.get("n_addends", 3), c.get("digits_each", 4)),
    "efficient_method": lambda rng, rung, signal, c: TK.shortcut(rng, rung, signal, c["strategy"], TK.digits(c) or (2, 1))
        if c.get("strategy") else I.efficient_method(rng, rung, signal, kind=one_of(c.get("kind"), rng)),
    "word_1step": lambda rng, rung, signal, c: W.word_1step(
        rng, rung, signal, c.get("digits_max", 2), tuple(c.get("regroups", (0, 1))), structure=c.get("structure"),
        op=one_of(c.get("op"), rng), table=c.get("table", False), digits=TK.digits(c) or c.get("digits"),
        max_total=c.get("max_total")),
    "word_2step": lambda rng, rung, signal, c: W.word_2step(rng, rung, signal, c["digits_max"], structure=c.get("structure")),
    "word_budget": lambda rng, rung, signal, c: W.word_budget(
        rng, rung, signal, c.get("n_costs", 3), tuple(c.get("budget_range", (5000, 12000))),
        c.get("one_cost_is_a_product", False)),
    "find_mistake": lambda rng, rung, signal, c: D.find_mistake(
        rng, rung, signal, op=one_of(c.get("op", "+"), rng), digits=_widths(c),
        planted=one_of(c["planted"], rng) if c.get("planted") else None),
    "explain_claim": lambda rng, rung, signal, c: D.explain_claim(
        rng, rung, signal, a_range=tuple(c.get("a_range", (120, 480))),
        claim_is_true=one_of(c.get("claim_is_true", [True, False]), rng), claim_topic=c.get("claim_topic", "compensation")),
    "missing_digit": lambda rng, rung, signal, c: MD.missing_digit(
        rng, rung, signal, {**c, "op": one_of(c.get("op", "+"), rng),
                            "width": one_of(c.get("width") or (TK.digits(c) or (2,))[0], rng)}),
    "equation": EQ.from_rule,
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
    "tally": C.tally,
    "equal_groups": _groups,
    "skip_counting": TM.skip_counting,
    "multiplication_square": TM.multiplication_square,
    "repeated_subtraction": DMOD.repeated_subtraction,
    "partitioning": WM.partitioning,
    "grid_method": WM.grid,
    "expanded_columns": WM.expanded,
    "lattice": WM.lattice,
}

# The rule keys each generator reads — and so the only keys a level of that kind may set (`engine audit`,
# "every key a level's rule sets is one its generator reads"). A key nothing reads is a promise the
# printed questions do not keep: ADDSUB.2D.NOREG's `order: shorter_first` printed longer-first sums.
READS = {
    "missing_number": {"kind", "hi"},
    "balance_scale": {"hi"},
    "number_wall": {"hi"},
    "number_line_jumps": {"op", "hi", "groups", "size"},
    "estimate_then_calc": {"op", "digits", "regroups", "round_to", "shape", "tolerance"},
    "multi_add": {"n_addends", "digits_each"},
    "efficient_method": {"kind", "strategy"},
    "word_1step": {"digits_max", "regroups", "structure", "op", "table", "digits", "max_total"},
    "word_2step": {"digits_max", "structure"},
    "word_budget": {"n_costs", "budget_range", "one_cost_is_a_product"},
    "find_mistake": {"op", "digits", "planted"},
    "explain_claim": {"a_range", "claim_is_true", "claim_topic"},
    "missing_digit": {"op", "width", "missing_count", "missing_in", "missing_place", "shape", "regroups"},
    "equation": {"shape", "hi", "known", "size"},
    "fact_family": {"shape", "hi"},
    "inverse_check": {"op", "digits_max"},
    "choose_estimate": {"op", "digits_max"},
    "possible_answer": {"op", "digits_max"},
    "odd_even": {"op", "digits_max"},
    "break_apart": {"op", "digits_max"},
    "tally": {"shape", "lo", "hi"},
    "equal_groups": {"shape", "method", "groups", "size"},
    "skip_counting": {"known", "groups"},
    "multiplication_square": {"groups", "size"},
    "repeated_subtraction": {"groups", "size"},
    "partitioning": {"digits"},
    "grid_method": {"digits"},
    "expanded_columns": {"digits"},
    "lattice": {"digits"},
}
SAMPLER_READS = {"op", "digits", "regroups", "max_total", "no_zero_top", "across_zero", "min_answer"}
# `within` — a skill's operation and digit shape — is read with every case: drawn inside it (`cases.for_level`)
# and measured against it (`verify.dimension_problems`); `methods`, the written methods its calculations are printed in
# (`draw.level`, ADR 0055)
CASE_LEVEL_READS = {"cases", "methods", "within", "max_total", "digits", "digits_max", "op", "layout"}
ALWAYS = {"format", "min_items"}


def unread_keys(check: dict[str, Any], kinds: Iterable[str] = ()) -> list[str]:
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


def native_item(fmt: str, check: dict[str, Any], rng: random.Random, rung: str, signal: str) -> I.Item:
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
            except O.CannotMake:
                raise  # the rule asks this kind for an operation it does not make: said, never an empty list
            except (KeyError, ValueError, RuntimeError):
                break  # a rule this generator cannot serve claims no misconceptions, and says so
            out |= {c for r in item.responses for c in (r.misconceptions or {})}
        return sorted(out)
    return M.applicable(pairs(check, n, seed))
