# fix-staff-by-id — who signed a people load is a staff id, never a name

Found by the architecture council gate, 2026-11-03: `engine staff import --apply --by "<name>"` and
`engine enrol k2 … --apply --by "<name>"` stored the typed text in `staff_role_grant.granted_by` and
`enrolment.recorded_by`, columns the website can read. Names stay in `pii` (CLAUDE.md rule 6; D-046). No migration: both
columns are text and now hold the staff id.

## Verified (all on a local database built from the migrations; nothing touched live)

- `bin/engine done fix-staff-by-id` → 8 sentences PROVED, 2 criteria PASSED; ends "NOT DONE" only because the one manual
  step (Nimish's load on live) is manual and live cannot be reached from the build container.
- `cd packages/engine && pytest -q tests/test_people.py tests/test_people_signer.py` → 25 passed (14 old, 11 new).
- `bin/check` → 34 passed (map, promises, strict types, ruff).
- Also green: `tests/test_staff*.py test_cli.py test_data_register.py test_roles.py test_loaders.py` → 72 passed.

## What changed

- `--by` is the signer's EMAIL. `engine/core/signer.py` looks it up through `public.staff_of_email` (engine only, lower-cases,
  logs the lookup) and the staff id, as text, is written. No match (or two) → refused in plain words that do not repeat what
  was typed, before any write, in a dry run too.
- Bootstrap: `engine staff import` may be signed by an email on the website's sign-in list (`config` `app.staff`) even
  before the staff rows exist; the id is looked up after the run has made them, in the same transaction, and the grants
  carry it. `enrol k2` has no such path: the staff must already be there.
- The same id is what `pii.read_child` writes to `access_log.actor` when a run reads a child to compare (a dry run still
  writes the fixed label "engine enrol k2 (dry run)").
- Code moved only because `people.py` was at 398 of 400 lines and `import_staff` at the complexity limit: `Report` →
  `core/report.py`, the staff-writing helpers → `core/staff_write.py`, behaviour unchanged.

## Not verified / open

1. "Two people with one email" cannot be built: `pii_staff_email_idx` is unique on (tenant, email). The case is refused
   (the function returns null) but has no test.
2. Rows already written with a typed name: none on live as far as this session knows (the load is still to come). Any that
   exist are not rewritten here.
3. Other `--by` options that write a typed name are outside the people slice and untouched — see the pull request.

## Handoff

- Live: nothing changed. Next: merge, then Nimish's load on 2026-11-04 with `--by <his email>` on both commands.
