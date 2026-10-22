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

## Handoff

- **Live:** nothing. Waits on C1 to C3.
- **Not in this slice:** marking still holds answers by `kind_trust`, one rule for every subject. The two agree while a
  subject keeps the starting numbers (test). Marking by a subject's own numbers is a decision in the PR.
- **Screen follow-up:** each subject's page shows `kind_stage` (stage, checks, right of n).
- **Next:** C5, one approval list.
