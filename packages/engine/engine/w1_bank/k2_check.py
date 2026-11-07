"""The maker–checker of K2 page drafting (goals/m1-12a-page-format.yaml, task M1-12a).

A maker drafts; code checks the format and the materials (k2_format); a checker, a stronger model with a different
prompt, is shown the school's own words and the draft and names each fault with a reason; the maker revises the parts at
fault ONCE, with those reasons; the revised page is checked once more. A second fault is not sent back again: the page
keeps the checker's reasons for a person. Nothing here knows a model or a database: `ask_maker(keys, revise)` and
`ask_checker(keys, drafts)` are whatever answers (the adapter in a run, a stand-in in a test), and money running out is
`batch.Stop`.
"""

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

from engine.w1_bank import k2_batch as batch
from engine.w1_bank.k2_format import Judge
from engine.w1_bank.k2_gaps import PAGE_PARTS
from engine.w1_bank.map_agents import Proposal

DRAFT, CHECK, CHECK_B, SPLIT = "k2_page_draft", "k2_page_check", "k2_page_check_b", "k2_materials_split"
VERSIONS = {
    DRAFT: 4,
    CHECK: 1,
    CHECK_B: 1,
    SPLIT: 3,
}  # the prompt rows a run asks for; draft v4 is lists and slips (M1-12a)
Fault = dict[str, str]
Verdict = tuple[str, list[Fault]]
AskMaker = Callable[[list[str], dict[str, tuple[dict, list[Fault]]] | None], object]
AskChecker = Callable[[list[str], dict[str, dict]], object]


@dataclass
class Result:
    parts: dict[str, dict] = field(default_factory=dict)  # page → its drafted parts, after any revision
    verdicts: dict[str, Verdict] = field(
        default_factory=dict
    )  # page → the checker's last verdict and its faults
    history: dict[str, list[dict]] = field(default_factory=dict)  # page → each round: who said what
    shadow: dict[str, dict[str, Verdict]] = field(
        default_factory=dict
    )  # other checkers → page → what they said
    left: dict[str, str] = field(default_factory=dict)  # page → why it has no draft
    stopped: str = ""
    faults: Counter[str] = field(default_factory=Counter)  # rule broken → times, over every ask of the maker
    stuck: int = 0  # pages not asked a third time: the same rule twice


def judge_checks(got: object, keys: list[str]) -> tuple[dict[str, Verdict], dict[str, str]]:
    """The checker's reply read item by item. A disagree always says why; an agree that names a fault is a disagree."""
    seen, twice = batch._by_key(got, set(keys))
    good: dict[str, Verdict] = {}
    bad: dict[str, str] = {}
    for key in keys:
        it = seen.get(key)
        if key in twice:
            bad[key] = "answered twice"
        elif it is None:
            bad[key] = "missing from the reply"
        elif it.get("verdict") not in ("agree", "disagree"):
            bad[key] = "verdict is not agree or disagree"
        else:
            listed = it.get("faults")
            faults = [
                {"part": f["part"], "reason": f["reason"].strip()}
                for f in (listed if isinstance(listed, list) else [])
                if isinstance(f, dict)
                and f.get("part") in PAGE_PARTS
                and isinstance(f.get("reason"), str)
                and f["reason"].strip()
            ]
            if it["verdict"] == "agree" and not faults:
                good[key] = ("agree", [])
            else:
                faults = faults or [{"part": "steps", "reason": "the checker disagreed without saying why"}]
                good[key] = ("disagree", faults)
    return good, bad


def parts_at_fault(faults: list[Fault], asked: list[str]) -> list[str]:
    """The asked parts the checker named; if it named none of them, all of them."""
    named = [p for p in asked if p in {f["part"] for f in faults}]
    return named or list(asked)


def _check(
    keys: list[str],
    drafts: dict[str, dict],
    ask: AskChecker,
    size: int,
    rounds: int,
    verdicts: dict[str, Verdict],
) -> None:
    """Fills `verdicts` as they come, so a run stopped half way still holds the ones it got."""
    pending = list(keys)
    for _ in range(rounds + 1):
        for i in range(0, len(pending), size):
            batch_keys = pending[i : i + size]
            got, _bad = judge_checks(batch.items(ask(batch_keys, drafts), "verdicts"), batch_keys)
            verdicts |= got
        pending = [k for k in pending if k not in verdicts]
        if not pending:
            break


def run(
    want: dict[str, list[str]],
    ask_maker: AskMaker,
    ask_checker: AskChecker,
    judge: Judge,
    size: int,
    rounds: int,
    shadows: dict[str, AskChecker] | None = None,
) -> Result:
    """`shadows` are other checkers shown the same first drafts: what they say is kept and compared, and never decides
    whether a page is revised (only the checker that drives does)."""
    res = Result()
    done = batch.run(want, lambda keys: ask_maker(keys, None), size, rounds, judge=judge)
    res.left, res.stopped, res.parts = dict(done.bad), done.stopped, dict(done.good)
    res.faults, res.stuck = done.faults, len(done.stuck)
    if res.stopped:
        return res
    try:
        _check(list(res.parts), res.parts, ask_checker, size, rounds, res.verdicts)
    except batch.Stop as e:
        res.stopped = str(e)
    res.history = {k: [{"round": 1, "verdict": v, "faults": f}] for k, (v, f) in res.verdicts.items()}
    for name, ask_shadow in (shadows or {}).items() if not res.stopped else []:
        res.shadow[name] = {}
        try:
            _check(list(res.parts), res.parts, ask_shadow, size, rounds, res.shadow[name])
        except batch.Stop as e:
            res.stopped = str(e)
    if res.stopped:
        return res
    faulty = {k: f for k, (v, f) in res.verdicts.items() if v != "agree"}
    if faulty:
        _revise(res, want, faulty, ask_maker, ask_checker, judge, size, rounds)
    return res


def _revise(
    res: Result,
    want: dict[str, list[str]],
    faulty: dict[str, list[Fault]],
    ask_maker: AskMaker,
    ask_checker: AskChecker,
    judge: Judge,
    size: int,
    rounds: int,
) -> None:
    asked = {k: parts_at_fault(f, want[k]) for k, f in faulty.items()}
    sent = {k: (res.parts[k], faulty[k]) for k in asked}
    revision = batch.run(
        asked, lambda keys: ask_maker(keys, {k: sent[k] for k in keys}), size, 0, judge=judge
    )
    for key, why in revision.bad.items():
        res.history[key].append({"round": 2, "note": f"revision refused: {why}"})
    if revision.stopped:
        res.stopped = revision.stopped
        return
    for key, parts in revision.good.items():
        res.parts[key] = res.parts[key] | parts
    again: dict[str, Verdict] = {}
    try:
        _check(
            list(revision.good), {k: res.parts[k] for k in revision.good}, ask_checker, size, rounds, again
        )
    except batch.Stop as e:
        res.stopped = str(e)
    for key, (verdict, faults) in again.items():
        res.verdicts[key] = (verdict, faults)
        res.history[key].append({"round": 2, "verdict": verdict, "faults": faults})


def take_kept(reuse: dict[str, dict], keys: list[str]) -> tuple[list[dict], list[str]]:
    """The kept first drafts for these pages, each taken once, and the pages that have none."""
    taken = [reuse.pop(k) for k in keys if k in reuse]
    return taken, [k for k in keys if k not in {i["key"] for i in taken}]


def remember(raw: dict[str, dict], it: dict, revised: bool) -> None:
    """What the maker said of itself: the first draft's words, and after a revision the doubts of both (the least
    confidence, every flag)."""
    key = it["key"]
    if not revised or key not in raw:
        raw[key] = it
        return
    first = raw[key]
    flags = [*(first.get("flags") or []), *(it.get("flags") or [])]
    confidence = [c for c in (first.get("confidence"), it.get("confidence")) if isinstance(c, int | float)]
    raw[key] = first | {"flags": flags, "confidence": min(confidence) if confidence else 0.0}


def proposal(
    key: str,
    parts: dict,
    raw: dict,
    verdict: Verdict | None,
    history: list[dict],
    least: float,
    stopped: bool,
    checks: list[dict] | None = None,
    stage: str = "",
    notes: list[str] | None = None,
    unread: bool = False,
) -> Proposal:
    """`notes` are what the page broke of the style rules that do not hold a page back: they ride on the proposal and its
    reason, and change neither its status nor its confidence. `unread`: it was recorded from a kept draft the checker
    has not read."""
    conf = raw.get("confidence")
    confidence = (
        min(max(float(conf), 0.0), 1.0)
        if isinstance(conf, int | float) and not isinstance(conf, bool)
        else 0.0
    )
    flags = [f for f in raw.get("flags") or [] if isinstance(f, str) and f.strip()]
    said, faults = verdict if verdict else ("", [])
    passed = said == "agree" and confidence >= least and not flags
    if flags:
        reason = "flagged by the drafter: " + "; ".join(flags)
    elif not verdict:
        reason = "not checked: the run stopped" if stopped else "no verdict came back for it"
        reason = "recorded from a kept draft; the checker has not read it" if unread else reason
    elif said != "agree":
        reason = "; ".join(f"{f['part']}: {f['reason']}" for f in faults)
    elif confidence < least:
        reason = f"confidence {confidence:.2f} is below {least:.2f}"
    else:
        reason = "the checker found no fault"
    if notes:
        reason += " | notes: " + "; ".join(notes)
    return Proposal(
        kind="page_part", subject_code=key, proposal={"parts": parts, "flags": flags, "history": history, "checks": checks or [], "stage": stage, "notes": notes or []},
        confidence=confidence, proposer=f"{DRAFT} v{VERSIONS[DRAFT]}", validator=f"{CHECK} v{VERSIONS[CHECK]}",
        problems=[], verdict=said, status="auto_passed" if passed else "needs_person", reason=reason,
    )  # fmt: skip


def said(res: Result, models: dict[str, str], key: str) -> list[dict]:
    """What each checker said of the page, labelled by its prompt and model: the one that drives, then the others."""
    got = ((CHECK, res.verdicts.get(key)), *((p, v.get(key)) for p, v in res.shadow.items()))
    return [
        {"checker": f"{p} v{VERSIONS[p]}", "model": models[p], "verdict": v[0], "faults": v[1]}
        for p, v in got
        if v
    ]


def proposals(
    res: Result,
    raw: dict[str, dict],
    models: dict[str, str],
    least: float,
    stopped: bool,
    stage: str,
    notes: dict[str, list[str]] | None = None,
) -> list[Proposal]:
    """The ledger's proposal for each page the run drafted."""
    return [
        proposal(
            key, parts, raw.get(key, {}), res.verdicts.get(key), res.history.get(key, []), least, stopped,
            said(res, models, key), stage, (notes or {}).get(key),
        )
        for key, parts in res.parts.items()
    ]  # fmt: skip
