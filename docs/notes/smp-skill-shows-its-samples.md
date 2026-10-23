# smp-skill-shows-its-samples: a skill shows its sample questions

Nimish, 2026-10-23, on an English Grade 3 skill's page: "The skill description does not have the example questions or
test questions for that level and skill. It's just showing the difficulty levels and what the description of difficulty
levels means. I was looking to have the questions also there. How will the educator approve without having sample
questions?" Goal: `goals/smp_skill_shows_its_samples.yaml`. W1 (Curriculum / approve), beside the C slices: E0's content
with the table its samples waited on (E0 note, "What waits").

## What changed

- **One additive migration**, `20261211090000_an_english_sample_is_stored_whole.sql` (numbered after PR #305's
  20261205..20261210): four new tables, `passage`, `rubric`, `english_sample` (skill, level, kind, number 1–3, the ask,
  the passage, the printed sentence, options / pairs, the right answer, other answers taken, key points, rubric) and
  `english_sample_wrong` (each likely wrong answer and the mistake it names, a real key to `misconception`). No existing
  table, column or row changes. Row security and both roles through `internal.apply_conventions()`; the website only reads.
  `skill_level_sample` (Maths, one line per example) is untouched.
- **Loader** (`engine/core/english.py::samples`): upserts the seed's passages, rubrics, samples and wrong answers; a row
  changes only when the seed's words do. It holds no approval and never touches `skill`, `skill_level` or an approval row.
  Run by `engine load` and by `engine load --settings`, which every deploy runs after live has the migration
  (deploy-engine.yml waits for it), so after the merge the samples reach live with no command from anyone.
- **The skill page**: under each level, its samples grouped by kind, three each, printed as the child sees them (the
  shared `Question` block now prints an English question: passage, ask, sentence, the box of words, or two columns to
  join), the right answer through the shared `Answers` block, and each likely wrong answer with its mistake's name. A kind
  a person reads says "a person reads every answer" and opens its rubric. None: "No sample questions yet." For an English
  skill, each level's approve button and the skill's "Approve, as <name>" / "Change the words first" sit under the samples
  (the top of the page points down to them); a Maths skill's page is as it was.

## Decided (by the orchestrator, for Nimish)

- New tables, not new columns on `skill_level_sample`; names as the seed's keys. Deploy loads them (additive, idempotent).
- The samples a level shows are those of the kinds the level uses (`skill_level_question_type`): a kind a person removes
  from a level takes its samples off the page with it.

## Verified

On a database built from this repository alone (`bin/testdb fresh`, Postgres 16 in this sandbox, main at edcef42), then this
branch's migration applied (twice: it is written to run twice), 2026-10-23:

- Tests first: `pytest tests/test_english_samples.py` before the migration → `4 failed`; after → `4 passed` (counts equal
  the seed: 2,499 samples, 253 passages, 7 rubrics, 4,366 wrong answers; a sample stored whole, its wrong answers each
  naming a mistake with a name; an approved level untouched by `load` and `load --settings`; the deploy's load adds them).
- `bin/engine load --check` → `english_sample 2499`, `english_sample_wrong 4366`, `passage 253`, `rubric 7`,
  `unchanged on a second run`. `bin/engine load --settings` → the same four counts.
- `pytest tests/test_roles.py tests/test_loaders.py tests/test_e0_english.py tests/test_english_kinds_and_samples.py
  tests/test_migration_order.py tests/test_english_samples.py` → all passed (`test_roles` holds row security and both
  roles' policies on every table, the four new ones included; the website writes none of them). One existing test
  changed on purpose: `test_a_deploy_loads_the_rows_the_engine_reads_as_settings_and_no_others` now expects the four
  sample tables beside prompt, threshold and config.
- `pytest tests/test_ux_rules.py tests/test_school_words.py` → `11 passed, 1 skipped`. `bin/engine ratchet --base
  origin/main` → `every baseline held or tightened`. `bin/check` → `31 passed`, lint clean. `npx tsc --noEmit` clean.
- Browser, 1440 px: `npx playwright test tests/u54-skill-shows-its-samples.spec.ts tests/u53-skill-name-opens-the-skill.spec.ts
  tests/e0-english.spec.ts` → `8 passed` (U54: from Approve the skills, an English Grade 3 draft's every level shows
  three samples per kind with the right answer and each wrong answer's mistake; the level's approve button below its
  samples; "Approve, as …" and "Change the words first" once, under the samples; an open kind says "a person reads every
  answer" and opens its rubric; with its samples removed, "No sample questions yet."). U53's English test now expects
  samples where it expected the sentence "No questions yet: English questions are made after this skill is approved"
  (the sentence Nimish objected to); its goal line names the new title.
- The wider list (u12, u17, u19, u23, u28, u5, u51 with the above): `28 passed, 2 failed, 6 did not run` in one session;
  the two (u17 worksheets of a Maths skill, u23 a grade's filtered rows) then passed on their own, `9 passed`. Neither
  opens an English skill. They depend on what the specs before them leave in the database; CI's fresh database decides.
- Sandbox only: this Playwright wanted a Chromium build the sandbox lacks; its path was linked to the installed one.

## Handoff

- **Live:** nothing until the merge. After it: `migrate live` adds the tables, the deploy loads the samples.
- **Before the merge:** the rehearsal on a copy of live (`rehearse update-live`, Actions → Run workflow) has NOT been run.
- **Next:** none for this goal.
- **Blocked:** nothing.
