# A1: sign in with Google, school accounts only

Inserted by Nimish on 2026-10-22 beside W1, gate 3 (B0–B4 untouched). Goal: `goals/a1-sign-in-with-google.yaml`.
ADR 0093.

## Verified

Run 2026-10-22 against `bin/testdb fresh` on a local Postgres 16 (CI uses 17).

- Every one of Nimish's sentences proved, and every criterion passing: `bin/engine done a1-sign-in-with-google`. All 15
  `says` PROVED; criteria PASSED (engine 54 passed; Playwright u49 + gate 23 passed; tsc and eslint clean; `bin/check`
  30 passed). It printed NOT DONE only because "the live database did not answer from here (ConnectionTimeout)". This
  branch has no migration.
- The tests catch a broken rule: with the `hd` check removed from `lib/google.ts`,
  `npx playwright test tests/u50-sign-in-with-google.spec.ts -g "Workspace"` → 1 failed. Then restored.
- The 18 specs moved from the password form to `tests/sign-in.ts`: `npx playwright test <those specs>` → 66 passed and
  1 failed. The failure is `u18 … Children finds a child`, which expects more than 2 children school-wide; run on its
  own on a fresh copy only u18's 2 exist. That depends on test order and was there before this branch. CI runs the
  whole suite.

## Handoff

- Live: nothing yet. Needs Nimish's three manual steps in the goal (Google OAuth client, Vercel env vars, his
  coordinator row).
- Open question for Nimish: his @cornerstoneschool.in address. It is not in the repository on purpose; he adds it with
  `engine staff add`.
- People on the list with a non-school email (e.g. a gmail) can no longer sign in. Their first school sign-in makes a
  new educator row, named as Google names them. Decisions already taken keep the old name.
- Next: a migration dropping `sign_in_failure` and the `sign_in.*` thresholds, once this is live.
