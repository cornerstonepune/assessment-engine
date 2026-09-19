"""Which evaluator judges an answer is decided by the question's own `eval_type` (ADR 0012).

Four kinds of assessable thing, differing in how the question is produced and — the part that
matters here — how a wrong answer is recognised:

    computable      the answer is computed, and each named mistake's wrong answer is computed
                    with it. A wrong answer is looked up in that table.
    closed_set      the answer comes from a table of content (capitals, dates, vocabulary);
                    wrong options are its confusable neighbours.
    rule_governed   a checker decides, and the rule violations are themselves the mistake list.
    open_response   no enumerable answer set. A person or a model judges it against a rubric,
                    and its mistakes are discovered by clustering real answers, never predicted.

Only `computable` and `open_response` have evaluators today. The other two are named, and refuse
loudly — a question the engine cannot judge must never be quietly marked, because a wrong mark
reaches a child's record as a fact about that child.
"""

import re

EVAL_TYPES = ("computable", "closed_set", "rule_governed", "open_response")


def _computable(response, written):
    """Exact answer, or within tolerance for an estimate; a wrong answer is named if the
    misconception table knows it and left unnamed if it does not (never forced to fit)."""
    if response.get("kind") == "tick":
        if not written:
            return "blank", []
        return ("correct" if written == response.get("answer") else "wrong"), []
    if response.get("kind") == "text":
        return "needs_teacher", []

    written = (written or "").strip()
    if not written:
        return "blank", []
    if not re.fullmatch(r"-?\d+", written):
        return "unreadable", []

    n, want = int(written), response.get("answer")
    if want is None:
        return "needs_teacher", []
    want = int(want)
    tolerance = response.get("tolerance")
    if n == want or (tolerance and abs(n - want) <= tolerance):
        return "correct", []
    named = sorted(code for code, wrong in (response.get("misconceptions") or {}).items() if int(wrong) == n)
    return "wrong", named


def _open_response(response, written):
    """Never auto-marked. The rubric and the child's words go to a person; `read_correction` and
    the gold set are how this kind's mistake vocabulary is learned, not a predictor table."""
    if not (written or "").strip():
        return "blank", []
    return "needs_teacher", []


def _unbuilt(name):
    def refuse(response, written):
        raise NotImplementedError(
            f"no evaluator for eval_type {name!r} yet — a question of this kind must not be"
            f" marked by the computable evaluator; build {name}'s evaluator first (ADR 0012)"
        )

    return refuse


EVALUATORS = {
    "computable": _computable,
    "open_response": _open_response,
    "closed_set": _unbuilt("closed_set"),
    "rule_governed": _unbuilt("rule_governed"),
}


def judge(eval_type, response, written):
    """→ (status, misconception codes). Status is one of correct | wrong | blank | unreadable |
    needs_teacher — blank, wrong and wrong-with-working stay distinct signals (CLAUDE.md rule 5)."""
    if eval_type not in EVALUATORS:
        raise ValueError(f"unknown eval_type {eval_type!r}; expected one of {', '.join(EVAL_TYPES)}")
    return EVALUATORS[eval_type](response, written)
