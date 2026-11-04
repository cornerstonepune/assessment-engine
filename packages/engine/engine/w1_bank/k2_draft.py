"""`engine curriculum draft | materials`: the run commands for K2 version 1 (goals/m1-11-k2-complete-v1.yaml).

The gaps of a K2 page are drafted in batches by one model and checked by another (v2 prompt rows), every reply judged
page by page (`k2_batch`); what passes is recorded in the M1-05 ledger as `page_part` and `material` proposals, and the
existing `engine curriculum apply` writes them, marked drafted, into parts that are still empty. Money: every call goes
through `llm.generate(stage=...)`, so the campaign's hard stop holds; every batch prints the spend so far and the
stage's limit; `--dry-run` prints a forecast and makes no call. A real run needs `--by`: every row keeps who ran it.
"""

import math
from collections.abc import Callable
from dataclasses import dataclass, field

import typer

from engine.adapters import llm, llm_budget
from engine.core import db
from engine.w1_bank import k2_batch as batch
from engine.w1_bank import map_ledger
from engine.w1_bank.cli_map import BY, staff_of
from engine.w1_bank.k2_gaps import PAGE_PARTS
from engine.w1_bank.k2_upload import config, curriculum_app
from engine.w1_bank.map_agents import Proposal

Ask = Callable[[str, dict], object]
DRAFT, CHECK, SPLIT = "k2_page_draft", "k2_page_validate", "k2_materials_split"
VERSION = 2  # the batched rows; v1 is one page a call and is not run
SHOWN = ("objective", "steps", "thinking", "level_0", "level_1", "level_2", "level_3")


@dataclass
class Report:
    forecast: str = ""
    calls: int = 0
    proposals: int = 0
    left: dict[str, str] = field(default_factory=dict)  # page → why it has no proposal
    stopped: str = ""
    lines: list[str] = field(default_factory=list)


def live_ask(conn: db.Conn, stage: str) -> Ask:
    """The adapter, one stage's calls. Each call is committed at once, paid or refused: the spend record (a flow_run
    row) must survive anything that goes wrong later in the run."""

    def ask(purpose: str, variables: dict) -> object:
        try:
            return llm.generate(conn, purpose, variables, version=VERSION, stage=stage)
        finally:
            conn.commit()

    return ask


def _thresholds(conn: db.Conn) -> dict[str, float]:
    rows = conn.execute(
        "select key, value from threshold where starts_with(key, 'k2.') or key = 'map.min_confidence'"
    )
    return {r["key"]: float(r["value"]) for r in rows.fetchall()}


def wanted(
    conn: db.Conn, tenant: db.Id, band: str, limit: int | None = None
) -> tuple[dict[str, list[str]], dict]:
    """→ each K2 page with an empty text part and which parts, and every page's row. A page that already has a proposal
    is not asked for again."""
    rows = {
        r["code"]: r
        for r in conn.execute(
            "select code, name, strand, materials, objective, steps, thinking, level_0, level_1, level_2, level_3"
            " from activity where tenant_id = %s and band = %s order by code",
            (tenant, band),
        ).fetchall()
    }
    done = _proposed(conn, tenant, "page_part")
    want = {c: [p for p in PAGE_PARTS if not (r[p] or "").strip()] for c, r in rows.items() if c not in done}
    want = {c: parts for c, parts in want.items() if parts}
    return (dict(list(want.items())[:limit]) if limit else want), rows


def _proposed(conn: db.Conn, tenant: db.Id, kind: str) -> set[str]:
    rows = conn.execute(
        "select subject_code from curriculum_proposal where tenant_id = %s and kind = %s and about is null",
        (tenant, kind),
    ).fetchall()
    return {r["subject_code"] for r in rows}


def _block(row: dict, parts: list[str], example: dict | None, with_draft: dict | None = None) -> str:
    wrote = [f"  {p}: {row[p].strip()}" for p in SHOWN if (row[p] or "").strip()]
    out = [f"key: {row['code']}", f"activity: {row['name']} (section: {row['strand']})"]
    out += ["the school wrote:", *wrote] if wrote else ["the school wrote nothing else for it"]
    if row["materials"].strip():
        out.append(f"materials: {row['materials'].strip()}")
    if with_draft is not None:
        out += ["the draft:", *[f"  {p}: {t}" for p, t in with_draft.items()]]
    else:
        out.append("draft: " + ", ".join(parts))
        if example:
            out.append(
                f"a page the school wrote for a similar activity: {example['name']}; steps: {example['steps'][:400]}"
            )
    return "\n".join(out)


def _example(row: dict, rows: dict) -> dict | None:
    """The first complete page of the same section: the style and length to match."""
    for r in rows.values():
        if (
            r["code"] != row["code"]
            and r["strand"] == row["strand"]
            and all((r[p] or "").strip() for p in PAGE_PARTS)
        ):
            return r
    return None


def forecast(conn: db.Conn, stage: str, pages: int, texts: int = 0) -> str:
    t = _thresholds(conn)
    size = int(t["k2.batch_pages"])
    prices = (conn.execute("select value from config where key = 'llm.prices'").fetchone() or {"value": {}})[
        "value"
    ]
    models = {
        r["purpose"]: r["model"]
        for r in conn.execute(
            "select purpose, model from prompt where version = %s and purpose = any(%s)",
            (VERSION, [DRAFT, CHECK, SPLIT]),
        ).fetchall()
    }

    def inr(purpose: str, n: int, tin: str, tout: str) -> float:
        rate = prices.get(models.get(purpose, ""), {})
        return n * (t[tin] * rate.get("in", 0) + t[tout] * rate.get("out", 0)) / 1_000_000

    cost = inr(DRAFT, pages, "k2.est_draft_in", "k2.est_draft_out") + inr(
        CHECK, pages, "k2.est_check_in", "k2.est_check_out"
    )
    cost += inr(SPLIT, texts, "k2.est_split_in", "k2.est_split_out")
    status = llm_budget.status(conn, db.tenant_slug(), DRAFT, stage)
    rate = next(iter((llm_budget.campaigns(conn) or {"-": {"inr_per_usd": 88}}).values()))["inr_per_usd"]
    calls = 2 * math.ceil(pages / size) + math.ceil(texts / int(t["k2.batch_materials"]))
    return (
        f"forecast (token counts assumed, not measured): {pages} pages and {texts} materials texts"
        f" → about {calls} calls, about ${cost / rate:.2f}; now {llm_budget.line(status)}; nothing was called"
    )


def _say_call(
    conn: db.Conn, stage: str, purpose: str, size: int, say: Callable[[str], None], rep: Report
) -> None:
    rep.calls += 1
    now = llm_budget.line(llm_budget.status(conn, db.tenant_slug(), purpose, stage))
    say(f"batch {rep.calls}: {purpose} {size} {'pages' if purpose != SPLIT else 'texts'}; {now}")


def _ask(conn, ask: Ask, stage: str, purpose: str, variables: dict, size: int, say, rep: Report) -> object:
    """One call. The money running out (or being uncountable) ends the run; a reply that broke its schema was paid for
    and counts as a reply with nothing in it, so its pages go round again."""
    try:
        reply = ask(purpose, variables)
    except llm.LLMSchemaError:
        reply = []
    except (
        llm.LLMError
    ) as e:  # the campaign's stop, or the vendor unable to answer: end cleanly, keep what is good
        raise batch.Stop(str(e)) from e
    _say_call(conn, stage, purpose, size, say, rep)
    return reply


def draft(
    conn: db.Conn,
    tenant: db.Id,
    staff: db.Id,
    band: str,
    stage: str,
    ask: Ask,
    limit: int | None = None,
    write: bool = False,
    dry_run: bool = False,
    say: Callable[[str], None] = typer.echo,
) -> Report:
    want, rows = wanted(conn, tenant, band, limit)
    rep = Report(forecast=forecast(conn, stage, len(want)))
    if dry_run or not want:
        say(rep.forecast if want else "nothing to draft: every page has every text part, or has been drafted")
        return rep
    t = _thresholds(conn)
    size, rounds = int(t["k2.batch_pages"]), int(t["k2.batch_rounds"])
    raw: dict[str, dict] = {}

    def call(keys: list[str]) -> list:
        text = "\n\n".join(_block(rows[k], want[k], _example(rows[k], rows)) for k in keys)
        got = batch.items(_ask(conn, ask, stage, DRAFT, {"pages": text}, len(keys), say, rep), "pages")
        raw.update({it["key"]: it for it in got if isinstance(it, dict) and isinstance(it.get("key"), str)})
        return got

    done = batch.run(want, call, size, rounds)
    rep.left, rep.stopped = dict(done.bad), done.stopped
    verdicts: dict[str, tuple[str, str]] = {}
    if not done.stopped:
        verdicts = _check(conn, stage, ask, done.good, rows, size, rounds, say, rep)
    made = [
        _proposal(k, parts, raw.get(k, {}), verdicts.get(k), t["map.min_confidence"], bool(done.stopped))
        for k, parts in done.good.items()
    ]
    rep.proposals = len(made)
    if write and made:
        map_ledger.record(conn, tenant, made, staff)
    say(f"{rep.proposals} pages recorded, {len(rep.left)} left for a person; {rep.stopped or 'run complete'}")
    return rep


def _check(
    conn, stage, ask, good: dict[str, dict], rows: dict, size: int, rounds: int, say, rep: Report
) -> dict:
    verdicts: dict[str, tuple[str, str]] = {}
    pending = list(good)
    for _ in range(rounds + 1):
        for i in range(0, len(pending), size):
            keys = pending[i : i + size]
            text = "\n\n".join(_block(rows[k], [], None, good[k]) for k in keys)
            try:
                reply = _ask(conn, ask, stage, CHECK, {"pages": text}, len(keys), say, rep)
            except batch.Stop as e:
                rep.stopped = str(e)
                return verdicts
            got, _bad = batch.judge_verdicts(batch.items(reply, "verdicts"), keys)
            verdicts |= got
        pending = [k for k in pending if k not in verdicts]
        if not pending:
            break
    return verdicts


def _proposal(
    key: str, parts: dict, raw: dict, verdict: tuple[str, str] | None, least: float, unchecked: bool
) -> Proposal:
    conf = raw.get("confidence")
    confidence = (
        min(max(float(conf), 0.0), 1.0)
        if isinstance(conf, int | float) and not isinstance(conf, bool)
        else 0.0
    )
    flags = [f for f in raw.get("flags") or [] if isinstance(f, str) and f.strip()]
    passed = bool(verdict) and verdict[0] == "agree" and confidence >= least and not flags
    if flags:
        reason = "flagged by the drafter: " + "; ".join(flags)
    elif unchecked or not verdict:
        reason = "not checked: the run stopped" if unchecked else "no verdict came back for it"
    elif verdict[0] != "agree":
        reason = verdict[1]
    elif confidence < least:
        reason = f"confidence {confidence:.2f} is below {least:.2f}"
    else:
        reason = verdict[1]
    return Proposal(
        kind="page_part", subject_code=key, proposal={"parts": parts, "flags": flags}, confidence=confidence,
        proposer=f"{DRAFT} v{VERSION}", validator=f"{CHECK} v{VERSION}", problems=[], verdict=verdict[0] if verdict else "",
        status="auto_passed" if passed else "needs_person", reason=reason,
    )  # fmt: skip


def materials(
    conn: db.Conn,
    tenant: db.Id,
    staff: db.Id,
    band: str,
    stage: str,
    ask: Ask,
    limit: int | None = None,
    write: bool = False,
    dry_run: bool = False,
    say: Callable[[str], None] = typer.echo,
) -> Report:
    todo = _proposed(conn, tenant, "material")
    rows = conn.execute(
        "select a.code, a.materials from activity a where a.tenant_id = %s and a.band = %s and btrim(a.materials) <> ''"
        " and not exists (select 1 from activity_material m where m.tenant_id = a.tenant_id and m.activity_code = a.code)"
        " order by a.code",
        (tenant, band),
    ).fetchall()
    text_of = {r["code"]: r["materials"] for r in rows if r["code"] not in todo}
    text_of = dict(list(text_of.items())[:limit]) if limit else text_of
    rep = Report(forecast=forecast(conn, stage, 0, len(text_of)))
    if dry_run or not text_of:
        say(rep.forecast if text_of else "nothing to split: every materials text has been split")
        return rep
    t = _thresholds(conn)
    size, rounds = int(t["k2.batch_materials"]), int(t["k2.batch_rounds"])
    final: dict[str, tuple[list, list]] = {}
    pending = list(text_of)
    for _ in range(rounds + 1):
        for i in range(0, len(pending), size):
            keys = pending[i : i + size]
            block = "\n\n".join(f"key: {k}\ntext: {text_of[k].strip()}" for k in keys)
            try:
                reply = _ask(conn, ask, stage, SPLIT, {"lists": block}, len(keys), say, rep)
            except batch.Stop as e:
                rep.stopped = str(e)
                break
            by_key = {
                it["key"]: it for it in batch.items(reply, "lists") if isinstance(it, dict) and "key" in it
            }
            for k in keys:
                if k in by_key:
                    final[k] = batch.judge_materials(by_key[k].get("items"), text_of[k])
        if rep.stopped:
            break
        pending = [k for k in pending if k not in final or final[k][1] or not final[k][0]]
        if not pending:
            break
    made = [_material_proposal(k, *final[k]) for k in text_of if k in final]
    rep.left = {k: rep.stopped or "missing from the reply" for k in text_of if k not in final}
    rep.proposals = len(made)
    if write and made:
        map_ledger.record(conn, tenant, made, staff)
    say(f"{rep.proposals} texts recorded, {len(rep.left)} left for a person; {rep.stopped or 'run complete'}")
    return rep


def _material_proposal(key: str, good: list, bad: list) -> Proposal:
    ok = bool(good) and not bad
    return Proposal(
        kind="material", subject_code=key, proposal={"items": good}, confidence=1.0,
        proposer=f"{SPLIT} v{VERSION}", validator="code: the school's own text", problems=bad, verdict="",
        status="auto_passed" if ok else "needs_person",
        reason="every line is in the school's text (checked by code; the model gave no confidence)" if ok
        else ("no line came back" if not good and not bad else "a line is not in the school's text, or lacks a unit"),
    )  # fmt: skip


def _run(command: Callable[..., Report], stage: str, limit: int | None, dry_run: bool, by: str) -> None:
    if not dry_run and not by.strip():  # before anything is read or asked: every row keeps who ran it
        raise typer.BadParameter(
            "--by is required for a real run: every row keeps who ran it (--dry-run needs none)"
        )
    cfg = config()
    with db.connect() as conn:
        tenant = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
        staff = None if dry_run else staff_of(conn, by)
        command(conn, tenant, staff, cfg["band"], stage, live_ask(conn, stage), limit, not dry_run, dry_run)


STAGE = typer.Option(..., "--stage", help="The stage of the campaign this run spends from (llm.campaigns)")
LIMIT = typer.Option(None, "--limit", help="Only the first N")
DRY = typer.Option(False, "--dry-run", help="Print the forecast and make no call")


@curriculum_app.command("draft")
def draft_cmd(stage: str = STAGE, limit: int | None = LIMIT, dry_run: bool = DRY, by: str = BY) -> None:
    """Draft the empty text parts of K2 pages, check them, record them in the ledger (apply them with `apply`)."""
    _run(draft, stage, limit, dry_run, by)


@curriculum_app.command("materials")
def materials_cmd(stage: str = STAGE, limit: int | None = LIMIT, dry_run: bool = DRY, by: str = BY) -> None:
    """Split the materials texts into items, check each against the school's text, record them in the ledger."""
    _run(materials, stage, limit, dry_run, by)
