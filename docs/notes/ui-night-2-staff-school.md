# ui-night-2-staff-school: who teaches which class, edited on a page

Nimish, 2026-10-22: "the staff table of who teaches which class and subject is edited on a Staff page, not by commands."
Goal: `goals/uxn2-staff-and-school.yaml`. Slice STA + SCH of UI part 2, stacked on `claude/ui-night-2-curriculum`. Web only,
no migration, no new table.

## Verified

- **Staff** (`/staff`): a table of people (person, role, classes they teach), the one filter row (role, a search), and on
  each row the person's classes open to checkboxes of every class a child is in, with "Save the classes". It does what
  `engine staff classes <email> G2 G3` does: a class no child is in refuses all of it, nothing changes; the rest of the
  person, their password hash among them, is kept, and no hash is ever on a page (`lib/queries-staff.ts` reads four fields).
  `app_web` already updates `config` (migration 20261021090000), so no grant changed.
- **School** (`/school`): each class, its grade, the children in it and who teaches it; a filter by grade. Reached from the
  menu's foot, "School and staff", and from each other.
- Spec `tests/u53-staff-and-school.spec.ts` (the file name must match `[sump]\d+-` or the suite never runs it).
- `bin/check` → 31 passed; `tests/test_ux_rules.py` → 7 passed (both pages are on `PageShell` and the blocks, none frozen).

## Schema follow-up (for the core track)

Subject per teacher (Ayush English, Achal Maths) has no place: the staff list is JSON in `config.app.staff` with no
`subject`, and a subject cannot be added to a JSON list without a decision on where the school keeps it. The class part is
done; no column pretends. Ayush's login `admin@cornerstoneschool.in` is an educator with no classes: a coordinator ticks
G3 and G4 for them on `/staff` once the English Grades 3 and 4 classes exist.

## Handoff

Next: Children and the class page, Question bank and Library, Approvals; English polish on #284's branch.
