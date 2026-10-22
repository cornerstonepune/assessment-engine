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
- `bin/engine done s2-the-assessment-card` (2026-10-22): 6 of 7 sentences PROVED; the seventh ("a page to retake…")
  failed only when run alone, since it leaned on the test before it. It now sets its own rows and passes alone (1 passed)
  and with the others (6 passed). Criteria: the engine's tests 16 passed; `bin/check` 30 passed; "every page still holds"
  311 passed, 3 failed: u15 (Today's class papers), u26 (the coordinator's Today), u46 (a name's colour) — the same three
  `docs/notes/ux9c-one-role.md` records as failing only on a local copy many runs old; this branch does not touch Today.
  CI's fresh copy decides. NOT DONE also because the live database did not answer from this machine.
- "Given on" checks the day against Pune's date, not the server's (`test_given.py`, 3 passed).

## Handoff

- **Live:** nothing until merged and deployed. No migration, no new table.
- **What changed:**
  - **The card** (`/papers/card`, opened from an assessment on Assessments with "Open its card"): the stages Made →
    approved for print → Given → Papers in → Read → Checked → Signed off → Results, the one it is at marked, and its next
    step. Each child's paper as proposed, with the way to the approve page where any child is changed.
  - **Given on** and **away, held for later**: the educator's word, written by the engine as a `flow_run` row (`given`,
    `absent`; `w2_print/given.py`, `POST /papers/given`, `POST /papers/absent`). The paper itself is not changed; papers
    put in without "Given on" still count as given.
  - **To photograph again**: what the newest file holding a copy lacked (the read-scan run's `lacks`), flagged on the
    card.
  - **Reading progress**: the engine writes how many pages it has read on the file's run as each copy is read
    (`inbox._progress`, its own connection); the card says "page 7 of 20, about 4 minutes left".
  - **The upload box at the top** of the card, Assessments and Marking.
- **Waits on C5/C3:** kinds of assessment as a dropdown anyone extends. The database allows four kinds
  (`sheet_instance_kind_check`); a fifth needs a table of kinds.
