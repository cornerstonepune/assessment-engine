# M1-09p — the staff preview of the educator's screens

D-076 (5 Nov 2026): the K2 educator's screens are built in the real app and shown to Nimish signed in as staff, while
the educator switch (`educator.timetable_enabled`) stays off. This is the gate that makes that possible, before any
screen. No migration.

## What changes

- `engine/w2_print/educator_gate.py`, the one rule: a route answers when the switch is on, or when the person holds an
  open grant in a role `educator.preview_roles` names (config, seed_once, `["head", "coordinator"]`).
- The timetable routes (`/timetable/day|week|period`) check it first, before any field, as before; a previewer who holds
  no class gets every class that has a timetable as her classes (`k2_day.my_classes`), since a timetable carries no child.
- The materials routes check it on every call, and a preview passes only a route that reads (a list, the catalogue,
  the reminders, the school's list, the review list); every other route counts as a write and answers "not switched
  on", as before. M1-16's `test_every_route_refuses_while_the_screens_are_off` caught this: a coordinator is a preview
  role, and the school's build writes. Which classes she may change is still the materials rule (a class she
  holds); reminders still wait for the switch alone (`materials_list.enabled`), so a preview sends nothing.

## From the code review (each fixed test first)

- The extra classes are the preview's only while switched off; once on, everyone sees only classes they hold.
- Only classes whose timetable is in force on the day asked; the grant is judged by the school's clock.
- A preview proposes no catalogue item (403 "The preview only looks"); the gate runs once per call; the switch is read
  in one place (`materials_list.enabled` reads the gate); a missing `educator.preview_roles` row previews nobody.

## Verified

- `uv run pytest -q tests/test_educator_gate.py tests/test_k2_day.py tests/test_layout.py tests/test_materials_list.py
  tests/test_materials_review.py tests/test_cli_materials.py` → 78 passed. The gate's own tests: 3 of 4 failed before
  the code (the switched-on path already worked); the review's 2 new tests failed before their fixes.
- `bin/check` → 34 passed.

## Handoff

- Next: the orchestrator grants Nimish 'head' on live. Then the screens (M1-09c) are visible to him there.
