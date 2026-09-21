"""Questions made of sentences: the stories, the names, and the generators that fill them.

Split out of `items.py` (CLAUDE.md rule 11: a file over the ceiling is split along a responsibility,
not exempted). Their real home is a row, not Python — a story template is content the school should
be able to change without an engineer, and ADR 0010 already says the model writes these templates
once per pattern. Until that lands, they live together here so the debt is one file, visible.
"""

from engine.assess import misconceptions as M
from engine.assess.items import Response, _cells, _item, sample_add, sample_sub

NAMES = [
    "Aarav",
    "Riya",
    "Kabir",
    "Meera",
    "Ishaan",
    "Saee",
    "Vihaan",
    "Anaya",
    "Dev",
    "Zoya",
    "Arjun",
    "Tara",
]
CONTEXTS_1STEP = [
    ("+", "{n} has {a} marbles. {n2} gives {n} {b} more. How many marbles does {n} have now?"),
    (
        "+",
        "A shop sells {a} laddoos in the morning and {b} in the evening. How many laddoos does it sell in the whole day?",
    ),
    (
        "+",
        "There are {a} children in the ground and {b} children in the hall. How many children are there altogether?",
    ),
    ("-", "A bus has {a} seats. {b} of them are taken. How many seats are empty?"),
    ("-", "{n} had ₹{a}. {n} bought a book for ₹{b}. How much money does {n} have left?"),
    ("-", "{n} collected {a} shells. {n2} collected {b}. How many more shells did {n} collect than {n2}?"),
]
# Kept apart from CONTEXTS_1STEP on purpose: `word_1step` picks a story first and then samples
# with an if-plus/else-minus branch, so a × story in that list would quietly be handed
# subtraction numbers. The × path in bank._sampled reads this list instead.
CONTEXTS_MUL = [
    "Each box has {a} pencils. There are {b} boxes. How many pencils are there altogether?",
    "One ticket to the mela costs ₹{a}. {n} buys {b} tickets. How much does {n} pay?",
    "A shelf holds {a} books. How many books are there on {b} shelves?",
    "{n} walks {a} steps to school every day. How many steps is that in {b} days?",
]
CONTEXTS_2STEP = [
    "{a} people are at a mela. {b} of them are adults and {c} are teachers. How many children are at the mela?",
    "{n} has ₹{a}. {n} buys a kite for ₹{b} and a ball for ₹{c}. How much money is left?",
    "A train has {a} passengers. At the first station {b} get off and {c} get on. How many passengers are on the train now?",
]
BUDGET = [
    "The class has ₹{budget} for a picnic. Bus tickets cost ₹{a}, snacks cost ₹{b} and a park ticket costs ₹{c}. How much money is left after paying for everything?",
]


def word_1step(rng, rung, signal, digits_max, regroups=(0, 1)):
    op, tpl = rng.choice(CONTEXTS_1STEP)
    if op == "+":
        a, b = sample_add(rng, digits_max, digits_max, set(regroups))
    else:
        a, b = sample_sub(rng, digits_max, digits_max, set(regroups))
    n, n2 = rng.sample(NAMES, 2)
    stem = tpl.format(a=a, b=b, n=n, n2=n2)
    ans = a + b if op == "+" else a - b
    mis = M.predict(op, a, b)
    mis["M_WRONG_OP"] = abs(a - b) if op == "+" else a + b
    r = Response("ans", "digits", str(ans), cells=_cells(max(ans, a + b)), misconceptions=mis)
    return _item("WP1", rung, "Application", "word_1step", stem, dict(a=a, b=b, op=op), [r], working_lines=3)


def word_2step(rng, rung, signal, digits_max):
    tpl = rng.choice(CONTEXTS_2STEP)
    n = rng.choice(NAMES)
    if "get on" in tpl:
        a = rng.randint(10 ** (digits_max - 1) + 50, 10**digits_max - 1)
        b = rng.randint(11, a // 3)
        c = rng.randint(11, 60)
        ans = a - b + c
        mis = {"M_ONE_STEP_ONLY": a - b, "M_WRONG_OP": a + b - c}
    else:
        a = rng.randint(10 ** (digits_max - 1) + 50, 10**digits_max - 1)
        b = rng.randint(11, a // 3)
        c = rng.randint(11, a // 3)
        ans = a - b - c
        mis = {"M_ONE_STEP_ONLY": a - b, "M_WRONG_OP": a - b + c}
    stem = tpl.format(a=a, b=b, c=c, n=n)
    mis = {k: v for k, v in mis.items() if v != ans}
    r = Response("ans", "digits", str(ans), cells=_cells(a + c), misconceptions=mis)
    return _item("WP2", rung, "Application", "word_2step", stem, dict(a=a, b=b, c=c), [r], working_lines=4)


def word_budget(rng, rung, signal):
    budget = rng.choice([5000, 8000, 10000, 12000])
    a = rng.randint(1200, 3900)
    b = rng.randint(600, 1900)
    c = rng.randint(400, 1500)
    ans = budget - a - b - c
    # M_WRONG_OP: the whole question read as "add it all up" — the budget spec names this mistake,
    # so the generator must compute the answer it produces or nothing can mark it.
    mis = {"M_ONE_STEP_ONLY": budget - a, "M_SUM_ONLY": a + b + c, "M_WRONG_OP": budget + a + b + c}
    rs = [Response("ans", "digits", str(ans), cells=5, misconceptions=mis)]
    return _item(
        "BUDGET",
        rung,
        "Application",
        "word_2step",
        BUDGET[0].format(budget=budget, a=a, b=b, c=c),
        dict(budget=budget, a=a, b=b, c=c),
        rs,
        working_lines=4,
    )
