# m1-09v: the staff preview is shown real materials lists, and nothing is kept (W2, gate N4)

## Verified
- `pytest -q tests/test_educator_gate.py tests/api/test_materials_routes.py tests/api/test_materials_school_routes.py
  tests/test_materials_list.py` → passed (the new preview test failed first: 403). Three materials_month tests fail on
  this machine's long-used copy with or without this change; they pass on a fresh one.
- `npx playwright test tests/m1-09-materials.spec.ts tests/m1-09-calendar.spec.ts tests/m1-09-tokens.spec.ts` → 20
  passed, twice in a row.
- `bin/check` → passed. Nothing applied live; no model call; no migration.

## The rule
- `/materials/build` and `/materials/school/build` let the staff preview through (`reads=True`). For a previewer the
  build runs inside a savepoint that is rolled back (`routes/materials.py` `unsaved`): the same code works the list out,
  and the answer is returned; nothing is kept. Everyone else builds and keeps, as before.
- A previewer may ask for any class with a timetable in force on the first day asked; others only a class they hold.
- `/materials/build` takes `group_by`, so the site uses the build's answer as it comes (an unsaved list cannot be read
  back by id).
- M1-16's `test_every_route_refuses_while_the_screens_are_off` now sets `educator.preview_roles` to none: its point is
  the switch; the preview is this branch's test.

## Handoff
- Stacked on #419 (the materials pages); retarget to main when #419 merges.
