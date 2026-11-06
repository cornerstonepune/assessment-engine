"""Read back a draft run from the replies flow_run kept (goals/m1-12d-draft-replay.yaml).

The first dev run saved 1 page of 60: the rest failed the code checks, twice, and nothing said which rule. Every paid
reply is kept on its flow_run row; judging them again with the run's own judge, in the order they were paid for, says
how many pages broke which rule on which ask. No model is called and nothing is written. The report is counts and rule
names and nothing of the school's: the job log is public.
"""

import json
import re
from collections import Counter

import typer

from engine.adapters import llm_budget
from engine.core import db
from engine.w1_bank import k2_batch as batch
from engine.w1_bank import map_replay
from engine.w1_bank.k2_draft import DRAFT, _judge, wanted
from engine.w1_bank.k2_upload import config, curriculum_app

Kept = tuple[str, object]  # (outcome, reply)
UNLISTED = (
    "uses_unlisted",
    "step_word_unlisted",
)  # the two rules that name a thing the page's materials do not
NAMED = (r"^uses '(.*)': not in the school's materials", r"^steps line \d+ uses '([^']*)', which")
SHOWN = 25  # the most distinct words one rule prints


def stored(conn: db.Conn, stage: str, gap_minutes: float) -> list[Kept]:
    """The latest run's kept replies of the page maker in this stage, oldest first: a pause longer than `gap_minutes`
    between two calls ends a run."""
    rows = conn.execute(
        "select started_at, result->>'outcome' as outcome, result->'reply' as reply from flow_run"
        " where flow = %s and trigger = %s and result ? 'outcome' order by started_at",
        (DRAFT, llm_budget.trigger_for(stage)),
    ).fetchall()
    calls: list[map_replay.Call] = [
        (r["started_at"], DRAFT, "", r["outcome"], r["reply"] or {}, "") for r in rows
    ]
    return [(c[3], c[4]) for c in map_replay.last_run(calls, gap_minutes)]


def kind_of(named: str, materials: str) -> str:
    """How a thing a draft names stands to the page's own materials text: no list at all; every word of it listed, either
    all in one piece but not side by side in that order, or spread over several pieces; some words listed; a near
    spelling of a listed word; or unrelated."""
    pieces = [set(t for t in batch._tokens(p) if t.isalpha()) for p in batch.pieces_of(materials)]
    mine = set().union(*pieces)
    toks = [t for t in batch._tokens(re.sub(r"[^A-Za-z ]", " ", named)) if t.isalpha()]
    if not mine:
        return "page_has_no_materials"
    if toks and all(t in mine for t in toks):
        return (
            "one_piece_not_contiguous" if any(all(t in p for t in toks) for p in pieces) else "spans_pieces"
        )
    if any(t in mine for t in toks):
        return "some_words_listed"
    if any(len(t) >= 4 and any(m[:4] == t[:4] for m in mine) for t in toks):
        return "near_spelling"
    return "not_related"


def _printable(word: str) -> bool:
    """A word the log may show: letters only, at most 12 of them, so never a phrase of the school's own text."""
    return word.isascii() and word.isalpha() and len(word) <= 12


def _unlisted(seen: dict[str, dict]) -> dict:
    """Per rule: the plain words that repeat (a word seen once is not printed, and a use is a phrase of the school's own
    text, so for a use only the kind is counted: the log is public) and how each stands to the page's materials."""
    out = {}
    for rule, got in seen.items():
        shown = Counter(
            {
                w: n
                for w, n in got["words"].items()
                if n >= 2 and _printable(w) and rule == "step_word_unlisted"
            }
        )
        out[rule] = {
            "words": dict(shown.most_common(SHOWN)),
            "once": sum(got["words"].values()) - sum(shown.values()),
            "kinds": dict(got["kinds"].most_common()),
        }
    return out


def tally(
    kept: list[Kept], want: dict[str, list[str]], judge, materials: dict[str, str] | None = None
) -> dict:
    """Each kept reply judged again: for the nth time a page was answered, how many pages, how many good, and the rules
    the others broke. A refused reply is one the run took as nothing."""
    seen: Counter[str] = Counter()
    ever_good: set[str] = set()
    asks: dict[int, dict] = {}
    refused = 0
    named: dict[str, dict] = {r: {"words": Counter(), "kinds": Counter()} for r in UNLISTED}
    for outcome, reply in kept:
        keys = [
            k
            for k in dict.fromkeys(
                it["key"] for it in batch.items(reply, "pages") if isinstance(it, dict) and "key" in it
            )
            if k in want
        ]
        if outcome == "refused" or not keys:
            refused += 1
            continue
        pages = batch.items(reply, "pages")  # the list inside the reply, as the run judged it
        good, bad = judge(pages, {k: want[k] for k in keys})
        for k in keys:
            seen[k] += 1
            row = asks.setdefault(seen[k], {"attempt": seen[k], "asked": 0, "good": 0, "faults": Counter()})
            row["asked"] += 1
            if k in good:
                row["good"] += 1
                ever_good.add(k)
            else:
                rule = batch.rule_of(bad.get(k, ""))
                row["faults"][rule] += 1
                what = next((m.group(1) for p in NAMED if (m := re.search(p, bad.get(k, "")))), None)
                if rule in named and what is not None:
                    named[rule]["words"][batch._stem(what.casefold())[:40]] += 1
                    named[rule]["kinds"][kind_of(what, (materials or {}).get(k, ""))] += 1
    return {
        "replies": len(kept),
        "refused": refused,
        "pages_good": len(ever_good),
        "pages_never_good": len(set(seen) - ever_good),
        "unlisted": _unlisted(named),
        "attempts": [{**a, "faults": dict(a["faults"].most_common())} for _, a in sorted(asks.items())],
    }


def kept_drafts(kept: list[Kept], want: dict[str, list[str]], judge) -> dict[str, dict]:
    """For each page, the first answer in the kept replies that the judge accepts (a refused reply is nothing): the first
    draft the maker already wrote and was paid for. A page never answered well has none."""
    out: dict[str, dict] = {}
    for outcome, reply in kept:
        if outcome == "refused":
            continue
        pages = batch.items(reply, "pages")
        items = {it["key"]: it for it in pages if isinstance(it, dict) and it.get("key") in want}
        good, _ = judge(pages, {k: want[k] for k in items})
        out |= {k: it for k, it in items.items() if k in good and k not in out}
    return out


def reusable(
    conn: db.Conn, tenant: db.Id, band: str, stage: str, gap_minutes: float = 10.0
) -> dict[str, dict]:
    """The first drafts the stage's latest run already paid for and the judge accepts now, for the pages still wanted."""
    want, rows = wanted(conn, tenant, band, None)
    return kept_drafts(stored(conn, stage, gap_minutes), want, _judge(conn, rows))


def lines(got: dict) -> list[str]:
    head = {k: got[k] for k in ("replies", "refused", "pages_good", "pages_never_good")}
    return [json.dumps(x) for x in (head, *got["attempts"], {"unlisted": got["unlisted"]})]


@curriculum_app.command("draft-replay")
def draft_replay(
    stage: str = typer.Option("dev_eval", "--stage", help="The stage whose latest draft run is read back"),
    gap_minutes: float = typer.Option(
        10.0, "--gap-minutes", help="A pause this long between calls ends a run"
    ),
) -> None:
    """Judge the kept replies of the latest draft run again: which rule each page broke on each ask. Counts and rule
    names only. No model, no write."""
    with db.connect() as conn:
        conn.read_only = True
        tenant = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
        kept = stored(conn, stage, gap_minutes)
        if not kept:
            typer.echo("no kept draft reply in this stage", err=True)
            raise typer.Exit(1)
        want, rows = wanted(conn, tenant, config()["band"], None)
        out = tally(kept, want, _judge(conn, rows), {k: r["materials"] or "" for k, r in rows.items()})
    for line in lines(out):
        typer.echo(line)
