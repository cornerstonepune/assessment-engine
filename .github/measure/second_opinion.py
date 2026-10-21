"""The second reader's second opinion, measured on live before it is switched on (ADR 0091, rule 7). Run by
engine-eval.yml (purpose read_with_examples) inside the engine, appended to this branch's
packages/engine/engine/w3_read/second_reader.py, so `evaluate` below is the code under review, not the deployed one.
It writes only the flow_run rows of what the model calls spent. Counts only: never a child's name, an answer or a scan
(rule 6)."""

import json

from engine.adapters import ocr
from engine.core import db

# an answer read in the boxes of a printed paper that the box reader did not stand behind but guessed (`_groups`)
OPINION = """coalesce(r.raw_read::jsonb ->> 'why', '') <> '' and r.raw_read::jsonb ->> 'why' not like 'read as%%'
  and r.raw_read::jsonb ->> 'why' not like '%%not a number%%' and r.raw_read::jsonb ? 'box'
  and coalesce(r.raw_read::jsonb ->> 'guess', '') <> '' and coalesce(r.raw_read::jsonb ->> 'guess_by', '') = ''"""

with db.connect() as c:
    print("-- printed papers read in their boxes: what a second opinion would have asked about, per paper")
    for r in c.execute(
        "select count(distinct c.id) as papers, count(*) as answers,"
        f" count(*) filter (where {OPINION}) as box_guesses,"
        f" count(distinct (c.id, r.raw_read::jsonb ->> 'box')) filter (where {OPINION}) as calls,"
        # a person's word on it (typed, or the one-click guess) is a read_correction; marking re-marks the status after it
        f" count(*) filter (where {OPINION} and not exists (select 1 from read_correction rc where rc.item_result_id = r.id)"
        "   and r.state = 'confirmed') as box_guesses_settled_with_no_persons_word,"
        " min(c.created_at)::date as first, max(c.created_at)::date as last"
        " from item_result r join capture c on c.id = r.capture_id"
        " where c.superseded_by is null and r.raw_read::jsonb ? 'boxes'"
    ).fetchall():
        print("  " + json.dumps(dict(r), default=str))
    print("-- what one call of the second reader has cost")
    for r in c.execute(
        "select count(*) as calls, round(avg(cost_inr), 3) as avg_inr, round(max(cost_inr), 3) as max_inr,"
        " round(avg(tokens_in)) as avg_tokens_in, min(started_at)::date as first, max(started_at)::date as last"
        " from flow_run where flow = 'read_with_examples' and status = 'ok' and cost_inr is not null"
    ).fetchall():
        print("  " + json.dumps(dict(r), default=str))
    # why a call failed, today: an eval that reads nothing must say why (21 Oct: 116 of 116 calls failed, spend Rs 0)
    print("-- the second reader's calls today, by outcome")
    for r in c.execute(
        "select status, left(coalesce(error, ''), 240) as error, count(*) as n from flow_run"
        " where flow = 'read_with_examples' and started_at::date = current_date group by 1, 2 order by 3 desc limit 8"
    ).fetchall():
        print("  " + json.dumps(dict(r), default=str))
    budget = c.execute("select value from threshold where key = 'llm.daily_budget_inr'").fetchone()
    spent = c.execute("select coalesce(sum(cost_inr), 0) as n from flow_run where started_at::date = current_date").fetchone()
    print("  " + json.dumps({"daily_budget_inr": budget and budget["value"], "spent_today_inr": spent["n"]}, default=str))
    print("-- the eval: the second reader on every checked answer the box reader guessed, notebook without its paper")
    t = evaluate(c, ocr.settings(c), None, second_opinion=True)  # noqa: F821 — defined by second_reader.py, above
    c.commit()  # the flow_run rows of what it spent, and nothing else
    print("  " + json.dumps({k: v for k, v in t.items() if k != "details"}, default=str))
