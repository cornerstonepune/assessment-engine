# C6: consent and data register (goals/c6-consent-and-data-register.yaml)

## Verified

- **Built:** migration 20261209090000.
  - `data_register` has 8 entries in a parent's words, each naming its tables. They are written from
    `supabase/seed/data_register.json` by `engine load` (`core/register.py`).
  - `consent` is given or withdrawn, with the parent's relation to the child, how, and who recorded it. It is never
    edited, carries no name, and holds a fingerprint of the register's words at the time. `consent_now` gives each
    child's latest answer and whether the register has changed since.
- **Completeness check:** every table with a `child_id`, plus `child`, `capture` and `item_result`, is named in an
  entry. A table added later that holds a child's data fails the test until the register says so.
- **Tests:** `test_data_register.py` 4 passed. The first run caught two answers in one sitting sharing a timestamp,
  so consent is now stamped with `clock_timestamp()`.

## Assembled onto main (#305, 2026-10-23)

C2 to C6 were merged each into the branch below it, so none reached main; #305 merges main with all five, in order
(every commit of every slice branch contained: `git rev-list origin/claude/<branch> ^HEAD | wc -l` → 0 for each).
- Rehearsal on a copy of live (Actions → rehearse update-live, run 39886818396, head abd0b7c): migrations 1203 to 1210
  applied on live's rows; `engine past` before, after the migrations and after update-live, identical:
  evidence 1748 `f8e77132…`, states 276 `a70d7cfe…`, scored 12665 `13bf1849…`, questions 51634 `e11078c5…`, levels 178
  `3f13044d…`.
- `bin/testdb fresh` builds; this slice's migration applied a second time on it: OK.

## Handoff

- **Live:** nothing. Waits on C1 to C5.
- **Manual:** a lawyer checks the words against the DPDP Act, 2023, and the school decides how long things are kept
  after a child leaves.
- **Screen follow-up:** a page showing the register as a parent reads it, and recording a parent's consent.
