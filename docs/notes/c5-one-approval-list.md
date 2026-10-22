# C5: one approval list (goals/c5-one-approval-list.yaml)

## Verified

- **Built:** migration 20261208090000.
  - `approval_kind` and `approval_state` are rows, seeded from `vocabulary.json`.
  - `approval` is a decision that is never edited: approved, or sent back with its reason (required), by whom and when.
    A second approval by the same person as the first is refused.
  - `approval_list` covers every skill level, way of asking and parent report. It reads each first approval where it
    always was (`skill.level_approved`, `question_type_approval`, `parent_note.approved_by`). Its state is draft, sent
    back, waiting for a second approval or approved.
  - `parent_note.sent_at` is refused until the report's state is approved, which needs two approvals by two people.
- **Fresh build:** 178 levels and 74 ways of asking are listed, all approved, as before.
- **Tests:** `test_approval_list.py` 5 passed. With `test_parent_report.py` and `test_vocabulary.py`: 40 passed.

## Handoff

- **Live:** nothing. Waits on C1 to C4.
- **Screen follow-up:** one Approvals page reading `approval_list`, with "Send back" (asks for a reason) and "Approve"
  (a second approval for a report). E0's Curriculum page can write a sending back as an `approval` row.
- **Next:** C6, the consent and data register.
