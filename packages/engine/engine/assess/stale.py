"""A stored question made by a rule its kind has since corrected (`engine bank recheck`, `w1_bank/cases.py`). It leaves
the bank rather than being changed in place, so a paper already printed with it still reads as it did. Each kind's own
rule is made again from the question's numbers and compared with what was stored. Pure: no I/O."""

from typing import Any, cast

from . import diagnosis as D
from . import division as DV
from . import estimate as E
from . import misconceptions as M
from . import operations as O
from . import words as W
from . import written as WR
from . import written_methods as WM


def key_problems(fmt: str, spec: dict[str, Any], responses: list[dict[str, Any]] | None = None) -> list[str]:
    """Why a stored question is no longer what its kind's rules make: estimates that rounded a 5 down (665 printed as
    660), closest-hundred questions from before the right option's place was drawn, when it was always the middle one, a
    straight sum whose stored wrong answers a predictor has since corrected (`engine bank recheck`'s own test: 68 × 17
    once named "one row out in the table"), a division whose boxes its predictors now key otherwise (`division.boxes`),
    a worked answer that asks the column its mistake always shows in (`diagnosis.asks_where`), a long multiplication
    keyed before its rows added without a carry had a name (`_stale_rows`), a written method whose boxes its rules
    now key otherwise (`_stale_method`), and a division in its layout printed before its exchanges had boxes
    (`_unread_exchanges`). Empty when it is current."""
    stale = (
        _stale_mistakes(fmt, spec, responses)
        + _stale_story(fmt, spec, responses)
        + _stale_rows(fmt, spec, responses)
        + _stale_method(fmt, spec, responses)
    )
    if stale:
        return [f"keyed by a mistake rule since corrected: {', '.join(stale)}"]
    if unread := _unread_exchanges(fmt, spec, responses):
        return [f"printed before its exchanges had boxes: {', '.join(unread)}"]
    if fmt == "estimate_then_calc" and (spec["ra"], spec["rb"]) != E.rounded(spec):
        return [
            f"rounded a 5 down: {spec['a']} {spec['op']} {spec['b']} printed as {spec['ra']}, {spec['rb']}"
        ]
    if fmt == "choose_estimate" and "right" not in spec:
        return ["made when the closest hundred was always the middle option"]
    if (
        fmt == "find_mistake"
        and any(r.get("rid") == "where" for r in responses or [])
        and not D.asks_where(spec)
    ):
        return [f"asks the column {spec['planted']} always shows in"]
    return []


def _stale_mistakes(fmt: str, spec: dict[str, Any], responses: list[dict[str, Any]] | None) -> list[str]:
    """The predicted mistakes a straight sum's stored key names at a value today's predictor no longer gives."""
    if fmt not in ("bare_sum", "column_grid") or not responses or not {"a", "b", "op"} <= spec.keys():
        return []
    # a division's quotient box, its remainder's and its exchanges', each keyed again (ADR 0056, 0063)
    if O.sign(spec["op"]) == "÷":
        now = DV.boxes(spec["a"], spec["b"], "column" if fmt == "column_grid" else "horizontal")
        return _changed({r.rid: r.misconceptions for r in now}, responses)
    table = M.TABLES.get(spec["op"], {})
    ans = next((r for r in responses if r.get("rid") == "ans"), cast(dict[str, Any], {}))
    stored: dict[str, Any] = ans.get("misconceptions") or {}
    now = M.predict(spec["op"], spec["a"], spec["b"]) if table else {}
    return sorted(c for c, v in stored.items() if c in table and now.get(c) != v)


def _unread_exchanges(fmt: str, spec: dict[str, Any], responses: list[dict[str, Any]] | None) -> list[str]:
    """The exchanges a division in its layout writes small that its stored key has no box for: printed before short
    division's exchanges were read (goals/md3d-division-methods.yaml), it cannot read 72 ÷ 4's 3."""
    a, b = spec.get("a"), spec.get("b")
    if (
        fmt != "column_grid"
        or O.sign(spec.get("op")) != "÷"
        or not (isinstance(a, int) and isinstance(b, int))
    ):
        return []
    have = {r.get("rid") for r in responses or []}
    return [r.rid for r in DV.exchanges(a, b) if r.rid not in have]


def _stale_rows(fmt: str, spec: dict[str, Any], responses: list[dict[str, Any]] | None) -> list[str]:
    """A long multiplication whose key cannot name its rows added without a carry (19 × 14 written 166), stored before
    the mistake was predicted on a multiplication (`written_methods.rows_added`, ADR 0055)."""
    a, b = spec.get("a"), spec.get("b")
    if (
        fmt != "column_grid"
        or O.sign(spec.get("op")) != "×"
        or not (isinstance(a, int) and isinstance(b, int))
    ):
        return []
    ans = [r for r in responses or [] if r.get("rid") == "ans"]
    stored: dict[str, Any] = (ans[0].get("misconceptions") or {}) if ans else {}
    rows = WM.rows_added(a, b)
    return sorted(c for c, v in rows.items() if c not in stored and v not in stored.values())


def _stale_method(fmt: str, spec: dict[str, Any], responses: list[dict[str, Any]] | None) -> list[str]:
    """The mistakes a written method's stored boxes name at a value its rules, or the predictors its steps use, no
    longer give, or do not name at all (ADR 0055): made again from its own numbers, every box is keyed as today."""
    if fmt not in WR.KINDS.values() or not responses or not {"a", "b", "method"} <= spec.keys():
        return []
    return _changed(
        {r.rid: r.misconceptions for r in WR.make(spec["method"], spec["a"], spec["b"], "").responses},
        responses,
    )


def _changed(now: dict[str, dict[str, Any]], responses: list[dict[str, Any]]) -> list[str]:
    """The mistakes each stored box names at a value other than its key made again today (`now`) gives, or does not
    name at all."""
    stale: set[str] = set()
    for r in responses:
        old: dict[str, Any] = r.get("misconceptions") or {}
        new: dict[str, Any] = now.get(r.get("rid") or "", {})
        stale |= {c for c in old.keys() | new.keys() if old.get(c) != new.get(c)}
    return sorted(stale)


def _stale_story(fmt: str, spec: dict[str, Any], responses: list[dict[str, Any]] | None) -> list[str]:
    """A story keyed when its other operation was named the wrong operation, before its shape's mistake had a name of
    its own (`words.wrong_op_by_shape`, ADR 0054); or a "times as many" story whose numbers added are its answer (2
    times as many as 2), which could never show that mistake."""
    named = W.wrong_op_by_shape().get(spec.get("structure") or "") if fmt == "word_1step" else None
    ans = [r for r in responses or [] if r.get("rid") == "ans"]
    stored: dict[str, Any] = (ans[0].get("misconceptions") or {}) if ans else {}
    a, b = spec.get("a"), spec.get("b")
    same = spec.get("op") == "×" and isinstance(a, int) and isinstance(b, int) and a + b == a * b
    if named and ("M_WRONG_OP" in stored or same):
        return ["M_WRONG_OP"]
    return []
