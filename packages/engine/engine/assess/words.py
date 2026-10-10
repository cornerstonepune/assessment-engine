"""Questions made of sentences: the stories, and the generators that put numbers in them.

The sentences are rows, not Python: `word_templates.json` beside this file, the file the school edits (ADR
0010 — the language is written once per pattern). Beside it, not in `supabase/seed/`: the engine reads it
while it runs, and the server's image holds `engine/` alone (`tests/test_image.py`). Each template says its story shape (taxonomy §10:
join or take away with the result, the change or the start unknown; two parts and a whole; compare, and
which side is unknown; the two-step shapes) and the operation the child carries out, so a story's shape
is known by construction, never guessed from its words. A story is its numbers, its shape and its operations, so
all three are in its spec and its key (`story_spec`, ADR 0053); one stored before that is matched back to its
template by `template_of` and keyed again (`engine bank rekey`).
"""

import json
import pathlib
import random
import re
from functools import lru_cache
from typing import Any, cast

from engine.assess import misconceptions as M
from engine.assess import operations as O
from engine.assess.items import Item, Response, cells, item, sample_add, sample_sub
from engine.assess.times_kinds import number

SEED = pathlib.Path(__file__).with_name("word_templates.json")


@lru_cache(maxsize=1)
def _seed():
    return json.loads(SEED.read_text())


def templates(
    fmt: str | None = None, op: str | None = None, structure: str | None = None
) -> list[dict[str, Any]]:
    return [
        t
        for t in _seed()["word_templates"]
        if (fmt is None or t["fmt"] == fmt)
        and (op is None or t["op"] == op)
        and (structure is None or t["structure"] == structure)
    ]


NAMES = _seed()["names"]
THINGS = _seed()["tally_things"]  # what a tally counts (`counting.tally`)


@lru_cache(maxsize=1)
def _patterns() -> list[tuple[re.Pattern[str], dict[str, Any]]]:
    """Each template as a pattern that matches the sentences it wrote, whatever the names and numbers."""
    out: list[tuple[re.Pattern[str], dict[str, Any]]] = []
    for t in templates():
        rx = re.escape(t["text"])
        rx = re.sub(r"\\\{(?:n|n2)\\\}", r"[A-Z][a-z]+", rx)
        rx = re.sub(r"\\\{[a-z0-9]+\\\}", r"[\\d,]+", rx)
        out.append((re.compile(rx), t))
    return out


def template_of(stem: str | None) -> dict[str, Any] | None:
    """The template that wrote a stored sentence, or None: how a story stored before its shape was in its spec
    finds it (`engine bank rekey`), and how a sentence a person wrote is told from one a template wrote."""
    return next((t for rx, t in _patterns() if rx.fullmatch(stem or "")), None)


def structure_of(stem: str | None) -> str | None:
    t = template_of(stem)
    return t["structure"] if t else None


def story_spec(tpl: dict[str, Any], **numbers: int) -> dict[str, Any]:
    """What a story is: its numbers, its shape and its operations, everything its template says but the words (ADR
    0053). Its key is made from this, so two shapes of one numbers pair are two questions; `bank rekey` builds a stored
    story's here too, in the same order, since the key is the spec as written. A two-step story's operations tell apart
    two templates of one shape whose answers differ (a number thought of, then added to or taken from)."""
    spec: dict[str, Any] = dict(numbers)
    if tpl["fmt"] == "word_1step":
        spec["op"] = tpl["op"]
    spec["structure"] = tpl["structure"]
    if tpl.get("remainder_use"):  # what a story that divides does with what is left over (goals/md3b3-…)
        spec["remainder_use"] = tpl["remainder_use"]
    if tpl["fmt"] == "word_2step":
        spec["ops"] = list(dict.fromkeys(tpl["op"]))
    if tpl.get("table"):
        spec["table"] = [[tpl["table"][0], numbers["a"]], [tpl["table"][1], numbers["b"]]]
    return spec


def word_1step(
    rng: random.Random,
    rung: str,
    signal: str,
    digits_max: int,
    regroups: Any = (0, 1),
    structure: str | None = None,
    op: str | None = None,
    table: bool = False,
    digits: Any = None,
    max_total: int | None = None,
) -> Item:
    """One step (§10.1). `structure` pins the story shape; `op` the operation the child carries out;
    `table` asks for a story whose numbers are read from a small table (§10.2), and only then.
    `digits` ([2, 1]: a teen and a single digit) and `max_total` bound the numbers, as a level's rule may.
    Asked for ×, its stories multiply (the cost of many, times as many, combinations: goals/md2b-times-advance.yaml);
    asked for no operation, they add and take away, as they always did."""
    op = op and O.require("word_1step", op, makes=("+", "-", "×"))
    pool = [
        t
        for t in templates("word_1step", structure=structure)
        if t["op"] in ((op,) if op else ("+", "-")) and bool(t.get("table")) == table
    ]
    if not pool:
        raise O.CannotMake(f"no one-step story for shape {structure!r} and operation {op!r}")
    tpl = rng.choice(pool)
    if digits and isinstance(digits[0], list):
        digits = rng.choice(digits)  # a level that allows several shapes, 2 + 1 digits or 1 + 2
    da, db = digits or (digits_max, digits_max)
    if tpl["op"] == "×":
        return _times(rng, rung, tpl, (da, db))
    if tpl["op"] == "+":
        a, b = sample_add(rng, da, db, set(regroups), max_total=max_total)
    else:
        a, b = sample_sub(rng, da, db, set(regroups), max_a=max_total)
    n, n2 = rng.sample(NAMES, 2)
    stem = tpl["text"].format(a=a, b=b, n=n, n2=n2)
    ans = a + b if tpl["op"] == "+" else a - b
    mis = M.predict(tpl["op"], a, b)
    mis["M_WRONG_OP"] = abs(a - b) if tpl["op"] == "+" else a + b
    r = Response("ans", "digits", str(ans), cells=cells(max(ans, a + b)), misconceptions=mis)
    return item(
        "WP1", rung, "Application", "word_1step", stem, story_spec(tpl, a=a, b=b), [r], working_lines=3
    )


@lru_cache(maxsize=1)
def wrong_op_by_shape() -> dict[str, str]:
    """{story shape: the mistake its other operation is}, from the template rows that name one (`wrong_op_as`)."""
    return {t["structure"]: t["wrong_op_as"] for t in templates("word_1step") if t.get("wrong_op_as")}


def wrong_op_as(tpl: dict[str, Any] | None, mis: dict[str, Any]) -> dict[str, Any]:
    """A story's mistakes, with the other operation named as its template names it (`wrong_op_as`): "three times as
    many" added, read as three more, is M_TIMES_AS_MORE; "5 for each child" multiplied, because the story says "each",
    is M_KEYWORD_OVERGENERALISED. Each is a misreading of the words, not the wrong operation picked (M_WRONG_OP). The
    samplers (`_times`, `divide_stories.story`) and a sentence checked on its way in (`verify.to_item`) name it here."""
    if not tpl or not tpl.get("wrong_op_as"):
        return mis
    return {(tpl["wrong_op_as"] if k == "M_WRONG_OP" else k): v for k, v in mis.items()}


def _own(rng: random.Random, v: Any) -> int:
    """A number a template sets: one value, or a [lo, hi] range it is drawn from."""
    if isinstance(v, list):
        span = cast(list[int], v)
        return rng.randint(span[0], span[-1])
    return int(v)


def _times(rng: random.Random, rung: str, tpl: dict[str, Any], sizes: tuple[int, int]) -> Item:
    """A story that multiplies: its numbers no table fact and not round, as its level's are, but a number the story
    itself sets (`numbers`): one it fixes ("twice as many" is × 2), or the range it takes (twice as many as a number to
    20: doubling, not a 2-digit multiplication)."""
    own: dict[str, Any] = tpl.get("numbers") or {}
    a, b = (_own(rng, own[k]) if k in own else number(rng, d) for k, d in (("a", sizes[0]), ("b", sizes[1])))
    if tpl.get("wrong_op_as") and a + b == a * b:
        # twice as many as 2 read as two more is 4, and right: the question could not tell the misreading
        raise RuntimeError("the numbers added would be the answer: draw again")
    n, n2 = rng.sample(NAMES, 2)
    mis = wrong_op_as(tpl, M.predict("×", a, b))
    r = Response("ans", "digits", str(a * b), cells=cells(a * b), misconceptions=mis)
    stem = tpl["text"].format(a=a, b=b, n=n, n2=n2)
    return item(
        "WP1", rung, "Application", "word_1step", stem, story_spec(tpl, a=a, b=b), [r], working_lines=3
    )


def _two_step_numbers(rng, structure, digits_max):
    lo, hi = 10 ** (digits_max - 1) + 50, 10**digits_max - 1
    a = rng.randint(lo, hi)
    b, c = rng.randint(11, a // 3), rng.randint(11, max(12, a // 3))
    if structure == "EXTRA_INFORMATION":
        c = rng.randint(6, 40)  # the number the story does not need is an age or a count of teachers
    if structure == "CONSTRAINT" and (a - b) % 2:
        b += 1
    return a, b, c


def evaluate(formula: str, nums: dict[str, int], flip: bool = False, divide: int = 1) -> float:
    """A template's answer, "a-b+c": a signed sum of its numbers. `flip` turns every operation after
    the first number round — the answer a child gets by choosing the wrong operation each time."""
    if set(formula) - set("abc+-"):  # read as signed numbers, a × or ÷ would be added: say so instead
        raise O.CannotMake(f"a story's answer adds and takes away its numbers, not {formula!r}")
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
    r = Response("ans", "digits", str(ans), cells=cells(a + b + c), misconceptions=mis)
    return item(
        "WP2", rung, "Application", "word_2step", stem, story_spec(tpl, a=a, b=b, c=c), [r], working_lines=4
    )


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
    return item("BUDGET", rung, "Application", "word_2step", stem, spec, rs, working_lines=4)
