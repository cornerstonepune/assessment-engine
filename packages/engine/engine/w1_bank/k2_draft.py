"""`engine curriculum draft | materials`: the run commands for K2 version 1 (goals/m1-11-k2-complete-v1.yaml).

The gaps of a K2 page are drafted in batches by a maker, judged page by page by code (`k2_batch`, `k2_format`), read by
a stronger checker that sees only the school's words, and revised once on the checker's reasons (`k2_check`); what is
drafted is recorded in the M1-05 ledger as `page_part` and `material` proposals, and the
existing `engine curriculum apply` writes them, marked drafted, into parts that are still empty. Money: every call goes
through `llm.generate(stage=...)`, so the campaign's hard stop holds; every batch prints the spend so far and the
stage's limit; `--dry-run` prints a forecast and makes no call. A real run needs `--by`: every row keeps who ran it.
"""

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field

import typer

from engine.adapters import llm, llm_budget
from engine.core import db
from engine.w1_bank import k2_batch as batch
from engine.w1_bank import k2_check, k2_shown, map_ledger
from engine.w1_bank.cli_map import BY, staff_of
from engine.w1_bank.k2_forecast import _models, _shadows, drafting_settings, forecast  # noqa: F401
from engine.w1_bank.k2_gaps import empty_parts
from engine.w1_bank.k2_upload import config, curriculum_app
from engine.w1_bank.map_agents import Proposal

Ask = Callable[[str, dict], object]
DRAFT, CHECK, SPLIT, VERSIONS = k2_check.DRAFT, k2_check.CHECK, k2_check.SPLIT, k2_check.VERSIONS
_settings = drafting_settings


@dataclass
class Report:
    forecast: str = ""
    calls: int = 0
    proposals: int = 0
    left: dict[str, str] = field(default_factory=dict)  # page → why it has no proposal
    stopped: str = ""
    lines: list[str] = field(default_factory=list)
    reused: int = 0  # pages whose first draft was read from a kept reply, not asked for
    bad_in_a_row: int = 0  # replies in a row that broke their schema
    bad_limit: int = 3


def live_ask(conn: db.Conn, stage: str) -> Ask:
    """The adapter, one stage's calls. Each call is committed at once, paid or refused: the spend record (a flow_run
    row) must survive anything that goes wrong later in the run."""

    def ask(purpose: str, variables: dict) -> object:
        try:
            return llm.generate(conn, purpose, variables, version=VERSIONS[purpose], stage=stage)
        finally:
            conn.commit()

    return ask


def wanted(
    conn: db.Conn, tenant: db.Id, band: str, limit: int | None = None
) -> tuple[dict[str, list[str]], dict]:
    """→ each K2 page with an empty text part and which parts, and every page's row, holding only the school's own words
    (a part a machine drafted earlier counts as empty). A page this maker has already drafted is not asked for again."""
    rows = {
        r["code"]: r
        for r in conn.execute(
            "select code, name, strand, materials, objective, steps, thinking, level_0, level_1, level_2, level_3"
            " from activity where tenant_id = %s and band = %s order by code",
            (tenant, band),
        ).fetchall()
    }
    for r in conn.execute(
        "select activity_code, part from activity_part_source where tenant_id = %s and source = 'drafted'",
        (tenant,),
    ).fetchall():
        if r["activity_code"] in rows:
            rows[r["activity_code"]][r["part"]] = (
                ""  # a machine's earlier words are not the school's: drafted again
            )
    done = _proposed(conn, tenant, "page_part", f"{DRAFT} v{VERSIONS[DRAFT]}")
    want = {c: empty_parts(r) for c, r in rows.items() if c not in done}
    want = {c: parts for c, parts in want.items() if parts}
    return (dict(list(want.items())[:limit]) if limit else want), rows


def _proposed(conn: db.Conn, tenant: db.Id, kind: str, proposer: str | None = None) -> set[str]:
    rows = conn.execute(
        "select subject_code from curriculum_proposal where tenant_id = %s and kind = %s and about is null"
        " and (%s::text is null or proposer = %s)",
        (tenant, kind, proposer, proposer),
    ).fetchall()
    return {r["subject_code"] for r in rows}


_block, _judge = k2_shown.block, k2_shown.judge_for  # the names the tests and the other modules know them by


def _say_call(
    conn: db.Conn, stage: str, purpose: str, size: int, say: Callable[[str], None], rep: Report
) -> None:
    rep.calls += 1
    now = llm_budget.line(llm_budget.status(conn, db.tenant_slug(), purpose, stage))
    say(f"batch {rep.calls}: {purpose} {size} {'pages' if purpose != SPLIT else 'texts'}; {now}")


def _ask(conn, ask: Ask, stage: str, purpose: str, variables: dict, size: int, say, rep: Report) -> object:
    """One call. The money running out (or being uncountable) ends the run; a reply that broke its schema was paid for
    and counts as a reply with nothing in it, so its pages go round again; too many of those in a row end the run."""
    try:
        reply = ask(purpose, variables)
        rep.bad_in_a_row = 0
    except llm.LLMSchemaError:
        reply = []
        rep.bad_in_a_row += 1
    except (
        llm.LLMError
    ) as e:  # the campaign's stop, or the vendor unable to answer: end cleanly, keep what is good
        raise batch.Stop(str(e)) from e
    _say_call(conn, stage, purpose, size, say, rep)
    if (
        rep.bad_in_a_row >= rep.bad_limit
    ):  # the same failure paid for again and again: the prompt needs a person
        raise batch.Stop(
            f"{rep.bad_in_a_row} replies in a row broke their schema; stopped, the prompt needs a person"
        )
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
    reuse: dict[str, dict] | None = None,
) -> Report:
    """`reuse` holds first drafts the maker already wrote and was paid for (kept replies the judge accepts): they are
    read as the maker's answer, once, and the checkers and the revision are asked as for any draft."""
    want, rows = wanted(conn, tenant, band, limit)
    reuse = {k: v for k, v in (reuse or {}).items() if k in want}
    shown = set(reuse)
    rep = Report(forecast=forecast(conn, stage, len(want), reused=len(reuse)))
    if dry_run or not want:
        say(rep.forecast if want else "nothing to draft: every page has every text part, or has been drafted")
        return rep
    t = _settings(conn)
    size, rounds = int(t["batch_pages"]), int(t["batch_rounds"])
    rep.bad_limit = int(t["stop_after_bad_replies"])
    raw: dict[str, dict] = {}
    examples = k2_shown.examples_of(rows)
    judge = k2_shown.judge_for(conn, rows)

    def ask_maker(keys: list[str], revise: dict | None) -> list:
        kept, keys = ([], keys) if revise else k2_check.take_kept(reuse, keys)
        got = list(kept)
        if keys:
            text = k2_shown.maker_text(rows, want, examples, keys, revise)
            got += batch.items(_ask(conn, ask, stage, DRAFT, {"pages": text}, len(keys), say, rep), "pages")
        for it in got:
            if isinstance(it, dict) and isinstance(it.get("key"), str):
                k2_check.remember(raw, it, bool(revise))
        return got

    def checker(purpose: str) -> k2_check.AskChecker:
        def ask_checker(keys: list[str], drafts: dict) -> object:
            text = "\n\n".join(k2_shown.block(rows[k], [], None, drafts[k]) for k in keys)
            return _ask(conn, ask, stage, purpose, {"pages": text}, len(keys), say, rep)

        return ask_checker

    shadows = {p: checker(p) for p in _shadows(conn)}
    res = k2_check.run(want, ask_maker, checker(CHECK), judge, size, rounds, shadows)
    _finish(conn, tenant, staff, write, stage, res, raw, shown - set(reuse), rep, say, judge.notes)  # type: ignore[attr-defined]
    return rep


def _finish(conn, tenant, staff, write, stage, res, raw, used, rep, say, notes=None) -> None:
    """Record what the run drafted and say, in counts and rule names only, how it went. `used` are the pages whose first
    draft was read from a kept reply: marked on their ledger row."""
    rep.left, rep.stopped, rep.reused = dict(res.left), res.stopped, len(used)
    for key in used & set(res.history):
        res.history[key][0]["reused"] = True
    least = map_ledger.rules(conn)["min_confidence"]
    made = k2_check.proposals(res, raw, _models(conn), least, bool(rep.stopped), stage, notes)
    rep.proposals = len(made)
    if write and made:
        map_ledger.record(conn, tenant, made, staff)
    if res.faults:  # which rule, so a run that loses its pages says why (the log is public)
        say(f"rules broken: {batch.line_of(res.faults)}; {res.stuck} pages not asked a third time")
    if notes := {k: v for k, v in (notes or {}).items() if k in res.parts}:  # advisory: the pages are kept
        say(
            f"notes on recorded pages (rules that do not hold a page back): {batch.line_of(Counter(batch.rule_of(n) for v in notes.values() for n in v))}"
        )
    if rep.reused:
        say(f"{rep.reused} first drafts read from kept replies (no maker call)")
    say(f"{rep.proposals} pages recorded, {len(rep.left)} left for a person; {rep.stopped or 'run complete'}")


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
    t = _settings(conn)
    size, rounds = int(t["batch_materials"]), int(t["batch_rounds"])
    rep.bad_limit = int(t["stop_after_bad_replies"])
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
        proposer=f"{SPLIT} v{VERSIONS[SPLIT]}", validator="code: the school's own text", problems=bad, verdict="",
        status="auto_passed" if ok else "needs_person",
        reason="every line is in the school's text (checked by code; the model gave no confidence)" if ok
        else ("no line came back" if not good and not bad else "a line is not in the school's text, or lacks a unit"),
    )  # fmt: skip


def _run(
    command: Callable[..., Report],
    stage: str,
    limit: int | None,
    dev: bool,
    dry_run: bool,
    by: str,
    tranche: bool = False,
    use_kept: bool = False,
) -> None:
    if sum([dev, tranche, limit is not None]) > 1:
        raise typer.BadParameter("give one of --dev, --tranche or --limit, not more")
    if not dry_run and not by.strip():  # before anything is read or asked: every row keeps who ran it
        raise typer.BadParameter(
            "--by is required for a real run: every row keeps who ran it (--dry-run needs none)"
        )
    cfg = config()
    with db.connect() as conn:
        tenant = db.one(conn, "select id from tenant where slug = %s", (db.tenant_slug(),))["id"]
        staff = None if dry_run else staff_of(conn, by)
        limit = int(_settings(conn)["dev_pages" if dev else "tranche_pages"]) if dev or tranche else limit
        extra = {}
        if use_kept:  # the first drafts the maker already wrote and was paid for in this stage
            from engine.w1_bank import k2_replay  # here, not above: k2_replay reads this module's judge

            extra["reuse"] = k2_replay.reusable(conn, tenant, cfg["band"], stage)
        command(
            conn,
            tenant,
            staff,
            cfg["band"],
            stage,
            live_ask(conn, stage),
            limit,
            not dry_run,
            dry_run,
            **extra,
        )


STAGE = typer.Option(..., "--stage", help="The stage of the campaign this run spends from (llm.campaigns)")
LIMIT = typer.Option(None, "--limit", help="Only the first N")
DEV = typer.Option(
    False, "--dev", help="Only the dev stage's pages: as many as the row k2.drafting names (dev_pages)"
)
DRY = typer.Option(False, "--dry-run", help="Print the forecast and make no call")


TRANCHE = typer.Option(
    False,
    "--tranche",
    help="Only the next pages not yet drafted: as many as the row k2.drafting names (tranche_pages)",
)


USE_KEPT = typer.Option(
    False,
    "--use-kept",
    help="Read a page's first draft from the kept replies of this stage when the judge accepts it: no maker call for it",
)


@curriculum_app.command("draft")
def draft_cmd(
    stage: str = STAGE,
    limit: int | None = LIMIT,
    dev: bool = DEV,
    dry_run: bool = DRY,
    by: str = BY,
    tranche: bool = TRANCHE,
    use_kept: bool = USE_KEPT,
) -> None:
    """Draft the empty text parts of K2 pages, check them, record them in the ledger (apply them with `apply`)."""
    _run(draft, stage, limit, dev, dry_run, by, tranche, use_kept)


@curriculum_app.command("materials")
def materials_cmd(
    stage: str = STAGE, limit: int | None = LIMIT, dev: bool = DEV, dry_run: bool = DRY, by: str = BY
) -> None:
    """Split the materials texts into items, check each against the school's text, record them in the ledger."""
    _run(materials, stage, limit, dev, dry_run, by)
