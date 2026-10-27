# asm2-by-topic-and-checking (W3, slices S2 / S3: the assessment list and checking)

Nimish, 2026-10-26, after using the Assessments page of #324 on live: assessments "by topic", a name a teacher would say, "Check
answers" by assessment and not by last upload, and the stages as a visible sequence. Goal: `goals/asm2_by_topic_and_checking.yaml`
(`bin/engine done asm2_by_topic_and_checking`). Web only; no migration, so no rehearsal.

## What changed

- **By topic** (`/papers?view=topic`): a switch beside the list. Every topic with an assessment is a collapsed row with its count
  (`lib/queries-by-topic.ts`: one grouped query); opening one (`&t=CODE`, one at a time) reads only that topic's assessments, ten
  to a page in the database (`assessmentList(..., page)`), the stage filter applied there too through a row's signature
  (`sigOf`/`sigsFor` in `lib/assessment-steps.ts`, the one rule `actionOf` read from both sides).
- **The name rule**: `builtName` in `apps/web/lib/assessment-steps.ts`: topic · skill(s) · level · kind · class (roll if one child's)
  · day. Three or more skills are counted, levels that differ are left out; the list is under "Made of" in the opened row. An
  educator's name (`assessment_name`) wins. The words are rows (topic, skill, difficulty, grade, class); only the joining is code,
  held by `u62-assessment-steps.spec.ts`. The kind words are still `KIND_WORDS` in code (pre-existing).
- **Check answers**: the queue runs one assessment at a time, the one waiting longest first (`checkQueue` orders by the assessment's
  key, `setKeySql`, one definition now shared with the list). One line per assessment (papers waiting, answers left, spot-checks,
  oldest wait), opening into its papers (roll, child, paper, answers left, Check this). "Next paper in this assessment" after a
  paper. The flat table and "Children in this file" are gone. The card is untouched.
- **Steps** are Created, Approved, Printed, Uploaded, Read, Checked, Results in, in that order; the stage filter is in those words.

## Verified

Local database built by `bin/testdb fresh` (Postgres 16), web as the owner role (CI runs it as `app_web`):

- `bin/check` → 32 passed. `npx tsc --noEmit` (apart from the generated `LayoutProps` the sandbox lacks), `npx eslint --max-warnings 0` clean.
- `asm2-by-topic` (4), `asm2-checking` (3), `u62-assessment-steps` (13), `u63`, `p6-check-is-quick` passed.

## Handoff

- gstack could not be installed: the permission layer refused the clone. The pages were looked at in Playwright screenshots at 1440 px.
- Not looked at on live (not reachable from the session).
