"""The tables' and the tens' kinds an Advance asks for, × and ÷ (goals/md3b1-facts-advance.yaml): a fact family, the
table backwards through its fact, a fact from a known fact, a fact scaled by ten and the cost of one, and the mistakes a
missing factor or divisor names. Each is built on the two numbers its case draws (`draw._pair`), as a straight
question's are, so a tables level's are table facts and the tens level's round numbers; a kind that drew its own
numbers almost never landed on a tables level. Deterministic given an RNG; pure: no I/O.

A box whose operation is not its question's names no "wrong operation" (M_WRONG_OP): a mistake is named by its
question's operation (`core/mistake_names.py`), and in a × fact family's division that name would say "added instead
of multiplying" of a child who multiplied instead of dividing."""

import random
from collections.abc import Callable
from typing import Any, cast

from . import div_mistakes as DM
from . import misconceptions as M
from . import operations as O
from . import words as W
from .items import Item, Response, cells, item

POWERS = (10, 100, 1000)
Build = Callable[[random.Random, int, int, str, dict[str, Any]], Item]


def _kept(mis: dict[str, int], right: int) -> dict[str, int]:
    return {k: v for k, v in mis.items() if v != right and v >= 0}


def _other_op(mis: dict[str, int]) -> dict[str, int]:
    """A box worked in the other operation from its question's: every mistake but the one named by the operation."""
    return {k: v for k, v in mis.items() if k != "M_WRONG_OP"}


def missing_mistakes(op: str, a: int, b: int, hidden: str) -> dict[str, int]:
    """What a child writes in the box of a × or ÷ missing number (a op b, the box hiding `a`, `b` or `both` of a
    square), as + and − name theirs (`verify._missing_distractors`). × read as + (8 × □ = 72 → 64) and the table one
    row out (→ 8); a zero too few where the box is 10, 100 or 1000 and no table fact (45 × □ = 4500 → 10); a square's
    row out and its two numbers added (□ × □ = 64 → 32). ÷ read as −, the divisor taken away once (□ ÷ 4 = 7 → 11,
    56 ÷ □ = 8 → 48), and the two numbers multiplied where the divisor is the box (→ 448)."""
    if op == "×":
        c = a * b
        if hidden == "both":
            return _kept({"M_MUL_ROW_OUT": a - 1} | ({"M_WRONG_OP": c // 2} if c % 2 == 0 else {}), a)
        boxed, known = (a, b) if hidden == "a" else (b, a)
        if boxed in POWERS and not (boxed <= 12 and known <= 12):
            return _kept({"M_TENS_ZERO_DROPPED": boxed // 10, "M_WRONG_OP": c - known}, boxed)
        return _kept({"M_WRONG_OP": c - known, "M_MUL_ROW_OUT": boxed - 1}, boxed)
    q = a // b
    if hidden == "a":
        return _kept({"M_DIV_SUBTRACTED": q + b}, a)
    return _kept({"M_DIV_SUBTRACTED": a - q, "M_WRONG_OP": a * q}, b)


def factor_missing(alt: dict[str, Any]) -> bool:
    """Whether a × missing number is about the place-value factor (Q14: 45 × □ = 4500), so its box hides 10, 100 or
    1000 and never the other number."""
    want = alt.get("place_value_factor")
    values = cast(list[Any], want) if isinstance(want, list) else [want]
    return alt.get("operation") == "MUL" and bool(values) and set(values) <= {"X10", "X100", "X1000"}


def boxed_factor(a: int, b: int, hidden: str) -> tuple[int, int]:
    """The two numbers in the order that puts 10, 100 or 1000 where the box is; RuntimeError where neither is one."""
    if (a, b)[hidden == "b"] in POWERS:
        return a, b
    if (b, a)[hidden == "b"] in POWERS:
        return b, a
    raise RuntimeError("no power of ten to hide: draw again")


def family(rng: random.Random, a: int, b: int, rung: str, alt: dict[str, Any]) -> Item:
    """4 × 7 = 28 gives 7 × 4 = □, 28 ÷ 4 = □ and 28 ÷ 7 = □ (§7, Y09), as 7 + 5 = 12 gives its three
    (`equality.fact_family`); each box keyed as the same sum asked the usual way."""
    if a == b:
        raise RuntimeError("a number times itself has two facts, not four: draw again")
    c = a * b
    parts = [
        (f"{b} × {a} = □", c, M.predict("×", b, a)),
        (f"{c} ÷ {a} = □", b, _other_op(DM.in_box(c, a, 0))),
        (f"{c} ÷ {b} = □", a, _other_op(DM.in_box(c, b, 0))),
    ]
    rs = [
        Response(f"f{i + 1}", "digits", str(ans), cells=cells(c), label=text, misconceptions=_kept(mis, ans))
        for i, (text, ans, mis) in enumerate(parts)
    ]
    given = f"{a} × {b} = {c}"
    spec = dict(
        given=given,
        facts=[t for t, _, _ in parts],
        shape="FROM_MULTIPLICATION",
        a=a,
        b=b,
        op="×",
        ops=["×", "÷"],
    )
    stem = f"{given}. Use it to finish these facts."
    return item("FACTS", rung, "Conceptual", "fact_family", stem, spec, rs, working_lines=0)


def backwards(rng: random.Random, a: int, b: int, rung: str, alt: dict[str, Any]) -> Item:
    """42 ÷ 6 = □ because 6 × □ = 42 (G20): a table fact read backwards, answered by dividing and again by its fact."""
    if b == 0 or a % b:
        raise RuntimeError("the table backwards is an exact division: draw again")
    q = a // b
    rs = [
        Response(
            "ans",
            "digits",
            str(q),
            cells=cells(a),
            label=f"{a} ÷ {b} = □",
            misconceptions=_kept(DM.in_box(a, b, 0), q),
        ),
        Response(
            "fact",
            "digits",
            str(q),
            cells=cells(a),
            label=f"{b} × □ = {a}",
            misconceptions=_other_op(missing_mistakes("×", b, q, "b")),
        ),
    ]
    spec = dict(a=a, b=b, op="÷", shape="TABLE_BACKWARDS", facts=[r.label for r in rs], ops=["÷", "×"])
    stem = "Divide, and write the times-table fact that gives the answer."
    return item("CHECK.TABLE", rung, "Conceptual", "inverse_check", stem, spec, rs, working_lines=1)


def derived(rng: random.Random, a: int, b: int, rung: str, alt: dict[str, Any]) -> Item:
    """7 × 8 = 56, so 7 × 9 = □ (H08): the row above given, the fact asked; stopping at it is the table one row out."""
    if min(a, b) < 2:
        raise RuntimeError("a fact from the row above needs a row above it: draw again")
    known = a * (b - 1)
    r = Response(
        "ans",
        "digits",
        str(a * b),
        cells=cells(a * b),
        label=f"{a} × {b} =",
        misconceptions=_kept(M.predict("×", a, b) | {"M_MUL_ROW_OUT": known}, a * b),
    )
    stem = f"{a} × {b - 1} = {known}. Use it to work out {a} × {b}."
    spec = {"a": a, "b": b, "op": "×", "strategy": "FACT_DERIVED"}
    return item("EFFICIENT", rung, "Conceptual", "efficient_method", stem, spec, [r], working_lines=1)


def _scaled_pair(a: int, b: int) -> tuple[int, int]:
    """(table number, other) for a round number whose zeros leave a table number and a table number beside it (60 and
    7: 6 and 7); RuntimeError for any other pair (45 × 100 has no fact under its zeros)."""
    for x, y in ((a, b), (b, a)):
        f = x
        while f and f % 10 == 0:
            f //= 10
        if x != f and 2 <= f <= 12 and 2 <= y <= 12 and 10 not in (f, y):
            return f, y
    raise RuntimeError("no table fact under the zeros: draw again")


def scaled(rng: random.Random, a: int, b: int, rung: str, alt: dict[str, Any]) -> Item:
    """6 × 7 = 42, so 60 × 7 = □ and 600 × 7 = □ (H10): the fact given, its round number ten and a hundred times its
    table number, each box one zero more."""
    f, y = _scaled_pair(a, b)
    rs = [
        Response(
            rid,
            "digits",
            str(x * y),
            cells=cells(f * 100 * y),
            label=f"{x} × {y} =",
            misconceptions=_kept(M.predict("×", x, y), x * y),
        )
        for rid, x in (("ans", f * 10), ("more", f * 100))
    ]
    stem = f"{f} × {y} = {f * y}. Use it to work out these."
    spec = {"a": f * 10, "b": y, "op": "×", "strategy": "SCALED_FACT"}
    return item("EFFICIENT", rung, "Conceptual", "efficient_method", stem, spec, rs, working_lines=1)


def story(rng: random.Random, a: int, b: int, rung: str, alt: dict[str, Any]) -> Item:
    """A story that divides (B07: 8 pencils cost ₹48. What does one cost?), its words a template row of its shape and
    its numbers the case's own, an exact division."""
    shape = alt.get("structure")
    pool = W.templates("word_1step", "÷", shape if isinstance(shape, str) else None)
    if not pool:
        raise O.CannotMake(f"no one-step story divides for shape {shape!r}")
    if b == 0 or a % b:
        raise RuntimeError("the story's division leaves something over: draw again")
    tpl = rng.choice(pool)
    n, n2 = rng.sample(W.NAMES, 2)
    q = a // b
    r = Response(
        "ans", "digits", str(q), cells=cells(a), misconceptions=W.added_as(tpl, _kept(DM.in_box(a, b, 0), q))
    )
    stem = tpl["text"].format(a=a, b=b, n=n, n2=n2)
    return item(
        "WP1", rung, "Application", "word_1step", stem, W.story_spec(tpl, a=a, b=b), [r], working_lines=3
    )


BUILT: dict[tuple[str, str, str | None], Build] = {
    ("fact_family", "MUL", "FROM_MULTIPLICATION"): family,
    ("inverse_check", "DIV", "TABLE_BACKWARDS"): backwards,
    ("efficient_method", "MUL", "FACT_DERIVED"): derived,
    ("efficient_method", "MUL", "SCALED_FACT"): scaled,
    ("word_1step", "DIV", None): story,
}


def builder(alt: dict[str, Any], fmt: str) -> Build | None:
    """The kind a case is built as on its own two numbers, or None for a kind that draws its own (`draw_native`)."""
    op = alt.get("operation")
    if not isinstance(op, str):
        return None
    what = next((alt[k] for k in ("shape", "strategy") if isinstance(alt.get(k), str)), None)
    return BUILT.get((fmt, op, what)) or BUILT.get((fmt, op, None))
