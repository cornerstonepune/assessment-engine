# m1-09a: an activity's page in the educator's screens (W2, gate N4)

## Verified
- `npx playwright test tests/m1-09-activity.spec.ts tests/m1-09-materials.spec.ts tests/m1-09-calendar.spec.ts
  tests/m1-09-tokens.spec.ts`: see the PR.
- `bin/check`, `eslint`, `test_ux_rules.py`: see the PR. Nothing applied live; no model call; no migration; no engine change.

## Choices
- Each part is drawn by the shared page-part component (`components/page-part/part.tsx`, #422), the same as on
  /curriculum: whose words (the school's, "Drafted, check me", "Kept by a person"), the steps as bullets, how to think as
  an idea and slips with the word highlighted. This page adds only its answers (`components/educator/page-answers.tsx`)
  and its layout (the parts, then Levels 0–3 and the materials beside).
- Gate: the page asks the engine's `/timetable/open` (with #419) and is not found when closed. M1-12b's page routes are
  not gated: they are W1's and serve the curriculum screens too (orchestrator, 5 Nov).
- Who may answer (orchestrator, 5 Nov): any member of staff can Keep, Edit or Send back a drafted part, as the routes allow.
- No name on the page: a kept part says "Kept by a person", never who; a test checks the page holds no staff name. There
  is no child on it.
- The period that names an activity, and each line of the materials list, now open its page.

## Handoff
- On main after the calendar (#414), the materials (#419) and the shared page part (#422).
