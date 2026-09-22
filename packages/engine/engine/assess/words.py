"""Questions made of sentences: the stories, and the generators that put numbers in them.

The sentences are rows, not Python: `supabase/seed/word_templates.json`, the file the school edits (ADR
0010 — the language is written once per pattern). Each template says its story shape (taxonomy §10:
join or take away with the result, the change or the start unknown; two parts and a whole; compare, and
which side is unknown; the two-step shapes) and the operation the child carries out, so a story's shape
is known by construction, never guessed from its words. Old questions whose sentence predates the stored
shape are matched back to their template by `structure_of`.
"""

import json
import pathlib
import re
from functools import lru_cache

from engine.assess import misconceptions as M
from engine.assess.items import Response, _cells, _item, sample_add, sample_sub

SEED = pathlib.Path(__file__).resolve().parents[4] / "supabase/seed/word_templates.json"


@lru_cache(maxsize=1)
def _seed():
    return json.loads(SEED.read_text())


def templates(fmt=None, op=None, structure=None):
    return [
        t
        for t in _seed()["word_templates"]
        if (fmt is None or t["fmt"] == fmt)
        and (op is None or t["op"] == op)
        and (structure is None or t["structure"] == structure)
    ]


NAMES = _seed()["names"]


@lru_cache(maxsize=1)
def _patterns():
    """Each template as a pattern that matches the sentences it wrote, whatever the names and numbers."""
    out = []
    for t in templates():
        rx = re.escape(t["text"])
        rx = re.sub(r"\\\{(?:n|n2)\\\}", r"[A-Z][a-z]+", rx)
        rx = re.sub(r"\\\{[a-z0-9]+\\\}", r"[\\d,]+", rx)
        out.append((re.compile(rx), t))
    return out


def template_of(stem):
    """The template that wrote a stored sentence, or None. A story's shape and its operations are read
    from it, never stored on the question, so the question's key is its numbers and words alone."""
    return next((t for rx, t in _patterns() if rx.fullmatch(stem or "")), None)


def structure_of(stem):
    t = template_of(stem)
    return t["structure"] if t else None


def word_1step(
    rng,
    rung,
    signal,
    digits_max,
    regroups=(0, 1),
    structure=None,
    op=None,
    table=False,
    digits=None,
    max_total=None,
):
    """One step (§10.1). `structure` pins the story shape; `op` the operation the child carries out;
    `table` asks for a story whose numbers are read from a small table (§10.2), and only then.
    `digits` ([2, 1]: a teen and a single digit) and `max_total` bound the numbers, as a level's rule may."""
    pool = [
        t
        for t in templates("word_1step", structure=structure)
        if t["op"] in ("+", "-") and (op is None or t["op"] == op) and bool(t.get("table")) == table
    ]
    if not pool:
        raise ValueError(f"no one-step story for shape {structure!r} and operation {op!r}")
    tpl = rng.choice(pool)
    if digits and isinstance(digits[0], list):
        digits = rng.choice(digits)  # a level that allows several shapes, 2 + 1 digits or 1 + 2
    da, db = digits or (digits_max, digits_max)
    if tpl["op"] == "+":
        a, b = sample_add(rng, da, db, set(regroups), max_total=max_total)
    else:
        a, b = sample_sub(rng, da, db, set(regroups), max_a=max_total)
    n, n2 = rng.sample(NAMES, 2)
    stem = tpl["text"].format(a=a, b=b, n=n, n2=n2)
    ans = a + b if tpl["op"] == "+" else a - b
    mis = M.predict(tpl["op"], a, b)
    mis["M_WRONG_OP"] = abs(a - b) if tpl["op"] == "+" else a + b
    spec = dict(a=a, b=b, op=tpl["op"])
    if tpl.get("table"):
        spec["table"] = [[tpl["table"][0], a], [tpl["table"][1], b]]
    r = Response("ans", "digits", str(ans), cells=_cells(max(ans, a + b)), misconceptions=mis)
    return _item("WP1", rung, "Application", "word_1step", stem, spec, [r], working_lines=3)


def _two_step_numbers(rng, structure, digits_max):
    lo, hi = 10 ** (digits_max - 1) + 50, 10**digits_max - 1
    a = rng.randint(lo, hi)
    b, c = rng.randint(11, a // 3), rng.randint(11, max(12, a // 3))
    if structure == "EXTRA_INFORMATION":
        c = rng.randint(6, 40)  # the number the story does not need is an age or a count of teachers
    if structure == "CONSTRAINT" and (a - b) % 2:
        b += 1
    return a, b, c


def evaluate(formula, nums, flip=False, divide=1):
    """A template's answer, "a-b+c": a signed sum of its numbers. `flip` turns every operation after
    the first number round — the answer a child gets by choosing the wrong operation each time."""
    total = 0
    for i, (sign, name) in enumerate(re.findall(r"([+-]?)([abc])", formula)):
        s = -1 if sign == "-" else 1
        total += nums[name] * (-s if flip and i else s)
    return total / divide


def word_2step(rng, rung, signal, digits_max, structure=None):
    """Two steps (§10.3), or one step with a number the story does not need (§10.2)."""
    pool = templates("word_2step", structure=structure)
    if not pool:
        raise ValueError(f"no two-step story for shape {structure!r}")
    tpl = rng.choice(pool)
    a, b, c = _two_step_numbers(rng, tpl["structure"], digits_max)
    nums, divide = {"a": a, "b": b, "c": c}, tpl.get("divide", 1)
    ans = evaluate(tpl["answer"], nums, divide=divide)
    if ans != int(ans) or ans <= 0 or (tpl["structure"] == "CONSTRAINT" and b >= a):
        raise RuntimeError("these numbers do not make this story")
    ans = int(ans)
    first = {"-": a - b, "+": a + b}[tpl["op"][0]]
    mis = {"M_ONE_STEP_ONLY": first, "M_WRONG_OP": evaluate(tpl["answer"], nums, flip=True, divide=divide)}
    mis = {k: int(v) for k, v in mis.items() if v != ans and v >= 0 and v == int(v)}
    n = rng.choice(NAMES)
    stem = tpl["text"].format(a=a, b=b, c=c, n=n)
    r = Response("ans", "digits", str(ans), cells=_cells(a + b + c), misconceptions=mis)
    spec = dict(a=a, b=b, c=c)
    return _item("WP2", rung, "Application", "word_2step", stem, spec, [r], working_lines=4)


def word_budget(rng, rung, signal, n_costs=3, budget_range=(5000, 12000), one_cost_is_a_product=False):
    """A budget, costs taken from it one after another (R14). Every level's rule is honoured: how many
    costs, how big the budget, and whether one cost is itself a product (a cap for each child)."""
    lo, hi = budget_range
    budget = rng.randrange(max(1000, lo // 500 * 500), hi + 1, 500)
    share = budget // (n_costs + 1)
    costs = [rng.randint(share // 3, share) for _ in range(min(n_costs, 3))]
    k = p = None
    if n_costs >= 4 and not one_cost_is_a_product:
        raise ValueError("the four-cost budget story has a cap for each child — set one_cost_is_a_product")
    if one_cost_is_a_product and n_costs >= 4:
        k, p = rng.randint(12, 32), rng.randint(15, 60)
        costs.append(k * p)
    ans = budget - sum(costs)
    if ans <= 0:
        raise RuntimeError("the costs are more than the budget")
    names = dict(zip("abc", costs))
    text = _seed()["budget"][str(min(n_costs, 4))]
    stem = text.format(budget=budget, k=k, p=p, **names)
    mis = {"M_ONE_STEP_ONLY": budget - costs[0], "M_SUM_ONLY": sum(costs), "M_WRONG_OP": budget + sum(costs)}
    rs = [Response("ans", "digits", str(ans), cells=len(str(budget)) + 1, misconceptions=mis)]
    spec = dict(budget=budget, **names, costs=costs)
    if k:
        spec |= {"children": k, "each": p}
    return _item("BUDGET", rung, "Application", "word_2step", stem, spec, rs, working_lines=4)
