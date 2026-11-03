# M0-02 — K2 curriculum upload

W1 (build the bank), gate 3 ("any topic, by rows only"), with the curriculum slice C3 beside it. Task M0-02; decisions
D-009, D-047, D-050 (Nimish: an upload, people edit it later, no signing step, keep who and when).

## Verified

- `cd packages/engine && uv run pytest -q tests/test_k2_upload.py` → 11 passed (on a fresh database built by
  `bin/testdb fresh`: every migration, then the seed). They cover: the sheet's rows read as written and every other row
  skipped with its reason; outcomes split into separate learning objectives, linked to their activity; a dry run writes
  nothing and a second upload changes nothing; every change kept with who and when and the history refuses an update;
  a word edited on the site is not written over; an empty cell never empties a field; an activity the database lacks
  is added under the next code.
- `bin/check` → 34 passed.
- `bin/engine done m0-02-k2-curriculum-upload` → every sentence PROVED, every criterion PASSED, ends "NOT DONE" because
  the live database cannot be reached from the build container and three steps are manual (below).

## What the migration does (additive only)

`20261224090000_k2_curriculum_upload.sql`: three columns on `activity` (`materials`, `level_0`, `sheet_no`), a link
table `activity_objective`, and a ledger `curriculum_edit` written by a trigger on every change to an activity or a
learning objective (who from `app.changed_by`, else the database role). No drop, no delete, no existing row touched.
GRANTs for `app_engine` and `app_web`; RLS by `internal.apply_conventions()`.

**Consequence, plainly: from this merge, editing `supabase/seed/registry.json` no longer changes any activity the
database already has.** The database is the master of the curriculum (D-050); change an activity on the site or by the
upload. The seed still adds an activity the database lacks. Proved by
`tests/test_loaders.py::test_a_seed_edit_does_not_overwrite_an_activity_the_database_has_and_an_activity_it_lacks_is_added`.
The seed-count test treats `activity` and `learning_objective` as floors now, since the upload grows them.

One change to existing behaviour, deliberately: `engine load` used to write all 2,216 activities back from
`registry.json` on every deploy. It now only adds an activity it does not have. Left as it was, the next deploy would
undo the upload and every edit a person made.

## Not verified / open

- The dry run on the real tab has not been run: the build container cannot download the tab (Google answers 401), the
  connector hands text to the model and not to a file, and the live database does not answer from here.
- The migration has not yet run on a copy of live (Actions, rehearse update-live, on this branch).
- Two column sets are read for the report only and not stored: the numbered levels (W:AB, with "is not willing" and
  "absent") and the Revised columns (AD:AI). Which of them is the school's final set of levels is Nimish's call.
- Learning objectives made from K2 outcomes carry an empty `signal`. Checked: no page and no engine code reads the
  `learning_objective` table at all (`grep` for `from|join learning_objective` finds only the seed loader and this
  upload); the `signal` the pages show is an item's, a different column. So nothing breaks, and nothing shows them yet.

## Handoff

- Live: nothing changed. In flight: this branch. Next: export the tab as CSV, run the dry run, read the counts, then
  `--apply --by <name>` once approved; run the command twice and the second must say 0 would change.
