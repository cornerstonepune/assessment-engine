"""Read back a dev-set run of the mapping agents from the replies flow_run kept (goals/m1-11d-map-replay.yaml).

A paid reply is kept on its flow_run row (M1-11c). The proposer and the code around it are deterministic given those
replies, so asking the same questions again, answered from the rows, rebuilds every decision the run made: the
confidence, the checker's verdict and why, where each proposal went. No model is called and nothing is written. What
this adds is the question the score alone cannot answer: for each activity, what was proposed against what people
linked, and why a proposal did not pass on its own.
"""

import math
from collections import Counter, deque
from collections.abc import Sequence
from datetime import datetime, timedelta

from engine.adapters import llm, llm_budget
from engine.core import db
from engine.w1_bank.map_agents import PROPOSE, VALIDATE, Ask, Proposal, Reply
from engine.w1_bank.map_probe import LABEL as PROBE

Call = tuple[datetime, str, str, str, Reply, str]  # (when, purpose, about, outcome, reply, reason)


def last_run(calls: Sequence[Call], gap_minutes: float) -> list[Call]:
    """The calls of the latest run: those after the last pause longer than `gap_minutes` between two calls."""
    ordered = sorted(calls, key=lambda c: c[0])
    start = 0
    for i in range(1, len(ordered)):
        if ordered[i][0] - ordered[i - 1][0] > timedelta(minutes=gap_minutes):
            start = i
    return ordered[start:]


def replaying(
    calls: Sequence[Call], shown: dict[str, frozenset[str]] | None = None
) -> tuple[Ask, dict[str, deque[Call]]]:
    """An Ask that answers each question with the next stored reply for that prompt, in the order they were paid for.
    A stored reply that names the activity it was for must meet that activity, or the run is not the one replayed.
    `shown`, when given, is filled with the skills of the examples the proposer was shown for each activity."""
    queues: dict[str, deque[Call]] = {PROPOSE: deque(), VALIDATE: deque()}
    for c in calls:
        queues.setdefault(c[1], deque()).append(c)

    def ask(purpose: str, about: str, variables: dict[str, object]) -> Reply:
        q = queues.get(purpose)
        if not q:
            raise llm.LLMError(f"the stored run has no more {purpose} replies (asked about {about})")
        if shown is not None and purpose == PROPOSE:
            shown[about] = _example_skills(variables)
        _, _, was, outcome, reply, reason = q.popleft()
        if was and was != about:
            raise llm.LLMError(
                f"the stored {purpose} reply was for {was}, but {about} is next: not the same run"
            )
        if outcome == "refused":
            raise llm.LLMSchemaError(reason)
        return reply

    return ask, queues


def _example_skills(variables: dict[str, object]) -> frozenset[str]:
    out: set[str] = set()
    raw = variables.get("examples")
    for ex in raw if isinstance(raw, list) else []:
        skills = ex.get("skills") if isinstance(ex, dict) else None
        out |= {str(k) for k in skills} if isinstance(skills, list) else set()
    return frozenset(out)


def family(skill: str) -> str:
    """A skill id's strand and family ('NUM.CNT' of 'NUM.CNT.01'): the ids are issued that way (the registry)."""
    return ".".join(skill.split(".")[:2])


def wrong_how(proposed: frozenset[str], gold: frozenset[str]) -> str:
    """Why a proposal is not within what people linked."""
    if not proposed:
        return "no skill proposed"
    if proposed & gold:
        return "adds a skill people did not link"
    if {family(s) for s in proposed} & {family(s) for s in gold}:
        return "a neighbouring skill of the same family"
    return "a skill of another family"


def held_back_why(p: Proposal, min_confidence: float) -> str:
    """The first reason, in the order the decision takes them, that a proposal went to a person or was rejected."""
    if p.status == "rejected":
        return "rejected: " + ("; ".join(p.problems) or p.reason)
    if not p.proposal.get("skills"):
        return "no skill proposed"
    if p.verdict != "agree":
        return "the checker disagreed" if p.verdict else "the checker was not heard"
    if p.confidence < min_confidence:
        return "confidence under the bar"
    return "audit sample" if p.reason == "audit sample" else "other"


def explain(made: Sequence[Proposal], gold: dict[str, frozenset[str]], min_confidence: float) -> dict:
    """Each skill proposal against what people linked, with the counts by cause."""
    rows, passed_wrong, held = [], Counter(), Counter()
    for p in sorted(made, key=lambda p: p.subject_code):
        raw = p.proposal.get("skills")
        proposed = frozenset(str(s) for s in raw) if isinstance(raw, list) else frozenset()
        g = gold.get(p.subject_code, frozenset())
        right = bool(proposed) and proposed <= g
        if p.status == "auto_passed":
            how = "right" if right else wrong_how(proposed, g)
            passed_wrong[how] += how != "right"
            cause = how
        else:
            cause = held_back_why(p, min_confidence)
            held[f"{cause}, " + ("would have been right" if right else "would not have been")] += 1
        rows.append(
            {
                "activity": p.subject_code,
                "status": p.status,
                "confidence": p.confidence,
                "proposed": sorted(proposed),
                "gold": sorted(g),
                "verdict": p.verdict,
                "cause": cause,
                "why": p.reason[:200],
            }
        )
    return {"rows": rows, "passed_wrong": +passed_wrong, "held_back": dict(held)}


def stored(conn: db.Conn, stage: str = "dev_eval") -> list[Call]:
    """Every kept reply of the two mapping prompts in a stage, with what it was for when the row says. A probe's call
    (map_probe) is not part of any run and is left out."""
    rows = conn.execute(
        "select started_at, flow, coalesce(request->>'about', '') as about, result->>'outcome' as outcome,"
        " result->'reply' as reply, coalesce(result->>'reason', '') as reason from flow_run"
        " where flow = any(%s) and trigger = %s and result ? 'outcome' and coalesce(request->>'about', '') not like %s"
        " order by started_at",
        ([PROPOSE, VALIDATE], llm_budget.trigger_for(stage), PROBE + "%"),
    ).fetchall()
    return [
        (r["started_at"], r["flow"], r["about"], r["outcome"], r["reply"] or {}, r["reason"]) for r in rows
    ]


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """The Wilson interval (95% by default) of k out of n: how far a share can be trusted, a small n widening it."""
    if not n:
        return 0.0, 0.0
    p, d = k / n, 1 + z * z / n
    centre, spread = p + z * z / (2 * n), z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - spread) / d, min(1.0, (centre + spread) / d)


def partial(
    made: Sequence[Proposal], gold: dict[str, frozenset[str]], min_confidence: float, held_total: int
) -> dict:
    """A run that may be cut short, in counts only (the log is public): how many of the held-out activities it reached,
    how the proposals went, the precision of those that passed on their own and the share that did, each with its
    interval, and the causes. No activity is named."""
    got = explain(made, gold, min_confidence)
    passed = [r for r in got["rows"] if r["status"] == "auto_passed"]
    right = sum(1 for r in passed if r["proposed"] and set(r["proposed"]) <= set(r["gold"]))
    n = len(got["rows"])
    return {
        "held_total": held_total,
        "answered": n,
        "unanswered": held_total - n,
        "passed": len(passed),
        "passed_right": right,
        "held_to_a_person": sum(1 for r in got["rows"] if r["status"] == "needs_person"),
        "rejected": sum(1 for r in got["rows"] if r["status"] == "rejected"),
        "precision_of_passed": round(right / len(passed), 3) if passed else 0.0,
        "precision_interval": [round(x, 3) for x in wilson(right, len(passed))],
        "share_passed": round(len(passed) / n, 3) if n else 0.0,
        "share_interval": [round(x, 3) for x in wilson(len(passed), n)],
        "passed_wrong": dict(got["passed_wrong"]),
        "held_back": got["held_back"],
    }


def sweep(made: Sequence[Proposal], gold: dict[str, frozenset[str]]) -> dict:
    """Precision against what people linked, for every proposal by its confidence and by the checker's verdict, and for
    each confidence bar that could be set. A proposal could pass on its own when code found nothing wrong, it names a
    skill and the checker agreed; the audit sample (a share of those, taken whatever they say) is left out."""

    def right(p: Proposal) -> bool:
        raw = p.proposal.get("skills")
        proposed = frozenset(str(s) for s in raw) if isinstance(raw, list) else frozenset()
        return bool(proposed) and proposed <= gold.get(p.subject_code, frozenset())

    def tally(key) -> dict[str, list[int]]:
        out: dict[str, list[int]] = {}
        for p in made:
            n = out.setdefault(str(key(p)), [0, 0])
            n[0] += 1
            n[1] += right(p)
        return dict(sorted(out.items()))

    eligible = [p for p in made if not p.problems and p.proposal.get("skills") and p.verdict == "agree"]
    bars = sorted({0.0, *(round(p.confidence, 3) for p in eligible)})
    table = {}
    for bar in bars:
        passing = [p for p in eligible if p.confidence >= bar]
        ok = sum(right(p) for p in passing)
        table[str(bar)] = {
            "passes": len(passing),
            "right": ok,
            "precision": round(ok / len(passing), 3) if passing else 0.0,
            "share": round(len(passing) / len(made), 3) if made else 0.0,
        }
    return {
        "by_confidence": tally(lambda p: round(p.confidence, 3)),
        "by_verdict": tally(lambda p: p.verdict or "none"),
        "if_confidence_at_least": table,
    }


def _proposed(p: Proposal) -> list[str]:
    raw = p.proposal.get("skills")
    return [str(k) for k in raw] if isinstance(raw, list) else []


def skill_split(
    made: Sequence[Proposal], gold: dict[str, frozenset[str]], shown: dict[str, frozenset[str]]
) -> dict:
    """Each proposed skill on its own against what people linked: by its place in the list, and by whether the proposer
    had been shown it in an example (a signal code can read, which the model's own confidence is not). Then what would
    follow from judging skills apart: an activity passing when every skill it names was in the examples, and a proposal
    split into the skills that pass and the ones offered to a person to add. Replay only: nothing here was run."""
    rows = [
        (p, k, k in gold.get(p.subject_code, frozenset()), i)
        for p in made
        for i, k in enumerate(_proposed(p), 1)
    ]
    rank: dict[str, list[int]] = {}
    seen: dict[str, list[int]] = {"in the examples": [0, 0], "not in the examples": [0, 0]}
    for p, k, ok, i in rows:
        for tally, key in (
            (rank, str(i)),
            (
                seen,
                "in the examples" if k in shown.get(p.subject_code, frozenset()) else "not in the examples",
            ),
        ):
            n = tally.setdefault(key, [0, 0])
            n[0] += 1
            n[1] += ok
    clean = [p for p in made if not p.problems and _proposed(p)]

    def in_examples(p: Proposal) -> bool:
        return all(k in shown.get(p.subject_code, frozenset()) for k in _proposed(p))

    def right(p: Proposal) -> bool:
        return set(_proposed(p)) <= gold.get(p.subject_code, frozenset())

    def table(pool: list[Proposal]) -> dict:
        out = {}
        for bar in sorted({0.0, *(round(p.confidence, 3) for p in pool)}):
            passing = [p for p in pool if p.confidence >= bar]
            ok = sum(right(p) for p in passing)
            out[str(bar)] = {
                "passes": len(passing),
                "right": ok,
                "precision": round(ok / len(passing), 3) if passing else 0.0,
                "share": round(len(passing) / len(made), 3) if made else 0.0,
            }
        return out

    split = {}
    for bar in sorted({0.0, *(round(p.confidence, 3) for p in made)}):
        auto = [
            (p, k)
            for p in clean
            if p.confidence >= bar
            for k in _proposed(p)
            if k in shown.get(p.subject_code, frozenset())
        ]
        kept = {(p.subject_code, k) for p, k in auto}
        offered = [(p, k) for p in clean for k in _proposed(p) if (p.subject_code, k) not in kept]
        ok = sum(k in gold.get(p.subject_code, frozenset()) for p, k in auto)
        split[str(bar)] = {
            "auto_skills": len(auto),
            "auto_right": ok,
            "auto_precision": round(ok / len(auto), 3) if auto else 0.0,
            "offered": len(offered),
            "offered_in_gold": sum(k in gold.get(p.subject_code, frozenset()) for p, k in offered),
        }
    return {
        "skills": {"proposed": len(rows), "in_gold": sum(ok for _, _, ok, _ in rows)},
        "by_rank": dict(sorted(rank.items())),
        "by_example": seen,
        "if_every_skill_was_in_the_examples": table([p for p in clean if in_examples(p)]),
        "if_every_skill_was_in_the_examples_and_the_checker_agreed": table(
            [p for p in clean if in_examples(p) and p.verdict == "agree"]
        ),
        "split_by_the_examples": split,
    }
