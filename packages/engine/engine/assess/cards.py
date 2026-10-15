"""A kind of question as a row (goals/sf1-a-kind-of-question-is-a-row.yaml, ADR 0075).

A kind (`question_format`) is data, never code:
- `text`, the sentence printed with its box: each number named in braces (`{a} × {b} × {c} = □`), `{n:ord}` printed
  as 9th, `{name}` a child's name;
- `ask`, the instruction above it, if any;
- `derive`, numbers worked from the drawn ones (a sequence's terms from its start and step);
- `answer`, the formula the child works, or a list of formulas for a list;
- `also`, each mistake by the formula (or list) of the wrong answer it writes.

A level's rule gives each drawn number's range (`numbers`: [lo, hi], or {"one_of": [...]}) and the answer's bounds
(`answer_within`). Formulas are worked by `own_stories.value`: + − × ÷ and brackets, every ÷ exact. No number is
below zero, and a question names at least one mistake its wrong answer shows.

Membership is decided by listing: every set of numbers the level allows is worked and printed, so a question belongs
when one of them prints its words and works its stored answer and mistakes; a level counts what it can make the same
way, and two sets that print the same words are one question. A level allows at most `LIMIT` sets of numbers, so the
listing is always whole. Deterministic; pure: no I/O.
"""

import ast
import functools
import itertools
import json
import math
import random
import re
import string
from typing import Any, cast

from . import words as W
from .items import Item, Response, cells, item
from .own_stories import Inexact, value

LIMIT = 50_000
NAME = "name"
SPACES = "You may not need every space."
Numbers = dict[str, int]
Answer = int | list[int]


def ordinal(n: int) -> str:
    """9 → 9th, 1 → 1st, 12 → 12th, 22 → 22nd."""
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


class _Words(string.Formatter):
    def format_field(self, value: Any, format_spec: str) -> str:
        return ordinal(value) if format_spec == "ord" else super().format_field(value, format_spec)


def _print(text: str, vals: dict[str, Any]) -> str:
    return _Words().format(text, **vals) if text else ""


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _plain(text: str) -> str:
    """Words as compared: no spaces, so "2,5,8, 11, □" is "2, 5, 8, 11, □"; any child's name as `{name}`."""
    for n in W.NAMES:
        text = re.sub(rf"\b{re.escape(n)}\b", "{name}", text)
    return _squash(text)


def _slots(text: str) -> set[str]:
    return set(re.findall(r"\{(\w+)(?::\w+)?\}", text or ""))


def _formulas(kind: dict[str, Any]) -> list[str]:
    out: list[str] = list(kind.get("derive", {}).values())
    for f in [kind["answer"], *kind.get("also", {}).values()]:
        out += f if isinstance(f, list) else [f]
    return out


def _names(formula: str) -> set[str]:
    return {n.id for n in ast.walk(ast.parse(formula, mode="eval")) if isinstance(n, ast.Name)}


def _span(spec: Any) -> list[int]:
    if isinstance(spec, dict) and "one_of" in spec:
        values = cast(list[int], cast(dict[str, Any], spec)["one_of"])
        return sorted({int(v) for v in values})
    if isinstance(spec, list) and len(cast(list[int], spec)) == 2:
        lo, hi = cast(list[int], spec)
        return list(range(int(lo), int(hi) + 1))
    raise ValueError(f"a number's range is [lo, hi] or {{'one_of': [...]}}, not {spec!r}")


def _drawn(kind: dict[str, Any]) -> list[str]:
    """The numbers a level draws for this kind: every one its formulas and words name, less those it derives."""
    used = (
        {n for f in _formulas(kind) for n in _names(f)} | _slots(kind["text"]) | _slots(kind.get("ask", ""))
    )
    return sorted(used - set(kind.get("derive", {})) - {NAME})


def problems(kind: dict[str, Any], rule: dict[str, Any]) -> list[str]:
    """Why this kind cannot be drawn at this level, before anything is: a formula or its words naming a number no range
    gives, a level of more sets of numbers than can be listed, numbers that make nothing, a mistake that never writes a
    wrong answer. Empty when it can."""
    return list(_problems(_key(kind, rule)))


@functools.lru_cache(maxsize=256)
def _problems(key: str) -> tuple[str, ...]:
    kind, rule = json.loads(key)
    return tuple(_why(kind, rule))


def _why(kind: dict[str, Any], rule: dict[str, Any]) -> list[str]:
    code, numbers, derived = kind["code"], rule.get("numbers", {}), set(kind.get("derive", {}))
    known = set(numbers) | derived | {NAME}
    out = [
        f"{code}: the formula {f!r} names {n}, which no range of the level gives"
        for f in _formulas(kind)
        for n in sorted(_names(f) - known)
    ]
    out += [
        f"{code}: its words name {n}, which no range of the level gives"
        for n in sorted((_slots(kind["text"]) | _slots(kind.get("ask", ""))) - known)
    ]
    if out:
        return out
    size = math.prod(len(_span(numbers[n])) for n in _drawn(kind))
    if size > LIMIT:
        return [f"{code}: the level allows {size} sets of numbers, more than the {LIMIT} that can be listed"]
    worked = [w for nums in _combos(kind, rule) if (w := _work(kind, rule, nums)) is not None]
    if not worked:
        return [
            f"{code}: the level's numbers make nothing — no answer falls within {rule.get('answer_within')}"
        ]
    out = [
        f"{code}: the mistake {m} never writes a wrong answer at this level"
        for m in kind.get("also", {})
        if not any(m in w[2] for w in worked)
    ]
    if not out and not any(w[2] for w in worked):
        out.append(f"{code}: no question at this level names a mistake its wrong answer shows")
    return out


def _combos(kind: dict[str, Any], rule: dict[str, Any]) -> list[Numbers]:
    drawn = _drawn(kind)
    spans = [_span(rule["numbers"][n]) for n in drawn]
    return [dict(zip(drawn, combo, strict=True)) for combo in itertools.product(*spans)]


def _answer(formula: str | list[str], vals: Numbers) -> Answer:
    return [value(f, vals) for f in formula] if isinstance(formula, list) else value(formula, vals)


def _work(
    kind: dict[str, Any], rule: dict[str, Any], nums: Numbers
) -> tuple[Numbers, Answer, dict[str, Answer]] | None:
    """The numbers worked: (every number, the right answer, each mistake's wrong answer), or None where these numbers do
    not make the question — a division not exact, a number below zero, an answer outside the level's bounds. A mistake
    whose wrong answer is the right one, or below zero, is left out."""
    try:
        vals = dict(nums)
        for k, f in kind.get("derive", {}).items():
            vals[k] = value(f, vals)
        right = _answer(kind["answer"], vals)
    except Inexact:
        return None
    each = right if isinstance(right, list) else [right]
    lo, hi = rule.get("answer_within", [0, math.inf])
    if min(vals.values()) < 0 or not all(lo <= x <= hi for x in each):
        return None
    wrong: dict[str, Answer] = {}
    for code, f in kind.get("also", {}).items():
        try:
            w = _answer(f, vals)
        except Inexact:
            continue
        if w != right and min(w if isinstance(w, list) else [w]) >= 0:
            wrong[code] = w
    return vals, right, wrong


def _key(kind: dict[str, Any], rule: dict[str, Any]) -> str:
    """What a listing depends on: the kind, and the level's numbers and bounds — not the rest of its rule."""
    level = {"numbers": rule.get("numbers", {}), "answer_within": rule.get("answer_within")}
    if level["answer_within"] is None:
        del level["answer_within"]
    return json.dumps([kind, level], sort_keys=True, ensure_ascii=False)


def _index(kind: dict[str, Any], rule: dict[str, Any]) -> dict[str, Numbers]:
    return _lookup(_key(kind, rule))


@functools.lru_cache(maxsize=256)
def _lookup(key: str) -> dict[str, Numbers]:
    """`_listed` as a lookup, built once a level: a bank's questions are each read through it."""
    return dict(_listed(key))


@functools.lru_cache(maxsize=256)
def _listed(key: str) -> tuple[tuple[str, Numbers], ...]:
    """Every question the level can make, by its words as compared (`_plain`) → the numbers that print them."""
    kind, rule = json.loads(key)
    out: dict[str, Numbers] = {}
    for nums in _combos(kind, rule):
        if (worked := _work(kind, rule, nums)) is not None and worked[2]:  # every question names a mistake
            out.setdefault(_squash(_print(kind["text"], {**worked[0], NAME: "{name}"})), nums)
    return tuple(out.items())


def count(kind: dict[str, Any], rule: dict[str, Any]) -> int:
    """How many different questions this kind makes at this level."""
    return len(_listed(_key(kind, rule)))


def _shown(a: Answer) -> str:
    return ", ".join(map(str, a)) if isinstance(a, list) else str(a)


def make(kind: dict[str, Any], rule: dict[str, Any], nums: Numbers, rung: str, signal: str) -> Item:
    """The question these numbers make; RuntimeError where they make none (the drawer draws again)."""
    worked = _work(kind, rule, nums)
    if worked is None or not worked[2]:
        raise RuntimeError("these numbers do not make this question; draw again")
    vals, right, wrong = worked
    named: dict[str, Any] = {**vals, NAME: W.NAMES[sum(nums.values()) % len(W.NAMES)]}
    sentence, ask, box = (_print(kind.get(k, ""), named) for k in ("text", "ask", "box"))
    spec: dict[str, Any] = {"kind": kind["code"], "numbers": dict(nums), "text": sentence}
    mistakes: dict[str, Any] = {
        c: w if isinstance(w, int) else _shown(w) for c, w in wrong.items()
    }  # a number as a number
    if isinstance(right, list):
        widest = max(len(str(x)) for x in right)
        spec |= {"spaces": len(right) + 2, "width": widest, "per": 1}
        r = Response("list", "list", _shown(right), cells=0, misconceptions=mistakes)
        stem = f"{sentence} {SPACES}"
    else:
        widest = max([right, *(w for w in wrong.values() if isinstance(w, int))])
        # a story prints whole above its answer's row (`box`: "□ pencils"); a sentence is the row its box stands in
        label, stem = (box, f"{ask} {sentence}".strip()) if box else (sentence, ask)
        r = Response("ans", "digits", str(right), cells=cells(widest), misconceptions=mistakes, label=label)
    return item(
        kind["code"], rung, signal, "card", stem, spec, [r], working_lines=int(kind.get("working_lines", 2))
    )


def every(kind: dict[str, Any], rule: dict[str, Any], rung: str, signal: str) -> list[Item]:
    """Every different question this kind makes at this level, once each. ValueError where the kind cannot be drawn
    at it (`problems`)."""
    if why := problems(kind, rule):
        raise ValueError("; ".join(why))
    return [make(kind, rule, nums, rung, signal) for _, nums in _listed(_key(kind, rule))]


def draw(kind: dict[str, Any], rule: dict[str, Any], rng: random.Random, rung: str, signal: str) -> Item:
    """One question of this kind at this level, any of those it can make alike."""
    listed = _listed(_key(kind, rule))
    if not listed:
        raise RuntimeError(f"{kind['code']}: the level's numbers make nothing")
    return make(kind, rule, rng.choice(listed)[1], rung, signal)


def sentence(it: Item | dict[str, Any]) -> str:
    """The words a question of a kind prints: its sentence, as its spec keeps it."""
    sp = it.spec if isinstance(it, Item) else it["spec"]
    return str(sp["text"])


def find(kind: dict[str, Any], rule: dict[str, Any], text: str) -> Numbers | None:
    """The numbers that print `text` at this level — a question, or an educator's example — or None where none do."""
    if problems(kind, rule):
        return None
    return _index(kind, rule).get(_plain(text))


def answer_for(kind: dict[str, Any], rule: dict[str, Any], text: str) -> str | None:
    """The answer the kind works for these printed words at this level, as it would be keyed; None where no numbers the
    level allows print them."""
    nums = find(kind, rule, text)
    return None if nums is None else str(make(kind, rule, nums, "R0", "Conceptual").responses[0].answer)


def belongs(kind: dict[str, Any], rule: dict[str, Any], it: Item | dict[str, Any]) -> list[str]:
    """Why a question is not this kind's at this level, as the kind and level now stand: its words printed by no
    numbers the level allows, or its answer or a mistake keyed otherwise than the formulas work them. Empty when it is.
    Read from the question as stored (an `Item`, or a bank row's `spec` and `responses`)."""
    d = it.to_dict() if isinstance(it, Item) else it
    text = sentence(d)
    nums = find(kind, rule, text)
    if nums is None:
        return [f"{text!r} is not one {kind['code']} makes at this level"]
    made = make(kind, rule, nums, "R0", "Conceptual")
    (want,) = made.responses
    (got,) = cast(list[dict[str, Any]], d["responses"])
    out: list[str] = []
    if str(got["answer"]) != str(want.answer):
        out.append(f"{text!r}: keyed {got['answer']}, the formula works {want.answer}")
    if dict(got.get("misconceptions") or {}) != want.misconceptions:
        out.append(f"{text!r}: its mistakes are keyed otherwise than its kind now names them")
    return out


def level(rng: random.Random, rung: str, signal: str, check: dict[str, Any]) -> Item:
    """One question of the level (`bands.NATIVE_GENERATORS["card"]`): its kinds, resolved by the bank into the rule
    (`check["kinds"]`), each drawn as often as it can make questions, so a level's mix follows what each kind holds."""
    kinds = [k for k in check["kinds"] if count(k, check)]
    if not kinds:
        raise RuntimeError("the level's kinds make nothing")
    k = rng.choices(kinds, weights=[count(k, check) for k in kinds])[0]
    return draw(k, check, rng, rung, signal)
