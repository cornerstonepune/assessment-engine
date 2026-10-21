# ux8a-numbers-true

Nimish, 2026-10-21: "focus on the UI/UX first, on whatever we have right now for math, making sure that every screen and
every other representation is thought through well: it's clear, it's accurate, clickability is fine." Slice UX8a of the
audit in `docs/notes/ux8-every-screen.md` (#253): its findings 1–5, the numbers and statements that were untrue.

## Verified

- Measured first: `u44-numbers-true.spec.ts`, one test per finding, run on the code before the change, all six failed:
  Today's "Still waiting" summed to 30 where the line above said 1; the reader's panel did not say whose it was; a
  paper that came back said "Waiting for a teacher to approve the pack" and "· null"; a home assessment said "focus";
  Curriculum's Grade 1 row counted "1" child who answered at a Grade 2 level only; a link to another class's week showed
  nothing of why.
- After the change: `npx playwright test tests/u44-numbers-true.spec.ts tests/s4-validation-queue.spec.ts
  tests/u42-curriculum-for-the-educator.spec.ts`: 28 passed. tsc and eslint clean.
- `bin/engine done ux8a-numbers-true` (2026-10-21, on a fresh `bin/testdb fresh` database): all six of Nimish's
  sentences PROVED; "every page still holds": 292 passed (11.0 min); `bin/check`: 28 passed. NOT DONE only because
  the work is not on main or live yet. A first run on a database the suite had already filled twice failed u15 and u26:
  Today lists the first five class packs, and their own packs had fallen into "and N more". On a fresh one, as CI
  builds, both pass.

## Handoff

- **Live:** nothing yet; this pull request waits for review.
- **What changed, for an educator:**
  - Today's "Is the queue shrinking?" counts their own classes, as every line above it does.
  - Marking's "How the reader is doing" says it is every class's record. It stays the school's: the reader's trust in a
    kind of question is earned across every class (`kind_trust`), so narrowing it would misstate it.
  - A child's paper says where it stands: waiting for approval, approved and printed, with the children, came back and
    read, or withdrawn. "Teacher" there is "educator" now, as is the reason "An educator set this by hand."
  - A paper's "For" line says roll, class, week and kind in the school's words, each only when the paper has it.
  - Curriculum counts a child under the grade of the level they answered; an answer with no question behind it counts
    under its skill's own grade.
  - A link to a class's week that is not on the list says so ("no papers have been made for it" or "not one of your
    classes") and what is shown instead.
- **Tests changed:** s4's reader sentence reads "In every class, people have checked N answers the reader read." (same
  number, checked against the database as before).
- **Database:** none. No migration, no seed, no bank query.
- **Next:** UX8b, a paper named by what it tests.
