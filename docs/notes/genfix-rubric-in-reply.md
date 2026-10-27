# genfix-rubric-in-reply: the first eval of english_generate, and why it gave no score

W1, steps N1 and N2 (the bank: questions made from an educator's sample). Goal: `goals/genfix_rubric_in_reply.yaml`.
Follows `docs/notes/gen-from-a-sample.md` (#337).

## The cause

Run 40469097359 (engine eval, english_generate, version 1, 2026-10-27) ended after one minute with
"english_generate output failed its schema: Additional properties are not allowed ('rubric_code' was unexpected)".

- Does a question made from a sample need a rubric? For the kinds a person marks by reading, yes: `english_check._open`
  refuses one without it. 3 of the 15 samples in the eval set are such kinds (ENG.REWRITE R_ENG_SENTENCE,
  ENG.SHORT_ANSWER R_ENG_ANSWER, ENG.SHORT_WRITE R_ENG_WRITE); the other 12 have none.
- But the rubric is not the model's to give. A question of the sample's pattern is read against the sample's rubric,
  which the educator chose and the checks passed; `generate._written` already put the sample's rubric (and passage) on
  every question, overwriting anything the model said.
- So the defect was in what was sent: the sample given to the model held `rubric_code` (null for the closed kinds,
  set for the open ones), and v1 said "in the same fields as the sample". The model did as told; the schema refused it.

## What changed

- The model is no longer sent the sample's rubric or passage code (`generate.CARRIED`); code carries both over.
- `english_generate` v2 (`supabase/seed/prompts/english_generate.v2.txt`, the same schema, Haiku 4.5) names its eight
  fields, "and no others", and says the passage and the rubric stay as the sample's. Seeded inactive. v1 kept as it was.
- A reply not in its schema's form is `llm.LLMSchemaError`. The educator's request is refused with "The writer's reply
  was not in the form we need; nothing was added."; the eval counts that sample's 5 questions as thrown away for that
  reason, and goes on to a score instead of ending.
- The engine eval workflow builds its command in `.github/eval/command.py` (tested by `tests/test_eval_command.py`):
  each purpose gets only its own options (`--review-version` parent_report only, `--jev-version` parent_review only);
  the version inputs are free text, checked to be whole numbers the seed holds, so no list goes stale.

## Verified

On a database built from this branch (`bin/testdb fresh`, Postgres 16 in this sandbox), 2026-10-27. The model is
replaced by fixed replies; the real adapter's schema check runs in the first and third tests below.

- Tests first: 5 failed (`could not be made just now (english_generate output failed its schema …)`; the eval raised
  the same; `'rubric_code' not in sample` false; no v2 row; the schema-row count), then `tests/test_generate.py` 9 passed.
- `tests/test_eval_command.py` collected with `FileNotFoundError` before the script; with it, 11 passed (with test_jev).
- `PURPOSE=english_generate VERSION=2 python3 .github/eval/command.py` → `engine eval english_generate --version 2`.
- `bin/engine done genfix_rubric_in_reply` → 5 of 5 sentences PROVED, 3 of 3 criteria PASSED; NOT DONE only because
  the live database cannot be reached from here.

## Not proven

- No model was called (no key here). v2's score is not known; it is not claimed to work and is not active.
- Whether Haiku 4.5 keeps to "no others" is what the eval measures.

## Handoff

- **Next:** after the merge and deploy, GitHub → Actions → engine eval → Run workflow on main: purpose
  `english_generate`, version `2`, review_version and jev_version empty. Record the score in DECISIONS-LOG.md; make v2
  active only if it meets `eval.english_generate.kept` (0.8).
- **Blocked:** English "Make more like this" stays switched off until that score.
