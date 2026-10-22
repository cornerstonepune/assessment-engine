# s2-the-assessment-card: one assessment, one card, Made to Results

Slice S2 of the scope Nimish locked on 2026-10-22 (`BUILD-ORDER.md` on #269, "the locked scope of 22 Oct"), built beside
the C slices because it needs no new table. Goal: `goals/s2-the-assessment-card.yaml`. W2 (N7, given out) and W3 (N8, the
reading's progress).

## Verified

- `s42-the-assessment-card.spec.ts` failed on main's code first (no card: 1 failed, 5 did not run), 2026-10-22, on a
  local copy built by `bin/testdb fresh`; passes on this branch: 6 passed.
- Engine: `cd packages/engine && uv run pytest -q tests/test_given.py tests/test_inbox.py tests/test_a_scan_read_whole.py
  tests/test_no_guessed_pages.py tests/test_upload.py tests/test_contract.py` → 35 passed. The two progress tests failed
  before the change (2 failed).

## Handoff

- **Live:** nothing until merged and deployed. No migration, no new table.
- **What changed:**
  - **The card** (`/papers/card`, opened from an assessment on Assessments with "Open its card"): the stages Made →
    approved for print → Given → Papers in → Read → Checked → Signed off → Results, the one it is at marked, and its next
    step. Each child's paper as proposed, with the way to the approve page where any child is changed.
  - **Given on** and **away, carried**: the educator's word, written by the engine as a `flow_run` row (`given`,
    `absent`; `w2_print/given.py`, `POST /papers/given`, `POST /papers/absent`). The paper itself is not changed; papers
    put in without "Given on" still count as given.
  - **To photograph again**: what the newest file holding a copy lacked (the read-scan run's `lacks`), flagged on the
    card.
  - **Reading progress**: the engine writes how many pages it has read on the file's run as each copy is read
    (`inbox._progress`, its own connection); the card says "page 7 of 20, about 4 minutes left".
  - **The upload box at the top** of the card, Assessments and Marking.
- **Waits on C5/C3:** kinds of assessment as a dropdown anyone extends. The database allows four kinds
  (`sheet_instance_kind_check`); a fifth needs a table of kinds.
