"""Item generators. Every generator is deterministic given an RNG and returns Item objects.

An Item has one or more Responses. A Response is one thing the child writes that can be
scored: a run of digit cells, a tick, or free text. Closed responses carry the correct
answer and the misconception -> wrong-answer table; open responses carry a rubric.
"""
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
import random, itertools, hashlib
from . import misconceptions as M
from .ladder import RUNGS

@dataclass
class Response:
    rid: str                 # e.g. "a", "b", "est", "brick2"
    kind: str                # digits | tick | text
    answer: Any              # str for digits/tick; None for text
    cells: int = 0           # number of digit cells (digits)
    options: List[str] = field(default_factory=list)   # for tick
    misconceptions: Dict[str, Any] = field(default_factory=dict)
    tolerance: Optional[int] = None    # for estimates: |read - answer| <= tolerance is correct
    rubric: Optional[str] = None       # for text
    label: str = ""                    # short label printed next to the cells

@dataclass
class Item:
    item_id: str
    template: str
    rung: str
    skills: List[str]
    signal: str
    fmt: str
    scaffolded: bool
    stem: str
    spec: Dict[str, Any]              # rendering payload
    responses: List[Response]
    working_lines: int = 2

    def to_dict(self):
        return asdict(self)

def _id(template, payload):
    h = hashlib.sha1(f"{template}|{payload}".encode()).hexdigest()[:8]
    return f"{template}-{h}"

def _cells(n):
    return len(str(n)) + 1

def _item(template, rung, signal, fmt, stem, spec, responses, scaffolded=False, working_lines=2, skills=None):
    return Item(_id(template, spec), template, rung, skills or RUNGS[rung]["skills"], signal, fmt,
                scaffolded, stem, spec, responses, working_lines)

# ---------------------------------------------------------------- operand samplers

def _regroup_count_add(a, b):
    w = max(len(str(a)), len(str(b)))
    da, db = M.digits(a, w), M.digits(b, w)
    c, n = 0, 0
    for x, y in zip(da, db):
        s = x + y + c
        c = 1 if s >= 10 else 0
        n += c
    return n

def _regroup_count_sub(a, b):
    w = max(len(str(a)), len(str(b)))
    da, db = M.digits(a, w), M.digits(b, w)
    n, borrow = 0, 0
    for x, y in zip(da, db):
        x -= borrow
        if x < y:
            n += 1; borrow = 1
        else:
            borrow = 0
    return n

def sample_add(rng, digits_a, digits_b, regroups, max_total=None, tries=2000):
    lo_a, hi_a = 10 ** (digits_a - 1), 10 ** digits_a - 1
    lo_b, hi_b = 10 ** (digits_b - 1), 10 ** digits_b - 1
    if digits_a == 1: lo_a = 1
    if digits_b == 1: lo_b = 1
    for _ in range(tries):
        a, b = rng.randint(lo_a, hi_a), rng.randint(lo_b, hi_b)
        if a == b or a % 10 == 0 or b % 10 == 0:
            continue
        if max_total and a + b > max_total:
            continue
        if _regroup_count_add(a, b) in regroups:
            return a, b
    raise RuntimeError(f"no add sample for {digits_a},{digits_b},{regroups}")

def sample_sub(rng, digits_a, digits_b, regroups, across_zero=False, tries=4000, max_a=None):
    lo_a, hi_a = 10 ** (digits_a - 1), 10 ** digits_a - 1
    if max_a: hi_a = min(hi_a, max_a)
    lo_b, hi_b = 10 ** (digits_b - 1), 10 ** digits_b - 1
    if digits_b == 1: lo_b = 1
    for _ in range(tries):
        a, b = rng.randint(lo_a, hi_a), rng.randint(lo_b, hi_b)
        if b >= a or a - b < (5 if digits_a >= 2 else 1) or b % 10 == 0 or (a % 10 == 0 and not across_zero and digits_a <= 2):
            continue
        ds = M.digits(a, digits_a)
        has_zero = 0 in ds[1:]
        if across_zero != has_zero:
            continue
        if _regroup_count_sub(a, b) in regroups:
            return a, b
    raise RuntimeError(f"no sub sample for {digits_a},{digits_b},{regroups},{across_zero}")

# ---------------------------------------------------------------- closed computation items

def bare_sum(rng, rung, signal, op, da, db, regroups, max_total=None, across_zero=False, layout="horizontal"):
    if op == "+":
        a, b = sample_add(rng, da, db, regroups, max_total)
    else:
        a, b = sample_sub(rng, da, db, regroups, across_zero, max_a=max_total)
    ans = a + b if op == "+" else a - b
    r = Response("ans", "digits", str(ans), cells=_cells(max(ans, a)), misconceptions=M.predict(op, a, b))
    fmt = "column_grid" if layout == "column" else "bare_sum"
    return _item(f"{'ADD' if op=='+' else 'SUB'}.{da}D{db}D.REG{'Z' if across_zero else ''.join(map(str,sorted(regroups)))}",
                 rung, signal, fmt, "", dict(a=a, b=b, op=op, layout=layout), [r],
                 working_lines=3 if layout == "horizontal" else 0)

def missing_number(rng, rung, signal, kind, hi):
    """a + □ = c  |  □ - b = c  |  c - □ = a  ; numbers to `hi`."""
    if kind == "add_missing_addend":
        c = rng.choice([hi, hi // 2, rng.randrange(20, hi, 5)]) if hi >= 40 else rng.randint(8, hi)
        a = rng.randint(1, c - 1); ans = c - a
        stem = f"{a} + □ = {c}"; mis = {"M_ADD_INSTEAD": a + c, "M_FACT_PM1": ans + 1}
    elif kind == "sub_missing_minuend":
        b = rng.randint(2, hi // 3); c = rng.randint(hi // 4, hi - b); ans = b + c
        stem = f"□ − {b} = {c}"; mis = {"M_SUB_INSTEAD": abs(c - b), "M_FACT_PM1": ans - 1}
    else:  # sub_missing_subtrahend
        c = rng.randint(hi // 4, hi - 2); a = rng.randint(1, c - 1); ans = c - a
        stem = f"{c} − □ = {a}"; mis = {"M_ADD_INSTEAD": c + a, "M_FACT_PM1": ans + 1}
    mis = {k: v for k, v in mis.items() if v != ans and v >= 0}
    r = Response("ans", "digits", str(ans), cells=_cells(hi), misconceptions=mis)
    return _item("MISSING.NUM", rung, signal, "missing_number", stem, dict(text=stem), [r], working_lines=1)

def balance_scale(rng, rung, signal, hi):
    """a + b = □ + c"""
    a = rng.randrange(10, hi // 2, 10 if hi >= 100 else 1)
    b = rng.randrange(10, hi // 2, 10 if hi >= 100 else 1)
    while b == a: b = rng.randrange(10, hi // 2, 10 if hi >= 100 else 1)
    c = rng.randrange(10, a + b - 5, 10 if hi >= 100 else 1)
    ans = a + b - c
    mis = {"M_EQUALS_MEANS_ANSWER": a + b, "M_ADD_ALL": a + b + c}
    mis = {k: v for k, v in mis.items() if v != ans}
    r = Response("ans", "digits", str(ans), cells=_cells(a + b), misconceptions=mis)
    return _item("BALANCE", rung, "Conceptual", "balance_scale", "Write the missing number so that the scales balance.",
                 dict(left=[a, b], right=[None, c]), [r], working_lines=1)

def number_wall(rng, rung, signal, hi):
    base = [rng.randint(3, hi) for _ in range(3)]
    m1, m2 = base[0] + base[1], base[1] + base[2]
    top = m1 + m2
    rs = [Response("m1", "digits", str(m1), cells=_cells(top), misconceptions=M.predict("+", base[0], base[1])),
          Response("m2", "digits", str(m2), cells=_cells(top), misconceptions=M.predict("+", base[1], base[2])),
          Response("top", "digits", str(top), cells=_cells(top), misconceptions=M.predict("+", m1, m2))]
    return _item("WALL", rung, signal, "number_wall", "The number in each brick is the sum of the two bricks below it. Complete the wall.",
                 dict(base=base), rs, working_lines=0)

def number_line_jumps(rng, rung, signal, op, hi):
    """a ± b shown as a jump of tens then ones. Landing boxes + answer are responses."""
    if op == "+":
        a = rng.randint(hi // 4, hi - 40); b = rng.randint(11, 39)
        while b % 10 == 0: b = rng.randint(11, 39)
        tens, ones = (b // 10) * 10, b % 10
        land1 = a + tens; ans = a + b
    else:
        a = rng.randint(hi // 2, hi - 1); b = rng.randint(11, 39)
        while b % 10 == 0 or b >= a: b = rng.randint(11, 39)
        tens, ones = (b // 10) * 10, b % 10
        land1 = a - tens; ans = a - b
    rs = [Response("land1", "digits", str(land1), cells=_cells(hi), misconceptions={"M_FACT_PM10": land1 + (10 if op=='+' else -10)}, label=f"after {op}{tens}"),
          Response("ans", "digits", str(ans), cells=_cells(hi), misconceptions=M.predict(op, a, b))]
    return _item("NLINE", rung, signal, "number_line_jumps", f"Complete {a} {op} {b}. Use the number line to help you.",
                 dict(a=a, b=b, op=op, tens=tens, ones=ones), rs, scaffolded=True, working_lines=0)

def partition_scaffold(rng, rung, signal, regroups):
    a, b = sample_add(rng, 3, 3, regroups)
    da, db = M.digits(a, 3), M.digits(b, 3)
    hund = (da[2] + db[2]) * 100; tens = (da[1] + db[1]) * 10; ones = da[0] + db[0]
    rs = [Response("a_t", "digits", str(da[1] * 10), cells=3, label="tens of first"),
          Response("a_o", "digits", str(da[0]), cells=2, label="ones of first"),
          Response("b_h", "digits", str(db[2] * 100), cells=4), Response("b_t", "digits", str(db[1] * 10), cells=3), Response("b_o", "digits", str(db[0]), cells=2),
          Response("hund", "digits", str(hund), cells=4), Response("tens", "digits", str(tens), cells=4), Response("ones", "digits", str(ones), cells=3),
          Response("ans", "digits", str(a + b), cells=5, misconceptions=M.predict("+", a, b))]
    return _item("PARTITION", rung, "Conceptual", "partition_scaffold", f"Complete the calculation {a} + {b} by partitioning.",
                 dict(a=a, b=b, a_h=da[2] * 100), rs, scaffolded=True, working_lines=0)

def sort_into_table(rng, rung, signal, op, n=4):
    """n two-digit calculations; child ticks 'needs regrouping' or 'no regrouping'. Tests recognition."""
    items, rs = [], []
    want = [1, 0] * (n // 2)
    rng.shuffle(want)
    for i, w in enumerate(want):
        if op == "+":
            a, b = sample_add(rng, 2, 2, {w})
        else:
            a, b = sample_sub(rng, 2, 2, {w})
        items.append(f"{a} {op} {b}")
        rs.append(Response(f"s{i}", "tick", "regroup" if w else "none", options=["regroup", "none"], label=f"{a} {op} {b}",
                           misconceptions={}))
    word = "Change a ten for 10 ones" if op == "-" else "Make a new ten"
    return _item("SORT", rung, "Conceptual", "sort_into_table",
                 f"For each calculation, tick the box that describes it. Do not work out the answer.",
                 dict(items=items, col_a=word, col_b="No regrouping needed"), rs, working_lines=0)

def estimate_then_calc(rng, rung, signal, op, digits_a, digits_b, regroups):
    if op == "+":
        a, b = sample_add(rng, digits_a, digits_b, regroups)
    else:
        a, b = sample_sub(rng, digits_a, digits_b, regroups)
    ra, rb = round(a, -1), round(b, -1)
    est = ra + rb if op == "+" else ra - rb
    ans = a + b if op == "+" else a - b
    rs = [Response("est", "digits", str(est), cells=_cells(max(est, ans)), tolerance=10, label="estimate"),
          Response("ans", "digits", str(ans), cells=_cells(max(est, ans)), misconceptions=M.predict(op, a, b), label="exact")]
    return _item("ESTIMATE", rung, signal, "estimate_then_calc",
                 f"Estimate first, then work out {a} {op} {b}.", dict(a=a, b=b, op=op, ra=ra, rb=rb), rs, scaffolded=True, working_lines=2)

def missing_digit(rng, rung, signal, op, width):
    """Column calculation with 1–2 hidden digits; brute-force guarantees a unique solution."""
    for _ in range(300):
        if op == "+":
            a, b = sample_add(rng, width, width, {1, 2})
            c = a + b
        else:
            a, b = sample_sub(rng, width, width, {1, 2})
            c = a - b
        sa, sb, sc = str(a), str(b).zfill(width), str(c)
        # hide one digit in a and one in b (never leading), keep c visible
        pa = rng.randint(1, len(sa) - 1); pb = rng.randint(1, len(sb) - 1)
        # count solutions
        sols = []
        for x in range(10):
            for y in range(10):
                aa = int(sa[:pa] + str(x) + sa[pa + 1:]); bb = int(sb[:pb] + str(y) + sb[pb + 1:])
                if (aa + bb if op == "+" else aa - bb) == c:
                    sols.append((x, y))
        if len(sols) == 1:
            rs = [Response("da", "digits", sa[pa], cells=1, label="top"), Response("db", "digits", sb[pb], cells=1, label="bottom")]
            return _item("MISSING.DIGIT", rung, signal, "missing_digit", "Write the missing digits.",
                         dict(a=sa[:pa] + "□" + sa[pa + 1:], b=sb[:pb] + "□" + sb[pb + 1:], c=sc, op=op), rs, working_lines=2)
    raise RuntimeError("no unique missing-digit item")

def digit_cards(rng, rung, signal, n_cards=3, addend=None):
    cards = rng.sample(range(1, 10), n_cards)
    if addend is None:
        addend = rng.randint(100, 400)
    best = max(int("".join(map(str, p))) + addend for p in itertools.permutations(cards))
    worst = min(int("".join(map(str, p))) + addend for p in itertools.permutations(cards))
    big = int("".join(map(str, sorted(cards, reverse=True))))
    rs = [Response("largest", "digits", str(best), cells=5, label="largest total",
                   misconceptions={"M_SMALLEST_NUMBER": worst, "M_FORGOT_ADDEND": big})]
    return _item("CARDS", rung, "Stretch", "digit_cards",
                 f"Use each of the digits {', '.join(map(str, cards))} once to make a {n_cards}-digit number. Add {addend} to your number. What is the largest total you can make? Show how you know.",
                 dict(cards=cards, addend=addend), rs + [Response("how", "text", None, rubric="Accept: largest digits placed in the highest places; or any argument that a bigger start gives a bigger total.")],
                 working_lines=3)

def efficient_method(rng, rung, signal):
    """Pairs with an obvious shortcut: near-multiples of 10/100 or same-tens."""
    kind = rng.choice(["near100", "same_tens", "near1000"])
    if kind == "near100":
        a = rng.randint(150, 480); b = rng.choice([98, 99, 199, 299]); op = "+"
    elif kind == "same_tens":
        t = rng.randint(2, 8) * 10; a = t * 10 + rng.randint(1, 9) + 100 * rng.randint(1, 4); b = (a // 10) * 10 - rng.randint(1, 3) * 10; op = "-"
        a, b = a, a - rng.randint(11, 19)
    else:
        a = rng.randint(2000, 4800); b = rng.choice([998, 999, 1999, 2998]); op = "+"
    ans = a + b if op == "+" else a - b
    rs = [Response("ans", "digits", str(ans), cells=_cells(ans), misconceptions=M.predict(op, a, b))]
    return _item("EFFICIENT", rung, signal, "efficient_method",
                 f"Use the most efficient method you can to work out {a} {op} {b}. Show your method.",
                 dict(a=a, b=b, op=op), rs + [Response("method", "text", None, rubric="Any compensation / friendly-number / counting-on method stated. Column method is correct but not 'most efficient'.")],
                 working_lines=3)

def partial_worked(rng, rung, signal):
    """Emyr-style: a 3-digit subtraction with the regrouping started; child completes the partition and the answer."""
    a, b = sample_sub(rng, 3, 3, {1})
    da, db = M.digits(a, 3), M.digits(b, 3)
    # find the regrouping column
    if da[0] < db[0]:
        parts = (da[2] * 100, (da[1] - 1) * 10, da[0] + 10)
    else:
        parts = ((da[2] - 1) * 100, da[1] * 10 + 100, da[0])
    rs = [Response("p2", "digits", str(parts[1]), cells=4, label="tens after regrouping"),
          Response("p3", "digits", str(parts[2]), cells=3, label="ones after regrouping"),
          Response("ans", "digits", str(a - b), cells=4, misconceptions=M.predict("-", a, b))]
    return _item("PARTIAL", rung, "Conceptual", "partial_worked",
                 f"Asha did not finish her calculation. Complete it for her.",
                 dict(a=a, b=b, p1=parts[0], b_parts=(db[2] * 100, db[1] * 10, db[0])), rs, scaffolded=True, working_lines=0)

def explain_claim(rng, rung, signal):
    """Compensation claim: a + b = (a-1) + (b+1). Tick + explain."""
    a = rng.randint(120, 480); b = rng.choice([99, 199, 299, 49, 79])
    claim = f"{a} + {b} gives the same total as {a - 1} + {b + 1}."
    name = rng.choice(["Zoya", "Aarav", "Meera", "Kabir", "Riya", "Dev"])
    rs = [Response("tick", "tick", "yes", options=["yes", "no"], label="Is this correct?"),
          Response("why", "text", None, rubric="Accept any explanation showing 1 moved from one number to the other, or that both sums equal the same total.")]
    return _item("CLAIM", "X1", "Conceptual", "explain_claim", f"{name} says: “{claim}” Is {name} correct? Explain your answer.",
                 dict(a=a, b=b, name=name), rs, working_lines=3)

def find_mistake(rng, rung, signal, op="+"):
    """A worked column calculation with one planted misconception; child ticks the wrong step and writes the correct answer."""
    if op == "+":
        a, b = sample_add(rng, 2, 2, {1}); mis = M.predict("+", a, b); code = rng.choice([c for c in ("M_NOCARRY", "M_CARRY_SKIP") if c in mis])
    else:
        a, b = sample_sub(rng, 2, 2, {1}); mis = M.predict("-", a, b); code = rng.choice([c for c in ("M_SMALL_FROM_LARGE", "M_NO_DECREMENT") if c in mis])
    wrong = mis[code]
    ans = a + b if op == "+" else a - b
    name = rng.choice(["Ishaan", "Anaya", "Vihaan", "Saee"])
    opts = ["ones column", "tens column", "both"]
    correct_opt = "ones column" if code in ("M_NOCARRY",) else ("tens column" if code == "M_CARRY_SKIP" else "ones column")
    rs = [Response("where", "tick", correct_opt, options=opts, label="Where is the mistake?"),
          Response("ans", "digits", str(ans), cells=_cells(max(ans, wrong)), misconceptions=mis, label="correct answer"),
          Response("why", "text", None, rubric=f"Names the mistake: {M.ADD_PREDICTORS.get(code, M.SUB_PREDICTORS.get(code))[1]}")]
    return _item("FTM", "X2", "Conceptual", "find_mistake", f"{name} worked out {a} {op} {b} and wrote {wrong}. That is not right.",
                 dict(a=a, b=b, op=op, wrong=wrong, planted=code), rs, working_lines=2)

# ---------------------------------------------------------------- word problems (deterministic contexts; LLM hook later)

NAMES = ["Aarav", "Riya", "Kabir", "Meera", "Ishaan", "Saee", "Vihaan", "Anaya", "Dev", "Zoya", "Arjun", "Tara"]
CONTEXTS_1STEP = [
    ("+", "{n} has {a} marbles. {n2} gives {n} {b} more. How many marbles does {n} have now?"),
    ("+", "A shop sells {a} laddoos in the morning and {b} in the evening. How many laddoos does it sell in the whole day?"),
    ("+", "There are {a} children in the ground and {b} children in the hall. How many children are there altogether?"),
    ("-", "A bus has {a} seats. {b} of them are taken. How many seats are empty?"),
    ("-", "{n} had ₹{a}. {n} bought a book for ₹{b}. How much money does {n} have left?"),
    ("-", "{n} collected {a} shells. {n2} collected {b}. How many more shells did {n} collect than {n2}?"),
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
    mis = M.predict(op, a, b); mis["M_WRONG_OP"] = abs(a - b) if op == "+" else a + b
    r = Response("ans", "digits", str(ans), cells=_cells(max(ans, a + b)), misconceptions=mis)
    return _item("WP1", rung, "Application", "word_1step", stem, dict(a=a, b=b, op=op), [r], working_lines=3)

def word_2step(rng, rung, signal, digits_max):
    tpl = rng.choice(CONTEXTS_2STEP)
    n = rng.choice(NAMES)
    if "get on" in tpl:
        a = rng.randint(10 ** (digits_max - 1) + 50, 10 ** digits_max - 1); b = rng.randint(11, a // 3); c = rng.randint(11, 60)
        ans = a - b + c; mis = {"M_ONE_STEP_ONLY": a - b, "M_WRONG_OP": a + b - c}
    else:
        a = rng.randint(10 ** (digits_max - 1) + 50, 10 ** digits_max - 1); b = rng.randint(11, a // 3); c = rng.randint(11, a // 3)
        ans = a - b - c; mis = {"M_ONE_STEP_ONLY": a - b, "M_WRONG_OP": a - b + c}
    stem = tpl.format(a=a, b=b, c=c, n=n)
    mis = {k: v for k, v in mis.items() if v != ans}
    r = Response("ans", "digits", str(ans), cells=_cells(a + c), misconceptions=mis)
    return _item("WP2", rung, "Application", "word_2step", stem, dict(a=a, b=b, c=c), [r], working_lines=4)

def word_budget(rng, rung, signal):
    budget = rng.choice([5000, 8000, 10000, 12000]); a = rng.randint(1200, 3900); b = rng.randint(600, 1900); c = rng.randint(400, 1500)
    ans = budget - a - b - c
    mis = {"M_ONE_STEP_ONLY": budget - a, "M_SUM_ONLY": a + b + c}
    rs = [Response("ans", "digits", str(ans), cells=5, misconceptions=mis)]
    return _item("BUDGET", rung, "Application", "word_2step", BUDGET[0].format(budget=budget, a=a, b=b, c=c), dict(budget=budget, a=a, b=b, c=c), rs, working_lines=4)

def missing_part_20(rng, rung, signal):
    c = rng.randint(8, 20); a = rng.randint(1, c - 1); ans = c - a
    r = Response("ans", "digits", str(ans), cells=2, misconceptions={"M_ADD_INSTEAD": a + c, "M_FACT_PM1": ans + 1})
    return _item("PPW20", rung, "Conceptual", "missing_number", f"{a} + □ = {c}", dict(text=f"{a} + □ = {c}"), [r], working_lines=1)

def multi_add(rng, rung, signal, n_addends=3, digits_each=4):
    lo, hi = 10 ** (digits_each - 1), 10 ** digits_each - 1
    xs = [rng.randint(lo, hi) for _ in range(n_addends)]
    while any(x % 10 == 0 for x in xs):
        xs = [rng.randint(lo, hi) for _ in range(n_addends)]
    ans = sum(xs)
    mis = {"M_DROP_CARRYOUT": ans % (10 ** digits_each), "M_FACT_PM10": ans + 10, "M_FACT_PM100": ans - 100}
    mis = {k: v for k, v in mis.items() if v != ans}
    r = Response("ans", "digits", str(ans), cells=len(str(ans)) + 1, misconceptions=mis)
    return _item(f"ADD.MULTI{n_addends}", rung, signal, "column_grid", "", dict(addends=xs, op="+", layout="column"), [r], working_lines=0)
