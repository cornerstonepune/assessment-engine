"""Read back a dev-set run of the mapping agents from the replies flow_run kept (goals/m1-11d-map-replay.yaml).

A paid reply is kept on its flow_run row (M1-11c). The proposer and the code around it are deterministic given those
replies, so asking the same questions again, answered from the rows, rebuilds every decision the run made: the
confidence, the checker's verdict and why, where each proposal went. No model is called and nothing is written. What
this adds is the question the score alone cannot answer: for each activity, what was proposed against what people
linked, and why a proposal did not pass on its own.
"""

from collections import Counter, deque
from collections.abc import Sequence
from datetime import datetime, timedelta

from engine.adapters import llm, llm_budget
from engine.core import db
from engine.w1_bank.map_agents import PROPOSE, VALIDATE, Ask, Proposal, Reply

Call = tuple[datetime, str, str, str, Reply, str]  # (when, purpose, about, outcome, reply, reason)


def last_run(calls: Sequence[Call], gap_minutes: float) -> list[Call]:
    """The calls of the latest run: those after the last pause longer than `gap_minutes` between two calls."""
    ordered = sorted(calls, key=lambda c: c[0])
    start = 0
    for i in range(1, len(ordered)):
        if ordered[i][0] - ordered[i - 1][0] > timedelta(minutes=gap_minutes):
            start = i
    return ordered[start:]


def replaying(calls: Sequence[Call]) -> tuple[Ask, dict[str, deque[Call]]]:
    """An Ask that answers each question with the next stored reply for that prompt, in the order they were paid for.
    A stored reply that names the activity it was for must meet that activity, or the run is not the one replayed."""
    queues: dict[str, deque[Call]] = {PROPOSE: deque(), VALIDATE: deque()}
    for c in calls:
        queues.setdefault(c[1], deque()).append(c)

    def ask(purpose: str, about: str, variables: dict[str, object]) -> Reply:
        q = queues.get(purpose)
        if not q:
            raise llm.LLMError(f"the stored run has no more {purpose} replies (asked about {about})")
        _, _, was, outcome, reply, reason = q.popleft()
        if was and was != about:
            raise llm.LLMError(
                f"the stored {purpose} reply was for {was}, but {about} is next: not the same run"
            )
        if outcome == "refused":
            raise llm.LLMSchemaError(reason)
        return reply

    return ask, queues


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


def stored(conn: db.Conn) -> list[Call]:
    """Every kept dev-stage reply of the two mapping prompts, with what it was for when the row says."""
    rows = conn.execute(
        "select started_at, flow, coalesce(request->>'about', '') as about, result->>'outcome' as outcome,"
        " result->'reply' as reply, coalesce(result->>'reason', '') as reason from flow_run"
        " where flow = any(%s) and trigger = %s and result ? 'outcome' order by started_at",
        ([PROPOSE, VALIDATE], llm_budget.trigger_for("dev_eval")),
    ).fetchall()
    return [
        (r["started_at"], r["flow"], r["about"], r["outcome"], r["reply"] or {}, r["reason"]) for r in rows
    ]
