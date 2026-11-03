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
- `engine/checks/rules.json` regenerated with `engine live rules --write --url <a database built from the migrations>`: exactly 40 rules added, all on the new tables, nothing else changed (CI's `test_rules` named the same 40).
- The migration applied twice in a row on a database built from every migration: no error, no row changed the second time.

## What the migration does (additive only) — `20261225090000_people_and_enrolment.sql`

New: `campus`, `academic_year`, `school_class`, `enrolment`, `staff`, `pii.staff`, `role`, `staff_role_grant`; functions
`enrol_child()`, `pii.read_staff()`, `internal.check_role_grant()`, `internal.forbid_delete()`, `internal.refuse_grant_edit()`, `internal.people_vocabulary()`, `public.staff_of_email()`;
one nullable column `pii.child.birthday`; one `config` row `people.class_teacher_rule`. Nothing dropped, deleted or
rewritten; no existing table read differently. RLS by `internal.apply_conventions()`; the engine may read and write the new
public tables, the website may only read them, and neither may touch `pii.staff` (only `pii.read_staff()`, which writes who
asked to `access_log`). On live it writes 13 `role` rows, 1 `campus` row and 1 `config` row, nothing else.
`enrolment` and `staff_role_grant` are listed in the data register's "class" entry (a test requires it).

Reconciled with the orchestrator's extract of people-and-access (done = in this PR; left out = said so):

| Item | State |
|---|---|
| 12 roles of D-026 as rows with scope (campus / class / class and subject / child) and `may_grant` | **done** (plus `educator`, the sign-in list's own role, so the import can run: 13 rows) |
| `staff_role_grant` dated (`valid_from`/`valid_to`), `granted_by`, `override_reason`, never deleted | **done**; delete is refused by a trigger, a grant ends by `valid_to` |
| `granted_by` is a staff id | **left out**: it is the typed `--by` name; every "who" column becomes a staff id in a later slice |
| One class teacher per class at a time | **done** as a trigger that warns and stands only with a reason (a partial unique index could not allow the override). **btree_gist is not needed and is not installed** |
| D-039 (from Grade 1 a core-subject teacher is not a class teacher, both ways round) as a config row plus a check needing `override_reason` | **done**; core subjects today are NUM and ENG (the only subjects that exist; science and Hindi are added to the row when they are subjects) |
| `may_grant` enforced (only head / coordinator give a role) | **left out**: stored on each role; enforcing needs `granted_by` as a staff id |
| `public.staff_of_email(email)` → staff id (orchestrator's decision, for M1-01) | **done**: lower-case match on `pii.staff.email`, returns the id only (null if none or ambiguous), each lookup written to `access_log`; tested for a known email, an unknown one and a case difference. It is in `public`, not `internal`: neither app role has USAGE on schema `internal`, so a grant there could never work (proved by calling it as each role). Engine only; the website has no caller yet |
| `internal.grants_now(staff_id)` | **left out** (not in the card as I was given it) |
| Per-person access rules | **left out**, as P-05 says; `apply_conventions()` still gives both app roles `using (true)` |
| `staff.campus_id`, `school_class` unique on (campus, year, grade, section) | **done** |
| Child keeps only id/active; class and roll move out of `child` | **left out**: `child.section`/`roll_no` stay because every page reads them; K2 children get both |

- A child is in a class only through `enrolment`; one open row per child and one open roll number per class (partial
  unique indexes). `enrol_child()` closes the open row and opens the new one; a second call changes nothing.
- The K2 class is grade K2, section `A` by default (`--section` changes it); the children's legacy `child.section` is `K2`.

## Commands

- `engine staff import [--apply --by NAME]` — copies the 8 entries of `config` `app.staff` into the staff tables and
  grants each person the role they hold there if it is a campus-wide role (coordinator, educator); a role held for a class
  (the list's `specialist`) adds the person and says the role is left to set there. The config is read, never changed;
  password hashes are not copied.
- `engine enrol k2 CSV [--apply --by NAME] [--teacher EMAIL] [--override-reason WHY] [--match-existing] [--from DAY]`.
  Reads number, name, birthday. Any refused row (a number twice, the same child twice, a roll number that is not one,
  a birthday that is not a date or not a K2 child's age, no name) stops the whole apply and says which line.

## Not verified / open — for the orchestrator

1. **The blueprint was read only through the orchestrator's extracts** (data-architecture core keys, people-and-access
   section 1 and 2); the repo `teacher-os` itself is private and was never cloned.
2. **No class list was used.** The CSV comes on 2026-11-04. Birthdays are read day-first (25/12/2020 or 2020-12-25);
   anything else is refused, not guessed. A name is split at the first space. The school year runs April to March.
3. **`move_child` does not write enrolment.** Only K2 children have enrolments, so nothing disagrees today, but the two
   must be joined before another class is enrolled. Not done here: it changes a live path.
4. **A dry run is not completely silent**: to compare names it reads children through `pii.read_child`, which writes to
   `access_log` (who asked). Every other table is untouched.
5. The K2 class educator is whoever Nimish names with `--teacher`; the sign-in list's `classes` does not say who is the
   class educator, so it is not inferred. A core-subject conflict (D-039) is caught at apply, not in the dry run (K2 is
   pre-primary, so it does not arise for this command).
6. Local runs used a database built from every migration plus the seed, without the question bank: the neighbouring
   suites pass except `test_vocabulary::test_every_link_is_a_key_the_database_checks`, which needs items. CI has them.
7. The rehearsal on a copy of live and the load into live have not been run from here (see the pull request).

## Handoff

- Live: nothing changed. In flight: this branch. Next: rehearsal green → merge → on 2026-11-04 the dry run on the real
  list → approve → `staff import --apply`, then `enrol k2 --apply --teacher …` → the same again must add nothing.

## Review notes (independent migration review, PASS WITH NOTES) — all done in this PR

1. A grant is never edited: a `before update` trigger refuses a change to any column but `valid_to`, which may only end an open grant or shorten an ended one. Tested for role, override reason, class and start date, and for reopening.
2. `staff_of_email` proved reachable as the engine and refused to the website (`SET ROLE`), and `pii.read_staff` the same; moved to `public` because the roles have no USAGE on `internal`.
3. The PL/pgSQL variable `found` is now `ids`.
4. No DELETE for the engine on any new table. The repo's default privileges hand it DELETE on every new table, so the migration revokes it explicitly; a test deletes from each as `app_engine` and is refused. No command here genuinely needs DELETE: a child leaves a class by an enrolment ending, a person by `staff.active`.
5. D-039 fails closed: a rule whose grade is not a grade, or a class whose grade cannot be read, refuses until `override_reason` is given. Tested.
6. Known gaps, accepted: `granted_by` and `recorded_by` are typed names in non-pii tables until staff ids carry; `may_grant` is stored, not enforced; no `grants_now()`.
