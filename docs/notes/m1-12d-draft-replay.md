# M1-12d: why the first dev run saved 1 page of 60

## Verified
- Run #12 (draft_dev): 31 maker batches, 1 page saved, 59 without a draft, no checker called, $1.31 spent in the run.
  Source: the job log (counts only) and `packages/engine/engine/w1_bank/k2_batch.py::run` (a page failing the code checks
  is asked again up to `batch_rounds` = 2 more times): 15 + 15 + 1 batches fits.
- Now: `bin/engine curriculum draft-replay --stage dev_eval` re-judges the kept replies of the latest run and prints counts per
  rule and per ask (no model, no write, no page text); run choice `draft_replay` on the server. Tests:
  `packages/engine/tests/test_k2_replay.py`.
- A page that breaks the same rule twice in a row is not asked a third time (`k2_batch.run`); the run log prints
  `rules broken: <rule> <count>, ...; N pages not asked a third time`.

## Handoff
- Dispatch `draft_replay` (free). Its counts say which rule fails: if one of the school's locked format rules (12 words a
  step, 8 steps, 1 to 4 slips) is the cause, the prompt changes (new version, tested by replay); the rule does not.
- Not known until then: whether the rule at fault is the materials check (`uses_unlisted`, `step_word_unlisted`) or a length.
- The forecast's worst case (`up to $`) still assumes every page goes round every time; with the retry stop it is now an
  overstatement.

## Correction (M1-12e)
- The first `draft_replay` (run 16) reported `missing: 59` on every ask. That was the replay's own fault: it judged the
  reply object `{"pages": [...]}` where the run judges the list inside it, so every page read as missing. Fixed in
  `k2_replay.tally`; test `test_a_reply_in_the_prompts_own_shape_an_object_holding_the_pages_is_judged_as_the_run_judged_it`
  fails without the fix and passes with it. The real per-rule counts need the replay dispatched again (free).
