# m1-09m: the materials pages in the educator's screens (W2, gate N4)

## Verified
- `npx playwright test tests/m1-09-materials.spec.ts` → 4 passed, twice in a row on the same database (each test starts
  from the plan). With the calendar and activity specs: see the PR.
- `pytest -q tests/test_educator_gate.py tests/test_k2_day.py tests/test_contract.py` → 28 passed.
- `bin/check` → passed. Nothing applied live; no model call; no migration.

## Choices
- One engine route, `/timetable/open`: whether her screens are open to her (the timetable's own gate), for a page that
  reads no timetable. Built for the activity page (M1-09a), moved here because this PR lands first.
- An activity's name is plain text in the list until the activity page is on main; then it becomes the link.
- Tables for rows of one kind (D-075), each the site's own `DataTable` (rule 2, `tests/test_ux_rules.py`): the class list
  grouped a table a day; the school's list and the notes paged.
- No send screen (D-076). Quantity, remove and add are plain forms (server actions), no client code.
- The staff preview changes nothing, and building a list writes: a previewer is told no list is built yet.
- The school's list and the notes are the coordinator's (`materials.consolidate_roles`); anyone else sees whose they are.
- Room for M1-16: the class list ends after its add form; the note and photograph go below it.

## Handoff
- On main after the calendar (#414); the activity page follows and turns each activity's name into a link.
