# m1-13b: the curriculum screens in the school's shell, behind the educator gate (W1, gate N1, screens only)

## Verified
- Engine: `cd packages/engine && uv run pytest -q tests/test_grades.py tests/test_ux_rules.py tests/test_web_gate.py tests/test_layout.py tests/test_contract.py tests/test_educator_gate.py tests/api/test_curriculum_gate.py tests/api/test_k2_page_routes.py tests/api/test_offers_routes.py` → 52 passed. The gate's 5 new tests were written first and seen failing (5 failed: no gate route, no refusal).
- Browser: `cd apps/web && npx playwright test tests/m1-13-curriculum-fill.spec.ts tests/m1-13c-page-part.spec.ts tests/u51-ux-rules.spec.ts tests/u53-the-menu.spec.ts tests/m1-09-calendar.spec.ts tests/m1-09-tokens.spec.ts --reporter=line` → 41 passed (on main as of #422).
- `bin/check` → 34 passed. `npx tsc --noEmit` and `npx eslint --max-warnings 0` on the changed files → no output (clean).

## What changed
- Layout: `app/(app)/curriculum/layout.tsx` wraps the area in `SchoolShell` with `lib/curriculum-menu.ts` (Curriculum, What is filled with "Check the drafted parts" under it, Skills offered). `Chrome` now draws the shell's `Crumbs` and `Summary` and no title, tabs or tokens of its own.
- Gate (replaces the config row `curriculum.screens_enabled`, removed from the seed): the engine's page and offers routes refuse with 403 "The curriculum screens are not switched on." unless `educator_gate.open_to` (switch on, or a role `educator.preview_roles` names), through `curriculum_staff` in `engine/api/deps.py` (the two routes' copies of the staff check are gone). New `POST /curriculum/page/gate` → `{open, previewing}`, which the pages ask before reading a row of their own (`mustBeOn` in `lib/curriculum-screens.ts`); not open is not found.
- Each page and action still calls `requireStaff()` itself (`tests/test_web_gate.py`), then `mustBeOn`.

## Readings taken (simplest)
- A previewer (switch off) may also Keep, Edit, Send back and answer an offer: curriculum work is the staff's own (22 Oct), and a preview that could only look would make the walk-through unusable to the one person it is shown to. The timetable and materials routes keep their rule that a preview only looks. If that should hold here too, the writes take `educator_gate.previewing` and refuse; one line each.
- The tabs are the menu's sub-items now; the strip of counts is the shell's `Summary`.

## Handoff
- Nimish needs the role `head` on live for the screens to show with the switch off.
- Config row `curriculum.screens_enabled` stays on live (seed_once, unused); nothing reads it.
