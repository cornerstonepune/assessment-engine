# M0-05 — People and enrolment, first slice

Task M0-05 (roadmap card in cornerstone-platform's sister repo teacher-os; decisions D-039, D-046, D-047, D-055).
Goal: `goals/m0-05-people-enrolment.yaml`. Nimish's words on record: "All parts should just function like a well-oiled machine, right?"

## Verified

- `bin/engine done m0-05-people-enrolment` → all 7 sentences PROVED, both criteria PASSED, ends "NOT DONE" because the
  live database cannot be reached from the build container and three steps are manual (below).
- `cd packages/engine && .venv/bin/python -m pytest -q tests/test_people.py` → 7 passed, twice in a row on one database
  (the tests leave the database as they found it). Placeholder people only ("Placeholder Ann", ann@example.test,
  "Placeholder Child 07"), test database only.
- `bin/check` → 34 passed (layout against `workflows.json`, promises, ratchet, strict types, migration order, ruff).
- The migration applied twice in a row on a database built from every migration: no error, no row changed the second time.

## What the migration does (additive only) — `20261225090000_people_and_enrolment.sql`

New: `campus`, `academic_year`, `school_class`, `enrolment`, `staff`, `pii.staff`, `role`, `staff_role_grant`; functions
`enrol_child()`, `pii.read_staff()`, `internal.check_role_grant()`, `internal.people_vocabulary()`; one nullable column
`pii.child.birthday`. Nothing dropped, deleted or rewritten; no existing table read differently. RLS by
`internal.apply_conventions()`; the engine may read and write the new public tables, the website may only read them, and
neither may touch `pii.staff` (only `pii.read_staff()`, which writes who asked to `access_log`).
On live it adds 4 `role` rows and 1 `campus` row (named for the school) — the only rows it writes.

- A child is in a class only through `enrolment`; one open row per child and one open roll number per class (partial
  unique indexes). `enrol_child()` closes the open row and opens the new one; a second call with the same class and roll
  changes nothing.
- The class-teacher rule (D-039) is a trigger on `staff_role_grant`: a second holder is refused with a message that
  says why, unless `override_reason` is given, and the reason stays on the grant. A direct insert meets it too.
- **btree_gist is not needed**: "one at a time" is a partial unique index and a trigger, not a range-overlap constraint.

## Commands

- `engine staff import [--apply --by NAME]` — copies the 8 entries of `config` `app.staff` into the staff tables and
  grants each person the role they hold there. The config is read, never changed; password hashes are not copied.
- `engine enrol k2 CSV [--apply --by NAME] [--teacher EMAIL] [--override-reason WHY] [--match-existing] [--from DAY]`.
  Reads number, name, birthday. Any refused row (a number twice, the same child twice, a roll number that is not one,
  a birthday that is not a date or not a K2 child's age, no name) stops the whole apply and says which line.

## Not verified / open — for the orchestrator

1. **The blueprint was not read.** `git clone` of cornerstonepune/teacher-os asked for credentials (it is not public from
   the build container) and attaching it was denied. The shapes below were chosen from the task text and this repo and
   should be checked against `data-architecture.md`, `people-and-access.md`, `modules.md`:
   - `school_class` has `grade_code` and `section`, where `section` is the string `child.section` already carries
     ("K2"). If the blueprint wants A/B sections beside a grade, that is one more column.
   - Roles: `coordinator`, `educator`, `specialist` (the ones `people.decides` names) and `class_teacher`, labelled
     "Class educator". They are rows made by the migration and by a trigger on new schools, as the evidence kinds
     are, not yet in a `supabase/seed` file (rule 1 prefers one).
   - The academic year runs April to March (label `2026-27`), named from the `--from` day; my assumption, India's school year.
2. **No class list was used.** The CSV comes on 2026-11-04. Its date format is read day-first (25/12/2020 or 2020-12-25);
   anything else is refused, not guessed. A name is split at the first space (first / rest).
3. **`move_child` does not write enrolment.** Moving a child with the existing route still changes `child.section`
   only. Only K2 children have enrolments, so nothing disagrees today, but the two must be joined before another
   class is enrolled. Not done here: it changes a live path.
4. **A dry run is not completely silent**: to compare names it reads children through `pii.read_child`, which writes to
   `access_log` (who asked). That is kept on purpose; every other table is untouched.
5. **Per-person access rules** (who may see which class) are left out, as P-05 says.
6. The class educator for K2 is whoever Nimish names with `--teacher`; the staff list carries `classes` per person but
   does not say who is the class educator, so it is not inferred.
7. The rehearsal on a copy of live and the load into live have not been run from here (see the pull request).

## Handoff

- Live: nothing changed. In flight: this branch. Next: rehearsal green → merge → on 2026-11-04 the dry run on the real
  list → approve → `staff import --apply`, then `enrol k2 --apply --teacher …` → the same again must add nothing.
