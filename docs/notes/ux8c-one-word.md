# ux8c-one-word

Nimish, 2026-10-21: "focus on the UI/UX first, on whatever we have right now for math, making sure that every screen and
every other representation is thought through well: it's clear, it's accurate, clickability is fine." Slice UX8c of the
audit in `docs/notes/ux8-every-screen.md` (#253): its findings 11–14 and 19–22.

## Verified

- Measured first: `u46-one-word.spec.ts`, one test per sentence, run on main's code: all five failed (Grade 2's
  Multiplication row "not taught yet" with "Mark taught"; the reports table named "waiting on a person"; the bank's
  total without what it counts; Today's "the nearest, sum (earlier paper)"; Children's "red skill" and the report card's
  "skill sets").
- After the change, with the tests it touches: `npx playwright test tests/u46-one-word.spec.ts
  tests/u40-taught-said-on-its-row.spec.ts tests/u6-report-card.spec.ts` and eleven more: all passed.
- `bin/engine done ux8c-one-word`: RESULT_DONE

## Handoff

- **Live:** nothing yet; this pull request waits for review.
- **What changed, for an educator:**
  - Curriculum: a grade's topic row says "not taught yet at this grade", true beside the panel that counts a topic taught
    when any of its skills is; its button is "Say it is taught", as the panel's.
  - Parent reports: the page lists reports "not up to date" (out of date, to approve, not written yet). It no longer
    calls a report no one has written "waiting on a person".
  - Question bank: the grade's total says it counts the skills taught in your classes, and that Curriculum counts every
    skill of the grade.
  - Today: "The reader settles a right answer by itself only on a kind of question it has earned trust on. It is trusted
    on 0 of 4 … the closest, …, needs 44 more answers where a person agrees with what it read."
  - Children's note says each colour by its own words; a child's name looks like the link it is.
  - The report card says "skill", never "skill set"; "1 question", "1 worksheet", "1 paper".
- **Tests changed:** u20 and u24 read the reports table by its new name; u40 presses "Say it is taught".
- **Database:** none.
- **Nimish to decide:** is a parent report no one has written yet a person's work (Today and the menu would count it),
  or the report-writing job's (`.github/workflows/write-reports.yml`)? The page says what it lists until then.
