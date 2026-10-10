"""A wrong answer no named mistake explains, and Jev's shortlist of what it might be (goals/j1-jev-mistakes.yaml).

Code names every mistake it can reproduce: a predictor computes the exact wrong number each named mistake makes on
these numbers (`assess.misconceptions.predict`), and marking matches the child's answer to it. Only a wrong answer no
predictor reproduces is asked about, and Jev only proposes: the three likeliest named mistakes, or NONE — a slip, a
miscount, or a mistake not yet named — each with its probability, for a person to pick from.

Measured on 120 cases built from the predictors themselves (ADR 0036): the right mistake among Jev's three in 113;
every one of 30 slips called NONE, none given a mistake it is not. What Jev is shown is the sum, the right answer and
the child's answer — never a name, never the page.
"""

import random

from engine.adapters import jev
from engine.assess import misconceptions as M
from engine.core import mistake_names

PURPOSE = "mistake_guess"
NONE = "NONE"
NONE_WORDS = "None of these: a slip, a miscount, or a mistake not listed"
SHORTLIST = 3
SIGN = {"+": "+", "-": "−"}


def codes(op):
    """Every named mistake of `op` that is a way of thinking, and NONE: what a wrong answer may be put down to. An
    off-by-one or a tens miscount is a slip, which is what NONE is for."""
    return [c for c in M.TABLES.get(op, {}) if not c.startswith("M_FACT")] + [NONE]


def options(conn, op):
    """{code: its name} for each of `codes(op)`: the name its row gives it for this operation, the words a person picks
    from too — never a copy the code keeps (rule 1, goals/md3b3-divide-mistakes-and-stories.yaml)."""
    name_of = mistake_names.names(conn)
    return {c: NONE_WORDS if c == NONE else name_of(c, op) for c in codes(op)}


def state(spec, wrote):
    a, b, op = spec["a"], spec["b"], spec["op"]
    return {"question": f"{a} {SIGN[op]} {b} = ?", "right_answer": M.compute(op, a, b), "child_answer": wrote}


def _one_sum(spec):
    return (
        isinstance(spec, dict)
        and spec.get("op") in SIGN
        and isinstance(spec.get("a"), int)
        and isinstance(spec.get("b"), int)
    )


def shortlist(conn, spec, wrote, ask=None):
    """→ [(code, p)] best first, at most three; None when there is nothing to ask: no answer, a right one, one code
    already explains, or a question that is not one + or − sum."""
    if not _one_sum(spec) or not str(wrote).strip().isdigit():
        return None
    n = int(wrote)
    if (
        n == M.compute(spec["op"], spec["a"], spec["b"])
        or n in M.predict(spec["op"], spec["a"], spec["b"]).values()
    ):
        return None
    out = (ask or jev.decide)(conn, PURPOSE, state(spec, str(wrote)), options(conn, spec["op"]))
    return [(c, round(p, 3)) for c, p in out["ranked"][:SHORTLIST]]


def gold(seed=7, named=90, slips=30):
    """Cases whose answer is known without a person: a wrong answer exactly one named mistake makes (by its
    predictor), or a slip none makes. The eval Jev is held to (`engine eval mistake_guess`)."""
    rng, cases = random.Random(seed), []
    while len(cases) < named:
        op, a, b = _sum(rng, rng.choice([2, 3]))
        made = {}
        for code, v in M.predict(op, a, b).items():
            made.setdefault(v, []).append(code)
        one = [(v, cs[0]) for v, cs in made.items() if len(cs) == 1 and not cs[0].startswith("M_FACT")]
        if one:
            v, code = rng.choice(one)
            cases.append({"op": op, "a": a, "b": b, "wrote": v, "want": code})
    while len(cases) < named + slips:
        op, a, b = _sum(rng, 3)
        right, made = M.compute(op, a, b), set(M.predict(op, a, b).values())
        v = right + rng.choice([-37, -23, 58, 71, 116, -104, 29])
        if v > 0 and v not in made:
            cases.append({"op": op, "a": a, "b": b, "wrote": v, "want": NONE})
    return cases


def _sum(rng, width):
    op = rng.choice("+-")
    a, b = (rng.randint(10 ** (width - 1), 10**width - 1) for _ in range(2))
    return (op, max(a, b), min(a, b)) if op == "-" else (op, a, b)


def evaluate(conn, cases, ask=None):
    """→ how Jev did on `cases`: first choice right, right among the shortlist, slips called NONE, and slips given a
    mistake they are not (the number that must stay 0)."""
    first = listed = slips_none = false_named = 0
    failed = []
    shown = {op: options(conn, op) for op in SIGN}
    for c in cases:
        try:
            out = (ask or jev.decide)(conn, PURPOSE, state(c, str(c["wrote"])), shown[c["op"]])
        except jev.JevError as e:
            failed.append(str(e))
            continue
        top = [code for code, _ in out["ranked"][:SHORTLIST]]
        first += top[0] == c["want"]
        listed += c["want"] in top
        if c["want"] == NONE:
            slips_none += top[0] == NONE
            false_named += top[0] != NONE
    return {"cases": len(cases), "first": first, "listed": listed, "slips": sum(c["want"] == NONE for c in cases),
            "slips_none": slips_none, "false_named": false_named,
            "unanswered": len(failed), "error": failed[0] if failed else ""}  # fmt: skip
