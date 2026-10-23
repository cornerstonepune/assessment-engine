# C4: validation rules per subject and kind (goals/c4-validation-rules-per-subject-and-kind.yaml)

## Verified

- **Built:** migration 20261207090000.
  - `validation_stage`: New, Learning, Trusted and Falls back, each with its words and whether every answer goes to a
    person. These are rows, seeded from `vocabulary.json`.
  - `validation_rule`: a subject's window and bar, for all its kinds or for one. Each subject starts with
    `marking.agreement_window` and `marking.agreement_gate`, and a subject added later gets the same.
  - `kind_stage`: every kind a subject's questions hold, with its checks and its stage. It reads the checks
    `kind_trust` reads (`answer_checked`, the reader's stood answers). "Falls back" means a window was trusted once and
    the newest is not.
- **Fresh build:** every maths kind is New, because no answer there has been checked.
- **Tests:** `test_validation_stages.py` 7 passed. With `test_profiles.py`, `test_rules.py` and `test_vocabulary.py`:
  32 passed. `bin/check`: 30 passed.

## Assembled onto main (#305, 2026-10-23)

C2 to C6 were merged each into the branch below it, so none reached main; #305 merges main with all five, in order
(every commit of every slice branch contained: `git rev-list origin/claude/<branch> ^HEAD | wc -l` → 0 for each).
- Rehearsal on a copy of live (Actions → rehearse update-live, run 39886818396, head abd0b7c): migrations 1203 to 1210
  applied on live's rows; `engine past` before, after the migrations and after update-live, identical:
  evidence 1748 `f8e77132…`, states 276 `a70d7cfe…`, scored 12665 `13bf1849…`, questions 51634 `e11078c5…`, levels 178
  `3f13044d…`.
- `bin/testdb fresh` builds; this slice's migration applied a second time on it: OK.
- Found on assembly: a subject could no longer be removed (validation_rule's link to it had no on-delete; the browser
  test s43, from main, adds and removes one). Fixed at its cause by `20261210090000_a_subject_takes_its_validation_rules_with_it.sql`;
  `tests/test_validation_stages.py::test_a_subject_taken_away_takes_its_rules_with_it` failed first, passes now
  (8 passed); browser suite on abd0b7c: 347 passed.

## Handoff

- **Live:** nothing. Waits on C1 to C3.
- **Not in this slice:** marking still holds answers by `kind_trust`, one rule for every subject. The two agree while a
  subject keeps the starting numbers (test). Marking by a subject's own numbers is a decision in the PR.
- **Screen follow-up:** each subject's page shows `kind_stage` (stage, checks, right of n).
- **Next:** C5, one approval list.
