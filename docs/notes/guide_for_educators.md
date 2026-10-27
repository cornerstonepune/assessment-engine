# guide_for_educators: the Guide inside the site

Goal `goals/guide_for_educators.yaml`. Nimish, 2026-10-27: "a guide page where everything is well explained through right
visuals and menu navigation ... so that people don't come to me ... how something is defined or calculated, the workflows
inside ... so that it's a transparent system." BUILD-ORDER: a cross-cutting help page; no workflow gate moves. It adds no
table, migration or engine code; it reads rows that already exist.

## Verified

- **Where it lives**: `/guide` (Start here), `/guide/<menu page>` for each of the 13 menu pages in the menu's order,
  `/guide/workflows`, `/guide/worked-out`, `/guide/words`, `/guide/report-a-problem`. Signed-in staff only (`requireStaff`).
  Reached from the menu panel's "Guide" link (`components/shell.tsx`, three lines) and the "?" in the corner of every
  `PageShell` header (`components/help-link.tsx`, which opens the guide page of the menu item the path belongs to).
- **The words are files**: `apps/web/guide/*.json`. Numbers, levels, grades, states and colours are tokens
  (`{t:key}`, `{t:key|pct}`, `{levels}`, `{level:i}`, `{state:code}`, `{colour:code}`), filled from the `threshold`,
  `difficulty`, `grade`, `child_state` and `state_colour` rows on each request (`lib/guide.ts`).
- **No drift** (`packages/engine/tests/test_guide.py`, no database, 23 tests): every menu item has a page and every page a
  menu item; every step of `workflows.json` is in `guide/steps.json`; every link resolves to a route or a guide section;
  every quoted button is written in the website's code; no digit, no threshold value in words, no level, grade, state,
  colour or subject name is typed; no jargon, no em dash, no sentence over 30 words.
- **Drawings are made, not captured**: the flow from `workflows.json`, the menu from `lib/menu.ts`, each page's layout from
  its guide file (numbered boxes, said again as a numbered list), the level ladder from `difficulty`, the states from
  `child_state` with the existing `Swatch` marks. No screenshot, no image file.
- **Changing a row changes the guide**: the browser test sets `calibration.too_easy_share` to 0.75 on the copy, sees
  "75%", and puts it back.

Commands: `cd packages/engine && uv run pytest -q tests/test_guide.py` (23 passed);
`cd apps/web && npx playwright test tests/u67-guide.spec.ts` (8 passed, desktop and 360 px);
`npx playwright test tests/u53-the-menu.spec.ts tests/u51-ux-rules.spec.ts` (12 passed); `bin/check` (32 passed);
`bin/engine done guide_for_educators`: every promise PROVED and every criterion PASSED; verdict NOT DONE only because the live
database did not answer from the build container (output in the PR).

## Handoff

- **Not confirmed from the code, so left out**: whether changing a child's level on Papers to approve remakes a paper
  already made; whether an edit to a level takes effect "from next week" (no code says so); "baseline" (the site has no
  such term; the guide uses its own words, "a check that places a child"); what the child page shows before any answer is
  checked (`firstStep` wording).
- **Found while reading, not changed** (outside this scope): Levels to review (`/skill-sets/levels`) has no menu item and no
  link from any page; the guide links to it. The "Papers to approve" menu item opens Assessments filtered to what waits.
  The `next_sheet.promote_at` row's description says "over the last two sheets"; the rule uses every signed-off answer.
  Class results' Grade column reads the first child's grade, the class page the grade most of its children are in.
  The reader's per-child floors (70/80/90/95, 10 checks, 6 readings) are numbers in `w3_read/profiles.py`, not rows.
- **Placeholders to fill**: "Report a problem or suggest something" (the feedback form had not merged); "Move a child"
  (PR #338 had not merged). Each says plainly that it is not on the site yet.
- gstack's browser was not installed: the session's permission check refused the clone. The pages were looked at with the
  pre-installed Playwright Chromium at 1440 px and 390 px instead; the phone test runs at 360 px, where CI's fonts first showed a long button label overflowing.
