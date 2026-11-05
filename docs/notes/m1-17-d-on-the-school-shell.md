# M1-17 brick D — the K2 pictures on the school's shell

W3, gate N10 (reading side). After #406 and #414 (the shell). No migration, no model call.

## What changed
- `/k2/*` renders inside `SchoolShell` (`app/(app)/k2/layout.tsx`, menu `lib/k2-menu.ts`: Children, then the educator's own menu): the
  school's white ground, sidebar (tabs on a phone), 12-column grid, the school's tokens for this shell alone. My own white-ground
  layout is gone. The chip and the notice use the shell's chip tokens (olive, amber and monsoon); no raw colour is left.
- A breadcrumb on every page (the shell's `Crumbs`), and a new `/k2` page: her classes, one class opens at once.
- **The gate (D-076, `educator.preview_roles`):** `POST /k2/picture` and `POST /k2/child` answer while `voice.screens_enabled` is off to a
  member of staff whose open grant is in a role the preview names; anyone else is still refused in the same words. The to-do and the
  coordinator's list (the voice reads) still wait for the switch. A preview only looks; both calls only read.

## Decided without an answer
- The preview rule is read through `educator_gate.previews` (the timetable's), on `voice.screens_enabled` (the K2 notes' switch), because
  the picture comes from the voice notes. If the K2 screens should follow `educator.timetable_enabled`, it is one line in the route.
- A previewer who holds no class reaches a class by its address: `/k2` lists the classes she holds, and a coordinator holds none. A list
  of every class for the preview needs an engine call that does not exist; not built.
- The shell's breadcrumb links are the shell's link colour (terracotta, `--link`). They are links to a class, never on a child's state.

## Verified (a local database from `bin/testdb fresh`; never live)
- Tests first: `tests/api/test_k2_routes.py::test_the_staff_preview_sees_the_picture_and_a_child_while_the_switch_is_off_and_nobody_else_does`
  failed (403) before the gate change and passes; two more hold that the to-do and the coordinator list still refuse a previewer and that a
  role the preview does not name is not the preview.
- Engine: 238 passed across the source-scanning, gate, state-naming, UX-rules, layout, types, contract and K2 suites; ruff clean; `bin/check` 34.
- Browser (voice notes, the calendar and its tokens, mine, UX rules): 42 passed. Mine now checks the shell: the sidebar marks Children,
  the breadcrumb names it, the ground is white, the app's font is unchanged on the next page, `/k2` opens a class in one tap, the tab
  bar shows on a phone. Screenshots at 1280 and 390 px in `docs/screens/m1-17/` are retaken.
- Not run: the full sharded suites (CI).

## Handoff
Next: the lowest state's words ("under half right", open point 1 of #406), the previewer's class list, and "ready next" listing
skills already practising (open point 2).
