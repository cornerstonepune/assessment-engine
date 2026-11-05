# m1-13b: the curriculum screens in the school's shell, behind the educator gate (W1, gate N1, screens only)

## Verified
- Engine: `cd packages/engine && uv run pytest -q tests/test_grades.py tests/test_ux_rules.py tests/test_web_gate.py tests/test_layout.py tests/test_contract.py tests/test_educator_gate.py tests/api/test_curriculum_gate.py tests/api/test_k2_page_routes.py tests/api/test_offers_routes.py` → passed (see the pull request for the count). The gate's tests were written first and seen failing (no refusal; then, after review, a preview's writes got through).
- Browser: `cd apps/web && npx playwright test tests/m1-13-curriculum-fill.spec.ts tests/m1-13c-page-part.spec.ts tests/u51-ux-rules.spec.ts tests/u53-the-menu.spec.ts tests/m1-09-calendar.spec.ts tests/m1-09-tokens.spec.ts --reporter=line` → 41 passed (on main as of #422).
- `bin/check` → 34 passed. `npx tsc --noEmit` and `npx eslint --max-warnings 0` on the changed files → no output (clean).

## What changed
- Layout: `app/(app)/curriculum/layout.tsx` wraps the area in `SchoolShell` with `lib/curriculum-menu.ts` (Curriculum, What is filled with "Check the drafted parts" under it, Skills offered). `Chrome` now draws the shell's `Crumbs` and `Summary` and no title, tabs or tokens of its own.
- Gate (replaces the config row `curriculum.screens_enabled`, removed from the seed): the engine's page and offers routes refuse with 403 "The curriculum screens are not switched on." unless `educator_gate.open_to` (switch on, or a role `educator.preview_roles` names), through `curriculum_staff` in `engine/api/deps.py` (the two routes' copies of the staff check are gone). The pages ask `POST /curriculum/page/gate` before reading a row of their own (`mustBeOn` in `lib/curriculum-screens.ts`); not open is not found.
- A preview only looks (D-076, as the timetable and materials routes), but the review does not wait for the educators' switch (the orchestrator's decision, 5 Nov): a member of staff whose open grant is in a role named by the new config row `curriculum.review_roles` (seeded `["head", "coordinator"]`, seed_once; a missing row names nobody) may keep, edit, send back and answer offers with the educator switch off; everyone else needs the switch on, else the engine says "The preview only looks: …" and the screens show the drafts and offers with nothing to press, and say so. `POST /curriculum/page/gate` → `{reviews}` tells the pages which. `educator_gate.holds(conn, staff, key)` is the one grant query (`previews` now calls it).
- Each page and action still calls `requireStaff()` itself (`tests/test_web_gate.py`), then `mustBeOn`.

## Readings taken (simplest)
- The tabs are the menu's sub-items now; the strip of counts is the shell's `Summary`; with the offers read failing its count is left out, not shown as 0.

## Handoff
- Nimish and Akanksha need the role `head` (or `coordinator`) on live for the screens and the review to work with the educator switch off. `curriculum.review_roles` is a setting: change the list to change who reviews.
- Config row `curriculum.screens_enabled` stays on live (seed_once, unused); nothing reads it.
