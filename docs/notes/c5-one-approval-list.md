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

## Assembled onto main (#305, 2026-10-23)

C2 to C6 were merged each into the branch below it, so none reached main; #305 merges main with all five, in order
(every commit of every slice branch contained: `git rev-list origin/claude/<branch> ^HEAD | wc -l` → 0 for each).
- Rehearsal on a copy of live (Actions → rehearse update-live, run 39886818396, head abd0b7c): migrations 1203 to 1210
  applied on live's rows; `engine past` before, after the migrations and after update-live, identical:
  evidence 1748 `f8e77132…`, states 276 `a70d7cfe…`, scored 12665 `13bf1849…`, questions 51634 `e11078c5…`, levels 178
  `3f13044d…`.
- `bin/testdb fresh` builds; this slice's migration applied a second time on it: OK.

## Handoff

- **Live:** nothing. Waits on C1 to C4.
- **Screen follow-up:** one Approvals page reading `approval_list`, with "Send back" (asks for a reason) and "Approve"
  (a second approval for a report). E0's Curriculum page can write a sending back as an `approval` row.
- **Next:** C6, the consent and data register.
