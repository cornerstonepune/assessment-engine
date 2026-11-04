# M1-11c — one bad reply costs one item, not the run

W1, gate N1. Goal `goals/m1-11c-one-bad-reply-costs-one-item.yaml`. First real model call, 4 Nov (map_dev, run 4): the mapping proposer
(`curriculum_map_propose` v1, Sonnet 5.5) added a field its schema forbids, `confidence_note`; the reply was refused and the whole eval
stopped after 8 paid calls (INR 4.53).

## Cause
The adapter does not constrain the vendor: the schema is appended to the prompt as text ("The JSON schema to match exactly") and the
reply is checked locally afterwards (`llm.generate`). The proposer's prompt lists six fields and never says there are no others, so a
model that wants to qualify its confidence adds a seventh. `reason` already carries that sentence, so `confidence_note` is not worth
declaring. Nothing was weakened: the schema is as strict as before.

## What was done, at the cause
- **Prompt:** `curriculum_map_propose` **v2** (same model and schema; v1 untouched, rule 2) says "exactly these six fields … no other
  field; anything else, including how sure you are and why, goes in reason". The map runs now use `--version 2`.
- **One bad reply is one item:** `propose` turns a proposer reply that broke its schema into **rejected** proposals for that one
  activity ("the proposer's reply broke its schema, so nothing is proposed for this activity", confidence 0.0, no parts) and asks the
  next. Rejected, not "needs a person", on purpose: a person approving an empty skill proposal would confirm "no skill". A checker
  reply that breaks its schema leaves that one proposal **for a person** (nothing was found wrong with it; it is just not checked).
  `model_ask` ends the run only when replies break **in a row, counted for each prompt** (so alternating prompts cannot hide a broken
  one; `k2.drafting` row, `stop_after_bad_replies`, 3, the rule the K2 drafting uses; a missing row is a plain error, not a crash
  in the middle of a failure).
- **The same trap in the batched K2 rows:** v2's items were `additionalProperties: false`, so one stray field on one page failed the
  whole reply (all four pages). **v3** (draft, check, materials; v2 left as it was) demands only the list and each item's `key`;
  the rest is described, not constrained, and judged item by item by code (`k2_batch`: a verdict of 5, items that are not a list or a
  page part that is not text are each judged bad and never crash the run; a test holds that). The top level stays strict. This is a
  deliberate move of the item checks from the schema to code, not "nothing weakened". `k2_draft` uses v3.

## The 8 calls (what is and is not recorded)
Each call leaves a `flow_run` row with tokens and cost (the failed one too: since #378 a reply that breaks its schema is still costed,
status `error`). That is INR 4.53 for the 8. **Nothing else was kept:** `engine eval` writes no ledger rows by design, so the replies of
the calls that answered were held in memory and lost when the run stopped, and the refused reply's text is not stored (only the
message naming `confidence_note`). The run printed nothing while it worked. Named, not built: have the eval print one line per
activity as it goes, so a stopped run still shows its work.

## Deploying it
Every deploy loads the settings (`engine load --settings`), so the new prompt rows (proposer v2; batched rows v3, all inactive) reach
the server's database with the engine; `map_dev` now asks for proposer v2, whose first eval is the dev run itself (rule 7).

## Not done, on purpose
Vendor-enforced structured output would make this class impossible, but it cannot be tested without a live call and the proposer's
schema uses `minimum`, `maximum` and `maxItems`, which a constrained mode may not take. It is the next option if v2 still strays.

## Verified
- `pytest tests/test_map_schema.py` → 9 failed before the code (the extra-field, missing-field and good-reply cases, the per-item path, the
  streak, the v3 rows), 9 passed after. 210 passed across the map, K2, budget, loaders, guide, layout and promise tests. `bin/check` → see the PR.

## Handoff
- Merge, deploy the engine, re-run `map_dev`. The first reply that strays again costs one activity, not the run.
