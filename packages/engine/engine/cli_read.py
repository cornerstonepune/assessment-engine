"""W3 — reading papers and placing them on the skill graph. Its own module so `cli.py` stays one
screen per workflow, the same reason `cli_legacy.py` exists."""

import json
from pathlib import Path

import typer

from engine import db, external, reread

read_app = typer.Typer(help="W3 — read papers and place them on the skill graph", no_args_is_help=True)


@read_app.command("map")
def read_map(
    path: str,
    pages: str = typer.Option("", "--pages", help="1,2,3 — default every page"),
    mask: float = typer.Option(
        -1.0, "--mask", help="fraction of page 1's top to paint out; default masks the name band (rule 6)"
    ),
    out: str = typer.Option("", "--out", help="write the questions and matches to this json"),
) -> None:
    """Place one paper's printed questions against the skill registry, and say what fraction landed.

    Reads the questions only — no child's answer, no educator's mark — so one booklet stands for
    every child who sat that form.
    """
    want = [int(p) for p in pages.split(",") if p.strip()] if pages else None
    with db.connect() as conn:
        before = external.spend_today(conn)
        questions, matches, r, groups, by_n, conflicts = external.run(
            conn, path, want, None if mask < 0 else mask
        )
        conn.commit()
        spent = external.spend_today(conn) - before

    if not questions:
        typer.echo("  no printed questions found — nothing to place")
        raise typer.Exit(1)

    typer.echo(
        f"\n  {Path(path).name}  —  {len(questions)} printed questions on {len({q['page'] for q in questions})} pages\n"
    )
    for m in sorted(matches, key=lambda m: (int("".join(c for c in m["n"] if c.isdigit()) or 0), m["n"])):
        q = by_n.get(m["n"], {})
        mark = {"clear": "  ok  ", "arguable": " ~ask ", "none": " MISS "}[m["confidence"]]
        typer.echo(
            f"{mark} {m['n']:>4}  {(m['skill_code'] or '—'):<14} {(q.get('what_it_tests') or '')[:62]}"
        )
        if m["confidence"] == "none" and m.get("proposed_skill"):
            typer.echo(f"            proposes: {m['proposed_skill']}  ({m['reason']})")
        elif m.get("alternative_codes"):
            typer.echo(f"            or: {', '.join(m['alternative_codes'])}")

    typer.echo(
        f"\n  clear {r['clear']}   arguable {r['arguable']}   no match {r['none']}   of {r['total']}"
        f"\n  MAPPED {r['mapped']:.0%}  (clear alone {r['clear_only']:.0%})   model spend Rs {spent:.2f}"
    )
    if conflicts:
        typer.echo(
            f"\n  {len(conflicts)} question(s) read from two different pages — one of each pair is"
            "\n  invented. Kept the page that holds a run of questions, dropped the lone one:"
        )
        for c in conflicts:
            typer.echo(f"    n={c['n']}{c['part']}: kept page {c['kept']}, dropped page {c['dropped']}")

    if groups:
        typer.echo("\n  what the registry is missing, grouped:")
        for name, ns in groups:
            typer.echo(f"    {len(ns):>2} x  {name}   (questions {', '.join(str(n) for n in ns)})")

    if out:
        Path(out).write_text(json.dumps({"questions": questions, "matches": matches, "rate": r}, indent=1))
        typer.echo(f"\n  written to {out}")


@read_app.command("stability")
def read_stability(
    questions_json: str,
    runs: int = typer.Option(5, "--runs", help="how many times to re-match the same questions"),
) -> None:
    """Re-match one saved extraction N times and report how much the answer moves.

    The mapping rate swung 84-95% across four runs of one paper. Extraction is vision and dear;
    matching is text and cheap — so re-matching a SAVED extraction isolates which half is unstable,
    for a few rupees rather than a few hundred.
    """
    saved = json.loads(Path(questions_json).read_text())["questions"]
    rates, per_q, fingerprints = [], {}, []
    with db.connect() as conn:
        before = external.spend_today(conn)
        for _ in range(runs):
            matches = external.match_skills(conn, saved)
            rates.append(external.rate(matches))
            fingerprints.append(external.fingerprint(matches))
            for m in matches:
                per_q.setdefault(m["n"], []).append((m["skill_code"], m["confidence"]))
        conn.commit()
        spent = external.spend_today(conn) - before

    # A provider that serves a repeated identical request from cache returns the SAME response every
    # time, and this command would then report perfect stability having sampled once. That happened:
    # five runs came back byte-identical, billed at three input tokens, for half the cost of five
    # real calls. Perfect agreement is the symptom of a cache hit, not evidence of a steady model.
    distinct = len(set(fingerprints))
    if runs > 1 and distinct == 1:
        typer.echo(
            f"\n  NOT A MEASUREMENT — all {runs} runs returned a byte-identical response."
            "\n  That is a cached answer served repeatedly, not the model sampled independently."
            "\n  Check flow_run.tokens_in: a cached call bills almost no input."
            "\n  Re-run later, or after the prompt row changes, to get distinct samples."
        )
        raise typer.Exit(2)

    mapped = [r["mapped"] for r in rates]
    typer.echo(f"\n  {len(saved)} questions, {runs} runs of the matcher alone\n")
    typer.echo(
        f"  MAPPED  min {min(mapped):.0%}   max {max(mapped):.0%}   spread {max(mapped) - min(mapped):.0%}"
    )
    typer.echo(f"  no-match count per run: {', '.join(str(r['none']) for r in rates)}")

    unstable = {n: v for n, v in per_q.items() if len({c for c, _ in v}) > 1}
    same = len(per_q) - len(unstable)
    typer.echo(
        f"\n  {same} of {len(per_q)} questions gave the SAME skill every run"
        f"   ({same / (len(per_q) or 1):.0%} stable)"
    )
    if unstable:
        typer.echo("\n  questions whose skill changed between runs:")
        for n, v in sorted(unstable.items(), key=lambda kv: (len(kv[1][0][0] or ""), kv[0])):
            seen = {}
            for code, conf in v:
                seen[code or "—"] = seen.get(code or "—", 0) + 1
            typer.echo(
                f"    {n:>4}  "
                + "   ".join(f"{k} x{c}" for k, c in sorted(seen.items(), key=lambda kv: -kv[1]))
            )
    typer.echo(f"\n  {distinct} distinct responses across {runs} runs   model spend Rs {spent:.2f}")


@read_app.command("eval")
def read_eval_cmd(
    runs: int = typer.Option(1, "--runs", help="repeats; the reported rate is the WORST of them"),
    reader: str = typer.Option("ocr", "--reader", help="ocr | model — what does the transcribing"),
) -> None:
    """Score the active `legacy_extract` against what a person actually saw on the page.

    The gold holds answers that are WRONG on purpose. A reader that computes instead of transcribing
    scores perfectly against right answers and catastrophically here — which is exactly how v3
    regressed 24/24 to 17/24 while every mark came back "correct".
    """
    from engine import read_eval

    with db.connect() as conn:
        version = conn.execute(
            "select version from prompt where purpose = 'legacy_extract' and active"
        ).fetchone()["version"]
        before = external.spend_today(conn)
        worst, per_run = read_eval.run(conn, runs, reader=reader)
        conn.commit()
        spent = external.spend_today(conn) - before

    who = "Textract + geometry" if reader == "ocr" else f"legacy_extract v{version}"
    typer.echo(f"\n  {who}, {runs} run(s), {worst['total']} responses of gold\n")
    for _f, k, want, said, state in worst["details"]:
        typer.echo(f"    {k:>4}  page says {want:<10} reader said {said:<10} [{state}]")
    typer.echo("\n  per sheet:")
    for i, s in enumerate(worst["sheets"], 1):
        typer.echo(
            f"    {i}. {s['paper']:<16} {s['exact']:>2}/{s['total']:<3} "
            f"{s['read_exactly_right']:>6.1%}   silently wrong {s['silently_wrong']}   {s['note'][:44]}"
        )
    typer.echo(
        f"\n  read exactly right   {worst['read_exactly_right']:.1%}   ({worst['exact']}/{worst['total']})"
        f"\n  given a row at all   {worst['responses_given_a_row']:.1%}   ({worst['missing']} missing)"
        f"\n  SILENTLY WRONG       {worst['silently_wrong_rate']:.1%}   ({worst['silently_wrong']})"
        f"   <- bar is 1%; the rest went to a person"
        f"\n  wrong value          {worst['wrong_value']}"
        f"\n  wrong answer_state   {worst['state_wrong']}"
    )
    if runs > 1:
        rates = [r["read_exactly_right"] for r in per_run]
        typer.echo(f"  spread over {runs} runs  {min(rates):.1%} – {max(rates):.1%}")
    typer.echo(f"  model spend Rs {spent:.2f}\n")


@read_app.command("waiting")
def read_waiting() -> None:
    """Every answer waiting for a person, counted by the reason the ENGINE gave for it.

    This used to be a SQL query in `STATE.md` that inferred the cause from the shape of the stored
    reading — "confidence is zero, so the count must not have lined up" — and it put five different
    failures in one bucket of 86. The reader knows which branch it took and now records it, so the
    biggest class is a fact rather than an inference, and the next person to work the list does not
    have to re-derive it.
    """
    with db.connect() as conn:
        rows = conn.execute(
            # An answer the READER stood behind carries no reason, because the reading was not the
            # problem: marking sent it to a person. A "find the mistake" question asks for a
            # judgement no code can make, and that is a different fact from a reading the engine
            # could not make out — putting the two in one bucket is what this command exists to
            # stop.
            "select case"
            "   when nullif(r.raw_read::jsonb->>'why','') is not null"
            "     then r.raw_read::jsonb->>'why'"
            "   when r.raw_read::jsonb->>'answer_state' = 'written'"
            "     then 'read cleanly; the judgement is the teacher''s'"
            "   else '(read before reasons were recorded)' end as why,"
            " count(*) as n"
            " from item_result r join capture c on c.id = r.capture_id"
            " where c.superseded_by is null and r.status in ('unreadable','needs_teacher')"
            " group by 1 order by 2 desc"
        ).fetchall()
        totals = conn.execute(
            "select count(*) as all_answers,"
            " count(*) filter (where r.status in ('correct','wrong','blank')) as settled"
            " from item_result r join capture c on c.id = r.capture_id where c.superseded_by is null"
        ).fetchone()

    waiting = sum(r["n"] for r in rows)
    typer.echo(f"\n  {waiting} answers waiting for a person, of {totals['all_answers']}\n")
    # Grouped, because "3 numbers in the region for 2 answers" and "1 numbers in the region for 2
    # answers" are one problem with two shapes and reading them as nineteen rows hides that.
    counted = {}
    for r in rows:
        key = (
            "the region held a different count of numbers than the question has answers"
            if ("numbers in the region" in r["why"])
            else r["why"]
        )
        counted[key] = counted.get(key, 0) + r["n"]
    for why, n in sorted(counted.items(), key=lambda kv: -kv[1]):
        typer.echo(f"    {n:>4}  ({n / waiting:>3.0%})  {why}")
    typer.echo(
        f"\n  settled by the engine  {totals['settled']}  ({totals['settled'] / totals['all_answers']:.0%})"
    )


@read_app.command("again")
def read_again(
    paper: list[str] = typer.Option([], "--paper", help="one paper's code; default every paper"),
) -> None:
    """Read every live scan again so each unclear answer carries the reader's guess. A paper a person
    has signed off or corrected is never read again; every settled answer whose reading changed is
    named. Exits 1 if any did, or if any file could not be read."""
    with db.connect() as conn:
        out = reread.run(conn, only=paper or None)
    for e in out["errors"]:
        typer.echo(f"  {e}", err=True)
    for c in out["changed"]:
        typer.echo(
            f"  CHANGED {c['item_result']}: {c['was']} ({c['read_was']}) -> {c['now']} ({c['read_now']})"
        )
    typer.echo(
        f"  {out['read']} read · {out['missing']} missing · {out['failed']} failed · "
        f"{len(out['changed'])} settled answers changed"
    )
    if out["changed"] or out["failed"] or out["missing"]:
        raise typer.Exit(1)


@read_app.command("stencil")
def read_stencil(form: str = typer.Option("", "--form", help="one printed form; default every one")) -> None:
    """Rebuild each paper's blank page from the children who sat it, and read the blank once (ADR 0022).

    Three copies at least: one copy votes for its own handwriting, and two average into a page that
    still carries both children's answers at half strength. The copies are masked exactly as
    a page is before it is read — name band painted out, the educator's red ink inpainted — so the
    blank holds no name and no teacher's mark.
    """
    from engine import legacy, stencil
    from engine.adapters import ocr

    with db.connect() as conn:
        groups = stencil.copies(conn)
        cfg = ocr.settings(conn)
    cli = ocr.client()
    for (f, page), found in sorted(groups.items()):
        if form and f != form:
            continue
        if len(found) < 3:
            typer.echo(
                f"  {f:<14} p{page}  {len(found)} cop{'y' if len(found) == 1 else 'ies'} — too few to vote; read as before"
            )
            continue
        jpegs = []
        for src, in_file, mask in found:
            imgs = legacy.render_pages(src)
            jpegs.append(
                ocr.mask_red_pen(legacy.mask_name_band(imgs[min(in_file, len(imgs)) - 1], mask), cfg)
            )
        blank, used, inliers = stencil.build(jpegs)
        if used < 3:
            # Two copies' median is their average, and both children's writing survives it at half
            # strength; one is a child's page with their answers on it. Neither is a blank.
            stencil.drop(f, page)
            typer.echo(
                f"  {f:<14} p{page}  only {used} of {len(found)} copies aligned — no blank; read as before"
            )
            continue
        jpeg = legacy._jpeg(blank)
        read = ocr.read(jpeg, cli)
        boxes = ocr.printed_boxes(jpeg, cfg)
        stencil.save(f, page, blank, read, [list(b) for b in boxes])
        typer.echo(
            f"  {f:<14} p{page}  {used} of {len(found)} copies aligned (inliers {min(inliers)}-{max(inliers)}),"
            f" {sum(1 for w in read['words'] if not w['hand'])} printed words, {len(boxes)} boxes"
        )
