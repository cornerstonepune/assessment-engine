"""A story question in anyone's words → its case, its shape, where it sits, and — for one step — its answer
(goals/j3-story-shape.yaml, goals/md4d2b1-times-story-shape.yaml).

A story's shape (taxonomy §10: join or take away with the result, the change or the start unknown; two parts and a
whole; compare, and which side is unknown; the two-step shapes; §13: equal groups, sharing and grouping, arrays, a
price, times as many, and what a division does with what is left over) is what decides the operation, so it decides the
answer. The engine's own stories carry it by construction (`words.template_of`, exact); a story written by an educator
or printed on an outside paper does not. Reading a shape from words is judgement, so Jev chooses it from the
taxonomy's own story cases (ADR 0036, ADR 0071) — and everything after is code: the numbers are read from the text, a
one-step answer is the case's operation on them (the operation is the engine's own templates'), and the skill set and
level are the ones whose level names the case. Code also holds Jev's choice to the story's numbers: a case whose own
stories print two numbers is not taken for a story that prints four; a one-step question over one number more is
extra information by definition; a division the case says comes out exact, on numbers that leave some over, is a
person's, and one that drops or rounds up what is left over, on numbers that leave nothing, is exact grouping. A choice
Jev is not `story.shape_sure_above` sure of is left for a person; a number written in words leaves the answer to a
person. Which taxonomies a version chooses among is its prompt row's (`json_schema.taxonomies`): v1 + and − alone.
"""

import re

from engine.adapters import jev, llm
from engine.assess import divide_stories as DS
from engine.assess import words as W
from engine.w1_bank import story_cases as SC

PURPOSE = "story_shape"
BAR = ("story.shape_sure_above", 0.6)
EXTRA = "EXTRA_INFORMATION"
NUMBER = re.compile(r"(?<![\w.])\d[\d,]*(?!\w)")  # "Class 2A" is a name, not a number
# the numbers each taxonomy's stories are shown with: + and −'s as v1 was scored on; × and ÷'s, a division that comes
# out exact (48 ÷ 6), and 50 where the case is about what is left over
EXAMPLE = {"ADD_SUB": {"a": 45, "b": 12, "c": 8}, "MUL_DIV": {"a": 48, "b": 6, "c": 4, "d": 3, "extra": 2}}
APART = (
    "remainder_use",
    "operation",
    "context",
    "taxonomy",
)  # what tells two cases of one shape apart, in order
PRINTED = re.compile(r"\{(a|b|c|d|extra)\}")


def _bar(conn):
    row = conn.execute("select value from threshold where key = %s", (BAR[0],)).fetchone()
    return float(row["value"]) if row else BAR[1]


def taxonomies(row):
    """The taxonomies whose story cases a prompt row chooses among (`json_schema.taxonomies`): v1 says none, and reads
    + and − alone, as it was scored."""
    return (row.get("json_schema") or {}).get("taxonomies") or ["ADD_SUB"]


def _known(conn, reads=("ADD_SUB",)):
    """{option: case row} for every story case of these taxonomies, each under a name of its own (`_keys`). A row's
    taxonomy is its own column's: a row loaded before M1 does not repeat it in its match (live, 2026-10-12)."""
    rows = [
        {**r, "match": {**r["match"], "taxonomy": r["taxonomy"]}}
        for r in conn.execute(
            "select code, label, taxonomy, match from taxonomy_case where taxonomy = any(%s) and match ? 'structure'"
            " order by taxonomy, code",
            (list(reads),),
        )
    ]
    return dict(zip(_keys([r["match"] for r in rows]), rows))


def _keys(matches):
    """A name for each case: its shape, and where cases share a shape, what sets each apart, the first of `APART` they
    differ on (an array that multiplies and one that divides: ARRAY_MUL, ARRAY_DIV; a remainder rounded up:
    GROUPING_ROUND_UP); a case with nothing of its own there keeps the shape's name."""
    out = []
    for m in matches:
        same = [o for o in matches if o["structure"] == m["structure"]]
        apart = next((k for k in APART if len({str(o.get(k)) for o in same}) > 1), None)
        out.append(m["structure"] + (f"_{m[apart]}" if apart and m.get(apart) else ""))
    if len(set(out)) != len(out):
        raise ValueError(f"two story cases share a name: {sorted(k for k in out if out.count(k) > 1)}")
    return out


def shapes(conn, reads=("ADD_SUB",)):
    """{option: (case code, what it is — the case's label and the engine's own stories of it)} for every story case of
    these taxonomies. The case rows alone say "work backwards" or "several conditions" with no story to show; a story
    beside each is what a reader of shapes needs."""
    return _meanings(_known(conn, reads))


def _fits(t, m):
    """Whether a story template is one of this case's: its shape, its taxonomy's operations, and what the case says of
    the operation, what is left over and a price list."""
    if t["structure"] != m["structure"]:
        return False
    plus = set(t["op"]) <= set("+-")
    if m["taxonomy"] == "ADD_SUB" or plus:
        return plus and m["taxonomy"] == "ADD_SUB"
    sign = {"MUL": "×", "DIV": "÷"}.get(m.get("operation"))
    return (
        (sign is None or t["op"] == sign)
        and t.get("remainder_use") == m.get("remainder_use")
        and bool(t.get("table")) == (m.get("context") == "TABLE_OR_CHART")
    )


def _templates(m, fmt=None):
    """The engine's own stories of a case: a shape × and ÷ share by name with + and − (a number the story does not
    need) is each taxonomy's own."""
    return [t for t in W.templates(fmt, structure=m["structure"]) if _fits(t, m)]


def _example(m):
    """Every one of the engine's own stories of the case, not the first: CONSTRAINT's first reads like working
    backwards, and a reader shown only that one took "two numbers, their total and their difference" for a compare."""
    nums = EXAMPLE[m["taxonomy"]] | ({"a": 50} if m.get("remainder_use") else {})
    return " / ".join(_told(t, nums) for t in _templates(m))


def _cells(t):
    """[(label, number's name)] of a story's table, as `words.story_spec` pairs them: each label beside a and b, or each
    beside the number it names (a price list: "b", "c")."""
    return [(c[0], c[1]) if isinstance(c, list) else (c, k) for c, k in zip(t.get("table") or [], "ab")]


def _told(t, nums):
    """A story as its reader sees it, a price list's prices before its question; a table of a and b beside two labels
    reads as its words say ("The table shows"), as v1 was scored on."""
    text = t["text"].format(**nums, n="Asha", n2="Ravi")
    priced = [c for c in t.get("table") or [] if isinstance(c, list)]
    return f"Price list: {', '.join(f'{label} {nums[k]}' for label, k in priced)}. {text}" if priced else text


def counts(m):
    """How many numbers the engine's own stories of this case print ({2} for most one-step cases, {1} for twice and
    half as many, {3} for most of two steps), a table's among them."""
    return {len(set(PRINTED.findall(t["text"])) | {k for _, k in _cells(t)}) for t in _templates(m)}


def one_step_op(m):
    """'+', '-', '×' or '÷' for a one-step case, as the engine's own stories of it carry it; None for any other."""
    ops = {t["op"] for t in _templates(m, "word_1step")}
    return ops.pop() if len(ops) == 1 and ops <= {"+", "-", "×", "÷"} else None


def _fixed(m):
    """The number a case's own stories fix and never print: twice as many and half as many are × 2 and ÷ 2."""
    got = {
        v
        for t in _templates(m, "word_1step")
        for v in (t.get("numbers") or {}).values()
        if isinstance(v, int)
    }
    return got.pop() if len(got) == 1 else None


def numbers(text):
    return [int(n.replace(",", "")) for n in NUMBER.findall(text)]


def _operands(m, text):
    ns, fixed = numbers(text), _fixed(m)
    return ns + [fixed] if len(ns) == 1 and fixed else ns


def worked(m, text):
    """(the answer, the remainder where the story asks for both) of a one-step story, computed: the case's operation on
    the story's two numbers — a take-away or a division of the larger by the smaller, whichever is written first, and
    what is left over used as the case says (`divide_stories.answered`). (None, None) when code cannot be sure of it,
    and for a division the case says comes out exact on numbers that leave some over."""
    op, ns = one_step_op(m), _operands(m, text)
    if op is None or len(ns) != 2:
        return None, None
    big, small = max(ns), min(ns)
    if op in "+×":
        return (sum(ns) if op == "+" else ns[0] * ns[1]), None
    if op == "-":
        return big - small, None
    if small == 0 or bool(big % small) != bool(m.get("remainder_use")):
        return None, None
    return DS.answered(m.get("remainder_use"), big, small)


def answer(m, text):
    return worked(m, text)[0]


def placed(conn, case):
    """[(skill set, level)] whose level names this case."""
    return [
        (r["code"], r["level"])
        for r in conn.execute(
            "select s.code, l.key as level from skill_set s, jsonb_each(s.difficulty) l"
            " where l.value->'check'->'cases' ? %s order by s.code, l.key",
            (case,),
        )
    ]


def name(conn, text, ask=None, version=None):
    """→ {shape, case, sure, how ('template' | 'jev' | 'jev+code' | None), answer, remainder, placed, ranked, why}, read
    by the purpose's active prompt row, or `version` (only an eval names one)."""
    known = _known(conn, taxonomies(llm.active_prompt(conn, PURPOSE, version=version)))
    tpl = W.template_of(text)
    own = next((k for k, r in known.items() if tpl and _fits(tpl, r["match"])), None)
    if own:
        return _named(conn, known, own, text, 1.0, "template", [], "")
    about = {k: meaning for k, (_, meaning) in _meanings(known).items()}
    try:
        got = (ask or jev.decide)(
            conn, PURPOSE, {"story": text.strip()}, about, **({"version": version} if version else {})
        )
    except jev.JevError as e:
        return _unnamed(str(e))
    jevs = got["ranked"] or [(got["choice"], 0.0)]
    order = SC.merged(SC.words(conn), known, jevs, text)  # a pair told apart by its print is code's to settle
    ranked = [(s, round(p, 3)) for s, p in order[:3]]
    best, p = order[0]
    if p < _bar(conn):
        return _unsure(conn, known, order, text, ranked)
    out = _held(conn, known, best, text, round(p, 3), ranked)
    if best != jevs[0][0] and out["how"] == "jev":
        out |= {
            "how": "jev+code",
            "why": f"Jev read {jevs[0][0]}; the story's own words and layout make it {best}",
        }
    return out


def _unsure(conn, known, order, text, ranked):
    """Left for a person, with the answer when every case Jev leans to — enough of them to pass the bar — works the
    same one. Nimish, 2026-10-12, of a story Jev split between joining and two parts of a whole: "it's 84"."""
    bar, (best, p) = _bar(conn), order[0]
    out = _unnamed(f"Jev is {p:.2f} sure it is {best}; below {bar} a person names the shape", ranked)
    lean, mass = [], 0.0
    for key, q in order:
        lean.append(key)
        mass += q
        if mass >= bar:
            break
    n = len(numbers(text))
    keys = {
        worked(known[k]["match"], text) if k in known and n in counts(known[k]["match"]) else None
        for k in lean
    }
    if mass >= bar and len(keys) == 1 and (one := keys.pop()) and one[0] is not None:
        out |= {
            "answer": one[0],
            "remainder": one[1],
            "why": out["why"] + f"; the answer is {one[0]} in each it leans to",
        }
    return out


def _meanings(known):
    return {
        k: (r["code"], f"{r['label']}. Stories of this shape: {_example(r['match'])}")
        for k, r in known.items()
    }


def _held(conn, known, best, text, sure, ranked):
    """Jev's choice held to the story's numbers: a case whose stories print two numbers is not taken for a story that
    prints four; a one-step question over one number more than its case prints has a number it does not need, which is
    what its taxonomy's EXTRA_INFORMATION case is, of the same operation."""
    m = known[best]["match"]
    n, want = len(numbers(text)), counts(m)
    if n in want:
        return _divided(conn, known, best, text, sure, ranked)
    extra = next(
        (
            k
            for k, r in known.items()
            if r["match"]["structure"] == EXTRA
            and r["match"]["taxonomy"] == m["taxonomy"]
            and r["match"].get("operation") in (None, m.get("operation"))
        ),
        None,
    )
    if one_step_op(m) and want and n == max(want) + 1 and extra:
        why = f"Jev read {best}; the story prints {n} numbers, so one is not needed"
        return _named(conn, known, extra, text, sure, "jev+code", ranked, why)
    return _unnamed(
        f"Jev read {best}, whose stories print {sorted(want)} numbers; this one prints {n}", ranked
    )


def _divided(conn, known, best, text, sure, ranked):
    """A one-step division held to what its numbers leave over. A case that says nothing is left over, read for numbers
    that leave some, is a person's: what the story does with them is not code's to guess. A case that drops what is
    left over or rounds it up, read for numbers that leave nothing, is the story of exact grouping: nothing is over."""
    m = known[best]["match"]
    ns = _operands(m, text)
    if one_step_op(m) != "÷" or len(ns) != 2:
        return _named(conn, known, best, text, sure, "jev", ranked, "")
    big, small = max(ns), min(ns)
    if small == 0:
        return _unnamed(f"Jev read {best}; a division by 0 is a person's", ranked)
    over, use = big % small, m.get("remainder_use")
    if over and not use:
        why = f"Jev read {best}; {big} ÷ {small} leaves {over} over, which a story of this case never does"
        return _unnamed(f"{why}: what the story does with them is a person's", ranked)
    exact = next(
        (
            k
            for k, r in known.items()
            if r["match"]["structure"] == m["structure"]
            and r["match"]["taxonomy"] == m["taxonomy"]
            and not r["match"].get("remainder_use")
        ),
        None,
    )
    if not over and use in ("ROUND_DOWN", "ROUND_UP") and exact:
        why = f"Jev read {best}; {big} ÷ {small} leaves nothing over, so nothing is dropped or rounded up"
        return _named(conn, known, exact, text, sure, "jev+code", ranked, why)
    return _named(conn, known, best, text, sure, "jev", ranked, "")


def _named(conn, known, key, text, sure, how, ranked, why):
    r = known[key]
    ans, rem = worked(r["match"], text)
    return {
        "shape": r["match"]["structure"],
        "case": r["code"],
        "sure": sure,
        "how": how,
        "answer": ans,
        "remainder": rem,
        "placed": placed(conn, r["code"]),
        "ranked": ranked,
        "why": why,
    }


def _unnamed(why, ranked=()):
    return {
        "shape": None,
        "case": None,
        "sure": None,
        "how": None,
        "answer": None,
        "remainder": None,
        "placed": [],
        "ranked": list(ranked),
        "why": why,
    }
