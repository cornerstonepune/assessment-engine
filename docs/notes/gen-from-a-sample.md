# gen-from-a-sample: more questions like an educator's sample

Nimish, 2026-10-26: "The capability to edit a certain level in a skill by putting in the sample questions, and the
ability for the system to then generate a certain number of questions of that pattern." Goal:
`goals/gen_from_a_sample.yaml`. W1, steps N1 and N2. Part B of two, stacked on Part A (`claude/gen-retire-a-kind`,
`docs/notes/gen-retire-a-kind.md`): it reuses Part A's `english_edit.withdraw`. ADR 0006 amended.

## What changed

- **One additive migration**, `20261215090000_a_question_made_from_a_sample.sql`: `english_sample_edit` gains
  `made_from` (the sample a question was made from) and `flow_run_id` (the model's run); `english_sample_now` shows
  `made_from`; `maths_sample` (a typed Maths sum, its layout, the level's case code measured it as, the questions code
  made of it; never changed).
- **English** (`engine/w1_bank/generate.py`, routes `POST /skill/{code}/sample/more`): the prompt row `english_generate`
  v1 (`supabase/seed/prompts.json`, Haiku 4.5, a JSON schema) writes questions like one sample; each goes through
  `english_edit.check`, the same code checks as an educator's own sample (#323), and one repeating a question already
  there is thrown away too. What passes is stored as new samples saying "Made from your sample N" (`english_edit.made`),
  removable one by one (the existing Remove), and the level waits for approval. The educator is told how many were
  written, kept and thrown away, with each reason in words.
- **Maths** (`POST /skill/{code}/maths/more`): no model. Code reads "47 + 38" (in a line or in columns), measures it
  (`assess/tags.derive`, `cases.of`), and where it is a case the level holds, makes more of that case by the existing
  generator (`refill.fill_cases` with a quota); else the sum is kept as a sample and nothing is made. The level waits
  for approval; each question made can be taken out of the bank from its own page, as any.
- **How many**: the educator's, at most the row `generate.max_per_request` (20). Who: whoever may change the skill.
- **The eval** (rule 7): `engine eval english_generate` asks for 5 like each of 15 fixed samples (one per English kind,
  `supabase/seed/english_generate_gold.json`) and scores the share passing every check against
  `eval.english_generate.kept` (0.8). The prompt is seeded inactive; `engine-eval.yml` offers it.
- **The skill page**: an English sample has "Make more like this" (how many, then "Make questions like this"); a Maths
  level has "More questions like a sample" (the sum, in a line or in columns, how many).

## Decided (by this session, for Nimish)

- Maths: a sample of a case its level does not hold is kept, not added to the level as a new case. Adding a case
  changes what the level is; that is the level's words to change (the edit page), not a side effect of a sample.
- The model is Haiku 4.5, the cheapest Anthropic model priced in `llm.prices`; about ₹2 a request of 20 at those
  prices (approximately: roughly 3,000 tokens in and 4,000 out; not yet measured). Spending is already capped by
  `llm.daily_budget_inr`.
- The bar 0.8 is set before the first score; thrown-away questions are never stored, so it prices waste, not risk.

## Verified

On a database built from this branch (`bin/testdb fresh`, Postgres 16 in this sandbox, 106 migrations, then this
branch's seed), 2026-10-26. The model is replaced in the engine tests by fixed replies: what is proven is the code that
decides; no model was called (no key here).

- Tests first: `tests/test_generate.py` collected with `cannot import name 'generate'` without the module. With it,
  2 failed first (the checker reads the kind from the question; `english_edit.check` now passes it), then `5 passed`.
- The prompt as the model would get it, filled for a Medium gap question: no placeholder left (`_fill`, `{{…}}`: none).
- `bin/engine done gen_from_a_sample` → 6 of 6 sentences `PROVED`, 5 of 5 criteria `PASSED` (engine `74 passed` in
  the set, `load --check` `unchanged on a second run`, browser `10 passed`, `tsc` clean, `bin/check` `32 passed`);
  `NOT DONE` only for what is not live.
- Browser u65, u64, u55, u54, e0 → `12 passed`. Screens looked at: the Maths form, the English "Make more like this",
  the notice.
- `engine eval`'s function was at its complexity ceiling; two scorers that take only a version moved to their own
  functions (`BY_VERSION`), and its frozen numbers were written down to what it measures now (C901 14, statements 54).
- `engine/checks/rules.json` written again from the local copy: the new columns' and table's seven rules only.

## Handoff

- **Live:** nothing until both merges. Before each: the rehearsal on a copy of live (`rehearse update-live`).
- **Next:** after the deploy, run the engine eval workflow for english_generate v1, record the score in
  DECISIONS-LOG.md, and make the row active only if it meets 0.8.
- **Blocked:** English making waits on that score (no model key in this session).
